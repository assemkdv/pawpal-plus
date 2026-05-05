"""CLI demo of the PawPal+ scheduling engine.

Exercises pet/task creation, sorting, filtering, recurring-task completion,
and conflict detection directly against pawpal_system.py, independent of the
Streamlit app. Run with: python main.py
"""

from datetime import datetime
from pawpal_system import Owner, Pet, Task, Scheduler


# Create owner
owner = Owner("User")

# Create pets
dog = Pet("Buddy", "Dog", 3)
cat = Pet("Whiskers", "Cat", 2)

# Add pets to owner
owner.add_pet(dog)
owner.add_pet(cat)

# Create tasks (today + different times)
now = datetime.now()

task1 = Task("Morning Walk", now.replace(hour=9, minute=0), priority=2, frequency="daily")
task2 = Task("Feed Cat", now.replace(hour=12, minute=0), priority=3, frequency="daily")
task3 = Task("Evening Walk", now.replace(hour=18, minute=0), priority=1, frequency="daily")

# Assign tasks to pets
dog.add_task(task1)
cat.add_task(task2)
dog.add_task(task3)

# Create scheduler
scheduler = Scheduler(owner)

# Generate today's plan
tasks_today = scheduler.generate_daily_plan()

# Print schedule nicely
print("\n🐾 Today's Schedule:\n")

for task in tasks_today:
    time_str = task.scheduled_time.strftime("%I:%M %p")
    status = "✅ Done" if task.completed else "⏳ Pending"
    print(f"- {task.description} at {time_str} | Priority: {task.priority} | {status}")

print("\nSorted Tasks")
sorted_tasks = scheduler.sort_by_time(scheduler.get_all_tasks())
for task in sorted_tasks:
    print(task.display_task())

print("\nPending Tasks")
pending_tasks = scheduler.filter_by_status(False)
for task in pending_tasks:
    print(task.display_task())

print("\nDog Tasks")
dog_tasks = scheduler.filter_by_pet("Buddy")
for task in dog_tasks:
    print(task.display_task())

print("\nCompleting a Task")

task_to_complete = owner.pets[0].tasks[0]
scheduler.complete_task(task_to_complete)

print("\nUpdated Tasks")
for task in owner.pets[0].tasks:
    print(task.display_task())

same_time = datetime.now().replace(hour=10, minute=0)

feed_task = Task("Feed Dog", same_time, 2, "daily")
vet_task = Task("Vet Visit", same_time, 3, "daily")

owner.pets[0].add_task(feed_task)
owner.pets[0].add_task(vet_task)

print("\nConflict Detection")

conflicts = scheduler.detect_conflicts()

if conflicts:
    for t1, t2 in conflicts:
        print(f"Conflict: '{t1.description}' and '{t2.description}' at {t1.scheduled_time}")
else:
    print("No conflicts detected.")