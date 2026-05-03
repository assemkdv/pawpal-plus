import logging
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pawpal_system import Owner, Pet, Task, Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PET_CARE_KNOWLEDGE = [
    "Dogs should be walked at least 30 minutes twice daily.",
    "Cats require protein-rich diets and should be fed 2-3 times daily.",
    "Pets need annual veterinary checkups.",
    "Dental hygiene is important for both cats and dogs.",
    "Long-haired pets need grooming every 1-2 days, while short-haired pets need grooming weekly.",
    "Cats should be groomed regularly to prevent matting and hairballs.",
    "Puppies need early socialization and training.",
    "Kittens need frequent feeding and play.",
    "Signs of illness include lethargy, vomiting, or appetite loss.",
    "Exercise and mental stimulation are essential for pets.",
    "Senior pets need more frequent vet visits and softer care."
]


class PetCareRAG:
    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.vectors = self.vectorizer.fit_transform(knowledge)

    def retrieve(self, query, top_k=2):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]

        # Only keep GOOD matches
        results = [self.knowledge[i] for i in top_indices if scores[i] > 0.15]
        return results


class PawPalAI:
    def __init__(self, owner: Owner, scheduler: Scheduler):
        self.owner = owner
        self.scheduler = scheduler
        self.rag = PetCareRAG(PET_CARE_KNOWLEDGE)

    def _execute_tool(self, tool_name, tool_input):
        try:
            if tool_name == "add_task":
                pet = next((p for p in self.owner.pets if p.name.lower() == tool_input["pet_name"].lower()), None)
                if not pet:
                    return f"❌ Pet '{tool_input['pet_name']}' not found."

                scheduled = datetime.now().replace(
                    hour=int(tool_input["hour"]),
                    minute=int(tool_input["minute"]),
                    second=0,
                    microsecond=0
                )

                task = Task(
                    description=tool_input["description"],
                    scheduled_time=scheduled,
                    priority=int(tool_input["priority"]),
                    frequency=tool_input["frequency"]
                )

                pet.add_task(task)
                return f"✅ Task '{task.description}' added for {pet.name} at {scheduled.strftime('%I:%M %p')}."

            elif tool_name == "list_tasks":
                tasks = self.scheduler.get_all_tasks()
                if not tasks:
                    return "No tasks found."

                return "\n".join([
                    f"- {t.description} at {t.scheduled_time.strftime('%I:%M %p')} (priority {t.priority})"
                    for t in tasks
                ])

            elif tool_name == "list_pets":
                if not self.owner.pets:
                    return "No pets added yet."

                return "\n".join([
                    f"- {p.name} ({p.type}, age {p.age})"
                    for p in self.owner.pets
                ])

            return "Unknown action."

        except Exception as e:
            return f"Error: {str(e)}"

    def chat(self, user_message):
        user_message_lower = user_message.lower()

        # ADD PET
        if "add pet" in user_message_lower:
            try:
                parts = user_message.split(",")

                name = parts[0].replace("add pet", "").strip()
                pet_type = parts[1].strip()
                age = int(parts[2].strip())

                new_pet = Pet(name=name, type=pet_type, age=age)
                self.owner.add_pet(new_pet)

                return f"🐾 Pet '{name}' added successfully!"

            except:
                return "⚠️ Format: add pet [name], [type], [age]\nExample: add pet Buddy, dog, 3"

        # LIST PETS
        if "list pets" in user_message_lower:
            return self._execute_tool("list_pets", {})

        # LIST TASKS
        if "list tasks" in user_message_lower:
            return self._execute_tool("list_tasks", {})

        # ADD TASK
        if "add task" in user_message_lower:
            try:
                parts = user_message.split(",")

                pet_name = parts[0].replace("add task", "").strip()
                description = parts[1].strip()
                hour = int(parts[2].strip())
                minute = int(parts[3].strip())
                priority = int(parts[4].strip())
                frequency = parts[5].strip()

                return self._execute_tool("add_task", {
                    "pet_name": pet_name,
                    "description": description,
                    "hour": hour,
                    "minute": minute,
                    "priority": priority,
                    "frequency": frequency
                })

            except:
                return "⚠️ Format: add task [pet], [description], [hour], [minute], [priority], [frequency]\nExample: add task Buddy, walk, 9, 0, 3, daily"

        # RAG
        retrieved = self.rag.retrieve(user_message)

        if retrieved:
            response = "🐾 PawPal+ Assistant\n\nBased on your question, here’s what I recommend:\n\n"
            for r in retrieved:
                response += f"- {r}\n"
            return response

        # SMART FALLBACKS
        if "groom" in user_message_lower and "cat" in user_message_lower:
            return "🐾 Cats should be groomed regularly. Long-haired cats need grooming daily or every 1–2 days, while short-haired cats can be brushed weekly."

        if "walk" in user_message_lower and "dog" in user_message_lower:
            return "🐾 Dogs should be walked at least twice a day for about 30 minutes."

        return "🐾 I can help with pet care tips or managing your pet tasks!"

    def reset_conversation(self):
        logger.info("Conversation reset")
