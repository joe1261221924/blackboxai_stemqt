"""
STEMQuest — CLI commands

  flask db-init         — create all tables (development only; use flask db upgrade in prod)
  flask seed            — seed demo accounts, courses, badges, and leaderboard data
  flask seed-db         — alias for seed (matches README docs)
  flask create-admin EMAIL NAME PASSWORD  — create or promote a user to admin
"""
from __future__ import annotations

import click
from flask import Flask


def register_commands(app: Flask) -> None:

    # ── db-init ────────────────────────────────────────────────────────────────

    @app.cli.command("db-init")
    def db_init():
        """Create all database tables (development shortcut; prefer flask db upgrade)."""
        from .extensions import db
        db.create_all()
        click.echo("All tables created.")

    # ── seed / seed-db ─────────────────────────────────────────────────────────

    def _run_seed() -> None:  # noqa: PLR0914
        from .extensions import db, bcrypt
        from .models.user        import User, UserRole
        from .models.course      import Course, Difficulty
        from .models.module      import Module
        from .models.lesson      import Lesson
        from .models.enrollment  import Enrollment
        from .models.gamification import PointsTransaction, Badge, UserBadge, UserStreak
        from .models.quiz        import Quiz, QuizQuestion, QuizOption
        from .utils.helpers      import new_id, utcnow, make_initials

        click.echo("Seeding demo data …")

        # ── Users ──────────────────────────────────────────────────────────────
        def _upsert_user(email: str, name: str, password: str, role: UserRole) -> User:
            u = User.query.filter_by(email=email).first()
            if u:
                return u
            pw = bcrypt.generate_password_hash(password).decode("utf-8")
            u = User(
                id=new_id(), email=email, name=name, password_hash=pw,
                role=role, avatar=make_initials(name),
                is_active=True, email_verified=True,
                created_at=utcnow(), updated_at=utcnow(),
            )
            db.session.add(u)
            return u

        student = _upsert_user("student@demo.test", "Demo Student", "password123", UserRole.student)
        admin   = _upsert_user("admin@demo.test",   "Demo Admin",   "password123", UserRole.admin)
        alice   = _upsert_user("alice@demo.test",   "Alice Chen",   "password123", UserRole.student)
        bob     = _upsert_user("bob@demo.test",     "Bob Smith",    "password123", UserRole.student)
        carlos  = _upsert_user("carlos@demo.test",  "Carlos Rivera","password123", UserRole.student)
        db.session.flush()

        # ── Badges ─────────────────────────────────────────────────────────────
        # slug is the machine-readable lock identifier; title is the display name.
        badge_defs = [
            dict(slug="signup",          title="Early Adopter",
                 description="Joined STEMQuest in the early days.",
                 points_required=None),
            dict(slug="first_lesson",    title="First Steps",
                 description="Completed your first lesson.",
                 points_required=None),
            dict(slug="quiz_passes",     title="Quiz Whiz",
                 description="Passed 5 or more quizzes.",
                 points_required=None),
            dict(slug="perfect_score",   title="Perfectionist",
                 description="Scored 100% on a quiz.",
                 points_required=None),
            dict(slug="streak_7",        title="Week Warrior",
                 description="Maintained a 7-day learning streak.",
                 points_required=None),
            dict(slug="xp_100",          title="Century Club",
                 description="Earned your first 100 XP.",
                 points_required=100),
            dict(slug="xp_500",          title="High Achiever",
                 description="Earned 500 XP in total.",
                 points_required=500),
            dict(slug="course_complete", title="Graduate",
                 description="Completed an entire course.",
                 points_required=None),
        ]
        badge_map: dict[str, Badge] = {}
        for bd in badge_defs:
            existing = Badge.query.filter_by(slug=bd["slug"]).first()
            if existing:
                badge_map[bd["slug"]] = existing
            else:
                b = Badge(id=new_id(), **bd)
                db.session.add(b)
                badge_map[bd["slug"]] = b
        db.session.flush()

        # ── Courses ────────────────────────────────────────────────────────────
        def _upsert_course(slug: str, **kwargs) -> Course:
            c = Course.query.filter_by(slug=slug).first()
            if c:
                return c
            c = Course(
                id=new_id(), slug=slug,
                instructor_id=admin.id,
                currency="USD",
                created_at=utcnow(), updated_at=utcnow(),
                **kwargs,
            )
            db.session.add(c)
            return c

        courses_def = [
            # ── Free ──────────────────────────────────────────────────────────
            dict(slug="intro-to-python",
                 title="Introduction to Python",
                 description="Learn Python fundamentals through interactive exercises. "
                              "Perfect for beginners with no prior coding experience.",
                 is_premium=False, price=0, published=True, category="Programming",
                 difficulty=Difficulty.beginner,
                 tags=["python", "programming", "beginner"],
                 total_lessons=4, estimated_hours=3),
            dict(slug="math-for-stem",
                 title="Essential Math for STEM",
                 description="Build a solid foundation in algebra, statistics, and "
                              "calculus concepts required for science and engineering.",
                 is_premium=False, price=0, published=True, category="Mathematics",
                 difficulty=Difficulty.beginner,
                 tags=["math", "algebra", "statistics"],
                 total_lessons=4, estimated_hours=4),
            # ── Premium ───────────────────────────────────────────────────────
            dict(slug="data-science-fundamentals",
                 title="Data Science Fundamentals",
                 description="Master data analysis, visualization, and machine learning "
                              "basics using Python, Pandas, and Scikit-learn.",
                 is_premium=True, price=49.99, published=True, category="Data Science",
                 difficulty=Difficulty.intermediate,
                 tags=["data science", "python", "ml"],
                 total_lessons=4, estimated_hours=8),
            dict(slug="robotics-and-arduino",
                 title="Robotics & Arduino Engineering",
                 description="Design and build autonomous robots using Arduino "
                              "microcontrollers, sensors, and servo motors.",
                 is_premium=True, price=59.99, published=True, category="Engineering",
                 difficulty=Difficulty.intermediate,
                 tags=["robotics", "arduino", "engineering"],
                 total_lessons=4, estimated_hours=10),
        ]
        courses: dict[str, Course] = {}
        for cd in courses_def:
            c = _upsert_course(**cd)
            courses[cd["slug"]] = c
        db.session.flush()

        # ── Modules, Lessons, Quizzes ──────────────────────────────────────────
        def _upsert_module(course: Course, title: str, sort_order: int, desc: str = "") -> Module:
            m = Module.query.filter_by(course_id=course.id, sort_order=sort_order).first()
            if m:
                return m
            m = Module(
                id=new_id(), course_id=course.id, title=title,
                description=desc, sort_order=sort_order, created_at=utcnow(),
            )
            db.session.add(m)
            return m

        def _upsert_lesson(
            module: Module, title: str, sort_order: int, content_body: str,
            summary: str = "", xp: int = 20,
            difficulty: Difficulty = Difficulty.beginner,
        ) -> Lesson:
            le = Lesson.query.filter_by(module_id=module.id, sort_order=sort_order).first()
            if le:
                return le
            le = Lesson(
                id=new_id(), module_id=module.id, course_id=module.course_id,
                title=title, summary=summary, content_body=content_body,
                difficulty_level=difficulty, xp_reward=xp, sort_order=sort_order,
                published=True, created_at=utcnow(),
            )
            db.session.add(le)
            return le

        def _upsert_quiz(lesson: Lesson, title: str, questions: list) -> Quiz | None:
            # Use a direct DB query rather than the dynamic relationship property
            # to avoid stale identity-map state during flush cycles.
            existing_quiz = Quiz.query.filter_by(lesson_id=lesson.id).first()
            if existing_quiz:
                return existing_quiz
            quiz = Quiz(
                id=new_id(), lesson_id=lesson.id, title=title,
                passing_score=70, xp_reward=30, created_at=utcnow(),
            )
            db.session.add(quiz)
            db.session.flush()
            for q_i, qd in enumerate(questions):
                q = QuizQuestion(
                    id=new_id(), quiz_id=quiz.id,
                    prompt=qd["prompt"],
                    explanation=qd.get("explanation"),
                    sort_order=q_i + 1, created_at=utcnow(),
                )
                db.session.add(q)
                db.session.flush()
                for o_i, od in enumerate(qd["options"]):
                    db.session.add(QuizOption(
                        id=new_id(), question_id=q.id,
                        option_text=od["text"], is_correct=od.get("correct", False),
                        sort_order=o_i + 1, created_at=utcnow(),
                    ))
            return quiz

        # Python course
        py  = courses["intro-to-python"]
        pm1 = _upsert_module(py,  "Python Basics",       1, "Variables, types, control flow")
        pm2 = _upsert_module(py,  "Functions & Modules", 2, "Defining functions, importing modules")
        pl1 = _upsert_lesson(pm1, "Variables and Data Types",    1,
                              "Python has dynamic typing. Variables are created on assignment.\n\n"
                              "```python\nname = 'Alice'\nage = 30\nprice = 9.99\n```",
                              summary="Learn Python variables")
        pl2 = _upsert_lesson(pm1, "Control Flow: if/for/while", 2,  # noqa: F841
                              "```python\nfor i in range(5):\n    if i % 2 == 0:\n        print(i)\n```",
                              summary="Conditionals and loops")
        pl3 = _upsert_lesson(pm2, "Defining Functions",          1,
                              "```python\ndef greet(name: str) -> str:\n    return f'Hello, {name}!'\n```",
                              summary="Writing reusable functions", xp=25)
        pl4 = _upsert_lesson(pm2, "Importing Modules",           2,  # noqa: F841
                              "```python\nimport math\nprint(math.sqrt(16))\n```",
                              summary="Using Python's ecosystem", xp=25)
        db.session.flush()

        _upsert_quiz(pl1, "Variables & Types Quiz", [
            {"prompt": "What is the output of: x = 5; print(type(x))?",
             "options": [{"text": "<class 'int'>",   "correct": True},
                         {"text": "<class 'str'>",   "correct": False},
                         {"text": "<class 'float'>", "correct": False}]},
            {"prompt": "Which of these creates a string in Python?",
             "options": [{"text": '"hello"', "correct": True},
                         {"text": "42",      "correct": False},
                         {"text": "True",    "correct": False}]},
        ])
        _upsert_quiz(pl3, "Functions Quiz", [
            {"prompt": "What keyword defines a function in Python?",
             "options": [{"text": "def",      "correct": True},
                         {"text": "func",     "correct": False},
                         {"text": "function", "correct": False}]},
            {"prompt": "What does 'return' do in a function?",
             "options": [{"text": "Sends a value back to the caller", "correct": True},
                         {"text": "Prints the value",                 "correct": False},
                         {"text": "Stops the program",               "correct": False}]},
        ])

        # Math course
        math  = courses["math-for-stem"]
        mm1   = _upsert_module(math, "Algebra Foundations", 1, "Equations, inequalities")
        mm2   = _upsert_module(math, "Statistics Basics",   2, "Mean, median, distributions")
        ml1   = _upsert_lesson(mm1, "Linear Equations",    1,
                                "A linear equation: ax + b = c.\n\nSolve: 2x + 3 = 11\n→ x = 4",
                                summary="Solving linear equations")
        ml2   = _upsert_lesson(mm1, "Functions and Graphs", 2,  # noqa: F841
                                "f(x) = 2x + 1. For x=3: f(3) = 7",
                                summary="Understanding functions")
        ml3   = _upsert_lesson(mm2, "Mean, Median, Mode",  1,
                                "Mean: average. Median: middle value. Mode: most frequent.",
                                summary="Descriptive statistics")
        ml4   = _upsert_lesson(mm2, "Standard Deviation",  2,  # noqa: F841
                                "Low SD = clustered near mean. High SD = widely spread.",
                                summary="Spread and variability", xp=25)
        db.session.flush()

        _upsert_quiz(ml1, "Linear Equations Quiz", [
            {"prompt": "Solve: 3x - 6 = 9",
             "options": [{"text": "x = 5", "correct": True},
                         {"text": "x = 3", "correct": False},
                         {"text": "x = 1", "correct": False}]},
        ])
        _upsert_quiz(ml3, "Statistics Quiz", [
            {"prompt": "What is the mean of [2, 4, 6, 8]?",
             "options": [{"text": "5", "correct": True},
                         {"text": "4", "correct": False},
                         {"text": "6", "correct": False}]},
        ])

        # Data Science course
        ds   = courses["data-science-fundamentals"]
        dm1  = _upsert_module(ds, "Python for Data Science",  1)
        dm2  = _upsert_module(ds, "Machine Learning Basics",  2)
        dl1  = _upsert_lesson(dm1, "NumPy & Pandas",          1,
                               "```python\nimport pandas as pd\ndf = pd.read_csv('data.csv')\n```",
                               xp=30, difficulty=Difficulty.intermediate)
        dl2  = _upsert_lesson(dm1, "Data Visualization",      2,  # noqa: F841
                               "```python\nimport matplotlib.pyplot as plt\nplt.plot([1,2,3],[4,5,6])\n```",
                               xp=30, difficulty=Difficulty.intermediate)
        dl3  = _upsert_lesson(dm2, "Linear Regression",       1,
                               "y = mx + b. Fit with sklearn's LinearRegression.",
                               xp=35, difficulty=Difficulty.intermediate)
        dl4  = _upsert_lesson(dm2, "Classification with sklearn", 2,  # noqa: F841
                               "Decision trees split data on feature thresholds.",
                               xp=35, difficulty=Difficulty.intermediate)
        db.session.flush()

        _upsert_quiz(dl1, "Pandas Quiz", [
            {"prompt": "Which library provides the DataFrame object?",
             "options": [{"text": "Pandas",  "correct": True},
                         {"text": "NumPy",   "correct": False},
                         {"text": "Seaborn", "correct": False}]},
        ])
        _upsert_quiz(dl3, "Linear Regression Quiz", [
            {"prompt": "What does the slope 'm' represent in y = mx + b?",
             "options": [{"text": "Rate of change of y per unit x", "correct": True},
                         {"text": "The y-intercept",               "correct": False},
                         {"text": "The variance",                  "correct": False}]},
        ])

        # Robotics course
        rob  = courses["robotics-and-arduino"]
        rm1  = _upsert_module(rob, "Arduino Fundamentals", 1)
        rm2  = _upsert_module(rob, "Sensors & Actuators",  2)
        rl1  = _upsert_lesson(rm1, "Arduino IDE & Setup",        1,
                               "Download Arduino IDE. Connect via USB.\nSketch has setup() and loop().",
                               xp=25, difficulty=Difficulty.intermediate)
        rl2  = _upsert_lesson(rm1, "Digital I/O",                2,
                               "Use pinMode(), digitalWrite(), digitalRead() to control LEDs.",
                               xp=25, difficulty=Difficulty.intermediate)
        rl3  = _upsert_lesson(rm2, "Ultrasonic Distance Sensor", 1,  # noqa: F841
                               "HC-SR04: Distance = (pulseIn / 2) * 0.0343 cm",
                               xp=30, difficulty=Difficulty.intermediate)
        rl4  = _upsert_lesson(rm2, "Servo Motor Control",        2,  # noqa: F841
                               "Servo.write(angle) rotates 0–180°. Use the Servo library.",
                               xp=30, difficulty=Difficulty.intermediate)
        db.session.flush()

        _upsert_quiz(rl1, "Arduino Setup Quiz", [  # noqa: F841
            {"prompt": "What are the two mandatory functions in an Arduino sketch?",
             "options": [{"text": "setup() and loop()", "correct": True},
                         {"text": "start() and run()",  "correct": False},
                         {"text": "init() and main()",  "correct": False}]},
        ])
        _upsert_quiz(rl2, "Digital I/O Quiz", [
            {"prompt": "Which function writes HIGH or LOW to a digital pin?",
             "options": [{"text": "digitalWrite()", "correct": True},
                         {"text": "analogWrite()",  "correct": False},
                         {"text": "pinOutput()",    "correct": False}]},
        ])

        # ── Enrollments ────────────────────────────────────────────────────────
        def _enroll(user: User, course: Course) -> None:
            if not Enrollment.query.filter_by(user_id=user.id, course_id=course.id).first():
                db.session.add(Enrollment(
                    id=new_id(), user_id=user.id, course_id=course.id,
                    source="free", is_active=True, created_at=utcnow(),
                ))

        _enroll(student, py)
        _enroll(student, math)
        _enroll(alice,   py)
        _enroll(alice,   ds)
        _enroll(bob,     math)
        _enroll(carlos,  py)
        _enroll(carlos,  rob)

        # ── XP + Badges (leaderboard seed data) ───────────────────────────────
        def _award_xp(user: User, points: int, reason: str, key_suffix: str) -> None:
            key = f"seed_{user.id}_{key_suffix}"
            if not PointsTransaction.query.filter_by(idempotency_key=key).first():
                db.session.add(PointsTransaction(
                    id=new_id(), user_id=user.id, amount=points,
                    reason=reason, idempotency_key=key, created_at=utcnow(),
                ))

        def _award_badge_seed(user: User, slug: str) -> None:
            badge = badge_map.get(slug)
            if badge and not UserBadge.query.filter_by(user_id=user.id, badge_id=badge.id).first():
                db.session.add(UserBadge(
                    id=new_id(), user_id=user.id, badge_id=badge.id,
                    awarded_at=utcnow(), created_at=utcnow(),
                ))

        def _set_streak(user: User, current: int, longest: int) -> None:
            from datetime import date as _date
            if not UserStreak.query.filter_by(user_id=user.id).first():
                db.session.add(UserStreak(
                    id=new_id(), user_id=user.id,
                    current_streak=current, longest_streak=longest,
                    last_activity_date=_date.today(),
                    created_at=utcnow(), updated_at=utcnow(),
                ))

        # student@demo.test — modest progress
        _award_xp(student, 10,  "Welcome to STEMQuest!", "signup")
        _award_xp(student, 20,  "Lesson completed",      "py_l1")
        _award_xp(student, 30,  "Passed quiz",           "quiz1")
        _award_badge_seed(student, "signup")
        _award_badge_seed(student, "first_lesson")
        _set_streak(student, 3, 3)

        # alice@demo.test — top of leaderboard
        _award_xp(alice, 10,  "Welcome to STEMQuest!", "signup")
        _award_xp(alice, 500, "Leaderboard seed",       "big_xp")
        _award_badge_seed(alice, "signup")
        _award_badge_seed(alice, "first_lesson")
        _award_badge_seed(alice, "xp_100")
        _award_badge_seed(alice, "xp_500")
        _award_badge_seed(alice, "perfect_score")
        _set_streak(alice, 14, 21)

        # bob@demo.test — second place
        _award_xp(bob, 10,  "Welcome to STEMQuest!", "signup")
        _award_xp(bob, 250, "Leaderboard seed",       "big_xp")
        _award_badge_seed(bob, "signup")
        _award_badge_seed(bob, "first_lesson")
        _award_badge_seed(bob, "xp_100")
        _set_streak(bob, 7, 10)

        # carlos@demo.test — third place
        _award_xp(carlos, 10,  "Welcome to STEMQuest!", "signup")
        _award_xp(carlos, 120, "Leaderboard seed",       "big_xp")
        _award_badge_seed(carlos, "signup")
        _award_badge_seed(carlos, "first_lesson")
        _award_badge_seed(carlos, "xp_100")
        _set_streak(carlos, 5, 5)

        db.session.commit()
        click.echo("Seed complete.")
        click.echo("  student@demo.test  / password123  (role: student)")
        click.echo("  admin@demo.test    / password123  (role: admin)")
        click.echo("  alice@demo.test    / password123  (leaderboard rank 1)")
        click.echo("  bob@demo.test      / password123  (leaderboard rank 2)")
        click.echo("  carlos@demo.test   / password123  (leaderboard rank 3)")

    @app.cli.command("seed")
    def seed():
        """Seed demo users, courses, modules, lessons, quizzes, badges, and leaderboard data."""
        _run_seed()

    @app.cli.command("seed-db")
    def seed_db():
        """Alias for 'seed' — matches README docs."""
        _run_seed()

    # ── create-admin ───────────────────────────────────────────────────────────

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("name")
    @click.argument("password")
    def create_admin(email: str, name: str, password: str):
        """Create a new admin account, or promote an existing user to admin."""
        from .extensions import db, bcrypt
        from .models.user import User, UserRole
        from .utils.helpers import new_id, make_initials, utcnow

        if len(password) < 8:
            click.echo("Error: password must be at least 8 characters.", err=True)
            return

        existing = User.query.filter_by(email=email).first()
        if existing:
            existing.role       = UserRole.admin
            existing.updated_at = utcnow()
            db.session.commit()
            click.echo(f"Promoted {email} to admin.")
        else:
            pw = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(
                id=new_id(), email=email, name=name, password_hash=pw,
                role=UserRole.admin, avatar=make_initials(name),
                is_active=True, email_verified=True,
                created_at=utcnow(), updated_at=utcnow(),
            )
            db.session.add(user)
            db.session.commit()
            click.echo(f"Admin account created: {email}")
