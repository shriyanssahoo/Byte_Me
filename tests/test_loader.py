"""
tests/test_loader.py

Basic unit tests for the data_loader and models.
Requires 'pytest' to run.
"""
import pytest
from src.models import Course, Classroom
from src.utils import get_floor_from_room, get_room_number_from_id

def test_classroom_parsing():
    """Tests the C/L prefix rule and floor parsing."""
    
    # Test correct parsing
    c101 = Classroom("C101", 90, "Classroom", 1, [])
    assert c101.floor == 1
    assert c101.room_type == "CLASSROOM"
    
    # Test prefix override
    # This is our C406 -> L406 data issue
    l406 = Classroom("L406", 78, "Classroom", 4, [])
    assert l406.floor == 4
    assert l406.room_type == "LAB" # Should be overridden
    
    # Test floor parsing
    assert get_floor_from_room("C004") == 0
    assert get_floor_from_room("L209") == 2
    
    # Test room number parsing
    assert get_room_number_from_id("L101") == 101
    assert get_room_number_from_id("L102") == 102

def test_course_ltpsc_parsing():
    """Tests the LTPSC parsing logic in the Course model."""
    
    # Standard L=3
    course1 = Course("CS101", "Test", 1, "CSE", "3-1-2-0-4", 4, [], 100, False, False, False, "FULL", "")
    assert course1.L == 3
    assert course1.T == 1
    assert course1.P == 2
    sessions1 = course1.get_required_sessions()
    assert sessions1["lecture"] == 2
    assert sessions1["tutorial"] == 1
    assert sessions1["practical"] == 1
    
    # Test L=1 rule
    course2 = Course("HS157", "Test 2", 1, "CSE", "1-0-0-0-1", 1, [], 100, True, False, False, "FULL", "a")
    assert course2.L == 1
    assert course2.T == 0
    assert course2.P == 0
    sessions2 = course2.get_required_sessions()
    assert sessions2["lecture"] == 0
    assert sessions2["tutorial"] == 1 # 1 from L=1 rule
    assert sessions2["practical"] == 0