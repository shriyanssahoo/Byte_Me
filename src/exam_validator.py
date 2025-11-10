"""
Validation tool to check if dataset will work for exam scheduling.
Run before generating exams to identify potential issues.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from exam_data_loader import ExamDataLoader
from datetime import datetime, timedelta


class ExamValidator:
    """Validates exam scheduling feasibility."""
    
    def __init__(self, data_dir='data'):
        self.loader = ExamDataLoader(data_dir)
        self.loader.load_all_data()
        self.issues = []
        self.warnings = []
    
    def validate_all(self):
        """Run all validation checks."""
        print("\n" + "="*90)
        print("EXAM SCHEDULING VALIDATION".center(90))
        print("="*90)
        
        self._check_data_loaded()
        self._check_room_capacity()
        self._check_exam_slots()
        self._check_student_enrollment()
        self._check_config()
        
        # Print results
        print("\n" + "="*90)
        print("VALIDATION RESULTS".center(90))
        print("="*90)
        
        if not self.issues and not self.warnings:
            print("\n✅ ALL CHECKS PASSED!")
            print("Your dataset is ready for exam scheduling.")
            return True
        
        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} WARNING(S):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if self.issues:
            print(f"\n❌ {len(self.issues)} CRITICAL ISSUE(S):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
            print("\n❌ CANNOT PROCEED - Please fix critical issues first!")
            return False
        
        print("\n⚠️  You can proceed, but address warnings for better results.")
        return True
    
    def _check_data_loaded(self):
        """Check if all required data is loaded."""
        print("\n📋 Checking data files...")
        
        if not self.loader.students:
            self.issues.append("No students found in students.csv")
        else:
            print(f"  ✓ Loaded {len(self.loader.students)} students")
        
        if not self.loader.exam_rooms:
            self.issues.append("No exam rooms found in exam_rooms.csv")
        else:
            print(f"  ✓ Loaded {len(self.loader.exam_rooms)} exam rooms")
        
        if not self.loader.courses:
            self.issues.append("No courses found in courses.csv")
        else:
            print(f"  ✓ Loaded {len(self.loader.courses)} courses")
        
        if not self.loader.exam_config:
            self.warnings.append("No exam config found, using defaults")
        else:
            print(f"  ✓ Loaded exam configuration")
    
    def _check_room_capacity(self):
        """Check if rooms can accommodate students."""
        print("\n🏫 Checking room capacity...")
        
        total_capacity = sum(room.capacity for room in self.loader.exam_rooms)
        total_students = len(self.loader.students)
        
        print(f"  Total room capacity: {total_capacity} seats")
        print(f"  Total students: {total_students}")
        
        # Worst case: all students have exam at same time
        if total_capacity < total_students:
            self.issues.append(
                f"Insufficient room capacity! "
                f"Need {total_students} seats, have {total_capacity}. "
                f"Add {total_students - total_capacity} more seats."
            )
        else:
            utilization = (total_students / total_capacity) * 100
            print(f"  ✓ Capacity sufficient (Utilization: {utilization:.1f}%)")
            
            if utilization > 90:
                self.warnings.append(
                    f"High room utilization ({utilization:.1f}%). "
                    "Consider adding more rooms for flexibility."
                )
    
    def _check_exam_slots(self):
        """Check if enough slots for all exams."""
        print("\n📅 Checking exam slots...")
        
        num_courses = len(self.loader.courses)
        
        # Calculate available slots
        start_date = datetime.strptime(
            self.loader.exam_config.get('exam_start_date', '2025-12-01'),
            '%Y-%m-%d'
        )
        
        # Count slots in 2 weeks (should be enough for most cases)
        slots_available = 0
        current_date = start_date
        
        for _ in range(14):  # 2 weeks
            if current_date.weekday() != 6:  # Not Sunday
                slots_available += 2  # FN + AN
            current_date += timedelta(days=1)
        
        print(f"  Courses to schedule: {num_courses}")
        print(f"  Available slots (2 weeks): {slots_available}")
        
        if num_courses > slots_available:
            weeks_needed = (num_courses / 12) + 1  # 12 slots per week
            self.warnings.append(
                f"Need {num_courses} slots but have {slots_available} in 2 weeks. "
                f"Exams will extend to ~{int(weeks_needed)} weeks."
            )
        else:
            days_needed = (num_courses / 2) + 1
            print(f"  ✓ Can finish in ~{int(days_needed)} days")
    
    def _check_student_enrollment(self):
        """Check student enrollment distribution."""
        print("\n👥 Checking student distribution...")
        
        # Count students by section
        sections = {}
        branches = {}
        
        for student in self.loader.students:
            section_key = f"{student.branch}-{student.section}"
            sections[section_key] = sections.get(section_key, 0) + 1
            branches[student.branch] = branches.get(student.branch, 0) + 1
        
        print(f"  Branches: {len(branches)}")
        for branch, count in sorted(branches.items()):
            print(f"    {branch}: {count} students")
        
        print(f"  Sections: {len(sections)}")
        for section, count in sorted(sections.items()):
            print(f"    {section}: {count} students")
        
        # Check for empty sections
        if not sections:
            self.issues.append("No students found with valid section assignments")
    
    def _check_config(self):
        """Check exam configuration."""
        print("\n⚙️  Checking exam configuration...")
        
        required_params = [
            'exam_start_date',
            'morning_slot_start',
            'morning_slot_2hr_end',
            'morning_slot_3hr_end',
            'afternoon_slot_start',
            'afternoon_slot_2hr_end',
            'afternoon_slot_3hr_end'
        ]
        
        missing = []
        for param in required_params:
            if param not in self.loader.exam_config:
                missing.append(param)
        
        if missing:
            self.warnings.append(f"Missing config parameters: {', '.join(missing)}")
        else:
            print(f"  ✓ All configuration parameters present")
            
            # Validate date format
            try:
                start_date = datetime.strptime(
                    self.loader.exam_config['exam_start_date'],
                    '%Y-%m-%d'
                )
                print(f"  Exam start date: {start_date.strftime('%d %B %Y')}")
                
                # Check if date is in past
                if start_date < datetime.now():
                    self.warnings.append("Exam start date is in the past")
                
            except ValueError:
                self.issues.append("Invalid exam_start_date format. Use YYYY-MM-DD")
    
    def get_recommendations(self):
        """Provide recommendations for scaling."""
        print("\n" + "="*90)
        print("SCALING RECOMMENDATIONS".center(90))
        print("="*90)
        
        total_students = len(self.loader.students)
        total_capacity = sum(room.capacity for room in self.loader.exam_rooms)
        num_courses = len(self.loader.courses)
        
        print("\n📊 Current Setup:")
        print(f"  Students: {total_students}")
        print(f"  Courses: {num_courses}")
        print(f"  Rooms: {len(self.loader.exam_rooms)} (Total capacity: {total_capacity})")
        
        print("\n💡 To Add More Courses:")
        print(f"  - Current: {num_courses} courses")
        print(f"  - Max in 1 week: 12 courses (Mon-Sat, FN+AN)")
        print(f"  - Max in 2 weeks: 24 courses")
        print(f"  - For {num_courses} courses: Need ~{(num_courses/12):.1f} weeks")
        
        print("\n💡 To Add More Students:")
        print(f"  - Current capacity: {total_capacity} seats")
        print(f"  - Current students: {total_students}")
        print(f"  - Available: {total_capacity - total_students} seats")
        print(f"  - To add 100 more students: Need {((total_students + 100)/48):.0f} rooms total")
        print(f"  - To add 200 more students: Need {((total_students + 200)/48):.0f} rooms total")
        
        print("\n💡 To Add More Rooms:")
        print(f"  - Add rooms to exam_rooms.csv")
        print(f"  - Format: room_id,capacity,rows,columns")
        print(f"  - Standard: 48 capacity, 8 rows, 3 columns")
        print(f"  - Example: C206,48,8,3")
        
        print("\n💡 To Add More Branches:")
        print(f"  - Add students to students.csv with new branch code")
        print(f"  - Example: 24BDS001,Name,DS,A,3")
        print(f"  - Update courses.csv with appropriate student_group")
        print(f"  - System will automatically handle mixing")


def main():
    """Run validation."""
    validator = ExamValidator()
    
    if validator.validate_all():
        validator.get_recommendations()
        return 0
    else:
        print("\n" + "="*90)
        return 1


if __name__ == "__main__":
    sys.exit(main())