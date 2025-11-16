"""
tests/test_scheduler.py

Basic unit tests for the scheduler logic.
Requires 'pytest' to run.
"""
import pytest
# FIX: Add ScheduledClass to the import list
from src.models import Course, Classroom, Section, Timetable, ScheduledClass
from src.scheduler import Scheduler
from src.utils import FACULTY_BREAK_SLOTS

@pytest.fixture
def basic_scheduler() -> Scheduler:
    """Returns a scheduler instance with a few rooms."""
    classrooms = [
        Classroom("C101", 100, "CLASSROOM", 1, []),
        Classroom("C102", 100, "CLASSROOM", 1, []),
        Classroom("L101", 50, "LAB", 1, []),
        Classroom("L102", 50, "LAB", 1, []), # Adjacent
        Classroom("L104", 50, "LAB", 1, []), # Not adjacent
    ]
    return Scheduler(classrooms, "PRE")

def test_faculty_break_rule(basic_scheduler):
    """Tests that the 30-min (3-slot) faculty break rule is enforced."""
    
    # Book a 90-min (9-slot) class at 9:00 (slot 0)
    day = 0 # Monday
    start_slot = 0
    duration = 9 # 9:00 - 10:30
    
    faculty_tt = basic_scheduler._get_or_create_faculty_schedule("Dr. Test")
    
    # Mock a booking
    mock_course = Course("CS101", "Test", 1, "CSE", "3-0-0-0-3", 3, ["Dr. Test"], 100, False, False, False, "FULL", "")
    mock_class = ScheduledClass(mock_course, "Lecture", "CSE-Sem1-Pre-A", ["Dr. Test"], ["C101"])
    faculty_tt.book_slot(day, start_slot, duration, mock_class)
    
    # Class ends at slot 9 (10:30)
    # Faculty is free from slot 9
    
    # Check availability for a 10:30 (slot 9) class -> SHOULD FAIL
    # This is 0-min break
    assert basic_scheduler._check_faculty_availability(["Dr. Test"], day, 9, 6) == False
    
    # Check availability for a 10:40 (slot 10) class -> SHOULD FAIL
    # This is 10-min break
    assert basic_scheduler._check_faculty_availability(["Dr. Test"], day, 10, 6) == False
    
    # Check availability for a 10:50 (slot 11) class -> SHOULD FAIL
    # This is 20-min break
    assert basic_scheduler._check_faculty_availability(["Dr. Test"], day, 11, 6) == False
    
    # Check availability for a 11:00 (slot 12) class -> SHOULD PASS
    # This is 30-min break (slot 9, 10, 11 are free)
    assert basic_scheduler._check_faculty_availability(["Dr. Test"], day, 12, 6) == True

def test_lab_adjacency(basic_scheduler):
    """Tests that the scheduler finds L101 and L102."""
    
    day = 0
    start_slot = 0
    duration = 12 # 120-min
    
    # Should find L101 and L102
    rooms = basic_scheduler._find_adjacent_labs(day, start_slot, duration, 100)
    assert rooms is not None
    assert len(rooms) == 2
    assert rooms[0].room_id == "L101"
    assert rooms[1].room_id == "L102"
    
    # Book L101 and check again, it should fail
    lab1_tt = basic_scheduler._get_or_create_room_schedule("L101")
    mock_course = Course("CS101", "Test", 1, "CSE", "3-0-0-0-3", 3, [], 100, False, False, False, "FULL", "")
    mock_class = ScheduledClass(mock_course, "Practical", "CSE-Sem1-Pre-A", [], ["L101"])
    lab1_tt.book_slot(day, start_slot, duration, mock_class)
    
    rooms_fail = basic_scheduler._find_adjacent_labs(day, start_slot, duration, 100)
    assert rooms_fail is None