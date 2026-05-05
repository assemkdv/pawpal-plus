from pawpal_system import Owner, Pet, Task, Scheduler
from ai_assistant import PawPalAI
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# Session state
if "owner" not in st.session_state:
    st.session_state.owner = Owner("User")
if "ai" not in st.session_state:
    st.session_state.ai = None
if "messages" not in st.session_state:
    st.session_state.messages = []

owner = st.session_state.owner

# Tabs
tab1, tab2, tab3 = st.tabs(["Pets & Tasks", "Schedule", "Assistant"])

# Tab 1: Manage Pets & Tasks
with tab1:
    st.header("Add a Pet")
    pet_name = st.text_input("Pet Name")
    pet_type = st.text_input("Pet Type")
    pet_age = st.number_input("Pet Age", min_value=0)

    if st.button("Add Pet"):
        if pet_name and pet_type:
            if owner.find_pet(pet_name):
                st.error(f"You already have a pet named '{pet_name}'. Pet names must be unique.")
            else:
                owner.add_pet(Pet(pet_name, pet_type, int(pet_age)))
                st.session_state.ai = None
                st.success(f"{pet_name} added!")
        else:
            st.error("Please enter pet name and type.")

    st.header("Your Pets")
    if owner.pets:
        for pet in owner.pets:
            st.write(f"🐾 **{pet.name}** ({pet.type}, {pet.age} yrs) — {len(pet.tasks)} task(s)")
    else:
        st.write("No pets added yet.")

    st.header("Add Task")
    if owner.pets:
        selected_pet = st.selectbox("Select Pet", [p.name for p in owner.pets])
        task_desc = st.text_input("Task Description")
        task_time = st.time_input("Task Time", value=datetime.now().replace(second=0, microsecond=0).time())
        task_priority = st.slider("Priority", 1, 5, 2)
        task_freq = st.selectbox("Frequency", ["once", "daily", "weekly"])

        if st.button("Add Task"):
            if task_desc:
                pet = owner.find_pet(selected_pet)
                scheduled = datetime.now().replace(
                    hour=task_time.hour, minute=task_time.minute, second=0, microsecond=0
                )
                pet.add_task(Task(task_desc, scheduled, task_priority, task_freq))
                st.success("Task added!")
            else:
                st.error("Please enter a task description.")
    else:
        st.warning("Add a pet first.")

# Tab 2: Schedule
with tab2:
    st.header("Schedule")
    scheduler = Scheduler(owner)

    view = st.radio("Show", ["Today", "Upcoming", "All"], horizontal=True)
    tasks = scheduler.sort_by_time(scheduler.get_all_tasks())
    today = datetime.now().date()

    if view == "Today":
        tasks = [t for t in tasks if t.scheduled_time.date() == today]
    elif view == "Upcoming":
        tasks = [t for t in tasks if t.scheduled_time.date() >= today]
    # "All" keeps every task, including past ones.

    if not tasks:
        st.info("No tasks to show for this view.")
    else:
        header_cols = st.columns([3, 2, 2, 1, 2, 2])
        for col, label in zip(header_cols, ["Task", "Date", "Time", "Priority", "Status", ""]):
            col.markdown(f"**{label}**")

        for task in tasks:
            cols = st.columns([3, 2, 2, 1, 2, 2])
            cols[0].write(task.description)
            cols[1].write(task.scheduled_time.strftime("%b %d"))
            cols[2].write(task.scheduled_time.strftime("%I:%M %p"))
            cols[3].write(task.priority)
            cols[4].write("Done" if task.completed else "Pending")
            if task.completed:
                cols[5].write("✅")
            else:
                if cols[5].button("Complete", key=f"complete-{id(task)}"):
                    scheduler.complete_task(task)
                    st.rerun()

        next_slot = scheduler.find_next_available_slot()
        if next_slot:
            st.caption(f"Next available slot: {next_slot.strftime('%b %d, %I:%M %p')}")

        for t1, t2 in scheduler.detect_conflicts():
            st.warning(
                f"⚠️ Conflict: '{t1.description}' and '{t2.description}' at "
                f"{t1.scheduled_time.strftime('%b %d, %I:%M %p')}"
            )

# Tab 3: Assistant
with tab3:
    st.header("Assistant")
    st.caption(
        "Chat using a small set of supported commands (type 'help' to see them), or ask a "
        "general pet care question. Pet care answers use lightweight local TF-IDF retrieval over "
        "a curated knowledge base — not an external LLM or API."
    )

    if st.session_state.ai is None:
        st.session_state.ai = PawPalAI(owner, Scheduler(owner))

    ai = st.session_state.ai

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("e.g. 'add task Buddy, walk, 9, 0, 3, daily' or 'How often should I groom my cat?'")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = ai.chat(user_input)
            st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

    if st.session_state.messages:
        if st.button("Clear Chat"):
            st.session_state.messages = []
            ai.reset_conversation()
            st.rerun()
