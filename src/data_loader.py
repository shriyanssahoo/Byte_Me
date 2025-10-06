"""
Data loader module to read input data from CSV files.
"""

import pandas as pd
from models import Course, Faculty, Room, Slot


class DataLoader:
    """Loads all input data from CSV files."""
    
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.courses = []
        self.faculty = {}
        self.rooms = []
        self.slots = []
    
    def load_all_data(self):
        """Load all data from CSV files."""
        self.load_faculty()
        self.load_rooms()
        self.load_slots()
        self.load_courses()
        print(f"✓ Loaded {len(self.courses)} courses")
        print(f"✓ Loaded {len(self.faculty)} faculty members")
        print(f"✓ Loaded {len(self.rooms)} rooms")
        print(f"✓ Loaded {len(self.slots)} time slots")
    
    def load_courses(self):
        """Load courses from courses.csv"""
        try:
            df = pd.read_csv(f'{self.data_dir}/courses.csv')
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            # Find the lectures column - try multiple possible names
            lectures_col = None
            possible_names = ['lectures_p', 'lectures_per_week', 'lectures', 'ltpsc', 'L-T-P-S-C']
            
            for col_name in possible_names:
                if col_name in df.columns:
                    lectures_col = col_name
                    break
            
            if not lectures_col:
                # Show what columns we actually have
                print(f"⚠ Available columns: {list(df.columns)}")
                raise KeyError("Could not find lectures column. Expected one of: " + ", ".join(possible_names))
            
            for _, row in df.iterrows():
                # Handle the lectures column (which contains L-T-P-S-C format)
                ltpsc = str(row[lectures_col]).strip()
                
                course = Course(
                    code=str(row['code']).strip(),
                    title=str(row['title']).strip(),
                    ltpsc=ltpsc,
                    faculty_id=str(row['faculty_id']).strip(),
                    student_group=str(row['student_group']).strip()
                )
                self.courses.append(course)
                
        except FileNotFoundError:
            print(f"⚠ Warning: courses.csv not found in {self.data_dir}")
        except KeyError as e:
            print(f"⚠ Error loading courses: Missing column {e}")
            print(f"   Expected columns: code, title, lectures_p, faculty_id, student_group")
        except Exception as e:
            print(f"⚠ Error loading courses: {e}")
    
    def load_faculty(self):
        """Load faculty from faculty.csv"""
        try:
            df = pd.read_csv(f'{self.data_dir}/faculty.csv')
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                faculty = Faculty(
                    faculty_id=str(row['faculty_id']).strip(),
                    name=str(row['name']).strip(),
                    max_hours_per_day=int(row.get('max_hours_per_day', 4))
                )
                self.faculty[str(row['faculty_id']).strip()] = faculty
                
        except FileNotFoundError:
            print(f"⚠ Warning: faculty.csv not found in {self.data_dir}")
        except Exception as e:
            print(f"⚠ Error loading faculty: {e}")
    
    def load_rooms(self):
        """Load rooms from rooms.csv"""
        try:
            df = pd.read_csv(f'{self.data_dir}/rooms.csv')
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                room = Room(
                    room_id=str(row['room_id']).strip(),
                    room_type=str(row['room_type']).strip(),
                    capacity=int(row['capacity'])
                )
                self.rooms.append(room)
                
        except FileNotFoundError:
            print(f"⚠ Warning: rooms.csv not found in {self.data_dir}")
        except Exception as e:
            print(f"⚠ Error loading rooms: {e}")
    
    def load_slots(self):
        """Generate standard time slots for the week."""
        # Define standard time slots (9 AM - 6 PM, with lunch 1:30-2:00 PM)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_slots = [
            ('09:00', '10:00'),
            ('10:10', '11:10'),
            ('11:20', '12:20'),
            ('12:30', '13:20'),
            # Lunch break 1:30 PM - 2:00 PM (skipped in scheduling)
            ('14:00', '15:00'),
            ('15:10', '16:10'),
            ('16:20', '17:20'),
            ('17:30', '18:00'),
        ]
        
        slot_id = 0
        for day in days:
            for start, end in time_slots:
                slot = Slot(slot_id, day, start, end)
                self.slots.append(slot)
                slot_id += 1
    
    def get_faculty_by_id(self, faculty_id):
        """Get faculty object by ID."""
        return self.faculty.get(faculty_id)