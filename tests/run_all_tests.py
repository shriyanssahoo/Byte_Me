"""
Master test runner - Runs all test suites.
Usage: python tests/run_all_tests.py
"""

import sys
import os

# Add tests directory to path
sys.path.insert(0, os.path.dirname(__file__))

import test_basic
import test_scheduler
import test_data_loader


def main():
    """Run all test suites and generate summary report."""
    print("\n" + "="*70)
    print("AUTOMATED TIMETABLE SCHEDULER - COMPLETE TEST SUITE")
    print("Team: Byte Me | IIIT Dharwad")
    print("="*70)
    
    all_passed = True
    
    # Run test_basic
    print("\n\n" + "▶"*35)
    print("RUNNING: Basic Unit Tests")
    print("▶"*35)
    if not test_basic.run_all_tests():
        all_passed = False
    
    # Run test_scheduler
    print("\n\n" + "▶"*35)
    print("RUNNING: Scheduler Algorithm Tests")
    print("▶"*35)
    if not test_scheduler.run_all_tests():
        all_passed = False
    
    # Run test_data_loader
    print("\n\n" + "▶"*35)
    print("RUNNING: Data Loader Tests")
    print("▶"*35)
    if not test_data_loader.run_all_tests():
        all_passed = False
    
    # Final summary
    print("\n\n" + "="*70)
    print("FINAL TEST REPORT")
    print("="*70)
    
    if all_passed:
        print("✅ ALL TEST SUITES PASSED")
        print("\nStatus: READY FOR DEPLOYMENT")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nStatus: NEEDS ATTENTION")
    
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)