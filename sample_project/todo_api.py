"""To-do list service (existing code)."""

VERSION = "1.0.0"

TASKS = []


def create_task(title):
    task = {"id": len(TASKS) + 1, "title": title, "status": "open"}
    TASKS.append(task)
    return task


def list_tasks():
    return list(TASKS)
