from pawpal_system import Owner, Scheduler
from ai_assistant import PawPalAI, PetCareRAG, PET_CARE_KNOWLEDGE


def _make_ai():
    owner = Owner("Test")
    scheduler = Scheduler(owner)
    return PawPalAI(owner, scheduler), owner


def test_add_pet_command():
    ai, owner = _make_ai()
    reply = ai.chat("add pet Buddy, dog, 3")

    assert "Buddy" in reply
    pet = owner.find_pet("Buddy")
    assert pet is not None
    assert pet.type == "dog"
    assert pet.age == 3


def test_add_pet_is_case_insensitive_but_preserves_the_value():
    ai, owner = _make_ai()
    ai.chat("Add Pet Buddy, dog, 3")

    # The command word itself is case-insensitive, but the extracted name
    # must be exactly "Buddy", not "Add Pet Buddy".
    assert owner.find_pet("Buddy") is not None
    assert owner.find_pet("Add Pet Buddy") is None


def test_add_pet_rejects_duplicate_name_case_insensitively():
    ai, owner = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    reply = ai.chat("add pet buddy, dog, 5")

    assert "already have a pet" in reply.lower()
    assert len(owner.pets) == 1


def test_ordinary_question_mentioning_add_pet_is_not_misrouted():
    ai, _ = _make_ai()
    reply = ai.chat("Can you add pet insurance tips to my notes?")

    assert "Format: add pet" not in reply


def test_add_task_command():
    ai, owner = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    reply = ai.chat("add task Buddy, walk, 9, 0, 3, daily")

    assert "added" in reply.lower()
    pet = owner.find_pet("Buddy")
    assert len(pet.tasks) == 1
    assert pet.tasks[0].description == "walk"


def test_add_task_rejects_invalid_hour_without_raw_exception_text():
    ai, _ = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    reply = ai.chat("add task Buddy, walk, 25, 0, 3, daily")

    assert "Hour" in reply
    assert "ValueError" not in reply
    assert "Traceback" not in reply


def test_add_task_rejects_invalid_minute():
    ai, _ = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    reply = ai.chat("add task Buddy, walk, 9, 75, 3, daily")

    assert "Minute" in reply


def test_add_task_rejects_invalid_priority():
    ai, _ = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    reply = ai.chat("add task Buddy, walk, 9, 0, 9, daily")

    assert "Priority" in reply


def test_add_task_rejects_invalid_frequency():
    ai, owner = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    reply = ai.chat("add task Buddy, walk, 9, 0, 3, sometimes")

    assert "Frequency" in reply
    pet = owner.find_pet("Buddy")
    assert len(pet.tasks) == 0


def test_list_pets_and_list_tasks_commands():
    ai, _ = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    ai.chat("add task Buddy, walk, 9, 0, 3, daily")

    assert "Buddy" in ai.chat("list pets")
    assert "walk" in ai.chat("list tasks")


def test_complete_task_command_marks_task_and_reports_next_occurrence():
    ai, owner = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    ai.chat("add task Buddy, walk, 9, 0, 3, daily")

    reply = ai.chat("complete task Buddy, walk")

    pet = owner.find_pet("Buddy")
    assert reply.startswith("✅")
    assert "Next occurrence" in reply
    assert pet.tasks[0].completed is True
    assert len(pet.tasks) == 2


def test_complete_task_ambiguous_match_asks_for_specificity():
    ai, owner = _make_ai()
    ai.chat("add pet Buddy, dog, 3")
    ai.chat("add task Buddy, walk, 9, 0, 3, once")
    ai.chat("add task Buddy, walk, 18, 0, 1, once")

    reply = ai.chat("complete task Buddy, walk")

    assert "more specific" in reply.lower()
    pet = owner.find_pet("Buddy")
    assert all(not t.completed for t in pet.tasks)


def test_complete_task_unknown_pet():
    ai, _ = _make_ai()
    reply = ai.chat("complete task Ghost, walk")

    assert "not found" in reply.lower()


def test_help_command_lists_supported_commands():
    ai, _ = _make_ai()
    reply = ai.chat("help")

    assert "add pet" in reply
    assert "complete task" in reply


def test_urgent_query_returns_vet_escalation_not_diagnosis():
    ai, _ = _make_ai()
    reply = ai.chat("My dog is having a seizure, what dosage of medication should I give?")

    assert "veterinar" in reply.lower()


def test_unsupported_species_gets_scope_message_not_unrelated_answer():
    ai, _ = _make_ai()
    reply = ai.chat("How do I care for my pet bird?")

    assert "dogs and cats" in reply.lower()


def test_retrieval_returns_relevant_entry_for_known_topic():
    rag = PetCareRAG(PET_CARE_KNOWLEDGE)
    results = rag.retrieve("How often should I groom my cat?")

    assert results
    assert any("groom" in r.lower() for r in results)


def test_retrieval_returns_empty_for_unrelated_query():
    rag = PetCareRAG(PET_CARE_KNOWLEDGE)
    results = rag.retrieve("What's the capital of France?")

    assert results == []


def test_chat_falls_back_gracefully_when_nothing_matches():
    ai, _ = _make_ai()
    reply = ai.chat("asdkjfhaskjdfh")

    assert "help" in reply.lower()
