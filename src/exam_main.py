"""
Main entry point for exam timetable and seating arrangement generation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from exam_data_loader import ExamDataLoader
from exam_scheduler import ExamScheduler
from exam_exporter import ExamExporter


def generate_exam_timetable():
    """Generate exam timetable and seating arrangements."""
    print("=" * 90)
    print("EXAM TIMETABLE & SEATING ARRANGEMENT GENERATOR".center(90))
    print("Team: Byte Me | IIIT Dharwad".center(90))
    print("=" * 90)
    
    # Step 1: Load data
    print("\n📂 Loading data...")
    loader = ExamDataLoader(data_dir='data')
    loader.load_all_data()
    
    if not loader.students:
        print("\n❌ No students found! Please create data/students.csv")
        return
    
    if not loader.exam_rooms:
        print("\n❌ No exam rooms found! Please create data/exam_rooms.csv")
        return
    
    if not loader.courses:
        print("\n❌ No courses found! Please check data/courses.csv")
        return
    
    # Step 2: Generate exam schedule
    scheduler = ExamScheduler(
        courses=loader.courses,
        students=loader.students,
        exam_rooms=loader.exam_rooms,
        exam_config=loader.exam_config
    )
    
    schedule = scheduler.generate_exam_schedule()
    
    # Step 3: Generate seating arrangements
    scheduler.generate_seating_arrangements()
    
    # Step 4: Export to Excel
    print("\n📊 Exporting to Excel...")
    exporter = ExamExporter(schedule)
    exporter.export_all()
    
    print("\n" + "=" * 90)
    print("✓ EXAM TIMETABLE GENERATION COMPLETE!".center(90))
    print("=" * 90)
    print("\nGenerated Files:")
    print("  - Exam seating arrangements (one file per day)")
    print("  - Student exam schedules (one file per section)")
    print("\nLocation: output/exams/")


if __name__ == "__main__":
    generate_exam_timetable()