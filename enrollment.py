"""
Enrollment model
================
Links a student to a course they have access to (free or paid).

Design notes
------------
* ``created_at`` is the authoritative enrollment timestamp (matches spec);
  the previous codebase used ``enrolled_at``.
* ``source`` records how the enrollment was granted:
    "free"     — student self-enrolled in a free course
    "purchase" — enrollment created after successful payment
    "admin"    — manually granted by an admin
  This is useful for analytics without a separate audit log.
* ``completed_at`` is set by the course service when 100 % of lessons are done.
* Unique constraint on ``(user_id, course_id)`` prevents duplicate rows; the
  service layer re-activates an existing row instead of inserting a duplicate.
* ``is_active`` allows soft-deactivation (e.g. refund) without deleting
  progress data.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (
        db.UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),
        db.Index("ix_enrollment_user_active", "user_id", "is_active"),
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
    course_id    = db.Column(
                       UUID(as_uuid=False),
                       db.ForeignKey("courses.id", ondelete="CASCADE"),
                       nullable=False,
                       index=True,
                   )
    # How the enrollment was granted
    source       = db.Column(
                       db.String(20),
                       nullable=False,
                       server_default="free",
                   )
    is_active    = db.Column(db.Boolean,              nullable=False, server_default=sa.true())
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at   = db.Column(
                       db.DateTime(timezone=True),
                       nullable=False,
                       server_default=db.text("now()"),
                   )

    # ── Relationships ──────────────────────────────────────────────────────
    user   = db.relationship("User",   back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "course_id":    self.course_id,
            "source":       self.source,
            "is_active":    self.is_active,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at":   self.created_at.isoformat()   if self.created_at   else None,
        }

    def __repr__(self) -> str:
        return f"<Enrollment user={self.user_id} course={self.course_id}>"
