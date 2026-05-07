from datetime import datetime, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler


def test_sorting_tasks_by_time():
    owner = Owner("Test")
    pet = Pet("Buddy", "Dog", 3)
    owner.add_pet(pet)

    t1 = Task("Late Task", datetime.now().replace(hour=18), 1, "daily")
    t2 = Task("Early Task", datetime.now().replace(hour=9), 1, "daily")

    pet.add_task(t1)
    pet.add_task(t2)

    scheduler = Scheduler(owner)
    sorted_tasks = scheduler.sort_by_time(scheduler.get_all_tasks())

    assert sorted_tasks[0].description == "Early Task"
    assert sorted_tasks[1].description == "Late Task"


def test_recurring_task_creates_new_task():
    owner = Owner("Test")
    pet = Pet("Buddy", "Dog", 3)
    owner.add_pet(pet)

    task = Task("Feed Dog", datetime.now(), 1, "daily")
    pet.add_task(task)

    new_task = task.mark_complete()

    assert task.completed is True
    assert new_task is not None
    assert new_task.scheduled_time.date() == (task.scheduled_time + timedelta(days=1)).date()


def test_weekly_recurrence_advances_by_a_week():
    task = Task("Grooming", datetime.now(), 1, "weekly")
    new_task = task.mark_complete()

    assert new_task is not None
    assert new_task.scheduled_time.date() == (task.scheduled_time + timedelta(weeks=1)).date()


def test_once_task_does_not_recur():
    task = Task("One-off vet visit", datetime.now(), 1, "once")
    new_task = task.mark_complete()

    assert task.completed is True
    assert new_task is None


def test_completing_same_task_twice_does_not_duplicate():
    owner = Owner("Test")
    pet = Pet("Buddy", "Dog", 3)
    owner.add_pet(pet)

    task = Task("Feed Dog", datetime.now().replace(hour=9, minute=0), 2, "daily")
    pet.add_task(task)

    scheduler = Scheduler(owner)
    scheduler.complete_task(task)
    scheduler.complete_task(task)
    scheduler.complete_task(task)

    # 1 original + exactly 1 generated occurrence, not 3.
    assert len(pet.tasks) == 2


def test_conflict_detection():
    owner = Owner("Test")
    pet = Pet("Buddy", "Dog", 3)
    owner.add_pet(pet)

    same_time = datetime.now().replace(hour=10, minute=0)

    t1 = Task("Task 1", same_time, 1, "daily")
    t2 = Task("Task 2", same_time, 1, "daily")

    pet.add_task(t1)
    pet.add_task(t2)

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()

    assert len(conflicts) == 1


def test_find_next_available_slot_at_hour_23_does_not_crash():
    owner = Owner("Test")
    pet = Pet("Buddy", "Dog", 3)
    owner.add_pet(pet)
    pet.add_task(Task("Late task", datetime.now().replace(hour=23, minute=0), 1, "once"))

    scheduler = Scheduler(owner)
    next_slot = scheduler.find_next_available_slot()

    assert next_slot is not None
    assert next_slot.hour == 0
    assert next_slot.date() == (datetime.now().replace(hour=23, minute=0) + timedelta(hours=1)).date()


def test_find_next_available_slot_finds_a_gap():
    owner = Owner("Test")
    pet = Pet("Buddy", "Dog", 3)
    owner.add_pet(pet)
    pet.add_task(Task("Morning", datetime.now().replace(hour=9, minute=0), 1, "once"))
    pet.add_task(Task("Evening", datetime.now().replace(hour=18, minute=0), 1, "once"))

    scheduler = Scheduler(owner)
    next_slot = scheduler.find_next_available_slot()

    assert next_slot.hour == 9


def test_owner_find_pet_is_case_insensitive():
    owner = Owner("Test")
    owner.add_pet(Pet("Buddy", "Dog", 3))

    assert owner.find_pet("buddy") is not None
    assert owner.find_pet("BUDDY") is not None
    assert owner.find_pet("Ghost") is None
