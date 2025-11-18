import pandas as pd
import os
from datetime import datetime, timedelta
from collections import defaultdict

# --- Start of Fix ---

# Get the directory of the current script (e.g., .../Byte_Me/src)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root (e.g., .../Byte_Me)
ROOT_DIR = os.path.join(SCRIPT_DIR, '..')

# Define the data and output paths relative to the root
DATA_DIR = os.path.join(ROOT_DIR, 'data')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output', 'exams')  # Changed: Added 'exams' subfolder

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load data using the correct paths
try:
    courses = pd.read_csv(os.path.join(DATA_DIR, 'course.csv'))
    students = pd.read_csv(os.path.join(DATA_DIR, 'students.csv'))
    exam_rooms = pd.read_csv(os.path.join(DATA_DIR, 'exam_rooms.csv'))
    exam_config = pd.read_csv(os.path.join(DATA_DIR, 'exam_config.csv'))
except FileNotFoundError as e:
    print(f"FATAL ERROR: Could not find data file: {e}")
    print(f"Please make sure your data files are in: {DATA_DIR}")
    exit()

# --- End of Fix ---

# Parse exam config
config = dict(zip(exam_config['parameter'], exam_config['value']))
# ... (rest of your script) ...
exam_start_date = datetime.strptime(config['exam_start_date'], '%Y-%m-%d')

# Filter courses that need exams (non-elective courses with registered students or core courses)
exam_courses = courses[
    ((courses['Elective (Yes/No)'].str.lower() == 'no') | 
     (courses['Registered Students'] > 0)) &
    (courses['Semester'].isin([1, 3, 5, 7]))
].copy()

# Prepare students data - group by branch and semester
students_dict = students.groupby(['branch', 'semester'], group_keys=False).apply(
    lambda x: x.sort_values('roll_number')['roll_number'].tolist()
).to_dict()

def create_seating_arrangement(student_list, rooms):
    """
    Create seating arrangement with two-pass column filling strategy:
    Pass 1: Fill odd columns (C1, C3, C5) with largest department
    Pass 2: Fill even columns (C2, C4, C6) with other departments
            (if others run out, fill with largest department)
    """
    seating_plan = {}
    
    # Split students by department/branch based on roll number prefix
    dept_students = defaultdict(list)
    for student in student_list:
        if 'BCS' in student:
            dept_students['CSE'].append(student)
        elif 'BDS' in student:
            dept_students['DSAI'].append(student)
        elif 'BEC' in student:
            dept_students['ECE'].append(student)
        else:
            # Default to CSE if pattern not recognized
            dept_students['CSE'].append(student)
    
    # Find largest department
    if not dept_students:
        return seating_plan
    
    largest_dept = max(dept_students.keys(), key=lambda k: len(dept_students[k]))
    
    # Separate largest dept from others
    largest_dept_students = dept_students[largest_dept].copy()
    other_dept_students = []
    for dept, students in dept_students.items():
        if dept != largest_dept:
            other_dept_students.extend(students)
    
    largest_idx = 0
    other_idx = 0
    
    # Process each room one by one
    for room in rooms:
        room_id = room['room_id']
        rows = room['rows']
        cols = room['columns']
        
        room_seating = []
        
        # Pass 1: Fill odd columns (1, 3, 5...) with largest department
        for row in range(rows):
            for col in range(cols):
                if (col + 1) % 2 == 1:  # Odd columns (C1, C3, C5)
                    if largest_idx < len(largest_dept_students):
                        room_seating.append({
                            'Room': room_id,
                            'Row': row + 1,
                            'Column': col + 1,
                            'Seat': f"R{row+1}C{col+1}",
                            'Roll_Number': largest_dept_students[largest_idx],
                            'Department': largest_dept
                        })
                        largest_idx += 1
        
        # Pass 2: Fill even columns (2, 4, 6...) with other departments
        # If other departments run out, fill with largest department
        for row in range(rows):
            for col in range(cols):
                if (col + 1) % 2 == 0:  # Even columns (C2, C4, C6)
                    if other_idx < len(other_dept_students):
                        # Fill with other departments
                        # Determine which department this student belongs to
                        student = other_dept_students[other_idx]
                        student_dept = 'DSAI' if 'BDS' in student else 'ECE' if 'BEC' in student else 'Other'
                        
                        room_seating.append({
                            'Room': room_id,
                            'Row': row + 1,
                            'Column': col + 1,
                            'Seat': f"R{row+1}C{col+1}",
                            'Roll_Number': student,
                            'Department': student_dept
                        })
                        other_idx += 1
                    elif largest_idx < len(largest_dept_students):
                        # If other depts exhausted, fill with largest dept
                        room_seating.append({
                            'Room': room_id,
                            'Row': row + 1,
                            'Column': col + 1,
                            'Seat': f"R{row+1}C{col+1}",
                            'Roll_Number': largest_dept_students[largest_idx],
                            'Department': largest_dept
                        })
                        largest_idx += 1
        
        # Sort by row and column for proper order
        room_seating.sort(key=lambda x: (x['Row'], x['Column']))
        
        if room_seating:  # Only add if room has students
            seating_plan[room_id] = pd.DataFrame(room_seating)
        
        # If all students are seated, stop processing more rooms
        if largest_idx >= len(largest_dept_students) and other_idx >= len(other_dept_students):
            break
    
    return seating_plan

def generate_exam_schedule():
    """Generate exam schedule - different departments can have exams at same time"""
    schedule = []
    current_date = exam_start_date
    slot = 'Morning'
    
    # Group courses by semester first
    for semester in sorted(exam_courses['Semester'].unique()):
        sem_courses = exam_courses[exam_courses['Semester'] == semester].copy()
        
        # Get unique course codes for this semester
        course_codes_scheduled = set()
        
        for _, course in sem_courses.iterrows():
            course_code = course['Course Code']
            
            # Skip if already scheduled
            if course_code in course_codes_scheduled:
                continue
            
            # Get all departments offering this course in this semester
            same_course_all_depts = sem_courses[sem_courses['Course Code'] == course_code]
            
            for _, dept_course in same_course_all_depts.iterrows():
                dept = dept_course['Department']
                student_key = (dept, semester)
                students_list = students_dict.get(student_key, [])
                
                if len(students_list) == 0 and dept_course['Registered Students'] == 0:
                    continue
                
                # Determine duration based on credits
                duration = '3hr' if dept_course['Credits'] >= 4 else '2hr'
                
                schedule.append({
                    'Date': current_date.strftime('%Y-%m-%d'),
                    'Slot': slot,
                    'Duration': duration,
                    'Course_Code': dept_course['Course Code'],
                    'Course_Name': dept_course['Course Name'],
                    'Semester': semester,
                    'Department': dept,
                    'Students': len(students_list) if students_list else dept_course['Registered Students']
                })
            
            course_codes_scheduled.add(course_code)
            
            # Move to next slot only after scheduling all depts for this course
            if slot == 'Morning':
                slot = 'Afternoon'
            else:
                slot = 'Morning'
                current_date += timedelta(days=1)
    
    return pd.DataFrame(schedule)

def generate_seating_plans(schedule_df):
    """Generate seating plans for each exam - combine all departments in same slot"""
    
    # Group by Date, Slot, and Course_Code to handle multiple departments together
    grouped = schedule_df.groupby(['Date', 'Slot', 'Course_Code'])
    
    for (date, slot, course_code), exam_group in grouped:
        # Collect all students from all departments for this exam slot
        all_students = []
        dept_info = []
        
        for _, exam in exam_group.iterrows():
            student_key = (exam['Department'], exam['Semester'])
            students_list = students_dict.get(student_key, [])
            
            if students_list:
                all_students.extend(students_list)
                dept_info.append(f"{exam['Department']} ({len(students_list)} students)")
        
        if not all_students:
            continue
        
        # Prepare rooms list
        rooms = exam_rooms.to_dict('records')
        
        # Create seating arrangement with all students
        seating_plan = create_seating_arrangement(all_students, rooms)
        
        if not seating_plan:
            print(f"Warning: No seating plan created for {course_code} on {date} {slot}")
            continue
        
        # Create Excel file with multiple sheets for each room
        date_str = date.replace('-', '')
        course_name = exam_group.iloc[0]['Course_Name']
        filename = os.path.join(OUTPUT_DIR, f"Exam_{course_code}{date_str}{slot}.xlsx") 
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Write exam details sheet
            exam_details_list = []
            for _, exam in exam_group.iterrows():
                exam_details_list.append({
                    'Date': exam['Date'],
                    'Slot': exam['Slot'],
                    'Duration': exam['Duration'],
                    'Course Code': exam['Course_Code'],
                    'Course Name': exam['Course_Name'],
                    'Semester': exam['Semester'],
                    'Department': exam['Department'],
                    'Students': exam['Students']
                })
            
            exam_details = pd.DataFrame(exam_details_list)
            
            # Add summary
            summary = pd.DataFrame([{
                'Total Students': len(all_students),
                'Departments': ', '.join(dept_info),
                'Rooms Used': len(seating_plan)
            }])
            
            exam_details.to_excel(writer, sheet_name='Exam_Details', index=False)
            summary.to_excel(writer, sheet_name='Exam_Details', startrow=len(exam_details)+2, index=False)
            
            # Write seating plan for each room in the visual format
            for room_id, room_df in seating_plan.items():
                sheet_name = f"Room_{room_id}"
                
                # Convert to visual column format (COL1, COL2, COL3)
                visual_seating = []
                rows = int(room_df['Row'].max())
                cols = int(room_df['Column'].max())
                
                for row_num in range(1, rows + 1):
                    row_data = {}
                    row_students = room_df[room_df['Row'] == row_num].sort_values('Column')
                    
                    for _, student_row in row_students.iterrows():
                        col_num = int(student_row['Column'])
                        col_label = f"COL{col_num}"
                        row_data[col_label] = student_row['Roll_Number']
                    
                    # Only add row if it has data
                    if row_data:
                        visual_seating.append(row_data)
                
                # Create DataFrame with column headers
                if visual_seating:
                    visual_df = pd.DataFrame(visual_seating)
                    
                    # Reorder columns to ensure COL1, COL2, COL3 order
                    available_cols = [col for col in visual_df.columns]
                    column_order = sorted(available_cols, key=lambda x: int(x.replace('COL', '')))
                    visual_df = visual_df[column_order]
                    
                    visual_df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    # If no data, create empty sheet with headers
                    empty_df = pd.DataFrame(columns=[f"COL{i}" for i in range(1, cols + 1)])
                    empty_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"✓ Created: {filename} ({len(all_students)} students from {len(exam_group)} departments)")

# Main execution
print("="*80)
print("EXAM SCHEDULER AND SEATING PLAN GENERATOR")
print("="*80)

# Generate schedule
print("\n[1/2] Generating exam schedule...")
schedule = generate_exam_schedule()
output_schedule_path = os.path.join(OUTPUT_DIR, 'Exam_Schedule.csv')
schedule.to_csv(output_schedule_path, index=False)
print(f"✓ Exam schedule created: {output_schedule_path}")
print(f"   Total exams scheduled: {len(schedule)}")

# Generate seating plans
print("\n[2/2] Generating seating plans...")
generate_seating_plans(schedule)

print("\n" + "="*80)
print("ALL FILES GENERATED SUCCESSFULLY!")
print("="*80)
print(f"Total exams: {len(schedule)}")
print(f"Output location: {os.path.abspath(OUTPUT_DIR)}")
print("\nSeating Strategy:")
print("  • Odd columns (C1, C3, C5): Largest department")
print("  • Even columns (C2, C4, C6): Other departments")
print("  • Maximum spacing between same-department students")
print("="*80)