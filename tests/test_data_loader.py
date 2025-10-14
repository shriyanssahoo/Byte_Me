"""
Unit tests for data loading functionality.
Tests CSV parsing, data validation, and error handling.
"""

import sys
import os
import csv
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_loader import DataLoader


def create_test_csv(filename, headers, rows):
    """Helper function to create test CSV files."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def test_load_valid_courses():
    """
    Test Case 13: Load Valid Courses CSV
    Description: Test loading correctly formatted courses.csv
    Expected Output: All courses loaded successfully
    """
    print("\n" + "="*70)
    print("TEST CASE 13: Load Valid Courses CSV")
    print("="*70)
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create test CSV
        create_test_csv(
            os.path.join(temp_dir, 'courses.csv'),
            ['code', 'title', 'lectures_p', 'faculty_id', 'student_group'],
            [
                ['CS101', 'Data Structures', '3-0-0-0-3', 'F001', '3rdSem-A'],
                ['CS102', 'Algorithms', '3-1-0-0-4', 'F002', '3rdSem-A'],
                ['MA101', 'Mathematics', '2-1-0-0-2', 'F003', '3rdSem-B'],
            ]
        )
        
        create_test_csv(
            os.path.join(temp_dir, 'faculty.csv'),
            ['faculty_id', 'name', 'max_hours_per_day'],
            [
                ['F001', 'Dr. A', '4'],
                ['F002', 'Dr. B', '4'],
                ['F003', 'Dr. C', '3'],
            ]
        )
        
        create_test_csv(
            os.path.join(temp_dir, 'rooms.csv'),
            ['room_id', 'room_type', 'capacity'],
            [
                ['R101', 'classroom', '60'],
                ['L201', 'lab', '30'],
            ]
        )
        
        print("Input:")
        print(f"  Created test CSV files with valid data")
        print(f"  - 3 courses")
        print(f"  - 3 faculty members")
        print(f"  - 2 rooms")
        
        loader = DataLoader(data_dir=temp_dir)
        loader.load_all_data()
        
        print("\nExpected Output:")
        print(f"  ✓ Courses loaded: {len(loader.courses)}")
        print(f"  ✓ Faculty loaded: {len(loader.faculty)}")
        print(f"  ✓ Rooms loaded: {len(loader.rooms)}")
        print(f"  ✓ Slots generated: {len(loader.slots)}")
        
        assert len(loader.courses) == 3, "Should load 3 courses"
        assert len(loader.faculty) == 3, "Should load 3 faculty"
        assert len(loader.rooms) == 2, "Should load 2 rooms"
        assert len(loader.slots) > 0, "Should generate time slots"
        
        print("\n✅ TEST PASSED: Valid CSV data loaded successfully")
        
    finally:
        shutil.rmtree(temp_dir)


def test_load_courses_with_whitespace():
    """
    Test Case 14: Handle CSV with Extra Whitespace
    Description: Test loading CSV with spaces in column names and values
    Expected Output: Data loaded correctly with whitespace stripped
    """
    print("\n" + "="*70)
    print("TEST CASE 14: Handle CSV with Extra Whitespace")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create CSV with extra spaces
        with open(os.path.join(temp_dir, 'courses.csv'), 'w', newline='') as f:
            f.write("code , title , lectures_p , faculty_id , student_group\n")
            f.write(" CS101 , Data Structures , 3-0-0-0-3 , F001 , 3rdSem-A \n")
        
        create_test_csv(
            os.path.join(temp_dir, 'faculty.csv'),
            ['faculty_id', 'name', 'max_hours_per_day'],
            [['F001', 'Dr. A', '4']]
        )
        
        create_test_csv(
            os.path.join(temp_dir, 'rooms.csv'),
            ['room_id', 'room_type', 'capacity'],
            [['R101', 'classroom', '60']]
        )
        
        print("Input:")
        print(f"  CSV with extra whitespace in headers and values")
        
        loader = DataLoader(data_dir=temp_dir)
        loader.load_all_data()
        
        print("\nExpected Output:")
        print(f"  ✓ Courses loaded: {len(loader.courses)}")
        print(f"  ✓ Course code (trimmed): '{loader.courses[0].code}'")
        
        assert len(loader.courses) == 1, "Should load 1 course"
        assert loader.courses[0].code == 'CS101', "Code should be trimmed"
        
        print("\n✅ TEST PASSED: Whitespace handled correctly")
        
    finally:
        shutil.rmtree(temp_dir)


def test_load_missing_file():
    """
    Test Case 15: Handle Missing CSV File
    Description: Test behavior when CSV file doesn't exist
    Expected Output: Graceful error handling, no crash
    """
    print("\n" + "="*70)
    print("TEST CASE 15: Handle Missing CSV File")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        print("Input:")
        print(f"  Empty directory (no CSV files)")
        
        loader = DataLoader(data_dir=temp_dir)
        loader.load_all_data()
        
        print("\nExpected Output:")
        print(f"  ✓ No crash on missing files")
        print(f"  ✓ Courses loaded: {len(loader.courses)} (should be 0)")
        print(f"  ✓ Faculty loaded: {len(loader.faculty)} (should be 0)")
        
        assert len(loader.courses) == 0, "Should have no courses"
        assert len(loader.faculty) == 0, "Should have no faculty"
        
        print("\n✅ TEST PASSED: Missing files handled gracefully")
        
    finally:
        shutil.rmtree(temp_dir)


def test_slot_generation():
    """
    Test Case 16: Time Slot Generation
    Description: Verify correct generation of time slots
    Expected Output: Proper slots for all weekdays with lunch break excluded
    """
    print("\n" + "="*70)
    print("TEST CASE 16: Time Slot Generation")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create minimal CSV files
        create_test_csv(
            os.path.join(temp_dir, 'courses.csv'),
            ['code', 'title', 'lectures_p', 'faculty_id', 'student_group'],
            []
        )
        create_test_csv(
            os.path.join(temp_dir, 'faculty.csv'),
            ['faculty_id', 'name', 'max_hours_per_day'],
            []
        )
        create_test_csv(
            os.path.join(temp_dir, 'rooms.csv'),
            ['room_id', 'room_type', 'capacity'],
            []
        )
        
        print("Input:")
        print(f"  Generate time slots for standard week")
        
        loader = DataLoader(data_dir=temp_dir)
        loader.load_all_data()
        
        # Check slot properties
        days = set(slot.day for slot in loader.slots)
        times = [(slot.start_time, slot.end_time) for slot in loader.slots]
        
        print("\nExpected Output:")
        print(f"  ✓ Total slots: {len(loader.slots)}")
        print(f"  ✓ Days covered: {sorted(days)}")
        print(f"  ✓ First slot: {loader.slots[0].start_time}-{loader.slots[0].end_time}")
        
        assert len(days) == 5, "Should have 5 weekdays"
        assert 'Monday' in days and 'Friday' in days, "Should include Mon-Fri"
        assert len(loader.slots) > 0, "Should generate slots"
        
        print("\n✅ TEST PASSED: Time slots generated correctly")
        
    finally:
        shutil.rmtree(temp_dir)


def test_invalid_ltpsc_format():
    """
    Test Case 17: Handle Invalid L-T-P-S-C Format
    Description: Test handling of malformed L-T-P-S-C values
    Expected Output: Default value used or graceful error
    """
    print("\n" + "="*70)
    print("TEST CASE 17: Handle Invalid L-T-P-S-C Format")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        create_test_csv(
            os.path.join(temp_dir, 'courses.csv'),
            ['code', 'title', 'lectures_p', 'faculty_id', 'student_group'],
            [
                ['CS101', 'Valid Course', '3-0-0-0-3', 'F001', '3rdSem-A'],
                ['CS102', 'Invalid Course', 'invalid', 'F001', '3rdSem-A'],
            ]
        )
        
        create_test_csv(
            os.path.join(temp_dir, 'faculty.csv'),
            ['faculty_id', 'name', 'max_hours_per_day'],
            [['F001', 'Dr. A', '4']]
        )
        
        create_test_csv(
            os.path.join(temp_dir, 'rooms.csv'),
            ['room_id', 'room_type', 'capacity'],
            [['R101', 'classroom', '60']]
        )
        
        print("Input:")
        print(f"  Course with valid L-T-P-S-C: '3-0-0-0-3'")
        print(f"  Course with invalid L-T-P-S-C: 'invalid'")
        
        loader = DataLoader(data_dir=temp_dir)
        loader.load_all_data()
        
        print("\nExpected Output:")
        print(f"  ✓ Courses loaded: {len(loader.courses)}")
        print(f"  ✓ Valid course lectures: {loader.courses[0].lectures_per_week}")
        print(f"  ✓ Invalid course lectures: {loader.courses[1].lectures_per_week} (default)")
        
        assert len(loader.courses) == 2, "Should load both courses"
        assert loader.courses[1].lectures_per_week == 3, "Should use default value of 3"
        
        print("\n✅ TEST PASSED: Invalid L-T-P-S-C handled with default value")
        
    finally:
        shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all data loader tests."""
    print("\n" + "="*70)
    print("DATA LOADER TESTS")
    print("Team: Byte Me")
    print("="*70)
    
    tests = [
        test_load_valid_courses,
        test_load_courses_with_whitespace,
        test_load_missing_file,
        test_slot_generation,
        test_invalid_ltpsc_format,
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