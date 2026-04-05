"""
STEMQuest — Gamification Service

Handles:
  - Idempotent XP awards via PointsTransaction.idempotency_key
  - Badge unlocking (one badge per user, idempotent via UniqueConstraint)
  - Streak updates (daily, based on UTC date objects — NOT ISO strings)
  - Adaptive learning recommendation from quiz score
  - Leaderboard assembly (students only, admins excluded)
  - Gamification summary for current user

FIELD MAPPING (service → model)
--------------------------------
PointsTransaction : amount        (not ``points``)
Badge             : slug          (not ``criteria``), title (not ``name``)
UserBadge         : awarded_at    (not ``earned_at``)
UserStreak        : last_activity_date  → native db.Date (Python ``date`` object, not string)

SAVEPOINT ISOLATION
-------------------
_award_points() and _award_badge() use SQLAlchemy nested transactions
(db.session.begin_nested() → SAVEPOINT on PostgreSQL / SQLite) so that an
IntegrityError on a duplicate key rolls back only the single INSERT and not
the entire outer transaction.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models.gamification import PointsTransaction, Badge, UserBadge, UserStreak
from ..models.user import User, UserRole
from ..models.quiz import Recommendation
from ..utils.helpers import new_id, utcnow

log = logging.getLogger(__name__)

# ── Adaptive thresholds ────────────────────────────────────────────────────────
REVIEW_THRESHOLD   = 50   # score < 50  → review
ADVANCED_THRESHOLD = 85   # score >= 85 → advanced
# 50 <= score < 85 → next

# ── Point values ──────────────────────────────────────────────────────────────
XP_LESSON_COMPLETE = 20
XP_QUIZ_PASS       = 30
XP_PERFECT_BONUS   = 50
XP_COURSE_COMPLETE = 100
XP_SIGNUP_BONUS    = 10


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _award_points(user_id: str, amount: int, reason: str, key: str) -> bool:
    """
    Insert a PointsTransaction only if the idempotency_key has never been used.

    Uses a SAVEPOINT so that a duplicate-key IntegrityError rolls back only
    this single INSERT without poisoning the outer session.

    Returns True if XP was newly awarded, False if the key already existed.
    """
    existing = PointsTransaction.query.filter_by(idempotency_key=key).first()
    if existing:
        return False

    tx = PointsTransaction(
        id=new_id(),
        user_id=user_id,
        amount=amount,          # model field: amount (not points)
        reason=reason,
        idempotency_key=key,
        created_at=utcnow(),
    )
    db.session.add(tx)
    try:
        sp = db.session.begin_nested()   # SAVEPOINT
        db.session.flush()
        sp.commit()
        return True
    except IntegrityError:
        sp.rollback()
        return False


def _award_badge(user_id: str, badge_id: str) -> bool:
    """
    Award a badge to the user.

    Uses a SAVEPOINT so that a UniqueConstraint violation on (user_id, badge_id)
    does not roll back the outer transaction.

    Returns True if newly awarded, False if already held.
    """
    existing = UserBadge.query.filter_by(user_id=user_id, badge_id=badge_id).first()
    if existing:
        return False

    ub = UserBadge(
        id=new_id(),
        user_id=user_id,
        badge_id=badge_id,
        awarded_at=utcnow(),    # model field: awarded_at (not earned_at)
        created_at=utcnow(),
    )
    db.session.add(ub)
    try:
        sp = db.session.begin_nested()   # SAVEPOINT
        db.session.flush()
        sp.commit()
        return True
    except IntegrityError:
        sp.rollback()
        return False


def _update_streak(user_id: str) -> UserStreak:
    """
    Update (or create) the UserStreak record for today's UTC date.

    IMPORTANT: last_activity_date is a native db.Date column.
    We compare Python ``date`` objects — NOT ISO strings.

    - Same day activity  → no change to streak count
    - Consecutive day   → streak + 1
    - Gap > 1 day       → reset to 1

    Returns the updated (not yet committed) UserStreak.
    """
    today     = date.today()                      # Python date object, not string
    yesterday = today - timedelta(days=1)

    streak = UserStreak.query.filter_by(user_id=user_id).first()

    if streak is None:
        streak = UserStreak(
            id=new_id(),
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
            last_activity_date=today,             # native date object
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.session.add(streak)
        return streak

    # last_activity_date may be a Python date or a datetime.date from the DB driver
    last = streak.last_activity_date
    if last == today:
        return streak   # already recorded activity today — no change

    if last == yesterday:
        streak.current_streak += 1
    else:
        streak.current_streak = 1   # gap — reset

    streak.longest_streak     = max(streak.longest_streak, streak.current_streak)
    streak.last_activity_date = today   # native date object
    streak.updated_at         = utcnow()
    return streak


def _badge_by_slug(slug: str) -> Badge | None:
    """Lookup a badge by its machine-readable slug. Model field: slug (not criteria)."""
    return Badge.query.filter_by(slug=slug).first()


def _total_xp(user_id: str) -> int:
    """Sum all PointsTransaction.amount rows for a user. Field: amount (not points)."""
    result = db.session.query(
        func.coalesce(func.sum(PointsTransaction.amount), 0)   # amount, not points
    ).filter(PointsTransaction.user_id == user_id).scalar()
    return int(result)


def _check_xp_milestone_badges(user_id: str) -> list[dict]:
    """Award XP milestone badges and return any newly earned ones."""
    new_badges: list[dict] = []
    total = _total_xp(user_id)
    for slug, threshold in [("xp_100", 100), ("xp_500", 500)]:
        if total >= threshold:
            b = _badge_by_slug(slug)          # slug (not criteria)
            if b and _award_badge(user_id, b.id):
                new_badges.append(b.to_dict())
    return new_badges


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_adaptive_recommendation(score: int) -> tuple[Recommendation, str]:
    """Return (Recommendation enum, human-readable advice string)."""
    if score < REVIEW_THRESHOLD:
        return (
            Recommendation.review,
            "Your score suggests reviewing the lesson material before moving on.",
        )
    if score >= ADVANCED_THRESHOLD:
        return (
            Recommendation.advanced,
            "Excellent work! You are ready for more advanced content.",
        )
    return (
        Recommendation.next,
        "Good job! Continue to the next lesson to keep progressing.",
    )


def reward_signup(user_id: str) -> None:
    """
    Award the one-time signup XP bonus and the Early Adopter badge.
    Idempotent — safe to call even if the user already has the bonus.
    Does NOT commit; caller is responsible for the final commit.
    """
    _award_points(
        user_id, XP_SIGNUP_BONUS, "Welcome to STEMQuest!", f"signup_{user_id}"
    )
    badge = _badge_by_slug("signup")          # slug (not criteria)
    if badge:
        _award_badge(user_id, badge.id)


def reward_lesson_complete(
    user_id: str, lesson_id: str, course_id: str, xp: int = XP_LESSON_COMPLETE
) -> dict:
    """
    Award XP for completing a lesson and update the daily streak.

    Returns {"xp_awarded": int, "new_badges": [badge_dict], "streak": streak_dict}.
    Does NOT commit; caller commits after course-completion check.
    """
    key     = f"lesson_complete_{user_id}_{lesson_id}"
    awarded = _award_points(user_id, xp, "Lesson completed", key)

    new_badges: list[dict] = []
    streak = _update_streak(user_id)

    # Badge: First Steps — first lesson ever
    badge_first = _badge_by_slug("first_lesson")
    if badge_first and _award_badge(user_id, badge_first.id):
        new_badges.append(badge_first.to_dict())

    # Badge: Week Warrior — 7-day streak
    if streak.current_streak >= 7:
        badge_streak = _badge_by_slug("streak_7")
        if badge_streak and _award_badge(user_id, badge_streak.id):
            new_badges.append(badge_streak.to_dict())

    # XP milestone badges
    new_badges.extend(_check_xp_milestone_badges(user_id))

    return {
        "xp_awarded": xp if awarded else 0,
        "new_badges": new_badges,
        "streak":     streak.to_dict(),
    }


def reward_course_complete(user_id: str, course_id: str) -> dict:
    """
    Award XP for completing an entire course.

    Returns {"xp_awarded": int, "new_badges": [badge_dict]}.
    Does NOT commit; caller commits.
    """
    key     = f"course_complete_{user_id}_{course_id}"
    awarded = _award_points(user_id, XP_COURSE_COMPLETE, "Course completed!", key)

    new_badges: list[dict] = []
    badge = _badge_by_slug("course_complete")
    if badge and _award_badge(user_id, badge.id):
        new_badges.append(badge.to_dict())

    new_badges.extend(_check_xp_milestone_badges(user_id))

    return {
        "xp_awarded": XP_COURSE_COMPLETE if awarded else 0,
        "new_badges": new_badges,
    }


def reward_quiz(
    user_id: str, quiz_id: str, score: int, passed: bool, perfect: bool
) -> dict:
    """
    Award XP for a quiz attempt (idempotent per quiz_id per user).

    Does NOT commit; caller commits after persisting the QuizAttempt row.
    Returns {"xp_awarded": int, "new_badges": [badge_dict]}.
    """
    xp_awarded  = 0
    new_badges: list[dict] = []

    if passed:
        key_pass = f"quiz_pass_{user_id}_{quiz_id}"
        if _award_points(user_id, XP_QUIZ_PASS, f"Passed quiz (score {score}%)", key_pass):
            xp_awarded += XP_QUIZ_PASS

    if perfect:
        key_perfect = f"quiz_perfect_{user_id}_{quiz_id}"
        if _award_points(user_id, XP_PERFECT_BONUS, "Perfect score bonus!", key_perfect):
            xp_awarded += XP_PERFECT_BONUS
            badge_perfect = _badge_by_slug("perfect_score")
            if badge_perfect and _award_badge(user_id, badge_perfect.id):
                new_badges.append(badge_perfect.to_dict())

    # Badge: Quiz Champion — 5 or more passing attempts
    from ..models.quiz import QuizAttempt
    pass_count = (
        QuizAttempt.query.filter_by(user_id=user_id, passed=True).count()
        + (1 if passed else 0)   # +1 because current attempt not yet committed
    )
    if pass_count >= 5:
        badge_champ = _badge_by_slug("quiz_passes")
        if badge_champ and _award_badge(user_id, badge_champ.id):
            new_badges.append(badge_champ.to_dict())

    new_badges.extend(_check_xp_milestone_badges(user_id))

    return {
        "xp_awarded": xp_awarded,
        "new_badges": new_badges,
    }


def award_points_admin(user_id: str, amount: int, reason: str, idempotency_key: str) -> bool:
    """
    Public wrapper used by the admin grant-points route.
    Commits the transaction.
    Returns True if XP was newly awarded.
    """
    awarded = _award_points(user_id, amount, reason, idempotency_key)
    db.session.commit()
    return awarded


def get_summary(user_id: str) -> dict:
    """
    Return the full gamification summary for a student dashboard.
    Admins are excluded from rank calculation.
    """
    from ..models.enrollment import Enrollment

    total_xp = _total_xp(user_id)
    streak   = UserStreak.query.filter_by(user_id=user_id).first()
    badges   = (
        UserBadge.query
        .filter_by(user_id=user_id)
        .join(Badge)
        .all()
    )
    enrollments = Enrollment.query.filter_by(user_id=user_id, is_active=True).count()

    # Rank: position among all students sorted by total XP descending.
    # PointsTransaction.amount (not .points) is the correct column.
    student_ids = db.session.query(User.id).filter_by(role=UserRole.student)
    user_totals = (
        db.session.query(
            PointsTransaction.user_id,
            func.sum(PointsTransaction.amount).label("total"),   # amount, not points
        )
        .filter(PointsTransaction.user_id.in_(student_ids))
        .group_by(PointsTransaction.user_id)
        .order_by(func.sum(PointsTransaction.amount).desc())     # amount, not points
        .all()
    )

    rank = len(user_totals) + 1   # default: last place if user has 0 XP
    for pos, row in enumerate(user_totals, start=1):
        if row.user_id == user_id:
            rank = pos
            break

    return {
        "total_xp":       total_xp,
        "rank":           rank,
        "current_streak": streak.current_streak if streak else 0,
        "longest_streak": streak.longest_streak if streak else 0,
        "badge_count":    len(badges),
        "badges":         [ub.to_dict() for ub in badges],
        "enrollments":    enrollments,
    }


def get_leaderboard(limit: int = 20) -> list[dict]:
    """
    Return top-N students by total XP.
    Admins are excluded.  Tied scores preserve insertion order.
    Uses PointsTransaction.amount (not .points).
    """
    student_ids = db.session.query(User.id).filter_by(role=UserRole.student)

    rows = (
        db.session.query(
            PointsTransaction.user_id,
            func.sum(PointsTransaction.amount).label("total_xp"),   # amount, not points
        )
        .filter(PointsTransaction.user_id.in_(student_ids))
        .group_by(PointsTransaction.user_id)
        .order_by(func.sum(PointsTransaction.amount).desc())         # amount, not points
        .limit(limit)
        .all()
    )

    result = []
    for rank, row in enumerate(rows, start=1):
        user = User.query.get(row.user_id)
        if not user:
            continue
        streak      = UserStreak.query.filter_by(user_id=row.user_id).first()
        badge_count = UserBadge.query.filter_by(user_id=row.user_id).count()
        result.append({
            "rank":        rank,
            "user_id":     row.user_id,
            "name":        user.name,
            "avatar":      user.avatar,
            "total_xp":    int(row.total_xp),
            "badge_count": badge_count,
            "streak":      streak.current_streak if streak else 0,
        })

    return result
