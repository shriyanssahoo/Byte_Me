"""
src/data_loader.py
(Rebuilt to correctly handle new 'elective'/'basket' logic and Sem 7)
"""

import csv
from typing import List, Tuple, Dict
from .models import Course, Classroom
from . import utils 
import os
import copy

def load_classrooms(filepath: str) -> List[Classroom]:
    """
    Reads the classroom_data.csv file and returns a list of Classroom objects.
    """
    print(f"Loading classrooms from {filepath}...")
    classrooms = []
    
    if not os.path.exists(filepath):
        print(f"Fatal Error: Classroom file not found at {filepath}")
        return []

    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    room_id = row.get("Room Number", "").strip().upper()
                    if not room_id:
                        continue
                    
                    try:
                        capacity_int = int(row.get("Capacity", 0))
                    except (ValueError, TypeError):
                        capacity_int = 0
                    
                    classroom = Classroom(
                        room_id=room_id,
                        capacity=capacity_int,
                        room_type=row.get("Type", "CLASSROOM").strip().upper(),
                        floor=utils.get_floor_from_room(room_id),
                        facilities=[f.strip() for f in row.get("Facilities", "").split(',')]
                    )
                    classrooms.append(classroom)
                except Exception as e:
                    print(f"Warning: Skipping invalid classroom row: {row}. Error: {e}")
                    
    except Exception as e:
        print(f"Fatal Error: Could not read classroom file. {e}")
        return []
    
    print(f"Successfully loaded {len(classrooms)} classrooms.")
    return classrooms

def _create_pseudo_courses(courses: List[Course]) -> List[Course]:
    """
    Bundles Sem 1/3 'electives' and Sem 5/7 'baskets' into pseudo-courses.
    """
    print("Bundling electives and baskets...")
    
    # --- NEW: Two-stage bundling ---
    
    # 1. Sem 1/3 Electives: Key = (Semester, Basket Code)
    sem_1_3_electives: Dict[Tuple[int, str], List[Course]] = {}
    
    # 2. Sem 5/7 Baskets: Key = (Semester, Department, Basket_Code)
    sem_5_7_baskets: Dict[Tuple[int, str, str], List[Course]] = {}
    
    courses_to_keep: List[Course] = [] # Non-basket/elective courses
    
    for course in courses:
        pref = course.pre_post_preference.lower()
        
        # Rule: 'elective' + basket_code + Sem 1/3
        if pref == 'elective' and course.semester in [1, 3] and course.basket_code:
            key = (course.semester, course.basket_code)
            sem_1_3_electives.setdefault(key, []).append(course)
        # Rule: 'basket' + basket_code + Sem 5/7
        elif pref == 'basket' and course.semester in [5, 7] and course.basket_code:
            key = (course.semester, course.department, course.basket_code)
            sem_5_7_baskets.setdefault(key, []).append(course)
        else:
            courses_to_keep.append(course)
            
    print(f"Found {len(sem_1_3_electives)} (Sem 1/3) elective bundles.")
    print(f"Found {len(sem_5_7_baskets)} (Sem 5/7) basket bundles.")
    
    # --- Process Sem 1/3 Electives ---
    for key, bundle in sem_1_3_electives.items():
        sem, basket = key
        template = bundle[0]
        
        pseudo_course = Course(
            course_code=f"ELECTIVE_{sem}_{basket}",
            course_name=f"Elective ({basket})",
            semester=sem,
            department="ALL_DEPTS", # Electives are cross-departmental
            ltpsc_str=template.ltpsc_str,
            credits=template.credits,
            instructors=["TBD"],
            registered_students=100,
            is_elective=False,
            is_half_semester=template.is_half_semester,
            is_combined=False,
            pre_post_preference="overflow", # Rule: Pre or Post
            basket_code="",
            is_pseudo_course=True
        )
        courses_to_keep.append(pseudo_course)

    # --- Process Sem 5/7 Baskets ---
    for key, bundle in sem_5_7_baskets.items():
        sem, dept, basket = key
        template = bundle[0]
        
        pseudo_course = Course(
            course_code=f"BASKET_{sem}_{dept}_{basket}",
            course_name=f"Basket ({basket})",
            semester=sem,
            department=dept, # Baskets are department-specific
            ltpsc_str=template.ltpsc_str,
            credits=template.credits,
            instructors=["TBD"],
            registered_students=100,
            is_elective=False,
            is_half_semester=template.is_half_semester,
            is_combined=False,
            pre_post_preference="basket_full", # Rule: Runs all semester
            basket_code="",
            is_pseudo_course=True
        )
        courses_to_keep.append(pseudo_course)
        
    print(f"Total courses after bundling: {len(courses_to_keep)}")
    return courses_to_keep


def load_and_process_courses(filepath: str) -> Tuple[List[Course], List[Course]]:
    """
    Main function to load courses from course.csv and process them into
    Pre and Post mid-semester lists based on the 'Pre /Post' column.
    """
    print(f"Loading and processing courses from {filepath}...")
    
    all_courses: List[Course] = []
    
    if not os.path.exists(filepath):
        print(f"Fatal Error: Course file not found at {filepath}")
        return [], []

    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            line_number = 1
            for row in reader:
                line_number += 1
                try:
                    course_code = row.get("Course Code", "").strip().upper()
                    if not course_code:
                        continue
                    
                    dept = row.get("Department", "UNKNOWN").strip().upper()
                    is_elective = row.get("Elective (Yes/No)", "No").strip().upper().startswith("Y")
                    is_half_sem = row.get("Half Semester (Yes/No)", "No").strip().upper().startswith("Y")
                    is_combined = row.get("Combined class", "No").strip().upper().startswith("Y")
                    
                    instructors_str = row.get("Instructor", "TBD").strip()
                    instructors = [name.strip() for name in instructors_str.split(',') if name.strip()]
                    if not instructors:
                        instructors = ["TBD"]
                        
                    semester = int(row.get("Semester", 0))
                    
                    if semester not in [1, 3, 5, 7]:
                        continue
                        
                    course = Course(
                        course_code=course_code,
                        course_name=row.get("Course Name", "Untitled"),
                        semester=semester,
                        department=dept,
                        ltpsc_str=row.get("LTPSC", "0-0-0-0-0"),
                        credits=int(row.get("Credits", 0)),
                        instructors=instructors,
                        registered_students=int(row.get("Registered Students", 0)),
                        is_elective=is_elective,
                        is_half_semester=is_half_sem,
                        is_combined=is_combined,
                        pre_post_preference=row.get("Pre /Post", ""),
                        basket_code=row.get("Basket Code", "").strip().upper()
                    )
                    
                    all_courses.append(course)
                        
                except Exception as e:
                    print(f"Warning: Skipping invalid course row (Line {line_number}): {row}. Error: {e}")

    except Exception as e:
        print(f"Fatal Error: Could not read course file. {e}")
        return [], []

    print(f"Loaded and validated {len(all_courses)} course offerings for Semesters 1, 3, 5, 7.")
    
    processed_courses = _create_pseudo_courses(all_courses)
    print(f"Bundling complete. Total processed courses: {len(processed_courses)}")

    pre_midsem_courses: List[Course] = []
    post_midsem_courses: List[Course] = []

    for course_template in processed_courses:
        course = copy.deepcopy(course_template)
        pref = course.pre_post_preference # This is now lowercase from the model
        
        # --- NEW SEM 7 RULE ---
        # If it's a Sem 7 course, it ONLY goes in the PRE list.
        if course.semester == 7:
            if pref in ['full', 'pre/post', 'basket_full', 'pre', 'basket']:
                pre_midsem_courses.append(course)
            elif pref == 'post':
                print(f"Warning: Sem 7 course {course.course_code} is 'post' only. This is not allowed. Skipping.")
            elif pref == 'elective':
                course.pre_post_preference = "overflow"
                pre_midsem_courses.append(course)
            continue # Go to the next course
            
        # --- Normal Logic for Sem 1, 3, 5 ---
        if pref == 'pre':
            pre_midsem_courses.append(course)
            
        elif pref == 'post':
            post_midsem_courses.append(course)
            
        elif pref == 'full':
            pre_midsem_courses.append(course)
            post_midsem_courses.append(copy.deepcopy(course))
            
        elif pref == 'pre/post':
            course.pre_post_preference = "SPLIT"
            pre_midsem_courses.append(course)
            post_midsem_courses.append(copy.deepcopy(course))
            
        elif pref == 'overflow': # (From pseudo-elective)
            pre_midsem_courses.append(course)
            
        elif pref == 'basket_full': # (From pseudo-basket)
            pre_midsem_courses.append(course)
            post_midsem_courses.append(copy.deepcopy(course))
        
        elif pref == '' and not course.is_pseudo_course:
            if course.is_half_semester:
                if not course.is_elective:
                    course.pre_post_preference = "SPLIT"
                    pre_midsem_courses.append(course)
                    post_midsem_courses.append(copy.deepcopy(course))
                else:
                    course.pre_post_preference = "overflow"
                    pre_midsem_courses.append(course)
            else:
                course.pre_post_preference = "FULL"
                pre_midsem_courses.append(course)
                post_midsem_courses.append(copy.deepcopy(course))
        
        elif pref not in ['elective', 'basket']:
             print(f"Warning: Unknown Pre/Post preference '{pref}' for {course.course_code}. Skipping.")

    print(f"Processed courses: {len(pre_midsem_courses)} pre-midsem definitions, {len(post_midsem_courses)} post-midsem definitions.")
    return pre_midsem_courses, post_midsem_courses