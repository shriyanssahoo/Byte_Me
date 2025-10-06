"""
Debug script to check your courses.csv file.
Run: python debug_csv.py
"""

import pandas as pd

print("=" * 70)
print("CHECKING YOUR COURSES.CSV FILE".center(70))
print("=" * 70)

try:
    df = pd.read_csv('data/courses.csv')
    
    print("\n✓ File loaded successfully!")
    print(f"\nRows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    
    print("\n📋 YOUR COLUMN NAMES:")
    print("-" * 70)
    for i, col in enumerate(df.columns, 1):
        print(f"{i}. '{col}' (length: {len(col)} chars)")
    
    print("\n📋 EXPECTED COLUMN NAMES:")
    print("-" * 70)
    expected = ['code', 'title', 'lectures_p', 'faculty_id', 'student_group']
    for i, col in enumerate(expected, 1):
        print(f"{i}. '{col}'")
    
    print("\n🔍 MATCHING CHECK:")
    print("-" * 70)
    for exp_col in expected:
        if exp_col in df.columns:
            print(f"✓ '{exp_col}' - FOUND")
        else:
            print(f"✗ '{exp_col}' - MISSING")
            # Try to find similar columns
            similar = [c for c in df.columns if exp_col.lower() in c.lower() or c.lower() in exp_col.lower()]
            if similar:
                print(f"  → Did you mean: {similar}?")
    
    print("\n📄 FIRST 3 ROWS OF DATA:")
    print("-" * 70)
    print(df.head(3).to_string())
    
    print("\n💡 SOLUTION:")
    print("-" * 70)
    print("Your CSV column names should be EXACTLY:")
    print("code,title,lectures_p,faculty_id,student_group")
    print("\nMake sure:")
    print("1. No spaces after commas")
    print("2. All lowercase")
    print("3. Exact spelling")

except FileNotFoundError:
    print("\n❌ File not found: data/courses.csv")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 70)