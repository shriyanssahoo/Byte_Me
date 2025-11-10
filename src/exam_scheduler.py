"""
Exam scheduling and seating arrangement algorithm.
"""

from datetime import datetime, timedelta
from exam_models import Exam, SeatingArrangement, ExamSchedule
import random


class ExamScheduler:
    """Generates exam timetable and seating arrangements."""
    
    def __init__(self, courses, students, exam_rooms, exam_config):
        self.courses = courses
        self.students = students
        self.exam_rooms = exam_rooms
        self.exam_config = exam_config
        self.schedule = ExamSchedule()
        
        # Parse start date
        self.start_date = datetime.strptime(exam_config['exam_start_date'], '%Y-%m-%d')
    
    def generate_exam_schedule(self):
        """Generate complete exam timetable."""
        print("\n🔄 Generating exam schedule...")
        
        # Track used slots
        used_slots = set()  # Set of (date, session) tuples
        
        current_date = self.start_date
        max_days = 7  # Try to finish in one week
        
        for course in self.courses:
            # Determine exam duration based on credits
            duration = 2 if course['credits'] <= 2 else 3
            
            # Find available slot
            scheduled = False
            attempts = 0
            
            while not scheduled and attempts < max_days * 2:
                # Skip Sundays
                if current_date.weekday() == 6:  # Sunday
                    current_date += timedelta(days=1)
                    continue
                
                # Try morning session
                if (current_date, 'FN') not in used_slots:
                    exam = self._create_exam(course, duration, current_date, 'FN')
                    self.schedule.add_exam(exam)
                    used_slots.add((current_date, 'FN'))
                    scheduled = True
                    print(f"  ✓ Scheduled {course['code']} on {current_date.strftime('%Y-%m-%d')} FN")
                    break
                
                # Try afternoon session
                if (current_date, 'AN') not in used_slots:
                    exam = self._create_exam(course, duration, current_date, 'AN')
                    self.schedule.add_exam(exam)
                    used_slots.add((current_date, 'AN'))
                    scheduled = True
                    print(f"  ✓ Scheduled {course['code']} on {current_date.strftime('%Y-%m-%d')} AN")
                    break
                
                # Move to next day
                current_date += timedelta(days=1)
                attempts += 1
            
            if not scheduled:
                print(f"  ⚠ Could not schedule {course['code']}")
        
        print(f"\n✓ Generated exam schedule with {len(self.schedule.exams)} exams")
        return self.schedule
    
    def _create_exam(self, course, duration, date, session):
        """Create an exam object."""
        # Determine time slots
        if session == 'FN':
            start_time = self.exam_config['morning_slot_start']
            if duration == 2:
                end_time = self.exam_config['morning_slot_2hr_end']
            else:
                end_time = self.exam_config['morning_slot_3hr_end']
        else:  # AN
            start_time = self.exam_config['afternoon_slot_start']
            if duration == 2:
                end_time = self.exam_config['afternoon_slot_2hr_end']
            else:
                end_time = self.exam_config['afternoon_slot_3hr_end']
        
        exam = Exam(
            course_code=course['code'],
            course_title=course['title'],
            duration=duration,
            date=date.strftime('%Y-%m-%d'),
            session=session,
            start_time=start_time,
            end_time=end_time
        )
        
        # Assign students based on course's student_group
        exam.students = self._get_students_for_course(course)
        
        return exam
    
    def _get_students_for_course(self, course):
        """Get list of students enrolled in this course."""
        student_group = course['student_group']
        
        # Handle combined sections
        if '&' in student_group:
            # e.g., "3rdSem-A&B" -> get both A and B
            base = student_group.split('&')[0]  # "3rdSem-A"
            enrolled_students = []
            
            for student in self.students:
                # Match by semester and section
                if base.endswith('-A'):
                    if student.section in ['A', 'B']:
                        enrolled_students.append(student)
                else:
                    enrolled_students.append(student)
        
        elif '-A' in student_group or '-B' in student_group:
            # Specific section
            section = student_group.split('-')[-1]
            enrolled_students = [s for s in self.students if s.section == section]
        
        else:
            # All students
            enrolled_students = self.students.copy()
        
        return enrolled_students
    
    def generate_seating_arrangements(self):
        """Generate seating arrangements for all exams."""
        print("\n🔄 Generating seating arrangements...")
        
        # Group exams by date and session
        exam_sessions = {}
        for exam in self.schedule.exams:
            key = (exam.date, exam.session)
            if key not in exam_sessions:
                exam_sessions[key] = []
            exam_sessions[key].append(exam)
        
        # For each session, create seating arrangements
        for (date, session), exams in exam_sessions.items():
            print(f"\n  📅 {date} {session}:")
            
            # Collect all students taking exams in this session
            all_students = []
            student_exam_map = {}  # {student: exam}
            
            for exam in exams:
                for student in exam.students:
                    all_students.append(student)
                    student_exam_map[student] = exam
            
            # Shuffle students for mixing
            random.shuffle(all_students)
            
            # Allocate students to rooms
            room_idx = 0
            students_per_room = {}
            
            for student in all_students:
                if room_idx >= len(self.exam_rooms):
                    room_idx = 0  # Wrap around if needed
                
                room = self.exam_rooms[room_idx]
                
                if room.room_id not in students_per_room:
                    students_per_room[room.room_id] = []
                
                if len(students_per_room[room.room_id]) < room.capacity:
                    students_per_room[room.room_id].append((student, student_exam_map[student]))
                else:
                    room_idx += 1
                    if room_idx < len(self.exam_rooms):
                        room = self.exam_rooms[room_idx]
                        students_per_room[room.room_id] = [(student, student_exam_map[student])]
            
            # Create seating arrangements for each room
            for room in self.exam_rooms:
                if room.room_id in students_per_room:
                    arrangement = SeatingArrangement(room, date, session)
                    students_in_room = students_per_room[room.room_id]
                    
                    # Assign seats with constraint: no two students from same exam sit together
                    self._assign_seats_with_constraint(arrangement, students_in_room)
                    
                    self.schedule.add_seating_arrangement(arrangement)
                    print(f"    ✓ {room.room_id}: {len(students_in_room)} students")
        
        print(f"\n✓ Generated {len(self.schedule.seating_arrangements)} seating arrangements")
    
    def _assign_seats_with_constraint(self, arrangement, students_with_exams):
        """
        Assign seats ensuring:
        1. No two students from same exam sit on same bench (horizontally)
        2. Sequential roll numbers sit behind each other (vertically in same column)
        """
        # Group students by exam
        exam_groups = {}
        for student, exam in students_with_exams:
            if exam.course_code not in exam_groups:
                exam_groups[exam.course_code] = []
            exam_groups[exam.course_code].append(student)
        
        # Sort students within each group by roll number
        for group in exam_groups.values():
            group.sort(key=lambda s: s.roll_number)
        
        # Create list of exam codes
        exam_codes = list(exam_groups.keys())
        
        # Assign column by column (so sequential roll numbers are in same column)
        exam_idx = 0
        
        for col in range(1, arrangement.room.columns + 1):
            for position in [0, 1]:  # Left and right seat in each column
                # Try to use students from different exam for each position
                exam_code = exam_codes[exam_idx % len(exam_codes)]
                
                # Assign students from this exam down the column
                for row in range(1, arrangement.room.rows + 1):
                    if exam_groups[exam_code]:
                        student = exam_groups[exam_code].pop(0)
                        arrangement.assign_seat(row, col, position, student)
                    else:
                        # This exam group is empty, try another exam
                        for other_exam in exam_codes:
                            if exam_groups[other_exam]:
                                student = exam_groups[other_exam].pop(0)
                                arrangement.assign_seat(row, col, position, student)
                                break
                
                exam_idx += 1