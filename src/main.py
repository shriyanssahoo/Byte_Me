"""
Main entry point for the timetable scheduler.
"""

import sys
import os
import pandas as pd

# Add src to path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

from data_loader import DataLoader
from scheduler import Scheduler


def generate_course_colors(courses):
    """Generate unique colors for each course."""
    colors = [
        'FFE6E6', 'E6F3FF', 'E6FFE6', 'FFF3E6', 'F3E6FF',
        'FFE6F3', 'E6FFFF', 'FFFFE6', 'FFE6CC', 'E6E6FF',
        'CCFFE6', 'FFE6E6', 'E6CCFF', 'FFCCCC', 'CCFFCC',
        'CCCCFF', 'FFCCFF', 'CCFFFF', 'FFFFCC', 'FFCCAA'
    ]
    
    course_color_map = {}
    unique_courses = list(set(course.code for course in courses))
    
    for i, course_code in enumerate(unique_courses):
        course_color_map[course_code] = colors[i % len(colors)]
    
    return course_color_map


def export_to_excel(timetable, courses, filename='output/timetable.xlsx'):
    """Export timetable to color-coded Excel file."""
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    # Generate color mapping
    course_colors = generate_course_colors(courses)
    
    # Prepare data for export
    data = []
    for assignment in timetable.assignments:
        data.append({
            'Day': assignment.slot.day,
            'Time': f"{assignment.slot.start_time}-{assignment.slot.end_time}",
            'Course Code': assignment.course.code,
            'Course Title': assignment.course.title,
            'L-T-P-S-C': assignment.course.ltpsc,
            'Faculty': assignment.faculty.name,
            'Room': assignment.room.room_id,
            'Student Group': assignment.student_group
        })
    
    df = pd.DataFrame(data)
    
    # Sort by student group, day, and time
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    df['Day'] = pd.Categorical(df['Day'], categories=day_order, ordered=True)
    df = df.sort_values(['Student Group', 'Day', 'Time'])
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Timetable"
    
    # Write data with formatting
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            
            # Style header row
            if r_idx == 1:
                cell.fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
                cell.font = Font(color="FFFFFF", bold=True, size=12)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                # Color code by course
                course_code = ws.cell(row=r_idx, column=3).value  # Course Code column
                if course_code in course_colors:
                    color = course_colors[course_code]
                    for col in range(1, 9):
                        ws.cell(row=r_idx, column=col).fill = PatternFill(
                            start_color=color,
                            end_color=color,
                            fill_type="solid"
                        )
                
                # Add borders
                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 25
    ws.column_dimensions['G'].width = 10
    ws.column_dimensions['H'].width = 18
    
    # Freeze header row
    ws.freeze_panes = 'A2'
    
    wb.save(filename)
    print(f"\n✓ Color-coded timetable exported to {filename}")


def print_failed_schedules(failed_schedules):
    """Print courses that could not be scheduled."""
    if not failed_schedules:
        print("\n✓ All courses scheduled successfully!")
        return
    
    print(f"\n{'='*90}")
    print("⚠ COURSES THAT COULD NOT BE SCHEDULED".center(90))
    print('='*90)
    
    # Group by course
    failed_by_course = {}
    for item in failed_schedules:
        key = (item['course_code'], item['course_title'], item['student_group'])
        if key not in failed_by_course:
            failed_by_course[key] = []
        failed_by_course[key].append(item['lecture_num'])
    
    for (code, title, group), lectures in sorted(failed_by_course.items()):
        print(f"\n{code} - {title}")
        print(f"  Student Group: {group}")
        print(f"  Failed Lectures: {', '.join(map(str, lectures))}")
        print(f"  Total Failed: {len(lectures)}")


def print_timetable_by_group(timetable, student_group):
    """Print timetable for a specific student group."""
    assignments = timetable.get_assignments_by_group(student_group)
    
    if not assignments:
        print(f"\nNo classes scheduled for {student_group}")
        return
    
    print(f"\n{'='*90}")
    print(f"TIMETABLE FOR {student_group}".center(90))
    print('='*90)
    
    # Group by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    for day in days:
        day_assignments = [a for a in assignments if a.slot.day == day]
        
        if day_assignments:
            print(f"\n{day.upper()}")
            print('-' * 90)
            
            # Sort by time
            day_assignments.sort(key=lambda a: a.slot.start_time)
            
            lunch_shown = False
            
            for assignment in day_assignments:
                time = f"{assignment.slot.start_time}-{assignment.slot.end_time}"
                
                # Show lunch break once before afternoon classes
                if not lunch_shown and assignment.slot.start_time >= '14:00':
                    print(f"{'13:30-14:00':13} | {'LUNCH BREAK':^73} |")
                    lunch_shown = True
                
                print(f"{time} | "
                      f"{assignment.course.code:8} | {assignment.course.title:30} | "
                      f"{assignment.faculty.name:20} | {assignment.room.room_id}")


def print_timetable_by_faculty(timetable, faculty_id, faculty_name):
    """Print timetable for a specific faculty member."""
    assignments = timetable.get_assignments_by_faculty(faculty_id)
    
    if not assignments:
        print(f"\nNo classes scheduled for {faculty_name}")
        return
    
    print(f"\n{'='*90}")
    print(f"TIMETABLE FOR {faculty_name}".center(90))
    print('='*90)
    
    # Group by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    for day in days:
        day_assignments = [a for a in assignments if a.slot.day == day]
        
        if day_assignments:
            print(f"\n{day.upper()}")
            print('-' * 90)
            
            # Sort by time
            day_assignments.sort(key=lambda a: a.slot.start_time)
            
            for assignment in day_assignments:
                print(f"{assignment.slot.start_time}-{assignment.slot.end_time} | "
                      f"{assignment.course.code:8} | {assignment.course.title:30} | "
                      f"{assignment.student_group:15} | {assignment.room.room_id}")


def main():
    """Main function to run the scheduler."""
    print("=" * 90)
    print("AUTOMATED TIMETABLE SCHEDULER - IIIT Dharwad".center(90))
    print("Team: Byte Me".center(90))
    print("=" * 90)
    
    # Step 1: Load data
    print("\n📂 Loading data...")
    loader = DataLoader(data_dir='data')
    loader.load_all_data()
    
    if not loader.courses:
        print("\n❌ No courses found! Please create data/courses.csv")
        return
    
    # Step 2: Generate timetable
    scheduler = Scheduler(
        courses=loader.courses,
        faculty_dict=loader.faculty,
        rooms=loader.rooms,
        slots=loader.slots
    )
    
    timetable = scheduler.generate_timetable()
    
    # Step 3: Validate
    scheduler.validate_timetable()
    
    # Step 4: Show failed schedules
    failed_schedules = scheduler.get_failed_schedules()
    print_failed_schedules(failed_schedules)
    
    # Step 5: Display results for individual sections only
    # Get unique student groups (excluding combined A&B)
    groups = set()
    for course in loader.courses:
        if '&' in course.student_group:
            # Split "3rdSem-A&B" into "3rdSem-A" and "3rdSem-B"
            base = course.student_group.split('&')[0]
            groups.add(base)
            if base.endswith('-A'):
                groups.add(base[:-1] + 'B')
        else:
            groups.add(course.student_group)
    
    for group in sorted(groups):
        # Only show individual sections (A or B), not combined
        if '&' not in group:
            print_timetable_by_group(timetable, group)
    
    # Display faculty schedules
    print("\n\n" + "=" * 90)
    print("FACULTY SCHEDULES".center(90))
    print("=" * 90)
    
    for faculty_id, faculty in sorted(loader.faculty.items()):
        print_timetable_by_faculty(timetable, faculty_id, faculty.name)
    
    # Step 6: Export to Excel
    export_to_excel(timetable, loader.courses)
    
    print("\n" + "=" * 90)
    print("✓ TIMETABLE GENERATION COMPLETE!".center(90))
    print("=" * 90)


if __name__ == "__main__":
    main()
