"""
main.py
(Corrected to create master PRE/POST schedules and pass them
to each scheduler run, fixing cross-semester conflicts)
"""

import os
from typing import List, Dict, Set
import src.utils as utils
from src.models import Section, Classroom, Course, Timetable
from src.data_loader import load_classrooms, load_and_process_courses
from src.scheduler import Scheduler
from src.validators import validate_all
from src.excel_exporter import ExcelExporter

# --- Configuration ---
DATA_DIR = "data"
OUTPUT_DIR = "output"
COURSE_FILE = os.path.join(DATA_DIR, "course.csv")
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
    if not pre_midsem_courses and not post_midsem_courses:
        print("Fatal Error: No courses loaded. Exiting.")
        return

    # --- 2. Master Loop: Generate All Timetables ---
    
    # --- NEW: Create master schedules ---
    # These will be shared across all PRE runs
    master_pre_faculty_schedules: Dict[str, Timetable] = {}
    master_pre_room_schedules: Dict[str, Timetable] = {}
    
    # These will be shared across all POST runs
    master_post_faculty_schedules: Dict[str, Timetable] = {}
    master_post_room_schedules: Dict[str, Timetable] = {}

    all_generated_sections: List[Section] = []
    overflow_courses_to_post: List[Course] = []

    for semester in SEMESTERS_TO_RUN:
        
        # --- PRE-MIDSEM RUN ---
        pre_sections = create_sections(semester, "PRE")
        pre_courses_for_sem = filter_courses_for_run(pre_midsem_courses, semester)
        
        # --- NEW: Pass master schedules to the Scheduler ---
        pre_scheduler = Scheduler(
            all_classrooms, 
            "PRE",
            master_pre_room_schedules, # Pass the PRE master room schedule
            master_pre_faculty_schedules # Pass the PRE master faculty schedule
        )
        populated_pre_sections, overflow_from_pre = pre_scheduler.run(pre_courses_for_sem, pre_sections)
        
        all_generated_sections.extend(populated_pre_sections)
        overflow_courses_to_post.extend(overflow_from_pre)
            
        # --- POST-MIDSEM RUN ---
        post_sections = create_sections(semester, "POST")
        post_courses_for_sem = filter_courses_for_run(post_midsem_courses, semester)
        
        overflow_for_this_sem = [c for c in overflow_courses_to_post if c.semester == semester]
        if overflow_for_this_sem:
            print(f"Adding {len(overflow_for_this_sem)} overflow electives to POST run for Sem {semester}")
            post_courses_for_sem.extend(overflow_for_this_sem)
        
        # --- NEW: Pass master schedules to the Scheduler ---
        post_scheduler = Scheduler(
            all_classrooms, 
            "POST",
            master_post_room_schedules, # Pass the POST master room schedule
            master_post_faculty_schedules # Pass the POST master faculty schedule
        )
        populated_post_sections, _ = post_scheduler.run(post_courses_for_sem, post_sections)
        
        all_generated_sections.extend(populated_post_sections)

    print(f"\n--- All {len(SEMESTERS_TO_RUN) * 2} Scheduling Runs Complete ---")
    print(f"Total sections generated: {len(all_generated_sections)}")

    # --- 3. Run Validators ---
    # We now validate the *master* schedules
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
    # The exporter needs ALL sections, but the master schedules
    
    # Combine all faculty schedules for the exporter
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