from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta

VALID_FREQUENCIES = {"once", "daily", "weekly"}


# Task
@dataclass
class Task:
    description: str
    scheduled_time: datetime
    priority: int
    frequency: str
    completed: bool = False

    def mark_complete(self):
        """Mark the task as completed and return next occurrence if recurring.

        Calling this again on an already-completed task is a no-op that
        returns None, so completing a task twice cannot create duplicate
        future occurrences.
        """
        if self.completed:
            return None

        self.completed = True

        # Handle recurring tasks
        if self.frequency == "daily":
            new_time = self.scheduled_time + timedelta(days=1)
        elif self.frequency == "weekly":
            new_time = self.scheduled_time + timedelta(weeks=1)
        else:
            return None

        # Create new task instance
        return Task(
            description=self.description,
            scheduled_time=new_time,
            priority=self.priority,
            frequency=self.frequency
        )

    def display_task(self):
        """Return a readable string of the task."""
        status = "Done" if self.completed else "Pending"
        return f"{self.description} at {self.scheduled_time} ({status})"


# Pet 
@dataclass
class Pet:
    name: str
    type: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        """Add a task to this pet."""
        self.tasks.append(task)

    def get_tasks(self):
        """Return all tasks for this pet."""
        return self.tasks


# Owner
class Owner:
    def __init__(self, name: str):
        self.name = name
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet):
        """Add a pet to the owner."""
        self.pets.append(pet)

    def find_pet(self, name: str) -> Optional[Pet]:
        """Return the pet matching name (case-insensitive), or None."""
        name = name.strip().lower()
        for pet in self.pets:
            if pet.name.strip().lower() == name:
                return pet
        return None

    def get_all_tasks(self):
        """Return all tasks across all pets."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks


# Scheduler 
class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner

    def get_all_tasks(self):
        """Return all tasks across all pets."""
        return self.owner.get_all_tasks()

    def get_tasks_for_today(self):
        """Return all tasks scheduled for today."""
        today = datetime.now().date()
        return [
            task for task in self.get_all_tasks()
            if task.scheduled_time.date() == today
        ]

    def get_pending_tasks(self):
        """Return all tasks that are not completed."""
        return [
            task for task in self.get_all_tasks()
            if not task.completed
        ]

    def generate_daily_plan(self):
        """Return sorted tasks for today based on priority and time."""
        tasks = self.get_tasks_for_today()
        # sort by priority (higher first) and time
        tasks.sort(key=lambda t: (-t.priority, t.scheduled_time))
        return tasks
    
    def sort_by_time(self, tasks):
        """Return tasks sorted by scheduled time."""
        return sorted(tasks, key=lambda task: task.scheduled_time)
    
    def filter_by_status(self, completed=True):
        """Return tasks filtered by completion status."""
        return [
            task for task in self.get_all_tasks()
            if task.completed == completed
        ]
    
    def filter_by_pet(self, pet_name):
        """Return tasks for a specific pet."""
        filtered_tasks = []

        for pet in self.owner.pets:
            if pet.name == pet_name:
                filtered_tasks.extend(pet.tasks)

        return filtered_tasks
    
    def complete_task(self, task):
        """Mark task complete and handle recurrence."""
        new_task = task.mark_complete()

        if new_task:
            # find the pet and add the new task
            for pet in self.owner.pets:
                if task in pet.tasks:
                    pet.add_task(new_task)
                    break

    def detect_conflicts(self):
        """Detect tasks that are scheduled at the same time."""
        tasks = self.get_all_tasks()
        conflicts = []

        # compare every pair of tasks
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                if tasks[i].scheduled_time == tasks[j].scheduled_time:
                    conflicts.append((tasks[i], tasks[j]))

        return conflicts   

    def find_next_available_slot(self):
        """Find the next available time slot after scheduled tasks."""
        tasks = self.sort_by_time(self.get_all_tasks())

        if not tasks:
            return None

        # start from first task time
        current_time = tasks[0].scheduled_time

        for task in tasks:
            # if there's a gap, return next free time
            if task.scheduled_time > current_time:
                return current_time
            current_time = task.scheduled_time

        # if no gaps, return last task time + 1 hour
        return current_time + timedelta(hours=1)