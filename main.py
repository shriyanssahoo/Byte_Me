"""
main.py

Simple timetable generator that creates Excel files
Run: python main.py
Output: Generates Department_Timetables.xlsx and Faculty_Timetables.xlsx
"""

import sys
import copy
from typing import List, Dict

try:
    import src.utils as utils
    from src.models import Section, Classroom, Course, Timetable
    from src.data_loader import load_classrooms, load_and_process_courses
    from src.scheduler import Scheduler
    from src.validators import validate_all
    from src.excel_exporter import ExcelExporter
except ImportError as e:
    print(f"ERROR: Could not import 'src' modules: {e}")
    print("Please ensure you're running this from the project root directory.")
    sys.exit(1)


def create_sections(semester: int, period: str) -> List[Section]:
    """Create section objects for a given semester and period"""
    sections = []
    for dept in ["CSE", "DSAI", "ECE"]:
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


def filter_courses_for_semester(all_courses: List[Course], semester: int) -> List[Course]:
    """Filter courses for a specific semester"""
    return [course for course in all_courses if course.semester == semester]


def copy_sem7_to_post(sem_7_pre_sections, master_post_faculty_schedules, master_post_room_schedules):
    """Copy Semester 7 PRE timetable to POST period"""
    sem_7_post_sections = []
    
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
    
    # Update faculty and room schedules for POST period
    for sec in sem_7_pre_sections:
        for day in range(len(utils.DAYS)):
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = sec.timetable.grid[day][slot]
                is_start = (slot == 0) or (sec.timetable.grid[day][slot-1] != s_class)
                
                if s_class and s_class.course.course_code not in ["LUNCH", "BREAK"] and is_start:
                    duration = s_class.course.get_session_duration(s_class.session_type)
                    if duration == 0:
                        duration = 1
                    
                    # Update faculty schedules
                    for instructor in s_class.instructors:
                        if instructor == "TBD":
                            continue
                        faculty_tt = master_post_faculty_schedules.setdefault(
                            instructor, Timetable(instructor, -1)
                        )
                        for i in range(duration):
                            if slot + i < utils.TOTAL_SLOTS_PER_DAY:
                                faculty_tt.grid[day][slot + i] = s_class
                    
                    # Update room schedules
                    for room_id in s_class.room_ids:
                        room_tt = master_post_room_schedules.setdefault(
                            room_id, Timetable(room_id, -1)
                        )
                        for i in range(duration):
                            if slot + i < utils.TOTAL_SLOTS_PER_DAY:
                                room_tt.grid[day][slot + i] = s_class
    
    return sem_7_post_sections


def generate_timetables():
    """Main timetable generation function"""
    print("\n" + "="*70)
    print("IIIT Dharwad - Automated Timetable Generator".center(70))
    print("="*70 + "\n")
    
    # Step 1: Load classrooms
    print("Step 1: Loading classroom data...")
    all_classrooms = load_classrooms("data/classroom_data.csv")
    if not all_classrooms:
        print("ERROR: Failed to load classrooms")
        return False
    print(f"✓ Loaded {len(all_classrooms)} classrooms")
    
    # Step 2: Load courses
    print("\nStep 2: Loading course data...")
    pre_midsem_courses, post_midsem_courses = load_and_process_courses("data/course.csv")
    if not pre_midsem_courses and not post_midsem_courses:
        print("ERROR: Failed to load courses")
        return False
    print(f"✓ Loaded {len(pre_midsem_courses)} PRE-midsem courses")
    print(f"✓ Loaded {len(post_midsem_courses)} POST-midsem courses")
    
    # Initialize tracking
    master_pre_faculty_schedules = {}
    master_pre_room_schedules = {}
    master_post_faculty_schedules = {}
    master_post_room_schedules = {}
    all_generated_sections = []
    overflow_courses_to_post = []
    
    # Step 3: Generate timetables for Semesters 1, 3, 5
    print("\nStep 3: Generating timetables...")
    for semester in [1, 3, 5]:
        print(f"\n  → Semester {semester}:")
        
        # PRE period
        pre_sections = create_sections(semester, "PRE")
        pre_courses = filter_courses_for_semester(pre_midsem_courses, semester)
        
        if pre_courses:
            print(f"    - PRE period: {len(pre_courses)} courses...")
            pre_scheduler = Scheduler(
                all_classrooms, "PRE",
                master_pre_room_schedules,
                master_pre_faculty_schedules
            )
            populated_pre, overflow = pre_scheduler.run(pre_courses, pre_sections)
            all_generated_sections.extend(populated_pre)
            overflow_courses_to_post.extend(overflow)
            print(f"      ✓ Generated {len(populated_pre)} section timetables")
            if overflow:
                print(f"      ! {len(overflow)} courses overflowed to POST period")
        
        # POST period
        post_sections = create_sections(semester, "POST")
        post_courses = filter_courses_for_semester(post_midsem_courses, semester)
        overflow_for_sem = [c for c in overflow_courses_to_post if c.semester == semester]
        if overflow_for_sem:
            post_courses.extend(overflow_for_sem)
        
        if post_courses:
            print(f"    - POST period: {len(post_courses)} courses...")
            post_scheduler = Scheduler(
                all_classrooms, "POST",
                master_post_room_schedules,
                master_post_faculty_schedules
            )
            populated_post, _ = post_scheduler.run(post_courses, post_sections)
            all_generated_sections.extend(populated_post)
            print(f"      ✓ Generated {len(populated_post)} section timetables")
    
    # Step 4: Generate Semester 7
    print(f"\n  → Semester 7:")
    sem_7_pre_sections = create_sections(7, "PRE")
    sem_7_courses = filter_courses_for_semester(pre_midsem_courses, 7)
    
    if sem_7_courses:
        print(f"    - PRE period: {len(sem_7_courses)} courses...")
        sem_7_scheduler = Scheduler(
            all_classrooms, "PRE",
            master_pre_room_schedules,
            master_pre_faculty_schedules
        )
        populated_sem7, _ = sem_7_scheduler.run(sem_7_courses, sem_7_pre_sections)
        all_generated_sections.extend(populated_sem7)
        print(f"      ✓ Generated {len(populated_sem7)} section timetables")
        
        # Copy to POST
        print(f"    - POST period: Copying from PRE...")
        sem_7_post = copy_sem7_to_post(
            populated_sem7,
            master_post_faculty_schedules,
            master_post_room_schedules
        )
        all_generated_sections.extend(sem_7_post)
        print(f"      ✓ Copied {len(sem_7_post)} section timetables")
    
    # Step 5: Validation
    print("\nStep 4: Validating timetables...")
    pre_sections = [s for s in all_generated_sections if s.period == "PRE"]
    post_sections = [s for s in all_generated_sections if s.period == "POST"]
    
    print(f"  - Validating PRE period ({len(pre_sections)} sections)...")
    validate_all(pre_sections, master_pre_faculty_schedules)
    print(f"    ✓ PRE period validated")
    
    print(f"  - Validating POST period ({len(post_sections)} sections)...")
    validate_all(post_sections, master_post_faculty_schedules)
    print(f"    ✓ POST period validated")
    
    # Step 6: Export to Excel
    print("\nStep 5: Exporting to Excel...")
    all_faculty_schedules = {**master_pre_faculty_schedules, **master_post_faculty_schedules}
    
    exporter = ExcelExporter(all_generated_sections, all_classrooms, all_faculty_schedules)
    
    print("  - Generating Department_Timetables.xlsx...")
    exporter.export_department_timetables("output/Department_Timetables.xlsx")
    print("    ✓ Department timetables exported")
    
    print("  - Generating Faculty_Timetables.xlsx...")
    exporter.export_faculty_timetables("output/Faculty_Timetables.xlsx")
    print("    ✓ Faculty timetables exported")
    
    # Summary
    print("\n" + "="*70)
    print("GENERATION COMPLETE".center(70))
    print("="*70)
    print(f"\n✓ Total sections generated: {len(all_generated_sections)}")
    print(f"✓ Total faculty schedules: {len(all_faculty_schedules)}")
    print(f"✓ Files created:")
    print(f"  - output/Department_Timetables.xlsx")
    print(f"  - output/Faculty_Timetables.xlsx")
    print("\n" + "="*70 + "\n")
    
    return True


if __name__ == '__main__':
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Generate timetables
    success = generate_timetables()
    
    if success:
        print("SUCCESS: Timetables generated successfully!")
        sys.exit(0)
    else:
        print("FAILED: Timetable generation encountered errors.")
        sys.exit(1)