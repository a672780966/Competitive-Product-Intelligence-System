from app.tasks import celery_app as celery  # noqa: F401 — re-export for celery CLI
from app.tasks.collection import collect_url, clean_content, extract_structured_data  # noqa: F401 — register tasks for Celery worker
