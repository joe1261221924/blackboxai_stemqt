"""
Lesson model
============
An individual learning unit (text + optional video) inside a module.

Design notes
------------
* ``content_body`` is the canonical name for lesson body text (matches spec).
* ``sort_order`` replaces the previous ``order`` column (reserved SQL keyword).
* ``published`` flag allows drafting before student visibility.
* ``difficulty_level`` re-uses the shared ``Difficulty`` enum from course.py
  so the DB enum type is not duplicated.
* ``xp_reward`` defaults to 10 XP per spec (was 20 previously).
* A unique constraint on ``(module_id, sort_order)`` prevents collisions.
* A composite index on ``(course_id, sort_order)`` enables efficient
  per-course lesson listings sorted by position.

Relationship naming (spec-aligned)
-----------------------------------
* ``lesson.quizzes``         — spec name; exposes the list of quizzes on this
  lesson.  Because Quiz.lesson_id has a unique constraint, there will be at
  most one row, but the relationship is typed as a list to match the spec
  contract.  The convenience accessor ``lesson.quiz`` (uselist=False) is
  preserved as a private-ish alias used by the seed command.
* ``lesson.progress_records`` — spec name; replaces the previous ``progress``
  accessor.  LessonProgress.back_populates must match this name.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from .course import Difficulty
from ..extensions import db


class Lesson(db.Model):
    __tablename__ = "lessons"
    __table_args__ = (
        db.UniqueConstraint("module_id", "sort_order", name="uq_lesson_module_sort_order"),
        # Composite index for per-course lesson listing sorted by position
        db.Index("ix_lessons_course_sort", "course_id", "sort_order"),
        # Index for filtering published lessons per module
        db.Index("ix_lessons_module_published", "module_id", "published"),
    )

    id              = db.Column(
                          UUID(as_uuid=False),
                          primary_key=True,
                          server_default=db.text("gen_random_uuid()"),
                      )
    module_id       = db.Column(
                          UUID(as_uuid=False),
                          db.ForeignKey("modules.id", ondelete="CASCADE"),
                          nullable=False,
                          index=True,
                      )
    # Denormalized course_id avoids an extra join for progress queries and
    # enables a direct composite index on (course_id, sort_order).
    course_id       = db.Column(
                          UUID(as_uuid=False),
                          db.ForeignKey("courses.id", ondelete="CASCADE"),
                          nullable=False,
                          index=True,
                      )
    title           = db.Column(db.String(300), nullable=False)
    # Spec: summary is nullable text.
    summary         = db.Column(db.Text, nullable=True)
    # Spec: content_body is not null.
    content_body    = db.Column(db.Text, nullable=False, server_default="")
    # Spec: video_url is nullable.
    video_url       = db.Column(db.Text, nullable=True)
    difficulty_level = db.Column(
                           db.Enum(Difficulty, name="difficulty"),
                           nullable=False,
                           default=Difficulty.beginner,
                           server_default=Difficulty.beginner.value,
                       )
    # Spec: xp_reward default 10.
    xp_reward       = db.Column(db.Integer, nullable=False, server_default="10")
    # Spec: published default true.
    published       = db.Column(db.Boolean, nullable=False, server_default=sa.true())
    # Spec: sort_order default 0.
    sort_order      = db.Column(db.Integer, nullable=False, server_default="0")
    created_at      = db.Column(
                          db.DateTime(timezone=True),
                          nullable=False,
                          server_default=db.text("now()"),
                      )

    # ── Relationships ──────────────────────────────────────────────────────
    module   = db.relationship("Module", back_populates="lessons")
    course   = db.relationship("Course", foreign_keys=[course_id])

    # Spec relationship name: lesson.quizzes (list; at most one due to DB unique constraint).
    quizzes  = db.relationship(
                   "Quiz", back_populates="lesson",
                   lazy="dynamic", cascade="all, delete-orphan",
               )

    # Spec relationship name: lesson.progress_records.
    # LessonProgress.back_populates must equal "progress_records".
    progress_records = db.relationship(
                           "LessonProgress", back_populates="lesson",
                           lazy="dynamic", cascade="all, delete-orphan",
                       )

    # Convenience accessor preserved for internal use (seed command, services).
    # Returns the single Quiz or None (Quiz.lesson_id is unique).
    @property
    def quiz(self):
        return self.quizzes.first()

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "module_id":        self.module_id,
            "course_id":        self.course_id,
            "title":            self.title,
            "summary":          self.summary,
            "content_body":     self.content_body,
            "video_url":        self.video_url,
            "difficulty_level": self.difficulty_level.value,
            "xp_reward":        self.xp_reward,
            "published":        self.published,
            "sort_order":       self.sort_order,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Lesson {self.title!r}>"
