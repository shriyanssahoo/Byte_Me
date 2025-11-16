"""
main.py
(Corrected to handle 'OVERFLOW' electives from PRE to POST)
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

def merge_schedules(master_schedules: Dict[str, Timetable], 
                    run_schedules: Dict[str, Timetable]):
    """
    Merges schedule data from a single run into the master schedule list.
    """
    for owner_id, run_timetable in run_schedules.items():
        if owner_id not in master_schedules:
            master_schedules[owner_id] = Timetable(owner_id, run_timetable.semester)
            
        master_tt = master_schedules[owner_id]
        
        for day in range(len(utils.DAYS)):
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = run_timetable.grid[day][slot]
                if s_class and s_class.course.course_code != "LUNCH":
                    if master_tt.grid[day][slot] is None:
                        master_tt.grid[day][slot] = s_class
                    else:
                        pass 

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
    
    all_generated_sections: List[Section] = []
    master_faculty_schedules: Dict[str, Timetable] = {}
    
    # --- NEW: Handle elective overflow ---
    overflow_courses_to_post: List[Course] = []

    for semester in SEMESTERS_TO_RUN:
        
        # --- PRE-MIDSEM RUN ---
        pre_sections = create_sections(semester, "PRE")
        pre_courses_for_sem = filter_courses_for_run(pre_midsem_courses, semester)
        
        pre_scheduler = Scheduler(all_classrooms, "PRE")
        populated_pre_sections, overflow_from_pre = pre_scheduler.run(pre_courses_for_sem, pre_sections)
        
        all_generated_sections.extend(populated_pre_sections)
        merge_schedules(master_faculty_schedules, pre_scheduler.faculty_schedules)
        overflow_courses_to_post.extend(overflow_from_pre) # Add failed electives to post list
            
        # --- POST-MIDSEM RUN ---
        post_sections = create_sections(semester, "POST")
        post_courses_for_sem = filter_courses_for_run(post_midsem_courses, semester)
        
        # Add overflow courses from the PRE run
        overflow_for_this_sem = [c for c in overflow_courses_to_post if c.semester == semester]
        if overflow_for_this_sem:
            print(f"Adding {len(overflow_for_this_sem)} overflow electives to POST run for Sem {semester}")
            post_courses_for_sem.extend(overflow_for_this_sem)
        
        post_scheduler = Scheduler(all_classrooms, "POST")
        populated_post_sections, _ = post_scheduler.run(post_courses_for_sem, post_sections)
        
        all_generated_sections.extend(populated_post_sections)
        merge_schedules(master_faculty_schedules, post_scheduler.faculty_schedules)

    print(f"\n--- All {len(SEMESTERS_TO_RUN) * 2} Scheduling Runs Complete ---")
    print(f"Total sections generated: {len(all_generated_sections)}")

    # --- 3. Run Validators ---
    is_valid = validate_all(
        all_generated_sections,
        master_faculty_schedules
    )
    
    if not is_valid:
        print("Warning: Conflicts were detected in the final schedule. Output may be unreliable.")

    # --- 4. Export All Results ---
    exporter = ExcelExporter(
        all_sections=all_generated_sections,
        all_classrooms=all_classrooms,
        all_faculty_schedules=master_faculty_schedules
    )
    
    exporter.export_department_timetables(DEPT_TIMETABLE_FILE)
    exporter.export_faculty_timetables(FACULTY_TIMETABLE_FILE)

    print("\n--- Timetable Generation Complete. ---")
    print(f"Output files are in the '{OUTPUT_DIR}' directory.")

if __name__ == "__main__":
    main()