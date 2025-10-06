"""
Basic unit tests for the timetable scheduler.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import Course, Faculty, Room, Slot, Assignment
from data_loader import DataLoader


def test_course_creation():
    """Test creating a course object."""
    course = Course(
        code='CS101',
        title='Data Structures',
        lectures_per_week=3,
        faculty_id='F001',
        student_group='3rdSem-A'
    )
    
    assert course.code == 'CS101'
    assert course.title == 'Data Structures'
    assert course.lectures_per_week == 3
    print("✓ test_course_creation passed")


def test_faculty_availability():
    """Test faculty availability checking."""
    faculty = Faculty(faculty_id='F001', name='Dr. Test', max_hours_per_day=4)
    
    # Initially available
    assert faculty.is_available('Monday', 1) == True
    
    # Mark as unavailable
    faculty.add_unavailable_slot('Monday', 1)
    assert faculty.is_available('Monday', 1) == False
    
    # Still available on other days
    assert faculty.is_available('Tuesday', 1) == True
    print("✓ test_faculty_availability passed")


def test_room_creation():
    """Test creating a room object."""
    room = Room(room_id='R101', room_type='classroom', capacity=60)
    
    assert room.room_id == 'R101'
    assert room.room_type == 'classroom'
    assert room.capacity == 60
    print("✓ test_room_creation passed")


def test_slot_creation():
    """Test creating a time slot."""
    slot = Slot(slot_id=1, day='Monday', start_time='09:00', end_time='10:00')
    
    assert slot.slot_id == 1
    assert slot.day == 'Monday'
    assert slot.start_time == '09:00'
    print("✓ test_slot_creation passed")


def test_data_loader():
    """Test loading data from CSV files."""
    # This test will only pass if CSV files exist
    try:
        loader = DataLoader(data_dir='data')
        loader.load_all_data()
        
        assert len(loader.courses) > 0, "No courses loaded"
        assert len(loader.faculty) > 0, "No faculty loaded"
        assert len(loader.rooms) > 0, "No rooms loaded"
        assert len(loader.slots) > 0, "No slots generated"
        
        print("✓ test_data_loader passed")
    except FileNotFoundError:
        print("⚠ test_data_loader skipped - CSV files not found")


if __name__ == "__main__":
    """Run all tests."""
    print("=" * 60)
    print("RUNNING BASIC TESTS".center(60))
    print("=" * 60)
    
    test_course_creation()
    test_faculty_availability()
    test_room_creation()
    test_slot_creation()
    test_data_loader()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS COMPLETED".center(60))
    print("=" * 60)