"""
src/data_loader.py
(Corrected with Type 1/Type 2 bundling and 'parent_pseudo_name' tagging)
(FIXED: Semester 1 electives now schedule only 1 session per week)
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

def _bundle_baskets_and_electives(courses: List[Course]) -> List[Course]:
    """
    Finds ALL elective/basket courses and bundles them based on the
    new rules:
    - ELECTIVES (Type 1): Cross-departmental (Sem, Basket)
    - BASKETS (Type 2): Department-specific (Sem, Dept, Basket)
    """
    print("Bundling electives and baskets...")
    
    # Key = (Semester, Basket Code)
    elective_bundles: Dict[Tuple[int, str], List[Course]] = {}
    
    # Key = (Semester, Department, Basket Code)
    basket_bundles: Dict[Tuple[int, str, str], List[Course]] = {}
    
    courses_to_keep: List[Course] = []
    
    for course in courses:
        pref = course.pre_post_preference.lower()
        
        if pref == 'elective' and course.basket_code:
            key = (course.semester, course.basket_code)
            elective_bundles.setdefault(key, []).append(course)
            
        elif pref == 'basket' and course.basket_code:
            key = (course.semester, course.department, course.basket_code)
            basket_bundles.setdefault(key, []).append(course)
            
        else:
            # This is a core course or a combined course
            courses_to_keep.append(course)
            
    print(f"Found {len(elective_bundles)} cross-departmental ELECTIVE bundles (Type 1).")
    print(f"Found {len(basket_bundles)} department-specific BASKET bundles (Type 2).")
    
    # --- Process Type 1: ELECTIVES (Cross-departmental) ---
    for key, bundle in elective_bundles.items():
        sem, basket = key
        template = bundle[0]
        
        # FIX: Force Semester 1 electives to have only 1 session per week
        if sem == 1 and basket == "A":
            ltpsc_str = "1-0-0-0-1"  # This creates 1 tutorial = 1 session/week
        else:
            ltpsc_str = template.ltpsc_str
        
        pseudo_name = f"Elective ({basket})" # This is the name we want to display
        
        pseudo_course = Course(
            course_code=f"PSEUDO_{sem}_{basket}",
            course_name=pseudo_name,
            semester=sem,
            department="ALL_DEPTS",  # Cross-departmental
            ltpsc_str=ltpsc_str,
            credits=template.credits,
            instructors=["TBD"],
            registered_students=100,
            is_elective=False,
            is_half_semester=template.is_half_semester,
            is_combined=False,
            pre_post_preference=template.pre_post_preference,
            basket_code=basket,
            is_pseudo_basket=True,
            bundled_courses=bundle
        )
        
        # "Tag" the original courses with the name to display
        for original_course in bundle:
            original_course.parent_pseudo_name = pseudo_name
            
        courses_to_keep.append(pseudo_course)
        
    # --- Process Type 2: BASKETS (Department-specific) ---
    for key, bundle in basket_bundles.items():
        sem, dept, basket = key
        template = bundle[0]
        pseudo_name = f"Basket ({basket})" # This is the name we want to display

        pseudo_course = Course(
            course_code=f"PSEUDO_{sem}_{dept}_{basket}",
            course_name=pseudo_name,
            semester=sem,
            department=dept,  # Department-specific
            ltpsc_str=template.ltpsc_str,
            credits=template.credits,
            instructors=["TBD"],
            registered_students=100,
            is_elective=False,
            is_half_semester=template.is_half_semester,
            is_combined=False,
            pre_post_preference=template.pre_post_preference,
            basket_code=basket,
            is_pseudo_basket=True,
            bundled_courses=bundle
        )
        
        # "Tag" the original courses with the name to display
        for original_course in bundle:
            original_course.parent_pseudo_name = pseudo_name

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
                        basket_code=row.get("Basket Code", "").strip()
                    )
                    
                    all_courses.append(course)
                        
                except Exception as e:
                    print(f"Warning: Skipping invalid course row (Line {line_number}): {row}. Error: {e}")

    except Exception as e:
        print(f"Fatal Error: Could not read course file. {e}")
        return [], []

    print(f"Loaded and validated {len(all_courses)} course offerings for Semesters 1, 3, 5, 7.")
    
    processed_courses = _bundle_baskets_and_electives(all_courses)
    print(f"Bundling complete. Total processed courses: {len(processed_courses)}")

    pre_midsem_courses: List[Course] = []
    post_midsem_courses: List[Course] = []

    for course_template in processed_courses:
        course = copy.deepcopy(course_template)
        
        pref = course.pre_post_preference 
        
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
        elif pref == 'elective':
            course.pre_post_preference = "OVERFLOW"
            pre_midsem_courses.append(course)
        elif pref == 'basket':
            course.pre_post_preference = "BASKET_FULL"
            pre_midsem_courses.append(course)
            post_midsem_courses.append(copy.deepcopy(course))
        elif pref == '':
            if course.is_half_semester:
                if not course.is_elective:
                    print(f"Warning: Course {course.course_code} is Half_Sem but has blank Pre/Post. Defaulting to SPLIT.")
                    course.pre_post_preference = "SPLIT"
                    pre_midsem_courses.append(course)
                    post_midsem_courses.append(copy.deepcopy(course))
                else:
                    print(f"Warning: Course {course.course_code} is Elective but has blank Pre/Post. Defaulting to OVERFLOW.")
                    course.pre_post_preference = "OVERFLOW"
                    pre_midsem_courses.append(course)
            else:
                print(f"Warning: Course {course.course_code} has blank Pre/Post. Defaulting to FULL.")
                course.pre_post_preference = "FULL"
                pre_midsem_courses.append(course)
                post_midsem_courses.append(copy.deepcopy(course))
        else:
            print(f"Warning: Unknown Pre/Post preference '{pref}' for {course.course_code}. Skipping.")

    print(f"Processed courses: {len(pre_midsem_courses)} pre-midsem definitions, {len(post_midsem_courses)} post-midsem definitions.")
    return pre_midsem_courses, post_midsem_courses