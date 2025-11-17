"""
src/validators.py
(Corrected to add LTPSC fulfillment check)
"""

from typing import List, Dict, Set
from .models import Section, ScheduledClass, Timetable, Course
from . import utils 

def validate_all(all_sections: List[Section], 
                 all_faculty_schedules: Dict[str, Timetable]) -> bool:
    """
    Runs all validation checks and prints a report.
    """
    print("\n--- RUNNING POST-SCHEDULING VALIDATION ---")
    
    student_conflicts = _check_student_conflicts(all_sections)
    faculty_conflicts = _check_faculty_conflicts(all_faculty_schedules)
    daily_limit_conflicts = _check_daily_limits(all_sections)
    break_conflicts = _check_student_breaks(all_sections)
    ltpsc_conflicts = _check_ltpsc_fulfillment(all_sections)
    
    if not student_conflicts and not faculty_conflicts and not daily_limit_conflicts and not break_conflicts and not ltpsc_conflicts:
        print("Validation PASSED: All timetables are conflict-free and LTPSC is fulfilled.")
        return True
    else:
        print("Validation FAILED:")
        if student_conflicts:
            print(f"  Found {len(student_conflicts)} student conflicts.")
            for c in student_conflicts: print(f"    - {c}")
        if faculty_conflicts:
            print(f"  Found {len(faculty_conflicts)} faculty conflicts.")
            for c in faculty_conflicts: print(f"    - {c}")
        if daily_limit_conflicts:
            print(f"  Found {len(daily_limit_conflicts)} daily limit violations.")
            for c in daily_limit_conflicts: print(f"    - {c}")
        if break_conflicts:
            print(f"  Found {len(break_conflicts)} missing student breaks.")
            for c in break_conflicts: print(f"    - {c}")
        if ltpsc_conflicts:
            print(f"  Found {len(ltpsc_conflicts)} LTPSC fulfillment errors.")
            for c in ltpsc_conflicts: print(f"    - {c}")
        return False

def _check_student_conflicts(all_sections: List[Section]) -> List[str]:
    """
    Checks for student conflicts (i.e., double-booking in a section's timetable).
    """
    conflicts = []
    for section in all_sections:
        for day in range(len(utils.DAYS)):
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = section.timetable.grid[day][slot]
                if s_class:
                    is_start = (slot == 0) or (section.timetable.grid[day][slot-1] != s_class)
                    if is_start and s_class.course.course_code not in ["LUNCH", "BREAK"]:
                        duration = s_class.course.get_session_duration(s_class.session_type)
                        if duration == 0: duration = 1
                        
                        for i in range(1, duration):
                            if (slot + i < utils.TOTAL_SLOTS_PER_DAY and
                                section.timetable.grid[day][slot+i] != s_class):
                                conflicts.append(f"Student Slot Conflict: {section.id} at {utils.DAYS[day]} {utils.slot_index_to_time_str(slot)}")
                                break
    return conflicts

def _check_faculty_conflicts(all_faculty_schedules: Dict[str, Timetable]) -> List[str]:
    """
    Checks for faculty conflicts (double-booking or break violations).
    """
    conflicts = []
    for faculty_name, timetable in all_faculty_schedules.items():
        
        for day in range(len(utils.DAYS)):
            last_class_end_slot = -100
            
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = timetable.grid[day][slot]
                if not s_class or s_class.course.course_code in ["LUNCH", "BREAK"]:
                    continue
                    
                is_start = (slot == 0) or (timetable.grid[day][slot-1] != s_class)
                
                if is_start:
                    if (slot - last_class_end_slot) < utils.FACULTY_BREAK_SLOTS:
                        conflicts.append(f"Faculty Break Violation: {faculty_name} at {utils.DAYS[day]} {utils.slot_index_to_time_str(slot)}")
                    
                    duration = s_class.course.get_session_duration(s_class.session_type)
                    if duration == 0: duration = 1
                    last_class_end_slot = slot + duration

    return conflicts

def _check_daily_limits(all_sections: List[Section]) -> List[str]:
    """
    Checks the "one-class-per-day" and "one-lab-per-day" constraint.
    """
    conflicts = []
    for section in all_sections:
        for day in range(len(utils.DAYS)):
            tracker: Dict[str, int] = {}
            
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = section.timetable.grid[day][slot]
                if s_class:
                    is_start = (slot == 0) or (section.timetable.grid[day][slot-1] != s_class)
                    if is_start and s_class.course.course_code not in ["LUNCH", "BREAK"]:
                        key = Timetable._get_session_key(
                            s_class.course.course_code, s_class.session_type
                        )
                        tracker[key] = tracker.get(key, 0) + 1
            
            for key, count in tracker.items():
                if count > 1:
                    conflict_str = f"Daily Limit Violation: {section.id} has {count} '{key}' sessions on {utils.DAYS[day]}"
                    conflicts.append(conflict_str)
                    
    return conflicts

def _check_student_breaks(all_sections: List[Section]) -> List[str]:
    """
    Checks that every class is followed by a BREAK, unless
    it's at the end of the day or just before lunch.
    """
    conflicts = []
    for section in all_sections:
        lunch_start, _ = utils.get_lunch_slots(section.semester)
        
        for day in range(len(utils.DAYS)):
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = section.timetable.grid[day][slot]
                if not s_class:
                    continue
                
                is_start = (slot == 0) or (section.timetable.grid[day][slot-1] != s_class)
                
                if is_start and s_class.course.course_code not in ["LUNCH", "BREAK"]:
                    duration = s_class.course.get_session_duration(s_class.session_type)
                    if duration == 0: duration = 1
                    
                    class_end_slot = slot + duration
                    
                    if class_end_slot == utils.TOTAL_SLOTS_PER_DAY:
                        continue
                    if class_end_slot == lunch_start:
                        continue
                        
                    break_missing = False
                    for i in range(utils.CLASS_BREAK_SLOTS):
                        break_slot_index = class_end_slot + i
                        
                        if break_slot_index >= utils.TOTAL_SLOTS_PER_DAY:
                            break_missing = True
                            break
                        
                        break_slot = section.timetable.grid[day][break_slot_index]
                        
                        if break_slot is None or break_slot.course.course_code != "BREAK":
                            break_missing = True
                            break
                    
                    if break_missing:
                        conflicts.append(f"Missing student break: {section.id} after {s_class.course.course_name} at {utils.DAYS[day]} {utils.slot_index_to_time_str(slot)}")
                        
    return conflicts

def _check_ltpsc_fulfillment(all_sections: List[Section]) -> List[str]:
    """
    Checks if the total number of scheduled sessions for each course
    matches its LTPSC requirements.
    """
    conflicts = []
    
    for section in all_sections:
        
        course_session_counts: Dict[str, Dict[str, int]] = {}
        for key, count in section.timetable.total_session_counts.items():
            parts = key.split('_')
            if len(parts) < 2: continue
            
            course_code = "_".join(parts[:-1])
            session_type = parts[-1]
            
            if course_code not in course_session_counts:
                course_session_counts[course_code] = {}
            course_session_counts[course_code][session_type] = count
            
        scheduled_courses: Dict[str, Course] = {}
        for day_grid in section.timetable.grid:
            for slot in day_grid:
                if slot and slot.course.course_code not in ["LUNCH", "BREAK"]:
                    scheduled_courses[slot.course.course_code] = slot.course

        for course_code, course in scheduled_courses.items():
            if course.is_pseudo_course:
                continue # Pseudo-courses use template LTPSC, skip validation
                
            required = course.get_required_sessions()
            scheduled = course_session_counts.get(course_code, {})
            
            req_lect = required.get('lecture', 0)
            req_tut = required.get('tutorial', 0)
            req_prac = required.get('practical', 0)
            
            sch_lect = scheduled.get('lecture', 0)
            sch_tut = scheduled.get('tutorial', 0)
            sch_prac = scheduled.get('practical', 0)
            
            if course.L == 1:
                req_tut += req_lect
                req_lect = 0
                
            if course.pre_post_preference == "SPLIT":
                if (section.period == "PRE" and section.section_name == "B") or \
                   (section.period == "POST" and section.section_name == "A"):
                    if sch_lect + sch_tut + sch_prac > 0:
                        conflicts.append(f"LTPSC Mismatch: {section.id} has SPLIT course {course_code} in wrong period.")
                    continue
            
            if sch_lect != req_lect:
                conflicts.append(f"LTPSC Mismatch: {section.id} for {course_code}: Expected {req_lect} Lectures, got {sch_lect}")
            if sch_tut != req_tut:
                conflicts.append(f"LTPSC Mismatch: {section.id} for {course_code}: Expected {req_tut} Tutorials, got {sch_tut}")
            if sch_prac != req_prac:
                conflicts.append(f"LTPSC Mismatch: {section.id} for {course_code}: Expected {req_prac} Practicals, got {sch_prac}")

    return sorted(list(set(conflicts)))