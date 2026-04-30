from pawpal_system import Owner, Pet, Task, Scheduler
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# Session state
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Assem")

owner = st.session_state.owner

# Tabs
tab1, tab2 = st.tabs(["Pets & Tasks", "Schedule"])

# Tab 1: Manage Pets & Tasks
with tab1:
    st.header("Add a Pet")
    pet_name = st.text_input("Pet Name")
    pet_type = st.text_input("Pet Type")
    pet_age = st.number_input("Pet Age", min_value=0)

    if st.button("Add Pet"):
        if pet_name and pet_type:
            owner.add_pet(Pet(pet_name, pet_type, int(pet_age)))
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
                for pet in owner.pets:
                    if pet.name == selected_pet:
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
    st.header("Today's Schedule")
    scheduler = Scheduler(owner)

    if st.button("Generate Schedule"):
        tasks = scheduler.sort_by_time(scheduler.get_all_tasks())
        if tasks:
            st.table(
                [
                    {
                        "Task": t.description,
                        "Time": t.scheduled_time.strftime("%I:%M %p"),
                        "Priority": t.priority,
                        "Status": "Done" if t.completed else "Pending",
                    }
                    for t in tasks
                ]
            )
            next_slot = scheduler.find_next_available_slot()
            if next_slot:
                st.info(f"Next available slot: {next_slot.strftime('%I:%M %p')}")
            for t1, t2 in scheduler.detect_conflicts():
                st.warning(f"⚠️ Conflict: '{t1.description}' and '{t2.description}' at the same time!")
        else:
            st.info("No tasks scheduled yet.")
