from datetime import datetime
from pawpal_system import Owner, Pet, Task, Scheduler


# Create owner
owner = Owner("Assem")

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
