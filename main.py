"""
main.py

Main entry point for the Automated Timetable Scheduler.
This has been rebuilt to handle Sem 1/3/5 and Sem 7 separately.
"""

import os
from typing import List, Dict, Set
import src.utils as utils
from src.models import Section, Classroom, Course, Timetable
from src.data_loader import load_classrooms, load_and_process_courses
from src.scheduler import Scheduler
from src.validators import validate_all
from src.excel_exporter import ExcelExporter
import copy

# --- Configuration ---
DATA_DIR = "data"
OUTPUT_DIR = "output"
COURSE_FILE = os.path.join(DATA_DIR, "course.csv")  # FIXED: Use course.csv
CLASSROOM_FILE = os.path.join(DATA_DIR, "classroom_data.csv")

DEPT_TIMETABLE_FILE = os.path.join(OUTPUT_DIR, "Department_Timetables.xlsx")
FACULTY_TIMETABLE_FILE = os.path.join(OUTPUT_DIR, "Faculty_Timetables.xlsx")

SEMESTERS_TO_RUN = [1, 3, 5, 7]
DEPARTMENTS = ["CSE", "DSAI", "ECE"]

def create_sections(semester: int, period: str) -> List[Section]:
    """  
    Generates the list of Section objects for a given semester and period.
    """
    sections = []
    for dept in DEPARTMENTS:
        if dept == "CSE":
            sections.append(Section(
                id=f"CSE-Sem{semester}-{period}-A",
                department="CSE",
                semester=semester,
                period=period,
                section_name="A"
            ))
            sections.append(Section(
                id=f"CSE-Sem{semester}-{period}-B",
                department="CSE",
                semester=semester,
                period=period,
                section_name="B"
            ))
        else:
            sections.append(Section(
                id=f"{dept}-Sem{semester}-{period}",
                department=dept,
                semester=semester,
                period=period,
                section_name=""
            ))
    return sections

def filter_courses_for_run(all_courses: List[Course], semester: int) -> List[Course]:
    """Filters the master course list for just one semester."""
    return [
        course for course in all_courses
        if course.semester == semester
    ]

def copy_sem7_to_post(
    sem_7_pre_sections: List[Section],
    master_post_faculty_schedules: Dict[str, Timetable],
    master_post_room_schedules: Dict[str, Timetable]
) -> List[Section]:
    """
    Handles the "Sem 7 PRE/POST are identical" rule.
    1. Creates new POST sections.
    2. Deep copies the PRE timetable grid to the POST sections.
    3. Manually copies all faculty/room bookings from PRE to POST master lists.
    """
    print("\n--- COPYING Sem 7 PRE to POST (as per rule) ---")
    sem_7_post_sections: List[Section] = []
    
    # 1. Create new POST sections and copy timetables
    for pre_sec in sem_7_pre_sections:
        post_sec = Section(
            id=pre_sec.id.replace("PRE", "POST"),
            department=pre_sec.department,
            semester=pre_sec.semester,
            period="POST",
            section_name=pre_sec.section_name
        )
        post_sec.timetable = copy.deepcopy(pre_sec.timetable)
        post_sec.timetable.owner_id = post_sec.id
        sem_7_post_sections.append(post_sec)

    # 2. Manually copy all bookings to POST master schedules
    for sec in sem_7_pre_sections: # Iterate the PRE sections
        for day in range(len(utils.DAYS)):
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = sec.timetable.grid[day][slot]
                
                # If this is the *start* of a real class
                is_start = (slot == 0) or (sec.timetable.grid[day][slot-1] != s_class)
                if s_class and s_class.course.course_code not in ["LUNCH", "BREAK"] and is_start:
                    
                    duration = s_class.course.get_session_duration(s_class.session_type)
                    if duration == 0: duration = 1 # Safeguard
                    
                    # Manually book faculty
                    for instructor in s_class.instructors:
                        if instructor == "TBD": continue
                        faculty_tt = master_post_faculty_schedules.setdefault(
                            instructor, Timetable(instructor, -1)
                        )
                        for i in range(duration):
                            if slot+i < utils.TOTAL_SLOTS_PER_DAY:
                                faculty_tt.grid[day][slot+i] = s_class
                    
                    # Manually book rooms
                    for room_id in s_class.room_ids:
                        room_tt = master_post_room_schedules.setdefault(
                            room_id, Timetable(room_id, -1)
                        )
                        for i in range(duration):
                            if slot+i < utils.TOTAL_SLOTS_PER_DAY:
                                room_tt.grid[day][slot+i] = s_class
                            
    print(f"Successfully copied {len(sem_7_post_sections)} Sem 7 POST sections.")
    return sem_7_post_sections

def main():
    """
    Main execution pipeline.
    """
    print("Starting Automated Timetable Scheduler...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 1. Load All Data (Once) ---
    all_classrooms = load_classrooms(CLASSROOM_FILE)
    if not all_classrooms:
        print("Fatal Error: No classrooms loaded. Exiting.")
        return
        
    pre_midsem_courses, post_midsem_courses = load_and_process_courses(COURSE_FILE)
    if not pre_midsem_courses:
        print("Warning: No PRE-midsem courses were processed. Check data_loader.py.")
    if not post_midsem_courses:
         print("Warning: No POST-midsem courses were processed. Check data_loader.py.")

    # --- 2. Master Loop: Generate All Timetables ---
    
    master_pre_faculty_schedules: Dict[str, Timetable] = {}
    master_pre_room_schedules: Dict[str, Timetable] = {}
    
    master_post_faculty_schedules: Dict[str, Timetable] = {}
    master_post_room_schedules: Dict[str, Timetable] = {}

    all_generated_sections: List[Section] = []
    overflow_courses_to_post: List[Course] = []

    # --- Schedule Sem 1, 3, 5 ---
    for semester in [1, 3, 5]:
        
        # --- PRE-MIDSEM RUN (Sem 1, 3, 5) ---
        pre_sections = create_sections(semester, "PRE")
        pre_courses_for_sem = filter_courses_for_run(pre_midsem_courses, semester)
        
        if pre_courses_for_sem:
            pre_scheduler = Scheduler(
                all_classrooms, "PRE",
                master_pre_room_schedules,
                master_pre_faculty_schedules
            )
            populated_pre_sections, overflow_from_pre = pre_scheduler.run(pre_courses_for_sem, pre_sections)
            
            all_generated_sections.extend(populated_pre_sections)
            overflow_courses_to_post.extend(overflow_from_pre)
        else:
            print(f"\n--- No PRE courses for Sem {semester}. Skipping PRE run. ---")
            
        # --- POST-MIDSEM RUN (Sem 1, 3, 5) ---
        post_sections = create_sections(semester, "POST")
        post_courses_for_sem = filter_courses_for_run(post_midsem_courses, semester)
        
        overflow_for_this_sem = [c for c in overflow_courses_to_post if c.semester == semester]
        if overflow_for_this_sem:
            print(f"Adding {len(overflow_for_this_sem)} overflow electives to POST run for Sem {semester}")
            post_courses_for_sem.extend(overflow_for_this_sem)
        
        if post_courses_for_sem:
            post_scheduler = Scheduler(
                all_classrooms, "POST",
                master_post_room_schedules,
                master_post_faculty_schedules
            )
            populated_post_sections, _ = post_scheduler.run(post_courses_for_sem, post_sections)
            all_generated_sections.extend(populated_post_sections)
        else:
            print(f"\n--- No POST courses for Sem {semester}. Skipping POST run. ---")

    # --- Schedule Sem 7 (PRE-MIDSEM ONLY) ---
    sem_7_pre_sections_list = create_sections(7, "PRE")
    sem_7_courses = filter_courses_for_run(pre_midsem_courses, 7)
    
    if sem_7_courses:
        sem_7_scheduler = Scheduler(
            all_classrooms, "PRE",
            master_pre_room_schedules,
            master_pre_faculty_schedules
        )
        populated_sem_7_pre_sections, _ = sem_7_scheduler.run(sem_7_courses, sem_7_pre_sections_list)
        all_generated_sections.extend(populated_sem_7_pre_sections)
        
        # --- Copy Sem 7 results to POST ---
        sem_7_post_sections = copy_sem7_to_post(
            populated_sem_7_pre_sections,
            master_post_faculty_schedules,
            master_post_room_schedules
        )
        all_generated_sections.extend(sem_7_post_sections)
    else:
        print("\n--- No Sem 7 courses found in PRE list. Skipping Sem 7. ---")


    print(f"\n--- All Scheduling Runs Complete ---")
    print(f"Total sections generated: {len(all_generated_sections)}")

    # --- 3. Run Validators ---
    print("\nValidating PRE-Midsem master schedule...")
    validate_all(
        [s for s in all_generated_sections if s.period == "PRE"],
        master_pre_faculty_schedules
    )
    
    print("\nValidating POST-Midsem master schedule...")
    validate_all(
        [s for s in all_generated_sections if s.period == "POST"],
        master_post_faculty_schedules
    )

    # --- 4. Export All Results ---
    all_faculty_schedules = {**master_pre_faculty_schedules, **master_post_faculty_schedules}
    
    exporter = ExcelExporter(
        all_sections=all_generated_sections,
        all_classrooms=all_classrooms,
        all_faculty_schedules=all_faculty_schedules
    )
    
    exporter.export_department_timetables(DEPT_TIMETABLE_FILE)
    exporter.export_faculty_timetables(FACULTY_TIMETABLE_FILE)

    print("\n--- Timetable Generation Complete. ---")
    print(f"Output files are in the '{OUTPUT_DIR}' directory.")

if __name__ == "__main__":
    main()