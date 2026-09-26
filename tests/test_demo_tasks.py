import pytest

from backend.demo_bug import Task, tasks, delete_task


@pytest.fixture(autouse=True)
def reset_tasks():
    """Restore the task list before every test."""
    tasks[:] = [
        Task(id=1, title="Task one", owner_id=1),
        Task(id=2, title="Task two", owner_id=2),
        Task(id=3, title="Task three", owner_id=3),
    ]


def test_list_has_three_tasks():
    assert len(tasks) == 3


def test_task_one_exists():
    assert tasks[0].id == 1


def test_task_two_exists():
    assert tasks[1].id == 2


def test_task_three_exists():
    assert tasks[2].id == 3


def test_task_one_title():
    assert tasks[0].title == "Task one"


def test_task_two_title():
    assert tasks[1].title == "Task two"


def test_task_three_title():
    assert tasks[2].title == "Task three"


def test_task_one_owner():
    assert tasks[0].owner_id == 1


def test_task_two_owner():
    assert tasks[1].owner_id == 2


def test_task_three_owner():
    assert tasks[2].owner_id == 3


def test_delete_existing_task():
    result = delete_task(2)
    assert result["deleted"] == 2


def test_delete_removes_task():
    delete_task(2)
    assert all(task.id != 2 for task in tasks)


def test_delete_returns_current_user():
    result = delete_task(2)
    assert result["by_user"] == 2


def test_delete_task_owned_by_current_user():
    result = delete_task(2)
    assert result["deleted"] == 2


def test_delete_owned_task_returns_user():
    result = delete_task(2)
    assert result["by_user"] == 2


def test_delete_changes_task_count():
    delete_task(2)
    assert len(tasks) == 2


def test_delete_missing_task():
    with pytest.raises(Exception):
        delete_task(999)


# These 3 tests expose the ownership bug.
# The current user is user 2, so deleting tasks owned by users 1 or 3
# must be rejected after the bug is fixed.


def test_delete_task_not_owner():
    with pytest.raises(Exception):
        delete_task(1)


def test_delete_task_other_user():
    with pytest.raises(Exception):
        delete_task(3)


def test_delete_task_unauthorized_owner():
    with pytest.raises(Exception):
        delete_task(1)