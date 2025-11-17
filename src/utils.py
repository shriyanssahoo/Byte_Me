"""
src/utils.py
"""
import re
from datetime import time
from typing import Tuple, List

# --- Core Time Constants ---
SLOT_DURATION_MINS: int = 10
START_TIME_STR: str = "09:00"
END_TIME_STR: str = "18:00"
DAYS: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# --- Derived Time Constants ---
START_TIME: time = time.fromisoformat(START_TIME_STR)
END_TIME: time = time.fromisoformat(END_TIME_STR)
TOTAL_DAY_MINUTES: int = (END_TIME.hour - START_TIME.hour) * 60
TOTAL_SLOTS_PER_DAY: int = TOTAL_DAY_MINUTES // SLOT_DURATION_MINS # 54 slots

# --- Configurable Break Time ---
CLASS_BREAK_MINS: int = 10

# --- Scheduling Logic Constants (Rule: 1.5hr, 1hr, 2hr) ---
LECTURE_SLOTS: int = 90 // SLOT_DURATION_MINS         # 9 slots (1.5 hours)
TUTORIAL_SLOTS: int = 60 // SLOT_DURATION_MINS       # 6 slots (1 hour)
PRACTICAL_SLOTS: int = 120 // SLOT_DURATION_MINS      # 12 slots (2 hours)
FACULTY_BREAK_SLOTS: int = 30 // SLOT_DURATION_MINS  # 3 slots (30 min)
CLASS_BREAK_SLOTS: int = CLASS_BREAK_MINS // SLOT_DURATION_MINS # 1 slot (10 min)


def time_to_slot_index(time_str: str) -> int:
    try:
        t = time.fromisoformat(time_str)
        if t < START_TIME or t >= END_TIME:
            return -1
        delta_mins = (t.hour - START_TIME.hour) * 60 + (t.minute - START_TIME.minute)
        return delta_mins // SLOT_DURATION_MINS
    except ValueError:
        return -1

def slot_index_to_time_str(index: int) -> str:
    if index < 0 or index >= TOTAL_SLOTS_PER_DAY:
        return "Invalid Slot"
    total_mins = index * SLOT_DURATION_MINS
    hours = START_TIME.hour + (total_mins // 60)
    minutes = START_TIME.minute + (total_mins % 60)
    if minutes >= 60:
        hours += 1
        minutes -= 60
    return f"{hours:02d}:{minutes:02d}"

def get_floor_from_room(room_id: str) -> int:
    match = re.search(r'\d', room_id)
    if not match:
        return -1
    numeric_part = room_id[match.start():]
    try:
        return int(numeric_part[0])
    except (ValueError, IndexError):
        return -1

def get_room_number_from_id(room_id: str) -> int:
    match = re.search(r'\d+', room_id)
    if not match:
        return -1
    try:
        return int(match.group(0))
    except ValueError:
        return -1

def get_lunch_slots(semester: int) -> Tuple[int, int]:
    start_slot = -1
    if semester == 1 or semester == 7:
        start_slot = time_to_slot_index("12:30")
    elif semester == 3:
        start_slot = time_to_slot_index("13:00")
    elif semester == 5:
        start_slot = time_to_slot_index("13:30")
    else:
        # Fallback for other semesters (e.g., if you add Sem 2)
        start_slot = time_to_slot_index("13:00")
        
    end_slot = start_slot + 3 # 30-minute lunch
    return (start_slot, end_slot)

def get_time_slots_list() -> List[str]:
    slots = []
    for i in range(TOTAL_SLOTS_PER_DAY):
        start = slot_index_to_time_str(i)
        end = slot_index_to_time_str(i + 1)
        slots.append(f"{start} - {end}")
    return slots