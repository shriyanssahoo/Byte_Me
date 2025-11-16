"""
src/scheduler.py
(Corrected: Core courses (is_combined=no) are now scheduled
independently per-section, fixing the "CS161 not scheduling" bug)
"""

from typing import List, Dict, Optional, Tuple, Set
from .models import Course, Classroom, Section, ScheduledClass, Timetable
from . import utils 
import copy
import random 

class Scheduler:
    """
    The main scheduling engine.
    """
    
    def __init__(self, classrooms: List[Classroom], run_period: str):
        self.run_period = run_period.upper()
        print(f"\n--- INITIALIZING {self.run_period} MIDSEM SCHEDULING RUN ---")
        
        self.all_classrooms = classrooms
        self.room_lookup = {r.room_id: r for r in classrooms} 
        self.c004_room = None
        self.general_classrooms: List[Classroom] = []
        self.labs: List[Classroom] = []
        
        for r in classrooms:
            if r.room_id == "C004":
                self.c004_room = r
            elif r.room_type == "CLASSROOM":
                self.general_classrooms.append(r)
            elif r.room_type == "LAB":
                self.labs.append(r)
        
        self.faculty_schedules: Dict[str, Timetable] = {}
        self.room_schedules: Dict[str, Timetable] = {}
        
        self.failed_courses: List[Tuple[Course, str]] = []
        self.overflow_electives: List[Course] = [] # For 'elective' rule

    def _get_or_create_faculty_schedule(self, faculty_name: str) -> Timetable:
        if faculty_name not in self.faculty_schedules:
            self.faculty_schedules[faculty_name] = Timetable(owner_id=faculty_name, semester=-1)
        return self.faculty_schedules[faculty_name]

    def _get_or_create_room_schedule(self, room_id: str) -> Timetable:
        if room_id not in self.room_schedules:
            if room_id not in self.room_lookup:
                raise ValueError(f"Attempted to schedule in non-existent room: {room_id}")
            self.room_schedules[room_id] = Timetable(owner_id=room_id, semester=-1)
        return self.room_schedules[room_id]

    def _get_total_duration_with_break(self, semester: int, start_slot: int, class_duration: int) -> int:
        class_end_slot = start_slot + class_duration
        lunch_start, _ = utils.get_lunch_slots(semester)
        
        is_end_of_day = (class_end_slot == utils.TOTAL_SLOTS_PER_DAY)
        is_before_lunch = (class_end_slot == lunch_start)
        
        if is_end_of_day or is_before_lunch:
            return class_duration
        else:
            return class_duration + utils.CLASS_BREAK_SLOTS

    def _check_faculty_availability(self, instructors: List[str], day: int, start_slot: int, duration: int) -> bool:
        for instructor in instructors:
            if instructor == "TBD":
                continue
            faculty_tt = self._get_or_create_faculty_schedule(instructor)
            
            check_start = start_slot - utils.FACULTY_BREAK_SLOTS
            check_end = start_slot + duration + utils.FACULTY_BREAK_SLOTS
            
            for slot in range(check_start, check_end):
                if 0 <= slot < utils.TOTAL_SLOTS_PER_DAY:
                    if not faculty_tt.is_slot_free(day, slot, 1):
                        return False
        return True

    def _find_available_room(self, day: int, start_slot: int, duration: int, 
                             room_type: str, capacity: int) -> Optional[Classroom]:
        
        if room_type == "LAB":
            room_pool = self.labs
        else:
            room_pool = self.general_classrooms
        
        sorted_rooms = sorted(
            [r for r in room_pool if r.capacity >= capacity],
            key=lambda r: r.capacity
        )
        
        random.shuffle(sorted_rooms)
        
        for room in sorted_rooms:
            room_tt = self._get_or_create_room_schedule(room.room_id)
            if room_tt.is_slot_free(day, start_slot, duration):
                return room
        return None
    
    def _find_adjacent_labs(self, day: int, start_slot: int, duration: int, 
                            capacity: int) -> Optional[List[Classroom]]:
        labs = sorted(
            self.labs,
            key=lambda r: (r.floor, utils.get_room_number_from_id(r.room_id))
        )
        
        for i in range(len(labs) - 1):
            lab1 = labs[i]
            lab2 = labs[i+1]
            
            if (lab1.floor != lab2.floor or
                utils.get_room_number_from_id(lab2.room_id) != utils.get_room_number_from_id(lab1.room_id) + 1):
                continue
                
            if (lab1.capacity + lab2.capacity) < capacity:
                continue
                
            lab1_tt = self._get_or_create_room_schedule(lab1.room_id)
            lab2_tt = self._get_or_create_room_schedule(lab2.room_id)
            
            if (lab1_tt.is_slot_free(day, start_slot, duration) and
                lab2_tt.is_slot_free(day, start_slot, duration)):
                return [lab1, lab2]
                
        return None

    def _find_common_slot(self, sections: List[Section], course: Course,
                         session_type: str, duration: int) -> Optional[Tuple[int, int]]:
        if not sections: return None
        semester = sections[0].semester
        
        avg_day_load = [0] * len(utils.DAYS)
        for day in range(len(utils.DAYS)):
            for section in sections:
                avg_day_load[day] += section.timetable.day_load_tracker[day]
        
        sorted_days = sorted(range(len(utils.DAYS)), key=lambda d: avg_day_load[d])

        for day in sorted_days:
            
            daily_limit_violation = any(
                s.timetable.check_daily_limit_violation(day, course.course_code, session_type) 
                for s in sections
            )
            if daily_limit_violation:
                continue

            for start_slot in range(utils.TOTAL_SLOTS_PER_DAY - duration + 1):
                
                total_duration = self._get_total_duration_with_break(semester, start_slot, duration)
                if (start_slot + total_duration) > utils.TOTAL_SLOTS_PER_DAY:
                    continue

                sections_free = all(
                    s.timetable.is_slot_free(day, start_slot, total_duration) for s in sections
                )
                if not sections_free:
                    continue

                faculty_free = self._check_faculty_availability(course.instructors, day, start_slot, duration)
                if not faculty_free:
                    continue
                    
                return (day, start_slot)
                
        return None

    def _book_session(self, sections: List[Section], class_info_template: ScheduledClass, 
                      day: int, start_slot: int, duration: int, rooms: List[Classroom]):
        room_ids = [r.room_id for r in rooms]
        
        booking = copy.deepcopy(class_info_template)
        booking.room_ids = room_ids
        
        for section in sections:
            section_booking = copy.copy(booking)
            section_booking.section_id = section.id
            section.timetable.book_slot(day, start_slot, duration, section_booking)
            
        for instructor in booking.instructors:
            if instructor == "TBD":
                continue
            faculty_tt = self._get_or_create_faculty_schedule(instructor)
            faculty_tt.book_slot(day, start_slot, duration, booking)
            
        for room in rooms:
            room_tt = self._get_or_create_room_schedule(room.room_id)
            room_tt.book_slot(day, start_slot, duration, booking)

    def _schedule_phase_combined(self, sections_by_dept: Dict[str, List[Section]], courses: List[Course]):
        print("  Running Phase 1: Combined Classes (is_combined=yes)")
        for course in courses:
            if not course.is_combined:
                continue

            # A combined course is only for sections *within its own department*
            sections_to_schedule = sections_by_dept.get(course.department, [])
            
            if not sections_to_schedule:
                continue

            room = self.c004_room
            if not room:
                self.failed_courses.append((course, "All Sections - C004 missing"))
                continue
            
            if room.capacity < course.registered_students:
                 self.failed_courses.append((course, f"C004 is too small for {course.registered_students} students"))
                 continue
            
            semester = sections_to_schedule[0].semester
            sessions = course.get_required_sessions()
            
            for session_type, count in sessions.items():
                if count == 0: continue
                duration = course.get_session_duration(session_type)
                
                for _ in range(count):
                    room_tt = self._get_or_create_room_schedule(room.room_id)
                    slot = None
                    
                    avg_day_load = [0] * len(utils.DAYS)
                    for day_idx in range(len(utils.DAYS)):
                        for s in sections_to_schedule:
                            avg_day_load[day_idx] += s.timetable.day_load_tracker[day_idx]
                    sorted_days = sorted(range(len(utils.DAYS)), key=lambda d: avg_day_load[d])

                    for day in sorted_days:
                        daily_limit_violation = any(
                            s.timetable.check_daily_limit_violation(day, course.course_code, session_type)
                            for s in sections_to_schedule
                        )
                        if daily_limit_violation:
                            continue

                        for start_slot in range(utils.TOTAL_SLOTS_PER_DAY - duration + 1):
                            total_duration = self._get_total_duration_with_break(semester, start_slot, duration)
                            if (start_slot + total_duration) > utils.TOTAL_SLOTS_PER_DAY:
                                continue

                            if (room_tt.is_slot_free(day, start_slot, duration) and
                                all(s.timetable.is_slot_free(day, start_slot, total_duration) for s in sections_to_schedule) and
                                self._check_faculty_availability(course.instructors, day, start_slot, duration)):
                                slot = (day, start_slot)
                                break
                        if slot: break
                    
                    if slot:
                        day, start_slot = slot
                        class_info = ScheduledClass(
                            course=course, session_type=session_type.capitalize(),
                            section_id="COMBINED", instructors=course.instructors, room_ids=[]
                        )
                        self._book_session(sections_to_schedule, class_info, day, start_slot, duration, [room])
                    else:
                        print(f"  Failed: {course.course_code} (Combined {session_type})")
                        self.failed_courses.append((course, f"All Sections - No common C004 slot for {session_type}"))

    def _find_common_slot_for_basket(self, sections: List[Section], course: Course, 
                                     session_type: str, duration: int) -> Optional[Tuple[int, int]]:
        
        if not sections: return None
        semester = sections[0].semester
        
        avg_day_load = [0] * len(utils.DAYS)
        for day in range(len(utils.DAYS)):
            for section in sections:
                avg_day_load[day] += section.timetable.day_load_tracker[day]
        sorted_days = sorted(range(len(utils.DAYS)), key=lambda d: avg_day_load[d])

        for day in sorted_days:
            
            daily_limit_violation = any(
                s.timetable.check_daily_limit_violation(day, course.course_code, session_type)
                for s in sections
            )
            if daily_limit_violation:
                continue

            for start_slot in range(utils.TOTAL_SLOTS_PER_DAY - duration + 1):
                
                total_duration = self._get_total_duration_with_break(semester, start_slot, duration)
                if (start_slot + total_duration) > utils.TOTAL_SLOTS_PER_DAY:
                    continue
                
                sections_free = all(
                    s.timetable.is_slot_free(day, start_slot, total_duration) for s in sections
                )
                if not sections_free:
                    continue

                # Baskets have TBD instructors, so no faculty check needed
                return (day, start_slot)
                
        return None

    def _schedule_phase_baskets(self, sections_by_dept: Dict[str, List[Section]], courses: List[Course]):
        print("  Running Phase 2: Baskets & Electives (is_pseudo_basket=true)")
        
        for course in courses:
            if not course.is_pseudo_basket:
                continue
            
            # This is a pseudo-course, get ALL sections for its semester
            all_semester_sections = sections_by_dept.get("ALL_DEPTS", [])
            sections_to_schedule = [s for s in all_semester_sections if s.semester == course.semester]
            
            unique_sections = []
            seen_ids = set()
            for s in sections_to_schedule:
                if s.id not in seen_ids:
                    unique_sections.append(s)
                    seen_ids.add(s.id)
            sections_to_schedule = unique_sections
            
            if not sections_to_schedule:
                continue
            
            sessions = course.get_required_sessions()
            for session_type, count in sessions.items():
                if count == 0: continue
                duration = course.get_session_duration(session_type)
                
                for _ in range(count):
                    # Find a common slot for all sections
                    slot = self._find_common_slot(sections_to_schedule, course, session_type, duration)
                    if not slot:
                        print(f"  Failed: {course.course_name} (No common slot)")
                        self.failed_courses.append((course, "No common slot"))
                        continue
                    
                    day, start_slot = slot
                    
                    # Book this pseudo-course in all sections, each gets its own room
                    all_rooms_found = True
                    rooms_to_book: List[Tuple[Section, Classroom]] = []
                    
                    for section in sections_to_schedule:
                        # Find a room *just for this section*
                        room = self._find_available_room(day, start_slot, duration, "CLASSROOM", 100) # 100=avg
                        if room:
                            rooms_to_book.append((section, room))
                        else:
                            all_rooms_found = False
                            self.failed_courses.append((course, f"Basket - No room for {section.id}"))
                            break
                    
                    if all_rooms_found:
                        # Book each section in its own room
                        for section, room in rooms_to_book:
                            class_info = ScheduledClass(
                                course=course, session_type=session_type.capitalize(),
                                section_id=section.id, instructors=course.instructors, room_ids=[]
                            )
                            self._book_session([section], class_info, day, start_slot, duration, [room])
                    else:
                        print(f"  Failed: {course.course_name} (Could not find rooms for all sections)")
                        # If it's an 'elective' (overflow), add to list
                        if course.pre_post_preference == "OVERFLOW" and self.run_period == "PRE":
                            self.overflow_electives.append(course)


    def _schedule_phase_core_courses(self, sections_by_dept: Dict[str, List[Section]], courses: List[Course]):
        print("  Running Phase 3: Core Courses (is_combined=no)")
        sorted_courses = sorted(courses, key=lambda c: (c.P == 0, c.L == 0))
        
        for course in sorted_courses:
            if course.is_combined or course.is_pseudo_basket:
                continue # Handled in other phases

            sections_to_schedule = []
            if course.pre_post_preference.lower() == "pre/post": # 'SPLIT' logic
                if self.run_period == "PRE":
                    sections_to_schedule = [s for s in sections_by_dept.get(course.department, []) if s.section_name == "A"]
                elif self.run_period == "POST":
                    sections_to_schedule = [s for s in sections_by_dept.get(course.department, []) if s.section_name == "B"]
            elif course.pre_post_preference.lower() in ["full", "pre", "post"]:
                sections_to_schedule = sections_by_dept.get(course.department, [])
            
            if not sections_to_schedule:
                continue
            
            # --- THIS IS THE FIX for CS161 ---
            # Loop through each section and schedule it independently
            for section in sections_to_schedule:
                sessions = course.get_required_sessions()
                session_map = [
                    ("Practical", sessions["practical"], utils.PRACTICAL_SLOTS),
                    ("Lecture", sessions["lecture"], utils.LECTURE_SLOTS),
                    ("Tutorial", sessions["tutorial"], utils.TUTORIAL_SLOTS)
                ]
                
                # Get student count for this section
                student_count = 100 # default
                if course.department == "CSE":
                    student_count = course.registered_students // 2
                else:
                    student_count = course.registered_students

                for session_type, count, duration in session_map:
                    if count == 0: continue
                    
                    for _ in range(count):
                        # Find slot for *this section only*
                        slot = self._find_common_slot([section], course, session_type, duration)
                        if not slot:
                            print(f"  Failed: {course.course_code} ({session_type} for {section.id} - No slot)")
                            self.failed_courses.append((course, f"{session_type} for {section.id} - No slot"))
                            continue
                        
                        day, start_slot = slot
                        
                        rooms = None
                        if session_type.lower() == "practical":
                            if course.department == "CSE" and student_count > 50: # 50 is one lab cap
                                rooms = self._find_adjacent_labs(day, start_slot, duration, student_count)
                            if not rooms:
                                room = self._find_available_room(day, start_slot, duration, "LAB", student_count)
                                rooms = [room] if room else None
                        else:
                            room = self._find_available_room(day, start_slot, duration, "CLASSROOM", student_count)
                            rooms = [room] if room else None
                        
                        if rooms:
                            class_info = ScheduledClass(
                                course=course, session_type=session_type.capitalize(),
                                section_id=section.id, instructors=course.instructors, room_ids=[]
                            )
                            self._book_session([section], class_info, day, start_slot, duration, rooms)
                        else:
                            print(f"  Failed: {course.course_code} ({session_type} for {section.id} - No room)")
                            self.failed_courses.append((course, f"{session_type} for {section.id} - No room"))


    def run(self, courses: List[Course], sections: List[Section]) -> Tuple[List[Section], List[Course]]:
        
        sections_by_dept: Dict[str, List[Section]] = {}
        for s in sections:
            sections_by_dept.setdefault(s.department, []).append(s)
            
            # Add section to cross-dept key
            sections_by_dept.setdefault("ALL_DEPTS", []).append(s)
        
        basket_courses = [c for c in courses if c.is_pseudo_basket]
        combined_courses = [c for c in courses if c.is_combined]
        core_courses = [c for c in courses if not c.is_combined and not c.is_pseudo_basket]
        
        self._schedule_phase_combined(sections_by_dept, combined_courses)
        self._schedule_phase_baskets(sections_by_dept, basket_courses)
        self._schedule_phase_core_courses(sections_by_dept, core_courses)
        
        print(f"--- {self.run_period} RUN COMPLETE ---")
        if self.failed_courses:
            print(f"  Warning: {len(self.failed_courses)} courses/sessions failed permanently in this run.")
        if self.overflow_electives:
            print(f"  Info: {len(set(c.course_code for c in self.overflow_electives))} electives failed room allocation and will overflow to POST.")
            
        return sections, list(set(self.overflow_electives))