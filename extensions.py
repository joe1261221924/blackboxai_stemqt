"""
STEMQuest — Flask extension singletons
=======================================
All extensions are instantiated here *without* an app object so they can be
imported anywhere without creating circular-import problems.  The actual
``app.init_app(ext)`` calls live in the app factory (``stemquest/__init__.py``).

Redis / RQ notes
----------------
* A single ``ConnectionPool`` is created by ``init_redis(app)`` and shared
  across all Redis client instances in the process.  This avoids creating a
  new connection on every request.
* ``redis_client`` — general-purpose client used for caching, idempotency
  keys, and webhook deduplication.
* ``task_queue`` — RQ ``Queue("stemquest_tasks")`` used to enqueue background
  jobs.  The queue name matches the worker's ``listen`` list in ``worker.py``.
* Both holders start as ``None`` so that test collection that imports this
  module does not attempt a Redis connection before fixtures set up the
  environment.

Rate limiting
-------------
Flask-Limiter is configured with ``RATELIMIT_STORAGE_URI`` (Redis DB 1 by
default) to keep rate-limit counters isolated from the application cache.
Setting ``RATELIMIT_SWALLOW_ERRORS=True`` ensures the API degrades gracefully
if Redis is temporarily unavailable.
"""
from __future__ import annotations

import logging
from typing import Optional

import redis
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from rq import Queue

log = logging.getLogger(__name__)

# ── Core Flask extensions ───────────────────────────────────────────────────
db      = SQLAlchemy()
migrate = Migrate()
jwt     = JWTManager()
cors    = CORS()
bcrypt  = Bcrypt()

# Flask-Limiter — storage URI and defaults set via app.config at init_app time
limiter = Limiter(key_func=get_remote_address)

# ── Redis / RQ ──────────────────────────────────────────────────────────────
# Populated by ``init_redis(app)`` called from the app factory.
# Kept as module-level holders so the worker process can import them directly.
_redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis]         = None
task_queue:   Optional[Queue]               = None


def init_redis(app) -> None:  # type: ignore[type-arg]
    """
    Create a shared ``ConnectionPool`` and initialise ``redis_client`` and
    ``task_queue``.

    Called once from the app factory after ``app.config`` is populated.
    Also stores the client on ``app.redis`` for worker access.

    Parameters
    ----------
    app:
        The Flask application instance (already configured).
    """
    global _redis_pool, redis_client, task_queue

    redis_url: str = app.config.get("REDIS_URL", "redis://localhost:6379/0")

    _redis_pool = redis.ConnectionPool.from_url(
        redis_url,
        max_connections=20,
        socket_timeout=5,
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=30,
    )

    redis_client = redis.Redis(connection_pool=_redis_pool, decode_responses=True)

    # RQ queue — uses the *same* connection pool so no extra connections
    task_queue = Queue(
        "stemquest_tasks",
        connection=redis.Redis(connection_pool=_redis_pool),
    )

    # Expose on app for convenience (e.g. tests, worker)
    app.redis = redis_client  # type: ignore[attr-defined]

    # Fail fast at startup; degrade gracefully at request time if Redis drops
    try:
        redis_client.ping()
        log.info("[redis] Connected — %s", redis_url.split("@")[-1])
    except redis.exceptions.ConnectionError as exc:
        log.warning(
            "[redis] Could not connect at startup (%s). "
            "Cache and background jobs will be unavailable.",
            exc,
        )


def get_redis() -> redis.Redis:
    """
    Return the shared Redis client.

    Raises
    ------
    RuntimeError
        If called before ``init_redis()`` has been invoked.
    """
    if redis_client is None:
        raise RuntimeError(
            "Redis has not been initialised.  Ensure init_redis(app) is called "
            "inside the app factory before any code that calls get_redis()."
        )
    return redis_client


def get_task_queue() -> Queue:
    """
    Return the shared RQ task queue.

    Raises
    ------
    RuntimeError
        If called before ``init_redis()`` has been invoked.
    """
    if task_queue is None:
        raise RuntimeError(
            "Task queue has not been initialised.  Ensure init_redis(app) is "
            "called inside the app factory."
        )
    return task_queue
