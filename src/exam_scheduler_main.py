"""
Exam Timetable and Seating Arrangement Generator
-------------------------------------------------
This single, consolidated file contains the complete logic for:
1.  Loading all data (config, rooms, students, and courses)
2.  Auto-registering students for exams based on rules
3.  Validating data for scheduling feasibility
4.  Scheduling exams into conflict-free time slots
5.  Generating physical seating arrangements with checkerboard logic
6.  Exporting all results to user-friendly Excel files.

This file REPLACES all separate exam module files.
"""

import pandas as pd
import openpyxl
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter  # FIX: Added missing import
from datetime import datetime, timedelta
import os
import sys
import random
import re  # FIX: Added missing import
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field

# --- 1. DATA MODELS ---

@dataclass
class Student:
    """Represents a single student and their exam list."""
    roll_number: str
    name: str
    branch: str
    section: str
    semester: int
    courses: Set[str] = field(default_factory=set) # Set of course_codes

    def __repr__(self):
        return f"Student({self.roll_number}, {self.name})"
        
    def __hash__(self):
        return hash(self.roll_number)
    def __eq__(self, other):
        return isinstance(other, Student) and self.roll_number == other.roll_number

@dataclass
class ExamRoom:
    """Represents an exam hall with seating dimensions."""
    room_id: str
    capacity: int
    rows: int
    columns: int # This is columns of benches

    def __repr__(self):
        return f"ExamRoom({self.room_id}, {self.capacity} seats)"

@dataclass
class Exam:
    """Represents a single exam to be scheduled."""
    course_code: str
    course_title: str
    duration: int # 2 or 3 hours
    students: List[Student] = field(default_factory=list)
    
    date: Optional[str] = None
    session: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    def __repr__(self):
        return f"Exam({self.course_code}, {len(self.students)} students)"
        
    def get_student_conflict_set(self) -> Set[Student]:
        """Returns a set of students for fast conflict checking."""
        return set(self.students)

@dataclass
class SeatingArrangement:
    """Represents the seating plan for one room in one session."""
    room: ExamRoom
    date: str
    session: str
    # seats: dict with key=(row, col, position) value=(Student, Exam)
    # position: 0=left, 1=right on bench
    seats: Dict[Tuple[int, int, int], Optional[Tuple[Student, Exam]]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize all seats as empty."""
        for row in range(1, self.room.rows + 1):
            for col in range(1, self.room.columns + 1):
                self.seats[(row, col, 0)] = None # Left seat
                self.seats[(row, col, 1)] = None # Right seat
    
    def assign_seat(self, row: int, col: int, position: int, student: Student, exam: Exam):
        self.seats[(row, col, position)] = (student, exam)
    
    def get_seat_data(self, row: int, col: int, position: int) -> Optional[Tuple[Student, Exam]]:
        return self.seats.get((row, col, position))

@dataclass
class ExamSchedule:
    """Holds the final generated schedule and seating plan."""
    exams: List[Exam] = field(default_factory=list)
    seating_arrangements: List[SeatingArrangement] = field(default_factory=list)
    
    # FIX: student_schedules now lives inside the schedule object
    student_schedules: Dict[Student, Set[Tuple[str, str]]] = field(default_factory=dict)
    
    def get_student_exams(self, student: Student) -> List[Exam]:
        """Get all exams for a specific student."""
        return [exam for exam in self.exams if student in exam.students]

# --- 2. DATA LOADER ---

class DataLoader:
    """Loads all 4 required CSV files from the data directory."""
    
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.exam_config: Dict[str, str] = {}
        self.exam_rooms: List[ExamRoom] = []
        self.students: Dict[str, Student] = {} # roll_number -> Student
        self.exams: Dict[str, Exam] = {} # course_code -> Exam

    def load_all_data(self):
        """Loads and processes all required data."""
        self.load_exam_config()
        self.load_exam_rooms()
        self.load_students()
        self.load_exam_courses()
        self.load_registrations()
        
        print(f"✓ Loaded {len(self.students)} students (Sem 3 only)")
        print(f"✓ Loaded {len(self.exam_rooms)} exam rooms")
        print(f"✓ Loaded {len(self.exams)} exams to be scheduled")
        print(f"✓ Loaded config (Start Date: {self.exam_config.get('exam_start_date')})")

    def load_exam_config(self):
        try:
            df = pd.read_csv(f'{self.data_dir}/exam_config.csv')
            df.columns = df.columns.str.strip()
            for _, row in df.iterrows():
                self.exam_config[str(row['parameter']).strip()] = str(row['value']).strip()
        except FileNotFoundError:
            print("FATAL ERROR: exam_config.csv not found.")
            sys.exit(1)

    def load_exam_rooms(self):
        try:
            df = pd.read_csv(f'{self.data_dir}/exam_rooms.csv')
            df.columns = df.columns.str.strip()
            for _, row in df.iterrows():
                self.exam_rooms.append(ExamRoom(
                    room_id=str(row['room_id']).strip(),
                    capacity=int(row['capacity']),
                    rows=int(row['rows']),
                    columns=int(row['columns'])
                ))
            self.exam_rooms.sort(key=lambda r: r.capacity, reverse=True)
        except FileNotFoundError:
            print("FATAL ERROR: exam_rooms.csv not found.")
            sys.exit(1)

    def load_students(self):
        try:
            df = pd.read_csv(f'{self.data_dir}/students.csv')
            df.columns = df.columns.str.strip()
            df = df[df['semester'] == 3] 
            for _, row in df.iterrows():
                student = Student(
                    roll_number=str(row['roll_number']).strip(),
                    name=str(row['name']).strip(),
                    branch=str(row['branch']).strip().upper(),
                    section=str(row['section']).strip(),
                    semester=int(row['semester'])
                )
                self.students[student.roll_number] = student
        except FileNotFoundError:
            print("FATAL ERROR: students.csv not found.")
            sys.exit(1)

    def load_exam_courses(self):
        """
        Loads Sem 3 courses from the *main* courses.csv.
        """
        try:
            df = pd.read_csv(f'{self.data_dir}/courses.csv')
            df.columns = [col.strip() for col in df.columns]
            
            df = df[df['Semester'] == 3] 
            
            for _, row in df.iterrows():
                code = str(row['Course Code']).strip().upper()
                if not code:
                    continue
                
                exam = Exam(
                    course_code=code,
                    course_title=str(row['Course Name']).strip(),
                    duration=2  # Hard-coded 2 hours
                )
                if code not in self.exams:
                    self.exams[exam.course_code] = exam
                
        except FileNotFoundError:
            print("FATAL ERROR: courses.csv not found.")
            sys.exit(1)
        except KeyError as e:
            print(f"FATAL ERROR: courses.csv is missing a required column: {e}")
            sys.exit(1)

    def load_registrations(self):
        """
        Auto-registers students based on the "all core courses" rule.
        """
        core_courses_by_branch: Dict[str, Set[str]] = {}
        try:
            df = pd.read_csv(f'{self.data_dir}/courses.csv')
            df.columns = [col.strip() for col in df.columns]
            df = df[df['Semester'] == 3]

            for _, row in df.iterrows():
                pref = str(row.get('Pre /Post', '')).strip().lower()
                if pref not in ['elective', 'basket']:
                    code = str(row['Course Code']).strip().upper()
                    branch = str(row['Department']).strip().upper()
                    
                    core_courses_by_branch.setdefault(branch, set()).add(code)
                    
        except FileNotFoundError:
            print("FATAL ERROR: courses.csv not found.")
            sys.exit(1)
        except KeyError as e:
            print(f"FATAL ERROR: courses.csv is missing a required column: {e}")
            sys.exit(1)

        for student in self.students.values():
            if student.branch in core_courses_by_branch:
                courses_to_add = core_courses_by_branch[student.branch]
                for code in courses_to_add:
                    if code in self.exams:
                        student.courses.add(code)
                        self.exams[code].students.append(student)
        
        empty_exams = [code for code, exam in self.exams.items() if not exam.students]
        for code in empty_exams:
            del self.exams[code]
            
        print(f"✓ Auto-registered students for {len(self.exams)} core exams.")


# --- 3. DATA VALIDATOR ---

class Validator:
    """Performs pre-run checks on the loaded data."""
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self.issues: List[str] = []

    def validate_all(self) -> bool:
        print("\n" + "="*90)
        print("VALIDATING EXAM DATA".center(90))
        print("="*90)
        
        self._check_capacity()
        self._check_student_enrollment()
        
        if self.issues:
            print("\n❌ VALIDATION FAILED:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
            return False
        
        print("\n✓ VALIDATION PASSED. Data is ready for scheduling.")
        return True

    def _check_capacity(self):
        total_capacity = sum(room.capacity for room in self.loader.exam_rooms)
        
        if not self.loader.exams:
            self.issues.append("No exams loaded to check capacity against.")
            return

        largest_exam_size = 0
        largest_exam_code = "N/A"
        if self.loader.exams:
            largest_exam = max(self.loader.exams.values(), key=lambda e: len(e.students))
            largest_exam_size = len(largest_exam.students)
            largest_exam_code = largest_exam.course_code
        
        print(f"  Total room capacity: {total_capacity} seats")
        print(f"  Largest exam: {largest_exam_code} ({largest_exam_size} students)")

        if total_capacity < largest_exam_size:
            self.issues.append(
                f"Insufficient room capacity! Largest exam needs {largest_exam_size} seats, "
                f"but only {total_capacity} are available."
            )
        else:
            print("  ✓ Room capacity is sufficient for the largest exam.")

    def _check_student_enrollment(self):
        unregistered_students = [s.roll_number for s in self.loader.students.values() if not s.courses]
        if unregistered_students:
            print(f"  Warning: {len(unregistered_students)} students are not registered for any exams.")
        else:
            print("  ✓ All students are registered for at least one exam.")

# --- 4. EXAM SCHEDULER ---

class ExamScheduler:
    """Schedules exams into slots and then arranges seating."""
    
    def __init__(self, exams: List[Exam], students: List[Student], 
                 exam_rooms: List[ExamRoom], exam_config: Dict[str, str]):
        
        self.all_exams = sorted(exams, key=lambda e: len(e.students), reverse=True)
        self.students = students
        self.exam_rooms = exam_rooms
        self.exam_config = exam_config
        self.start_date = datetime.strptime(exam_config['exam_start_date'], '%Y-%m-%d')
        
        self.final_schedule = ExamSchedule()
        # FIX: Assign student_schedules to the correct object
        self.final_schedule.student_schedules = {s: set() for s in students}

    def _get_exam_times(self, duration: int, session: str) -> Tuple[str, str]:
        # FIX: Provide defaults to .get() to satisfy linter
        if session == 'FN':
            start = self.exam_config.get('morning_slot_start', '10:00')
            end = self.exam_config.get('morning_slot_2hr_end', '12:00')
        else: # AN
            start = self.exam_config.get('afternoon_slot_start', '14:00')
            end = self.exam_config.get('afternoon_slot_2hr_end', '16:00')
        return start, end

    def _find_next_slot(self, current_date: datetime, current_session: str) -> Tuple[datetime, str]:
        if current_session == 'FN':
            return current_date, 'AN'
        else:
            new_date = current_date + timedelta(days=1)
            if new_date.weekday() == 6:
                new_date += timedelta(days=1)
            return new_date, 'FN'

    def generate_exam_schedule(self) -> ExamSchedule:
        print("\n" + "="*90)
        print("SCHEDULING EXAMS".center(90))
        print("="*90)
        
        current_date = self.start_date
        current_session = 'FN'
        
        if current_date.weekday() == 6:
            current_date += timedelta(days=1)
            
        unscheduled_exams = list(self.all_exams)
        
        slot_count = 0
        while unscheduled_exams and slot_count < 30:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"  Trying slot: {date_str} {current_session}...")
            
            students_busy_in_slot: Set[Student] = set()
            exams_in_slot: List[Exam] = []
            
            exam_fit_found = True
            while exam_fit_found:
                exam_fit_found = False
                
                exam_to_schedule = None
                for exam in unscheduled_exams:
                    exam_students = exam.get_student_conflict_set()
                    if not exam_students.intersection(students_busy_in_slot):
                        exam_to_schedule = exam
                        exam_fit_found = True
                        break
                
                if exam_to_schedule:
                    unscheduled_exams.remove(exam_to_schedule)
                    start, end = self._get_exam_times(2, current_session)
                    
                    exam_to_schedule.date = date_str
                    exam_to_schedule.session = current_session
                    exam_to_schedule.start_time = start
                    exam_to_schedule.end_time = end
                    
                    self.final_schedule.exams.append(exam_to_schedule)
                    exams_in_slot.append(exam_to_schedule)
                    
                    students_busy_in_slot.update(exam_to_schedule.get_student_conflict_set())

            # FIX: Use the student_schedules from the schedule object
            for student in students_busy_in_slot:
                self.final_schedule.student_schedules[student].add((date_str, current_session))
                
            if exams_in_slot:
                codes = [e.course_code for e in exams_in_slot]
                print(f"    ✓ Scheduled {len(exams_in_slot)} exams: {', '.join(codes)}")
            else:
                print(f"    - Slot skipped (no exams fit).")

            current_date, current_session = self._find_next_slot(current_date, current_session)
            slot_count += 1
        
        if unscheduled_exams:
            print(f"  FATAL: Could not schedule {len(unscheduled_exams)} exams. Ran out of slots.")
        
        print(f"\n✓ Exam scheduling complete. {len(self.final_schedule.exams)} exams scheduled.")
        return self.final_schedule

    def generate_seating_arrangements(self):
        print("\n" + "="*90)
        print("GENERATING SEATING ARRANGEMENTS".center(90))
        print("="*90)
        
        exams_by_slot: Dict[Tuple[str, str], List[Exam]] = {}
        for exam in self.final_schedule.exams:
            if not exam.date or not exam.session:
                continue
            key = (exam.date, exam.session)
            
            # FIX: Explicitly check and add to list
            if key not in exams_by_slot:
                exams_by_slot[key] = []
            exams_by_slot[key].append(exam)
            
        for (date, session), exams_in_slot in exams_by_slot.items():
            print(f"  Arranging seats for {date} {session}...")
            
            all_students_in_slot: List[Tuple[Student, Exam]] = []
            for exam in exams_in_slot:
                sorted_students = sorted(exam.students, key=lambda s: s.roll_number)
                for student in sorted_students:
                    all_students_in_slot.append((student, exam))
            
            room_iter = iter(self.exam_rooms)
            current_room = next(room_iter, None)
            if not current_room: 
                print(f"  FATAL: No rooms available for {date} {session}.")
                continue
                
            arrangement = SeatingArrangement(current_room, date, session)
            self.final_schedule.seating_arrangements.append(arrangement)
            
            seat_count = 0
            
            students_by_exam: Dict[str, List[Tuple[Student, Exam]]] = {}
            for student, exam in all_students_in_slot:
                # FIX: Explicitly check and add to list
                if exam.course_code not in students_by_exam:
                    students_by_exam[exam.course_code] = []
                students_by_exam[exam.course_code].append((student, exam))

            exam_codes = list(students_by_exam.keys())
            if not exam_codes: continue
            
            exam_code_count = len(exam_codes)
            exam_idx = 0
            
            student_iterators = {code: iter(students) for code, students in students_by_exam.items()}

            for col in range(1, current_room.columns + 1):
                for pos in [0, 1]: # Left, Right
                    
                    current_exam_code = exam_codes[exam_idx % exam_code_count]
                    exam_idx += 1
                    
                    for row in range(1, current_room.rows + 1):
                        
                        student_data_tuple = next(student_iterators[current_exam_code], None)
                        
                        if not student_data_tuple:
                            found_student = False
                            for _ in range(exam_code_count):
                                current_exam_code = exam_codes[exam_idx % exam_code_count]
                                exam_idx += 1
                                student_data_tuple = next(student_iterators[current_exam_code], None)
                                if student_data_tuple:
                                    found_student = True
                                    break
                            if not found_student:
                                break
                        
                        if student_data_tuple:
                            student_to_seat, exam_to_seat = student_data_tuple
                            
                            # --- Constraint Check ---
                            if pos == 1: # Right seat, check left
                                left_data = arrangement.get_seat_data(row, col, 0)
                                if left_data:
                                    left_student, left_exam = left_data # Unpack
                                    if left_exam == exam_to_seat:
                                        # CONFLICT! Put student *tuple* back
                                        students_by_exam[current_exam_code].append(student_data_tuple)
                                        student_iterators[current_exam_code] = iter(students_by_exam[current_exam_code])
                                        continue
                            
                            arrangement.assign_seat(row, col, pos, student_to_seat, exam_to_seat)
                            seat_count += 1
                        
                        if seat_count >= current_room.capacity:
                            current_room = next(room_iter, None)
                            if not current_room:
                                break
                            arrangement = SeatingArrangement(current_room, date, session)
                            self.final_schedule.seating_arrangements.append(arrangement)
                            seat_count = 0
                            
                    if not current_room: break
                if not current_room: break
            
            remaining_students = 0
            for code, iterator in student_iterators.items():
                remaining = len(list(iterator))
                if remaining > 0:
                    print(f"    WARNING: {remaining} students for {code} could not be seated.")
                    remaining_students += remaining
            
            if remaining_students > 0:
                 print(f"  FATAL: Ran out of rooms for {date} {session}. "
                       f"{remaining_students} students unscheduled.")
                
        print("\n✓ Seating arrangement complete.")

# --- 5. EXCEL EXPORTER ---

class ExamExporter:
    """Exports exam schedule and seating arrangements to Excel."""
    
    def __init__(self, schedule: ExamSchedule):
        self.schedule = schedule
    
    def export_all(self, output_dir='output/exams'):
        os.makedirs(output_dir, exist_ok=True)
        
        arrangements_by_date: Dict[str, List[SeatingArrangement]] = {}
        for arr in self.schedule.seating_arrangements:
            arrangements_by_date.setdefault(arr.date, []).append(arr)
        
        for date, arrangements in arrangements_by_date.items():
            arrangements.sort(key=lambda a: (a.session, a.room.room_id))
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            filename = f"{output_dir}/Exam_Seating_{date_obj.strftime('%d_%m_%Y')}.xlsx"
            self._export_date_seating(date, arrangements, filename)
            print(f"  ✓ Exported: {filename}")
        
        self._export_student_schedules(output_dir)
    
    def _export_date_seating(self, date: str, arrangements: List[SeatingArrangement], filename: str):
        """Export seating arrangement for one date."""
        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            default_sheet = wb["Sheet"]
            if default_sheet: # FIX: Safety check
                wb.remove(default_sheet)
        
        sessions: Dict[str, List[SeatingArrangement]] = {}
        for arr in arrangements:
            sessions.setdefault(arr.session, []).append(arr)
        
        for session in ['FN', 'AN']:
            if session not in sessions:
                continue
            
            for arrangement in sessions[session]:
                sheet_name = f"{arrangement.room.room_id}_{session}"
                ws = wb.create_sheet(title=sheet_name)
                self._format_room_seating(ws, arrangement)
        
        try:
            wb.save(filename)
        except PermissionError:
            print(f"  FATAL ERROR: Could not save {filename}. Is it open in Excel?")

    
    def _format_room_seating(self, ws: Worksheet, arrangement: SeatingArrangement):
        """Format one room's seating arrangement."""
        room = arrangement.room
        date_obj = datetime.strptime(arrangement.date, '%Y-%m-%d')
        
        ws.merge_cells('A1:F1')
        cell = ws['A1']
        cell.value = f"Date {date_obj.strftime('%d/%m/%Y')}"
        cell.font = Font(size=12, bold=True)
        cell.alignment = Alignment(horizontal='left')
        
        ws.merge_cells('A2:F2')
        cell = ws['A2']
        cell.value = f"Room {room.room_id} | Session {arrangement.session}"
        cell.font = Font(size=12, bold=True)
        cell.alignment = Alignment(horizontal='left')
        
        current_row = 4
        
        ws.merge_cells(f'A{current_row}:F{current_row}')
        cell = ws.cell(current_row, 1)
        cell.value = "WINDOW / BOARD" # type: ignore
        cell.font = Font(size=11, bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        current_row += 1
        
        for i, col_label in enumerate(["COL 1", "COL 2", "COL 3"]):
            col_idx = (i * 2) + 1
            ws.merge_cells(start_row=current_row, start_column=col_idx, end_row=current_row, end_column=col_idx + 1)
            cell = ws.cell(current_row, col_idx)
            cell.value = col_label # type: ignore
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        current_row += 1
        
        for row in range(1, room.rows + 1):
            for col in range(1, room.columns + 1):
                left_data = arrangement.get_seat_data(row, col, 0)
                right_data = arrangement.get_seat_data(row, col, 1)
                
                left_roll = left_data[0].roll_number if left_data else ""
                right_roll = right_data[0].roll_number if right_data else ""
                
                ws.cell(current_row, (col*2 - 1), left_roll)
                ws.cell(current_row, (col*2), right_roll)
            
            current_row += 1
        
        ws.merge_cells(f'A{current_row}:F{current_row}')
        cell = ws.cell(current_row, 1)
        cell.value = "DOOR" # type: ignore
        cell.font = Font(size=11, bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        
        for r in range(current_row):
            ws.row_dimensions[r+1].height = 25
            for c in range(6):
                cell = ws.cell(r+1, c+1)
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = Border(
                    left=Side(style='thin'), right=Side(style='thin'),
                    top=Side(style='thin'), bottom=Side(style='thin')
                )
                ws.column_dimensions[get_column_letter(c+1)].width = 15

    
    def _export_student_schedules(self, output_dir: str):
        """Export student-wise exam schedules."""
        students_by_section: Dict[str, List[Student]] = {}
        
        # FIX: Use the student_schedules dict from the schedule object
        for student in self.schedule.student_schedules.keys():
            section_key = f"{student.branch}-{student.section}"
            
            # FIX: Explicitly check and add to list
            if section_key not in students_by_section:
                students_by_section[section_key] = []
            students_by_section[section_key].append(student)
            
        for section_key, students in students_by_section.items():
            filename = f"{output_dir}/Student_Exam_Schedule_{section_key}.xlsx"
            self._export_section_schedule(section_key, list(students), filename)
            print(f"  ✓ Exported: {filename}")
    
    def _export_section_schedule(self, section_key: str, students: List[Student], filename: str):
        """Export exam schedule for one section."""
        wb = openpyxl.Workbook()
        ws = wb.active
        if not ws:
            ws = wb.create_sheet(title=section_key)
        else:
            ws.title = section_key
        
        headers = ['Roll Number', 'Student Name', 'Course Code', 'Course Name', 'Date', 'Session', 'Time', 'Room', 'Seat']
        ws.append(headers) # type: ignore
        
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

        students.sort(key=lambda s: s.roll_number)
        
        for student in students:
            student_exams = self.schedule.get_student_exams(student)
            if not student_exams:
                ws.append([student.roll_number, student.name, "No exams scheduled"]) # type: ignore
                continue
                
            for exam in sorted(student_exams, key=lambda e: (e.date or "", e.session or "")):
                room, seat = self._find_student_seat(student, exam)
                ws.append([ # type: ignore
                    student.roll_number,
                    student.name,
                    exam.course_code,
                    exam.course_title,
                    exam.date or "TBA",
                    exam.session or "TBA",
                    f"{exam.start_time or 'TBA'}-{exam.end_time or 'TBA'}",
                    room,
                    seat
                ])
                
        # FIX: Use enumerate and get_column_letter
        for col_idx, col in enumerate(ws.columns, 1):
            max_length = 0
            column_letter = get_column_letter(col_idx)
            for cell in col:
                try:
                    val_str = str(cell.value)
                    if len(val_str) > max_length:
                        max_length = len(val_str)
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = adjusted_width

        try:
            wb.save(filename)
        except PermissionError:
            print(f"  FATAL ERROR: Could not save {filename}. Is it open in Excel?")

        
    def _find_student_seat(self, student: Student, exam: Exam) -> Tuple[str, str]:
        """Find a student's assigned seat for a specific exam."""
        for arr in self.schedule.seating_arrangements:
            if arr.date == exam.date and arr.session == exam.session:
                for (row, col, pos), seat_data in arr.seats.items():
                    if seat_data and seat_data[0] == student:
                        position = "Left" if pos == 0 else "Right"
                        return arr.room.room_id, f"R{row}C{col}-{position[0]}"
        return "TBA", "TBA"

# --- 6. MAIN EXECUTION ---

def main():
    """Main function to run the validator, scheduler, and exporter."""
    print("=" * 90)
    print("EXAM TIMETABLE & SEATING ARRANGEMENT GENERATOR".center(90))
    print("=" * 90)
    
    # 1. Load Data
    print("\n📂 Loading data...")
    loader = DataLoader(data_dir='data')
    try:
        loader.load_all_data()
    except Exception as e:
        print(f"\n❌ FATAL ERROR during data loading: {e}")
        print("Please ensure all required CSV files exist in the 'data' directory.")
        return 1
        
    # 2. Validate Data
    validator = Validator(loader)
    if not validator.validate_all():
        print("\n❌ CANNOT PROCEED. Please fix critical issues in your data files.")
        return 1
        
    # 3. Generate Exam Schedule
    scheduler = ExamScheduler(
        list(loader.exams.values()),
        list(loader.students.values()),
        loader.exam_rooms,
        loader.exam_config
    )
    schedule = scheduler.generate_exam_schedule()
    
    # 4. Generate Seating
    scheduler.generate_seating_arrangements()
    
    # 5. Export
    print("\n📊 Exporting to Excel...")
    exporter = ExamExporter(schedule)
    exporter.export_all()
    
    print("\n" + "=" * 90)
    print("✓ EXAM TIMETABLE GENERATION COMPLETE!".center(90))
    print("=" * 90)

if __name__ == "__main__":
    sys.exit(main())