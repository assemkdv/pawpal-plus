import logging
import re
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity

from pawpal_system import Owner, Pet, Task, Scheduler, VALID_FREQUENCIES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# General pet care information, written for this project. Not veterinary
# advice. Kept intentionally general and conservative: no dosages,
# diagnoses, or treatment plans.
PET_CARE_KNOWLEDGE = [
    "Dogs should be walked at least 30 minutes twice daily for exercise and mental stimulation.",
    "Adult dogs are usually fed once or twice a day; how much to feed depends on the dog's age, "
    "size, and activity level, so check with your veterinarian for specific feeding guidance.",
    "Cats are usually fed two to three small meals a day; ask your veterinarian how much to feed "
    "based on your cat's age and weight, and always keep fresh water available.",
    "Dogs and cats generally benefit from annual veterinary checkups; your veterinarian can "
    "recommend an appropriate vaccination schedule for your pet.",
    "Dental hygiene is important for both cats and dogs; regular tooth brushing and dental "
    "checkups help prevent disease.",
    "Long-haired pets generally need grooming every 1-2 days, while short-haired pets can "
    "usually be groomed weekly.",
    "Cats should be groomed regularly to help prevent matting and hairballs.",
    "Puppies need early socialization and basic training, starting with short, positive sessions.",
    "Kittens need frequent feeding, supervised play, and a safe space to explore.",
    "Common signs of illness in pets include lethargy, vomiting, diarrhea, or loss of appetite; "
    "if these persist or seem severe, contact your veterinarian.",
    "Regular exercise and mental stimulation, such as toys and play, are important for the "
    "wellbeing of both dogs and cats.",
    "Senior pets generally need more frequent veterinary visits and softer, easier-to-manage "
    "care routines.",
    "Some common human foods, including chocolate, onions, garlic, grapes, and xylitol, are "
    "toxic to dogs and cats. Keep these foods out of reach, and contact a veterinarian if your "
    "pet eats any of them.",
    "If your pet is showing signs of a medical emergency, such as difficulty breathing, collapse, "
    "seizures, severe bleeding, or suspected poisoning, contact a veterinarian or emergency "
    "animal clinic immediately.",
]

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _normalize_word(word):
    """Strip a few common English suffixes so simple singular/plural and verb-form
    variants (cat/cats, groom/grooming/grooms) overlap during matching.

    This is a small heuristic, not a real stemmer/lemmatizer - it won't catch
    irregular forms (e.g. feed/fed). Good enough for a small knowledge base
    without adding an NLP dependency.
    """
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("ed") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _analyze(text):
    words = _WORD_RE.findall(text.lower())
    return [_normalize_word(w) for w in words if w not in ENGLISH_STOP_WORDS and len(w) > 1]


class PetCareRAG:
    """Local TF-IDF retrieval over a curated pet care knowledge base.

    This performs retrieval only: it returns the closest matching knowledge
    base sentence(s) verbatim. No generative model is involved, so this is
    retrieval-based question answering, not retrieval-augmented generation.
    """

    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.vectorizer = TfidfVectorizer(analyzer=_analyze)
        self.vectors = self.vectorizer.fit_transform(knowledge)

    def retrieve(self, query, top_k=2):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]

        # Only keep reasonably confident matches.
        results = [self.knowledge[i] for i in top_indices if scores[i] > 0.15]
        return results


# Chat command prefixes. Commands are matched only when the message starts
# with one of these (case-insensitively) so ordinary questions that merely
# mention a phrase like "add pet" aren't misrouted into command parsing.
CMD_HELP = "help"
CMD_ADD_PET = "add pet"
CMD_ADD_TASK = "add task"
CMD_COMPLETE_TASK = "complete task"
CMD_LIST_PETS = "list pets"
CMD_LIST_TASKS = "list tasks"

ADD_PET_FORMAT_HELP = "⚠️ Format: add pet [name], [type], [age]\nExample: add pet Buddy, dog, 3"
ADD_TASK_FORMAT_HELP = (
    "⚠️ Format: add task [pet], [description], [hour], [minute], [priority 1-5], [once/daily/weekly]\n"
    "Example: add task Buddy, walk, 9, 0, 3, daily"
)
COMPLETE_TASK_FORMAT_HELP = (
    "⚠️ Format: complete task [pet], [description]\nExample: complete task Buddy, walk"
)

HELP_TEXT = (
    "🐾 Supported commands:\n"
    "- add pet [name], [type], [age] (example: add pet Buddy, dog, 3)\n"
    "- add task [pet], [description], [hour 0-23], [minute 0-59], [priority 1-5], [once/daily/weekly]\n"
    "  (example: add task Buddy, walk, 9, 0, 3, daily)\n"
    "- complete task [pet], [description] (example: complete task Buddy, walk)\n"
    "- list pets\n"
    "- list tasks\n"
    "- help\n\n"
    "You can also ask general pet care questions, such as 'How often should I groom my cat?'"
)

URGENT_KEYWORDS = [
    "emergency", "poison", "poisoned", "poisoning", "toxic", "bleeding",
    "collapse", "collapsed", "seizure", "seizing", "difficulty breathing",
    "can't breathe", "cannot breathe", "not breathing", "overdose",
    "dosage", "how much medication", "medication dose",
]

VET_ESCALATION_MESSAGE = (
    "🚨 This sounds like it could be an emergency. PawPal+ can't diagnose your pet or "
    "recommend medication or dosages. Please contact your veterinarian or the nearest "
    "emergency animal clinic right away."
)

SUPPORTED_SPECIES_TERMS = {"dog", "dogs", "puppy", "puppies", "cat", "cats", "kitten", "kittens"}
UNSUPPORTED_SPECIES_TERMS = [
    "bird", "parrot", "reptile", "lizard", "snake", "turtle", "tortoise",
    "fish", "hamster", "rabbit", "guinea pig", "ferret", "chinchilla", "gerbil",
]

UNSUPPORTED_SPECIES_MESSAGE = (
    "🐾 PawPal+'s pet care knowledge base currently focuses mainly on dogs and cats, so I "
    "don't have reliable guidance for that animal. Please check a species-specific resource "
    "or ask your veterinarian."
)


class PawPalAI:
    def __init__(self, owner: Owner, scheduler: Scheduler):
        self.owner = owner
        self.scheduler = scheduler
        self.rag = PetCareRAG(PET_CARE_KNOWLEDGE)

    def _execute_tool(self, tool_name, tool_input):
        try:
            if tool_name == "add_task":
                pet = self.owner.find_pet(tool_input["pet_name"])
                if not pet:
                    return f"❌ Pet '{tool_input['pet_name']}' not found."

                scheduled = datetime.now().replace(
                    hour=tool_input["hour"],
                    minute=tool_input["minute"],
                    second=0,
                    microsecond=0,
                )

                task = Task(
                    description=tool_input["description"],
                    scheduled_time=scheduled,
                    priority=tool_input["priority"],
                    frequency=tool_input["frequency"],
                )

                pet.add_task(task)
                return f"✅ Task '{task.description}' added for {pet.name} at {scheduled.strftime('%I:%M %p')}."

            elif tool_name == "list_tasks":
                tasks = self.scheduler.get_all_tasks()
                if not tasks:
                    return "No tasks found."

                return "\n".join([
                    f"- {t.description} at {t.scheduled_time.strftime('%b %d, %I:%M %p')} "
                    f"(priority {t.priority}, {'done' if t.completed else 'pending'})"
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

        except Exception:
            logger.exception("Unexpected error executing tool %s", tool_name)
            return "⚠️ Something went wrong while processing that request. Please check your input and try again."

    def _handle_add_pet(self, stripped):
        rest = stripped[len(CMD_ADD_PET):]
        parts = rest.split(",")
        if len(parts) != 3:
            return ADD_PET_FORMAT_HELP

        name = parts[0].strip()
        pet_type = parts[1].strip()
        age_raw = parts[2].strip()

        if not name or not pet_type:
            return ADD_PET_FORMAT_HELP
        if not age_raw.lstrip("-").isdigit():
            return "⚠️ Pet age must be a whole number.\n" + ADD_PET_FORMAT_HELP

        age = int(age_raw)
        if age < 0:
            return "⚠️ Pet age can't be negative."

        if self.owner.find_pet(name):
            return f"⚠️ You already have a pet named '{name}'. Pet names must be unique."

        self.owner.add_pet(Pet(name=name, type=pet_type, age=age))
        return f"🐾 Pet '{name}' added successfully!"

    def _handle_add_task(self, stripped):
        rest = stripped[len(CMD_ADD_TASK):]
        parts = rest.split(",")
        if len(parts) != 6:
            return ADD_TASK_FORMAT_HELP

        pet_name = parts[0].strip()
        description = parts[1].strip()
        hour_raw, minute_raw, priority_raw = parts[2].strip(), parts[3].strip(), parts[4].strip()
        frequency = parts[5].strip().lower()

        if not pet_name or not description:
            return ADD_TASK_FORMAT_HELP

        try:
            hour = int(hour_raw)
            minute = int(minute_raw)
            priority = int(priority_raw)
        except ValueError:
            return "⚠️ Hour, minute, and priority must be whole numbers.\n" + ADD_TASK_FORMAT_HELP

        if not (0 <= hour <= 23):
            return "⚠️ Hour must be between 0 and 23."
        if not (0 <= minute <= 59):
            return "⚠️ Minute must be between 0 and 59."
        if not (1 <= priority <= 5):
            return "⚠️ Priority must be between 1 and 5."
        if frequency not in VALID_FREQUENCIES:
            return f"⚠️ Frequency must be one of: {', '.join(sorted(VALID_FREQUENCIES))}."

        return self._execute_tool("add_task", {
            "pet_name": pet_name,
            "description": description,
            "hour": hour,
            "minute": minute,
            "priority": priority,
            "frequency": frequency,
        })

    def _handle_complete_task(self, stripped):
        rest = stripped[len(CMD_COMPLETE_TASK):]
        parts = rest.split(",")
        if len(parts) != 2:
            return COMPLETE_TASK_FORMAT_HELP

        pet_name = parts[0].strip()
        description = parts[1].strip()
        if not pet_name or not description:
            return COMPLETE_TASK_FORMAT_HELP

        pet = self.owner.find_pet(pet_name)
        if not pet:
            return f"❌ Pet '{pet_name}' not found."

        matches = [
            t for t in pet.tasks
            if not t.completed and t.description.strip().lower() == description.lower()
        ]

        if not matches:
            return f"❌ No incomplete task named '{description}' found for {pet.name}."
        if len(matches) > 1:
            return (
                f"⚠️ {len(matches)} incomplete tasks named '{description}' found for {pet.name}. "
                "Please use a more specific or unique task description."
            )

        task = matches[0]
        tasks_before = len(pet.tasks)
        self.scheduler.complete_task(task)

        if len(pet.tasks) > tasks_before:
            next_task = pet.tasks[-1]
            return (
                f"✅ '{task.description}' marked complete for {pet.name}. "
                f"Next occurrence scheduled for {next_task.scheduled_time.strftime('%b %d, %I:%M %p')}."
            )
        return f"✅ '{task.description}' marked complete for {pet.name}."

    def _urgent_response(self, lower_message):
        if any(keyword in lower_message for keyword in URGENT_KEYWORDS):
            return VET_ESCALATION_MESSAGE
        return None

    def _unsupported_species_response(self, lower_message):
        mentions_unsupported = any(term in lower_message for term in UNSUPPORTED_SPECIES_TERMS)
        mentions_supported = any(term in lower_message for term in SUPPORTED_SPECIES_TERMS)
        if mentions_unsupported and not mentions_supported:
            return UNSUPPORTED_SPECIES_MESSAGE
        return None

    def chat(self, user_message):
        stripped = user_message.strip()
        lower = stripped.lower()

        if lower.startswith(CMD_HELP):
            return HELP_TEXT
        if lower.startswith(CMD_ADD_PET):
            return self._handle_add_pet(stripped)
        if lower.startswith(CMD_ADD_TASK):
            return self._handle_add_task(stripped)
        if lower.startswith(CMD_COMPLETE_TASK):
            return self._handle_complete_task(stripped)
        if lower.startswith(CMD_LIST_PETS):
            return self._execute_tool("list_pets", {})
        if lower.startswith(CMD_LIST_TASKS):
            return self._execute_tool("list_tasks", {})

        urgent = self._urgent_response(lower)
        if urgent:
            return urgent

        species_notice = self._unsupported_species_response(lower)
        if species_notice:
            return species_notice

        retrieved = self.rag.retrieve(user_message)
        if retrieved:
            response = "🐾 Based on your question, here's what I found in the pet care knowledge base:\n\n"
            for r in retrieved:
                response += f"- {r}\n"
            return response

        # Small fixed fallbacks for common phrasing the retrieval step may miss.
        if "groom" in lower and "cat" in lower:
            return "🐾 Cats should be groomed regularly. Long-haired cats need grooming daily or every 1-2 days, while short-haired cats can be brushed weekly."
        if "walk" in lower and "dog" in lower:
            return "🐾 Dogs should be walked at least twice a day for about 30 minutes."

        return "🐾 I can help with pet care tips or managing your pet tasks. Type 'help' to see supported commands."

    def reset_conversation(self):
        logger.info("Conversation reset")
