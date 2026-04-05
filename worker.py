"""
RQ worker entry-point.

Run with:
    python worker.py

The worker imports the Flask app so that the app context is available for
tasks that use Flask-SQLAlchemy.  The RQ Queue object is created directly
from a Redis connection.

RQ 2.x API NOTES
-----------------
``rq.Connection`` context manager was removed in RQ 2.x.  Workers are now
initialised by passing the connection and queues directly to ``Worker()``.
The correct usage is:

    worker = Worker(queues, connection=conn)
    worker.work()

NOT the old:
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
"""
import os
import logging

import redis
from rq import Worker, Queue

from stemquest import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger(__name__)

QUEUE_NAMES = ["stemquest_tasks"]

app = create_app(os.environ.get("FLASK_ENV", "development"))

conn = redis.from_url(app.config["REDIS_URL"])


def main() -> None:
    queues  = [Queue(name, connection=conn) for name in QUEUE_NAMES]
    worker  = Worker(queues, connection=conn)     # RQ 2.x API — no Connection ctx manager

    log.info("STEMQuest RQ worker starting — listening on: %s", QUEUE_NAMES)

    with app.app_context():
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
