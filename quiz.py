"""
Quiz models
===========
Quiz, QuizQuestion, QuizOption, QuizAttempt

Design notes
------------
* All PKs use PostgreSQL UUID generation (``gen_random_uuid()``) and the
  ``sqlalchemy.dialects.postgresql.UUID`` column type — consistent with the
  rest of the schema.
* ``Quiz.xp_reward`` is the XP awarded for passing.  Spec default: 20.
* ``Quiz.lesson_id`` carries a UNIQUE constraint enforcing one quiz per lesson
  at the database level.  The relationship on Lesson is typed as a list
  (``lesson.quizzes``) per the spec contract; in practice it always contains
  at most one item.
* ``QuizQuestion.prompt`` is the canonical question text field (matches spec).
* ``QuizQuestion.explanation`` stores the post-answer explanation shown to
  students after submission.
* ``QuizQuestion.sort_order`` / ``QuizOption.sort_order`` maintain display
  ordering; unique constraints prevent positional collisions.
* ``QuizAttempt.perfect`` (boolean) marks a 100 % score — simpler and faster
  to query than comparing score == 100.
* ``Recommendation`` enum is explicitly named ``"recommendation"`` so
  PostgreSQL creates a stable named type rather than an anonymous one.
* All ``created_at`` columns use ``server_default`` so the DB clock is used.
* ``QuizAttempt`` has a composite index on ``(user_id, quiz_id)`` for the
  "fetch all attempts for this student on this quiz" query pattern.

Relationship naming (spec-aligned)
------------------------------------
* ``quiz.lesson``    — back_populates ``"quizzes"`` to match ``Lesson.quizzes``.
* ``quiz.questions`` — back_populates ``"quiz"``.
* ``quiz.attempts``  — back_populates ``"quiz"``.
"""
from __future__ import annotations

import enum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db


class Recommendation(str, enum.Enum):
    review   = "review"
    next     = "next"
    advanced = "advanced"


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id            = db.Column(
                        UUID(as_uuid=False),
                        primary_key=True,
                        server_default=db.text("gen_random_uuid()"),
                    )
    lesson_id     = db.Column(
                        UUID(as_uuid=False),
                        db.ForeignKey("lessons.id", ondelete="CASCADE"),
                        nullable=False,
                        unique=True,   # DB-level enforcement: one quiz per lesson.
                        index=True,
                    )
    title         = db.Column(db.String(300), nullable=False)
    # Spec: passing_score default 70 (percentage 0-100).
    passing_score = db.Column(db.Integer, nullable=False, server_default="70")
    # Spec: xp_reward default 20.
    xp_reward     = db.Column(db.Integer, nullable=False, server_default="20")
    created_at    = db.Column(
                        db.DateTime(timezone=True),
                        nullable=False,
                        server_default=db.text("now()"),
                    )

    # ── Relationships ──────────────────────────────────────────────────────
    # back_populates must equal "quizzes" — the spec-aligned list relationship on Lesson.
    lesson    = db.relationship("Lesson",    back_populates="quizzes")
    questions = db.relationship(
                    "QuizQuestion", back_populates="quiz",
                    order_by="QuizQuestion.sort_order",
                    cascade="all, delete-orphan", lazy="selectin",
                )
    attempts  = db.relationship(
                    "QuizAttempt", back_populates="quiz",
                    lazy="dynamic", cascade="all, delete-orphan",
                )

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self, include_correct: bool = False) -> dict:
        return {
            "id":            self.id,
            "lesson_id":     self.lesson_id,
            "title":         self.title,
            "passing_score": self.passing_score,
            "xp_reward":     self.xp_reward,
            "questions":     [q.to_dict(include_correct=include_correct)
                               for q in self.questions],
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Quiz {self.title!r}>"


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        db.UniqueConstraint("quiz_id", "sort_order", name="uq_question_quiz_sort_order"),
        db.Index("ix_quiz_questions_quiz", "quiz_id", "sort_order"),
    )

    id          = db.Column(
                      UUID(as_uuid=False),
                      primary_key=True,
                      server_default=db.text("gen_random_uuid()"),
                  )
    quiz_id     = db.Column(
                      UUID(as_uuid=False),
                      db.ForeignKey("quizzes.id", ondelete="CASCADE"),
                      nullable=False,
                      index=True,
                  )
    prompt      = db.Column(db.Text,        nullable=False)
    explanation = db.Column(db.Text,        nullable=True)   # shown post-submission
    sort_order  = db.Column(db.Integer,     nullable=False,  server_default="1")
    created_at  = db.Column(
                      db.DateTime(timezone=True),
                      nullable=False,
                      server_default=db.text("now()"),
                  )

    # ── Relationships ──────────────────────────────────────────────────────
    quiz    = db.relationship("Quiz",       back_populates="questions")
    options = db.relationship(
                  "QuizOption", back_populates="question",
                  order_by="QuizOption.sort_order",
                  cascade="all, delete-orphan", lazy="selectin",
              )

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self, include_correct: bool = False) -> dict:
        return {
            "id":          self.id,
            "quiz_id":     self.quiz_id,
            "prompt":      self.prompt,
            "explanation": self.explanation,
            "sort_order":  self.sort_order,
            "options":     [o.to_dict(include_correct=include_correct)
                             for o in self.options],
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<QuizQuestion quiz={self.quiz_id} order={self.sort_order}>"


class QuizOption(db.Model):
    __tablename__ = "quiz_options"
    __table_args__ = (
        db.UniqueConstraint("question_id", "sort_order", name="uq_option_question_sort_order"),
        db.Index("ix_quiz_options_question", "question_id", "sort_order"),
    )

    id          = db.Column(
                      UUID(as_uuid=False),
                      primary_key=True,
                      server_default=db.text("gen_random_uuid()"),
                  )
    question_id = db.Column(
                      UUID(as_uuid=False),
                      db.ForeignKey("quiz_questions.id", ondelete="CASCADE"),
                      nullable=False,
                      index=True,
                  )
    option_text = db.Column(db.Text,    nullable=False)
    is_correct  = db.Column(db.Boolean, nullable=False, server_default=sa.false())
    sort_order  = db.Column(db.Integer, nullable=False, server_default="1")
    created_at  = db.Column(
                      db.DateTime(timezone=True),
                      nullable=False,
                      server_default=db.text("now()"),
                  )

    # ── Relationships ──────────────────────────────────────────────────────
    question = db.relationship("QuizQuestion", back_populates="options")

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self, include_correct: bool = False) -> dict:
        data: dict = {
            "id":          self.id,
            "question_id": self.question_id,
            "option_text": self.option_text,
            "sort_order":  self.sort_order,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }
        if include_correct:
            data["is_correct"] = self.is_correct
        return data

    def __repr__(self) -> str:
        return f"<QuizOption question={self.question_id} order={self.sort_order}>"


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        # Most common access pattern: all attempts by user on a given quiz
        db.Index("ix_quiz_attempts_user_quiz", "user_id", "quiz_id"),
        # Used in the badge check (count passing attempts by user)
        db.Index("ix_quiz_attempts_user_passed", "user_id", "passed"),
    )

    id          = db.Column(
                      UUID(as_uuid=False),
                      primary_key=True,
                      server_default=db.text("gen_random_uuid()"),
                  )
    user_id     = db.Column(
                      UUID(as_uuid=False),
                      db.ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False,
                      index=True,
                  )
    quiz_id     = db.Column(
                      UUID(as_uuid=False),
                      db.ForeignKey("quizzes.id", ondelete="CASCADE"),
                      nullable=False,
                      index=True,
                  )
    # Denormalized for convenient analytics without joining quizzes → lessons
    lesson_id   = db.Column(
                      UUID(as_uuid=False),
                      db.ForeignKey("lessons.id", ondelete="CASCADE"),
                      nullable=False,
                      index=True,
                  )
    score           = db.Column(db.Integer, nullable=False)           # 0–100
    passed          = db.Column(db.Boolean, nullable=False)
    perfect         = db.Column(db.Boolean, nullable=False, server_default=sa.false())
    answers         = db.Column(db.JSON,    nullable=False, default=dict)  # {question_id: option_id}
    recommendation  = db.Column(
                          db.Enum(Recommendation, name="recommendation"),
                          nullable=False,
                          default=Recommendation.next,
                          server_default=Recommendation.next.value,
                      )
    xp_awarded      = db.Column(db.Integer, nullable=False, server_default="0")
    created_at      = db.Column(
                          db.DateTime(timezone=True),
                          nullable=False,
                          server_default=db.text("now()"),
                      )

    # ── Relationships ──────────────────────────────────────────────────────
    quiz   = db.relationship("Quiz",   back_populates="attempts")
    user   = db.relationship("User",   back_populates="quiz_attempts")
    lesson = db.relationship("Lesson", foreign_keys=[lesson_id])

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "user_id":        self.user_id,
            "quiz_id":        self.quiz_id,
            "lesson_id":      self.lesson_id,
            "score":          self.score,
            "passed":         self.passed,
            "perfect":        self.perfect,
            "answers":        self.answers,
            "recommendation": self.recommendation.value,
            "xp_awarded":     self.xp_awarded,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<QuizAttempt user={self.user_id} quiz={self.quiz_id} score={self.score}>"
