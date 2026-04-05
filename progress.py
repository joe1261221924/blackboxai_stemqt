"""
LessonProgress model
====================
Records that a student has completed (or is working through) a specific lesson.

Design notes
------------
* ``completed`` is an explicit boolean (matches spec) rather than inferring
  completion from the presence of the row; this keeps the door open for
  partial-progress extensions without a schema migration.
* ``completed_at`` is nullable: set once, atomically, when ``completed``
  transitions to True.  Never reset.
* ``created_at`` records when the progress row was first inserted, i.e. when
  the student first opened/attempted the lesson.
* Unique constraint on ``(user_id, lesson_id)`` ensures exactly one row per
  student + lesson.  The service layer issues an UPDATE instead of INSERT on
  revisit.
* ``course_id`` is denormalized from Lesson to enable the progress-percentage
  query (``COUNT(*) WHERE user_id=X AND course_id=Y AND completed=TRUE``)
  without joining through lessons → modules → courses.
* A composite index on ``(user_id, course_id)`` directly backs that query.

Relationship naming (spec-aligned)
------------------------------------
* ``lesson_progress.lesson`` — ``back_populates="progress_records"`` must
  match the ``Lesson.progress_records`` relationship name set in lesson.py.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        # One record per student + lesson — service layer upserts, never inserts twice.
        db.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
        # Efficient per-course progress percentage calculation.
        db.Index("ix_progress_user_course", "user_id", "course_id"),
        # Quick lookup of completed lessons for a user (leaderboard, badge checks).
        db.Index("ix_progress_user_completed", "user_id", "completed"),
    )

    id           = db.Column(
                       UUID(as_uuid=False),
                       primary_key=True,
                       server_default=db.text("gen_random_uuid()"),
                   )
    user_id      = db.Column(
                       UUID(as_uuid=False),
                       db.ForeignKey("users.id", ondelete="CASCADE"),
                       nullable=False,
                       index=True,
                   )
    lesson_id    = db.Column(
                       UUID(as_uuid=False),
                       db.ForeignKey("lessons.id", ondelete="CASCADE"),
                       nullable=False,
                       index=True,
                   )
    # Denormalized for efficient per-course progress aggregation.
    course_id    = db.Column(
                       UUID(as_uuid=False),
                       db.ForeignKey("courses.id", ondelete="CASCADE"),
                       nullable=False,
                       index=True,
                   )
    # Spec: completed boolean, default false.
    completed    = db.Column(db.Boolean, nullable=False, server_default=sa.false())
    # Spec: completed_at is nullable datetime.
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Spec: created_at datetime, default utcnow.
    created_at   = db.Column(
                       db.DateTime(timezone=True),
                       nullable=False,
                       server_default=db.text("now()"),
                   )

    # ── Relationships ──────────────────────────────────────────────────────
    user   = db.relationship("User",   back_populates="lesson_progress")
    # back_populates must equal "progress_records" — the spec-aligned name on Lesson.
    lesson = db.relationship("Lesson", back_populates="progress_records")

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "lesson_id":    self.lesson_id,
            "course_id":    self.course_id,
            "completed":    self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at":   self.created_at.isoformat()   if self.created_at   else None,
        }

    def __repr__(self) -> str:
        return (
            f"<LessonProgress user={self.user_id} lesson={self.lesson_id} "
            f"done={self.completed}>"
        )
