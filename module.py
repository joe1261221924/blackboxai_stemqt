"""
Module model
============
An ordered group of lessons within a course.

Design notes
------------
* ``sort_order`` is the canonical column name (matches spec).  The previous
  codebase used ``order``, which is also a reserved SQL keyword and caused
  quoting issues on some databases.
* A unique constraint on ``(course_id, sort_order)`` prevents two modules
  from occupying the same position within a course.
* ``created_at`` uses ``server_default`` so the DB clock is authoritative.
"""
from __future__ import annotations

from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db


class Module(db.Model):
    __tablename__ = "modules"
    __table_args__ = (
        db.UniqueConstraint("course_id", "sort_order", name="uq_module_course_sort_order"),
        # Fast retrieval of all modules for a course in order
        db.Index("ix_modules_course_sort", "course_id", "sort_order"),
    )

    id          = db.Column(
                      UUID(as_uuid=False),
                      primary_key=True,
                      server_default=db.text("gen_random_uuid()"),
                  )
    course_id   = db.Column(
                      UUID(as_uuid=False),
                      db.ForeignKey("courses.id", ondelete="CASCADE"),
                      nullable=False,
                      index=True,
                  )
    title       = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text,        nullable=False, server_default="")
    sort_order  = db.Column(db.Integer,     nullable=False, server_default="1")
    created_at  = db.Column(
                      db.DateTime(timezone=True),
                      nullable=False,
                      server_default=db.text("now()"),
                  )

    # ── Relationships ──────────────────────────────────────────────────────
    course  = db.relationship("Course",  back_populates="modules")
    lessons = db.relationship(
                  "Lesson", back_populates="module",
                  order_by="Lesson.sort_order", lazy="dynamic",
                  cascade="all, delete-orphan",
              )

    # ── Serialization ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "course_id":   self.course_id,
            "title":       self.title,
            "description": self.description,
            "sort_order":  self.sort_order,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Module {self.title!r} (sort_order={self.sort_order})>"
