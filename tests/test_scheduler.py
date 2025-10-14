"""
Unit tests for the scheduling algorithm.
Tests conflict detection, constraint handling, and schedule generation.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import Course, Faculty, Room, Slot
from scheduler import Scheduler


def test_conflict_detection():
    """
    Test Case 8: Conflict Detection
    Description: Verify that the scheduler detects faculty, room, and student conflicts
    Expected Output: Conflicts are detected and reported correctly
    """
    print("\n" + "="*70)
    print("TEST CASE 8: Conflict Detection")
    print("="*70)
    
    # Create test data
    courses = [
        Course('CS101', 'DS', '2-0-0-0-2', 'F001', '3rdSem-A'),
        Course('CS102', 'Algo', '2-0-0-0-2', 'F001', '3rdSem-B'),
    ]
    
    faculty = {
        'F001': Faculty('F001', 'Dr. Test', 4)
    }
    
    rooms = [
        Room('R101', 'classroom', 60),
        Room('R102', 'classroom', 60)
    ]
    
    slots = [
        Slot(0, 'Monday', '09:00', '10:00'),
        Slot(1, 'Monday', '10:10', '11:10'),
        Slot(2, 'Tuesday', '09:00', '10:00'),
    ]
    
    print("Input:")
    print(f"  Courses: 2 (CS101 for 3rdSem-A, CS102 for 3rdSem-B)")
    print(f"  Faculty: 1 (F001 teaching both courses)")
    print(f"  Rooms: 2")
    print(f"  Slots: 3")
    
    scheduler = Scheduler(courses, faculty, rooms, slots)
    timetable = scheduler.generate_timetable()
    is_valid = scheduler.validate_timetable()
    
    print("\nExpected Output:")
    print(f"  ✓ Timetable generated")
    print(f"  ✓ Total assignments: {len(timetable.assignments)}")
    print(f"  ✓ Conflict-free: {is_valid}")
    
    assert is_valid, "Timetable should be conflict-free"
    
    print("\n✅ TEST PASSED: Conflict detection working correctly")


def test_lunch_break_constraint():
    """
    Test Case 9: Lunch Break Constraint
    Description: Verify that no classes are scheduled during lunch break (13:30-14:00)
    Expected Output: No assignments during lunch break time
    """
    print("\n" + "="*70)
    print("TEST CASE 9: Lunch Break Constraint")
    print("="*70)
    
    courses = [Course('CS101', 'DS', '5-0-0-0-5', 'F001', '3rdSem-A')]
    faculty = {'F001': Faculty('F001', 'Dr. Test', 4)}
    rooms = [Room('R101', 'classroom', 60)]
    
    # Include lunch break slot
    slots = [
        Slot(0, 'Monday', '12:30', '13:20'),
        Slot(1, 'Monday', '13:30', '14:00'),  # Lunch break
        Slot(2, 'Monday', '14:00', '15:00'),
        Slot(3, 'Tuesday', '09:00', '10:00'),
        Slot(4, 'Tuesday', '10:10', '11:10'),
    ]
    
    print("Input:")
    print(f"  Course with 5 lectures per week")
    print(f"  Slots including 13:30-14:00 (lunch break)")
    
    scheduler = Scheduler(courses, faculty, rooms, slots)
    timetable = scheduler.generate_timetable()
    
    # Check no classes during lunch
    lunch_assignments = [
        a for a in timetable.assignments 
        if a.slot.start_time >= '13:30' and a.slot.end_time <= '14:00'
    ]
    
    print("\nExpected Output:")
    print(f"  ✓ Total assignments: {len(timetable.assignments)}")
    print(f"  ✓ Assignments during lunch break: {len(lunch_assignments)}")
    
    assert len(lunch_assignments) == 0, "No classes should be scheduled during lunch break"
    
    print("\n✅ TEST PASSED: Lunch break constraint respected")


def test_one_lecture_per_day():
    """
    Test Case 10: One Lecture Per Course Per Day
    Description: Verify maximum one lecture of same course on same day
    Expected Output: No course has multiple lectures on the same day
    """
    print("\n" + "="*70)
    print("TEST CASE 10: One Lecture Per Course Per Day")
    print("="*70)
    
    courses = [Course('CS101', 'DS', '3-0-0-0-3', 'F001', '3rdSem-A')]
    faculty = {'F001': Faculty('F001', 'Dr. Test', 4)}
    rooms = [Room('R101', 'classroom', 60)]
    
    # Multiple slots on same day
    slots = [
        Slot(0, 'Monday', '09:00', '10:00'),
        Slot(1, 'Monday', '10:10', '11:10'),
        Slot(2, 'Monday', '11:20', '12:20'),
        Slot(3, 'Tuesday', '09:00', '10:00'),
        Slot(4, 'Wednesday', '09:00', '10:00'),
    ]
    
    print("Input:")
    print(f"  Course: CS101 with 3 lectures per week")
    print(f"  Multiple slots available on Monday")
    
    scheduler = Scheduler(courses, faculty, rooms, slots)
    timetable = scheduler.generate_timetable()
    
    # Count lectures per day
    day_count = {}
    for assignment in timetable.assignments:
        key = (assignment.course.code, assignment.slot.day)
        day_count[key] = day_count.get(key, 0) + 1
    
    max_per_day = max(day_count.values()) if day_count else 0
    
    print("\nExpected Output:")
    print(f"  ✓ Total assignments: {len(timetable.assignments)}")
    print(f"  ✓ Max lectures per day: {max_per_day}")
    
    assert max_per_day <= 1, "Should not have more than 1 lecture per day"
    
    print("\n✅ TEST PASSED: One lecture per day constraint satisfied")


def test_section_splitting():
    """
    Test Case 11: Combined Section Splitting (A&B)
    Description: Verify courses with A&B are split into separate sections
    Expected Output: Separate schedules for Section A and Section B
    """
    print("\n" + "="*70)
    print("TEST CASE 11: Combined Section Splitting")
    print("="*70)
    
    courses = [Course('CS101', 'DS', '2-0-0-0-2', 'F001', '3rdSem-A&B')]
    faculty = {'F001': Faculty('F001', 'Dr. Test', 4)}
    rooms = [Room('R101', 'classroom', 60), Room('R102', 'classroom', 60)]
    
    slots = [
        Slot(i, 'Monday', f'{9+i}:00', f'{10+i}:00') 
        for i in range(5)
    ]
    
    print("Input:")
    print(f"  Course: CS101 for combined sections (3rdSem-A&B)")
    print(f"  Expected: Separate schedules for A and B")
    
    scheduler = Scheduler(courses, faculty, rooms, slots)
    timetable = scheduler.generate_timetable()
    
    # Check both sections have assignments
    section_a = [a for a in timetable.assignments if a.student_group == '3rdSem-A']
    section_b = [a for a in timetable.assignments if a.student_group == '3rdSem-B']
    
    print("\nExpected Output:")
    print(f"  ✓ Section A assignments: {len(section_a)}")
    print(f"  ✓ Section B assignments: {len(section_b)}")
    print(f"  ✓ Both sections scheduled separately: {len(section_a) > 0 and len(section_b) > 0}")
    
    assert len(section_a) > 0, "Section A should have assignments"
    assert len(section_b) > 0, "Section B should have assignments"
    
    print("\n✅ TEST PASSED: Combined sections split correctly")


def test_day_distribution():
    """
    Test Case 12: Even Day Distribution
    Description: Verify classes are distributed evenly across weekdays
    Expected Output: No single day is overloaded
    """
    print("\n" + "="*70)
    print("TEST CASE 12: Even Day Distribution")
    print("="*70)
    
    courses = [
        Course('CS101', 'DS', '3-0-0-0-3', 'F001', '3rdSem-A'),
        Course('CS102', 'Algo', '3-0-0-0-3', 'F002', '3rdSem-A'),
    ]
    
    faculty = {
        'F001': Faculty('F001', 'Dr. A', 4),
        'F002': Faculty('F002', 'Dr. B', 4),
    }
    
    rooms = [Room('R101', 'classroom', 60)]
    
    # Create slots for all weekdays
    slots = []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slot_id = 0
    for day in days:
        for hour in range(9, 13):
            slots.append(Slot(slot_id, day, f'{hour:02d}:00', f'{hour+1:02d}:00'))
            slot_id += 1
    
    print("Input:")
    print(f"  Courses: 2 courses with 3 lectures each")
    print(f"  Total lectures to schedule: 6")
    
    scheduler = Scheduler(courses, faculty, rooms, slots)
    timetable = scheduler.generate_timetable()
    
    # Count per day
    day_count = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0, 'Friday': 0}
    for assignment in timetable.assignments:
        if assignment.student_group == '3rdSem-A':
            day_count[assignment.slot.day] += 1
    
    max_load = max(day_count.values())
    min_load = min(day_count.values())
    
    print("\nExpected Output:")
    print(f"  Day-wise distribution:")
    for day, count in day_count.items():
        print(f"    {day}: {count} classes")
    print(f"  ✓ Max load on any day: {max_load}")
    print(f"  ✓ Min load on any day: {min_load}")
    print(f"  ✓ Difference: {max_load - min_load}")
    
    # Allow max difference of 2
    assert max_load - min_load <= 2, "Distribution should be relatively even"
    
    print("\n✅ TEST PASSED: Classes distributed evenly across days")


def run_all_tests():
    """Run all scheduler tests."""
    print("\n" + "="*70)
    print("SCHEDULER ALGORITHM TESTS")
    print("Team: Byte Me")
    print("="*70)
    
    tests = [
        test_conflict_detection,
        test_lunch_break_constraint,
        test_one_lecture_per_day,
        test_section_splitting,
        test_day_distribution,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)