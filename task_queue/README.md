# Removed

The `task_queue` Python package was deleted. Import **`services.task_service`** (`enqueue_task`, `push_existing_task`, …) and **`services.task_payload`** (`parse_payload`) instead. Queue primitives: **`redis_queue_pkg.redis_queue`**.
