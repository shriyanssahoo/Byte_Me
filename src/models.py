"""
src/models.py
Program Description: This file defines the core data structures (Data Classes) used throughout the application. It acts as the "schema" for the software, defining what a Student, Course, Classroom, and Timetable look like. It contains logic for parsing course structures (L-T-P-S-C), calculating session durations, and managing the grid structure of the weekly timetable.
"""

from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from . import utils 

@dataclass
class Classroom:
    room_id: str
    capacity: int
    room_type: str 
    floor: int
    facilities: List[str]

    def __post_init__(self):
        if self.room_id.startswith('C'):
            self.room_type = "CLASSROOM"
        elif self.room_id.startswith('L'):
            self.room_type = "LAB"

@dataclass
class Course:
    course_code: str
    course_name: str
    semester: int
    department: str
    ltpsc_str: str
    credits: int
    instructors: List[str]
    registered_students: int
    is_elective: bool
    is_half_semester: bool
    is_combined: bool
    pre_post_preference: str
    basket_code: str
    
    is_pseudo_basket: bool = False
    bundled_courses: List['Course'] = field(default_factory=list) 
    parent_pseudo_name: Optional[str] = None
    
    L: int = 0
    T: int = 0
    P: int = 0
    
    def __post_init__(self):
        self._parse_ltpsc()
        self._normalize_data()

    def _normalize_data(self):
        self.department = self.department.upper().strip()
        self.course_code = self.course_code.upper().strip()
        self.pre_post_preference = self.pre_post_preference.lower().strip()
        self.basket_code = self.basket_code.upper().strip()

    def _parse_ltpsc(self):
        try:
            if not self.ltpsc_str:
                self.ltpsc_str = "0-0-0-0-0"
            parts = list(map(int, self.ltpsc_str.split('-')))
            if len(parts) >= 3:
                self.L = parts[0]
                self.T = parts[1]
                self.P = parts[2]
        except (ValueError, TypeError, IndexError):
            print(f"Warning: Invalid LTPSC format '{self.ltpsc_str}' for {self.course_code}. Defaulting to 0-0-0.")
            self.L, self.T, self.P = 0, 0, 0

    def get_required_sessions(self) -> Dict[str, int]:
        sessions = {"lecture": 0, "tutorial": 0, "practical": 0}
        
        if self.L in [2, 3]:
            sessions["lecture"] = 2
        elif self.L == 1:
            sessions["tutorial"] += 1
        
        sessions["tutorial"] += self.T
        
        if self.P > 0 and self.P % 2 == 0:
            sessions["practical"] = self.P // 2
        elif self.P > 0:
            print(f"Warning: P={self.P} for {self.course_code} is not even. Rounding up.")
            sessions["practical"] = (self.P + 1) // 2
        return sessions
        
    def get_session_duration(self, session_type: str) -> int:
        session_type_lower = session_type.lower()
        if session_type_lower == "lecture":
            return utils.LECTURE_SLOTS
        if session_type_lower == "tutorial":
            return utils.TUTORIAL_SLOTS
        if session_type_lower == "practical":
            return utils.PRACTICAL_SLOTS
        return 0

@dataclass
class ScheduledClass:
    course: Course
    session_type: str  # This will now ALWAYS be lowercase (e.g., 'lecture')
    section_id: str
    instructors: List[str]
    room_ids: List[str]

@dataclass
class Section:
    id: str
    department: str
    semester: int
    period: str
    section_name: str
    
    timetable: 'Timetable' = field(init=False)
    
    def __post_init__(self):
        self.timetable = Timetable(self.id, self.semester)
        lunch_start, lunch_end = utils.get_lunch_slots(self.semester)
        self.timetable.set_lunch_break(lunch_start, lunch_end)

class Timetable:
    def __init__(self, owner_id: str, semester: int = -1):
        self.owner_id = owner_id
        self.semester = semester
        self.grid: List[List[Optional[ScheduledClass]]] = [
            [None for _ in range(utils.TOTAL_SLOTS_PER_DAY)]
            for _ in range(len(utils.DAYS))
        ]
        
        self.daily_session_tracker: List[Set[str]] = [set() for _ in range(len(utils.DAYS))]
        self.day_load_tracker: List[int] = [0] * len(utils.DAYS)
        self.total_session_counts: Dict[str, int] = {}
        
        self.lunch_marker = self._create_marker_class("LUNCH", "Lunch Break")
        self.break_marker = self._create_marker_class("BREAK", "Break")

    def _create_marker_class(self, code: str, name: str) -> ScheduledClass:
        course = Course(code, name, 0, "", "0-0-0-0-0", 0, [], 0, False, False, False, "", "")
        return ScheduledClass(
            course=course,
            session_type=code.lower(),
            section_id=self.owner_id,
            instructors=[],
            room_ids=[]
        )

    def set_lunch_break(self, start_slot: int, end_slot: int):
        if start_slot == -1: return
        for day in range(len(utils.DAYS)):
            for slot in range(start_slot, end_slot):
                if 0 <= slot < utils.TOTAL_SLOTS_PER_DAY:
                    self.grid[day][slot] = self.lunch_marker

    def is_slot_free(self, day_index: int, start_slot: int, duration_slots: int) -> bool:
        if (start_slot + duration_slots) > utils.TOTAL_SLOTS_PER_DAY:
            return False
        for i in range(duration_slots):
            slot = start_slot + i
            if self.grid[day_index][slot] is not None:
                return False
        return True

    @staticmethod
    def _get_session_key(course_code: str, session_type: str) -> str:
        # No .lower() needed, session_type is guaranteed to be lowercase
        if session_type in ["lecture", "tutorial"]:
            return f"{course_code}_CLASS"
        elif session_type == "practical":
            return f"{course_code}_LAB"
        else:
            return f"{course_code}_{session_type}"

    def check_daily_limit_violation(self, day_index: int, course_code: str, session_type: str) -> bool:
        # session_type is guaranteed to be lowercase
        key = self._get_session_key(course_code, session_type)
        return key in self.daily_session_tracker[day_index]

    def book_slot(self, day_index: int, start_slot: int, duration_slots: int, class_info: ScheduledClass):
        if not self.is_slot_free(day_index, start_slot, duration_slots):
            current_class = self.grid[day_index][start_slot]
            if current_class is None or not current_class.course.is_pseudo_basket:
                print(f"Warning: Attempted to double-book {self.owner_id} at {utils.DAYS[day_index]} {utils.slot_index_to_time_str(start_slot)}")
        
        for i in range(duration_slots):
            slot = start_slot + i
            if 0 <= slot < utils.TOTAL_SLOTS_PER_DAY:
                self.grid[day_index][slot] = class_info
        
        # --- THIS IS THE FIX ---
        # Track stats for ALL classes, including placeholders, but not breaks
        if class_info.course.course_code not in ["LUNCH", "BREAK"]:
            # We trust class_info.session_type is already lowercase
            session_key = self._get_session_key(class_info.course.course_code, class_info.session_type)
            self.daily_session_tracker[day_index].add(session_key)
            
            if not class_info.course.is_pseudo_basket:
                ltpsc_key = f"{class_info.course.course_code}_{class_info.session_type}"
                self.total_session_counts[ltpsc_key] = self.total_session_counts.get(ltpsc_key, 0) + 1
            
            self.day_load_tracker[day_index] += duration_slots
        # --- END OF FIX ---

        class_end_slot = start_slot + duration_slots
        lunch_start, _ = utils.get_lunch_slots(self.semester)
        is_end_of_day = (class_end_slot == utils.TOTAL_SLOTS_PER_DAY)
        is_before_lunch = (class_end_slot == lunch_start)
        
        if not is_end_of_day and not is_before_lunch:
            for i in range(utils.CLASS_BREAK_SLOTS):
                break_slot = class_end_slot + i
                if break_slot < utils.TOTAL_SLOTS_PER_DAY and self.grid[day_index][break_slot] is None:
                    self.grid[day_index][break_slot] = self.break_marker
                    if class_info.course.course_code not in ["LUNCH", "BREAK"]:
                        self.day_load_tracker[day_index] += 1