"""General utility helpers used across the backend."""
from __future__ import annotations

import uuid
import re
from datetime import datetime, timezone


def new_id() -> str:
    """Generate a compact UUID-4 string (36 chars, no prefix)."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def make_initials(name: str) -> str:
    """Return 1-2 character initials from a full name."""
    parts = name.strip().split()
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def paginate_query(query, page: int = 1, per_page: int = 20) -> dict:
    """Return paginated SQLAlchemy query result as a dict."""
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items":      result.items,
        "total":      result.total,
        "page":       result.page,
        "per_page":   result.per_page,
        "pages":      result.pages,
        "has_next":   result.has_next,
        "has_prev":   result.has_prev,
    }
