"""
Basic unit tests for the timetable scheduler.
Tests core data models and basic functionality.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import Course, Faculty, Room, Slot, Assignment, Timetable


def test_course_creation():
    """
    Test Case 1: Course Object Creation
    Description: Verify that a Course object is created correctly with all attributes
    Expected Output: Course object with correct code, title, and parsed lectures_per_week
    """
    print("\n" + "="*70)
    print("TEST CASE 1: Course Object Creation")
    print("="*70)
    
    course = Course(
        code='CS101',
        title='Data Structures',
        ltpsc='3-1-0-0-4',
        faculty_id='F001',
        student_group='3rdSem-A'
    )
    
    # Test inputs
    print("Input:")
    print(f"  Code: CS101")
    print(f"  Title: Data Structures")
    print(f"  L-T-P-S-C: 3-1-0-0-4")
    print(f"  Faculty ID: F001")
    print(f"  Student Group: 3rdSem-A")
    
    # Assertions
    assert course.code == 'CS101', "Course code mismatch"
    assert course.title == 'Data Structures', "Course title mismatch"
    assert course.ltpsc == '3-1-0-0-4', "L-T-P-S-C format mismatch"
    assert course.lectures_per_week == 4, "Lectures per week should be 3+1=4"
    assert course.faculty_id == 'F001', "Faculty ID mismatch"
    assert course.student_group == '3rdSem-A', "Student group mismatch"
    
    # Expected output
    print("\nExpected Output:")
    print(f"  ✓ Course code: {course.code}")
    print(f"  ✓ Course title: {course.title}")
    print(f"  ✓ Lectures per week: {course.lectures_per_week}")
    print(f"  ✓ Faculty ID: {course.faculty_id}")
    
    print("\n✅ TEST PASSED: Course created successfully with all attributes")


def test_ltpsc_parsing():
    """
    Test Case 2: L-T-P-S-C Format Parsing
    Description: Verify correct parsing of different L-T-P-S-C formats
    Expected Output: Correct calculation of total lectures per week
    """
    print("\n" + "="*70)
    print("TEST CASE 2: L-T-P-S-C Format Parsing")
    print("="*70)
    
    test_cases = [
        ('2-1-0-0-2', 3),  # 2 lectures + 1 tutorial = 3
        ('3-0-2-0-4', 3),  # 3 lectures + 0 tutorials = 3
        ('4-0-0-0-4', 4),  # 4 lectures + 0 tutorials = 4
        ('2-2-0-0-3', 4),  # 2 lectures + 2 tutorials = 4
    ]
    
    print("Input & Expected Output:")
    for ltpsc, expected in test_cases:
        course = Course('TEST', 'Test Course', ltpsc, 'F001', '3rdSem-A')
        print(f"  L-T-P-S-C: {ltpsc} → Expected: {expected}, Got: {course.lectures_per_week}")
        assert course.lectures_per_week == expected, f"Failed for {ltpsc}"
    
    print("\n✅ TEST PASSED: All L-T-P-S-C formats parsed correctly")


def test_faculty_availability():
    """
    Test Case 3: Faculty Availability Management
    Description: Test adding unavailable slots and checking availability
    Expected Output: Faculty correctly marked as available/unavailable
    """
    print("\n" + "="*70)
    print("TEST CASE 3: Faculty Availability Management")
    print("="*70)
    
    faculty = Faculty(faculty_id='F001', name='Dr. Test', max_hours_per_day=4)
    
    print("Input:")
    print(f"  Faculty: {faculty.name}")
    print(f"  Max hours per day: {faculty.max_hours_per_day}")
    
    # Initially available
    print("\nTest 1: Check initial availability")
    print(f"  Checking Monday, Slot 1")
    assert faculty.is_available('Monday', 1) == True, "Should be available initially"
    print(f"  Result: ✓ Available")
    
    # Mark as unavailable
    print("\nTest 2: Mark slot as unavailable")
    faculty.add_unavailable_slot('Monday', 1)
    print(f"  Marked Monday, Slot 1 as unavailable")
    assert faculty.is_available('Monday', 1) == False, "Should be unavailable after marking"
    print(f"  Result: ✓ Correctly marked unavailable")
    
    # Still available on other days
    print("\nTest 3: Check availability on other days")
    print(f"  Checking Tuesday, Slot 1")
    assert faculty.is_available('Tuesday', 1) == True, "Should still be available on other days"
    print(f"  Result: ✓ Still available on Tuesday")
    
    print("\n✅ TEST PASSED: Faculty availability management working correctly")


def test_room_creation():
    """
    Test Case 4: Room Object Creation
    Description: Verify Room object creation with different types
    Expected Output: Room objects with correct attributes
    """
    print("\n" + "="*70)
    print("TEST CASE 4: Room Object Creation")
    print("="*70)
    
    test_rooms = [
        ('R101', 'classroom', 60),
        ('L201', 'lab', 30),
        ('AUDIT', 'Auditorium', 200),
    ]
    
    print("Input & Expected Output:")
    for room_id, room_type, capacity in test_rooms:
        room = Room(room_id=room_id, room_type=room_type, capacity=capacity)
        print(f"\n  Room ID: {room.room_id}")
        print(f"  Type: {room.room_type} (normalized to: {room.room_type.lower()})")
        print(f"  Capacity: {room.capacity}")
        
        assert room.room_id == room_id, "Room ID mismatch"
        assert room.room_type == room_type.lower(), "Room type should be lowercase"
        assert room.capacity == capacity, "Capacity mismatch"
        print(f"  ✓ Room created correctly")
    
    print("\n✅ TEST PASSED: All rooms created with correct attributes")


def test_slot_creation():
    """
    Test Case 5: Time Slot Creation
    Description: Verify time slot creation with various times
    Expected Output: Slot objects with correct day and time attributes
    """
    print("\n" + "="*70)
    print("TEST CASE 5: Time Slot Creation")
    print("="*70)
    
    slot = Slot(slot_id=1, day='Monday', start_time='09:00', end_time='10:00')
    
    print("Input:")
    print(f"  Slot ID: 1")
    print(f"  Day: Monday")
    print(f"  Start Time: 09:00")
    print(f"  End Time: 10:00")
    
    assert slot.slot_id == 1, "Slot ID mismatch"
    assert slot.day == 'Monday', "Day mismatch"
    assert slot.start_time == '09:00', "Start time mismatch"
    assert slot.end_time == '10:00', "End time mismatch"
    
    print("\nExpected Output:")
    print(f"  ✓ Slot ID: {slot.slot_id}")
    print(f"  ✓ Day: {slot.day}")
    print(f"  ✓ Time: {slot.start_time}-{slot.end_time}")
    
    print("\n✅ TEST PASSED: Time slot created successfully")


def test_assignment_creation():
    """
    Test Case 6: Assignment Creation
    Description: Test creating a class assignment linking all entities
    Expected Output: Assignment object with all relationships intact
    """
    print("\n" + "="*70)
    print("TEST CASE 6: Assignment Creation")
    print("="*70)
    
    course = Course('CS101', 'Data Structures', '3-0-0-0-3', 'F001', '3rdSem-A')
    faculty = Faculty('F001', 'Dr. Test', 4)
    room = Room('R101', 'classroom', 60)
    slot = Slot(1, 'Monday', '09:00', '10:00')
    
    assignment = Assignment(
        course=course,
        faculty=faculty,
        room=room,
        slot=slot,
        student_group='3rdSem-A'
    )
    
    print("Input:")
    print(f"  Course: {course.code} - {course.title}")
    print(f"  Faculty: {faculty.name}")
    print(f"  Room: {room.room_id}")
    print(f"  Slot: {slot.day} {slot.start_time}-{slot.end_time}")
    print(f"  Student Group: 3rdSem-A")
    
    assert assignment.course.code == 'CS101', "Course mismatch"
    assert assignment.faculty.name == 'Dr. Test', "Faculty mismatch"
    assert assignment.room.room_id == 'R101', "Room mismatch"
    assert assignment.slot.day == 'Monday', "Slot day mismatch"
    assert assignment.student_group == '3rdSem-A', "Student group mismatch"
    
    print("\nExpected Output:")
    print(f"  ✓ Assignment created linking all entities")
    print(f"  ✓ Course: {assignment.course.code}")
    print(f"  ✓ Faculty: {assignment.faculty.name}")
    print(f"  ✓ Room: {assignment.room.room_id}")
    print(f"  ✓ Time: {assignment.slot.day} {assignment.slot.start_time}")
    
    print("\n✅ TEST PASSED: Assignment created with all relationships")


def test_timetable_management():
    """
    Test Case 7: Timetable Management
    Description: Test adding assignments and filtering by group/faculty
    Expected Output: Correct retrieval of assignments by filters
    """
    print("\n" + "="*70)
    print("TEST CASE 7: Timetable Management")
    print("="*70)
    
    timetable = Timetable()
    
    # Create test entities
    course1 = Course('CS101', 'DS', '3-0-0-0-3', 'F001', '3rdSem-A')
    course2 = Course('CS102', 'Algo', '3-0-0-0-3', 'F002', '3rdSem-A')
    course3 = Course('CS201', 'OS', '3-0-0-0-3', 'F001', '3rdSem-B')
    
    faculty1 = Faculty('F001', 'Dr. A', 4)
    faculty2 = Faculty('F002', 'Dr. B', 4)
    
    room1 = Room('R101', 'classroom', 60)
    slot1 = Slot(1, 'Monday', '09:00', '10:00')
    slot2 = Slot(2, 'Monday', '10:10', '11:10')
    slot3 = Slot(3, 'Tuesday', '09:00', '10:00')
    
    # Create assignments
    a1 = Assignment(course1, faculty1, room1, slot1, '3rdSem-A')
    a2 = Assignment(course2, faculty2, room1, slot2, '3rdSem-A')
    a3 = Assignment(course3, faculty1, room1, slot3, '3rdSem-B')
    
    timetable.add_assignment(a1)
    timetable.add_assignment(a2)
    timetable.add_assignment(a3)
    
    print("Input:")
    print(f"  Added 3 assignments to timetable")
    print(f"    - CS101 for 3rdSem-A by F001")
    print(f"    - CS102 for 3rdSem-A by F002")
    print(f"    - CS201 for 3rdSem-B by F001")
    
    # Test filtering by group
    print("\nTest 1: Get assignments for 3rdSem-A")
    group_a = timetable.get_assignments_by_group('3rdSem-A')
    assert len(group_a) == 2, "Should have 2 assignments for 3rdSem-A"
    print(f"  Result: ✓ Found {len(group_a)} assignments")
    
    print("\nTest 2: Get assignments for 3rdSem-B")
    group_b = timetable.get_assignments_by_group('3rdSem-B')
    assert len(group_b) == 1, "Should have 1 assignment for 3rdSem-B"
    print(f"  Result: ✓ Found {len(group_b)} assignments")
    
    print("\nTest 3: Get assignments for Faculty F001")
    faculty_assignments = timetable.get_assignments_by_faculty('F001')
    assert len(faculty_assignments) == 2, "F001 should have 2 assignments"
    print(f"  Result: ✓ Found {len(faculty_assignments)} assignments")
    
    print("\n✅ TEST PASSED: Timetable management and filtering working correctly")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("AUTOMATED TIMETABLE SCHEDULER - UNIT TESTS")
    print("Team: Byte Me")
    print("="*70)
    
    tests = [
        test_course_creation,
        test_ltpsc_parsing,
        test_faculty_availability,
        test_room_creation,
        test_slot_creation,
        test_assignment_creation,
        test_timetable_management,
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