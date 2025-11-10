"""
Data loader for exam scheduling.
"""

import pandas as pd
from datetime import datetime
from exam_models import Student, ExamRoom


class ExamDataLoader:
    """Loads all input data for exam scheduling."""
    
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.students = []
        self.exam_rooms = []
        self.courses = []
        self.exam_config = {}
    
    def load_all_data(self):
        """Load all data from CSV files."""
        self.load_students()
        self.load_exam_rooms()
        self.load_exam_config()
        self.load_courses_for_exam()
        print(f"✓ Loaded {len(self.students)} students")
        print(f"✓ Loaded {len(self.exam_rooms)} exam rooms")
        print(f"✓ Loaded {len(self.courses)} courses for exams")
    
    def load_students(self):
        """Load students from students.csv"""
        try:
            df = pd.read_csv(f'{self.data_dir}/students.csv')
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                student = Student(
                    roll_number=str(row['roll_number']).strip(),
                    name=str(row['name']).strip(),
                    branch=str(row['branch']).strip(),
                    section=str(row['section']).strip(),
                    semester=int(row['semester'])
                )
                self.students.append(student)
                
        except FileNotFoundError:
            print(f"⚠ Warning: students.csv not found in {self.data_dir}")
        except Exception as e:
            print(f"⚠ Error loading students: {e}")
    
    def load_exam_rooms(self):
        """Load exam rooms from exam_rooms.csv"""
        try:
            df = pd.read_csv(f'{self.data_dir}/exam_rooms.csv')
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                room = ExamRoom(
                    room_id=str(row['room_id']).strip(),
                    capacity=int(row['capacity']),
                    rows=int(row['rows']),
                    columns=int(row['columns'])
                )
                self.exam_rooms.append(room)
                
        except FileNotFoundError:
            print(f"⚠ Warning: exam_rooms.csv not found in {self.data_dir}")
        except Exception as e:
            print(f"⚠ Error loading exam rooms: {e}")
    
    def load_exam_config(self):
        """Load exam configuration from exam_config.csv"""
        try:
            df = pd.read_csv(f'{self.data_dir}/exam_config.csv')
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                param = str(row['parameter']).strip()
                value = str(row['value']).strip()
                self.exam_config[param] = value
                
        except FileNotFoundError:
            print(f"⚠ Warning: exam_config.csv not found in {self.data_dir}")
            # Set defaults
            self.exam_config = {
                'exam_start_date': '2025-12-01',
                'morning_slot_start': '10:00',
                'morning_slot_2hr_end': '12:00',
                'morning_slot_3hr_end': '13:00',
                'afternoon_slot_start': '14:00',
                'afternoon_slot_2hr_end': '16:00',
                'afternoon_slot_3hr_end': '17:00'
            }
        except Exception as e:
            print(f"⚠ Error loading exam config: {e}")
    
    def load_courses_for_exam(self):
        """Load courses from courses.csv for exam scheduling"""
        try:
            df = pd.read_csv(f'{self.data_dir}/courses.csv')
            df.columns = df.columns.str.strip()
            
            # Find the lectures column
            lectures_col = None
            for col_name in ['lectures_p', 'lectures_per_week', 'lectures', 'ltpsc']:
                if col_name in df.columns:
                    lectures_col = col_name
                    break
            
            if not lectures_col:
                print(f"⚠ Could not find lectures column")
                return
            
            for _, row in df.iterrows():
                ltpsc = str(row[lectures_col]).strip()
                
                # Parse credits from L-T-P-S-C format
                try:
                    parts = ltpsc.split('-')
                    credits = int(parts[4]) if len(parts) >= 5 else 3
                except:
                    credits = 3
                
                course = {
                    'code': str(row['code']).strip(),
                    'title': str(row['title']).strip(),
                    'credits': credits,
                    'student_group': str(row['student_group']).strip()
                }
                self.courses.append(course)
                
        except FileNotFoundError:
            print(f"⚠ Warning: courses.csv not found in {self.data_dir}")
        except Exception as e:
            print(f"⚠ Error loading courses: {e}")
    
    def get_students_by_section(self, section):
        """Get all students in a specific section."""
        return [s for s in self.students if s.section == section]
    
    def get_students_by_branch(self, branch):
        """Get all students in a specific branch."""
        return [s for s in self.students if s.branch == branch]