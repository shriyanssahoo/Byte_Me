"""
Data models for exam timetable and seating arrangement.
"""

class Student:
    """Represents a student enrolled in courses."""
    def __init__(self, roll_number, name, branch, section, semester):
        self.roll_number = roll_number
        self.name = name
        self.branch = branch
        self.section = section
        self.semester = semester
        self.courses = []  # List of course codes student is enrolled in
    
    def __repr__(self):
        return f"Student({self.roll_number}, {self.name})"


class ExamRoom:
    """Represents an exam hall with seating arrangement."""
    def __init__(self, room_id, capacity, rows, columns):
        self.room_id = room_id
        self.capacity = capacity
        self.rows = rows
        self.columns = columns
    
    def __repr__(self):
        return f"ExamRoom({self.room_id}, {self.capacity} seats)"


class Exam:
    """Represents a scheduled exam."""
    def __init__(self, course_code, course_title, duration, date, session, start_time, end_time):
        self.course_code = course_code
        self.course_title = course_title
        self.duration = duration  # in hours
        self.date = date
        self.session = session  # 'FN' or 'AN'
        self.start_time = start_time
        self.end_time = end_time
        self.students = []  # List of Student objects taking this exam
        self.room_allocations = {}  # {room_id: [list of students]}
    
    def __repr__(self):
        return f"Exam({self.course_code}, {self.date} {self.session})"


class SeatingArrangement:
    """Represents seating arrangement for one room for one exam session."""
    def __init__(self, room, date, session):
        self.room = room
        self.date = date
        self.session = session
        # seats: dict with key=(row, col, position) value=Student or None
        # position: 0=left, 1=right on bench
        self.seats = {}
        self._initialize_seats()
    
    def _initialize_seats(self):
        """Initialize all seats as empty."""
        for row in range(1, self.room.rows + 1):
            for col in range(1, self.room.columns + 1):
                self.seats[(row, col, 0)] = None  # Left seat
                self.seats[(row, col, 1)] = None  # Right seat
    
    def assign_seat(self, row, col, position, student):
        """Assign a student to a specific seat."""
        self.seats[(row, col, position)] = student
    
    def get_seat(self, row, col, position):
        """Get the student at a specific seat."""
        return self.seats.get((row, col, position))
    
    def __repr__(self):
        return f"SeatingArrangement({self.room.room_id}, {self.date} {self.session})"


class ExamSchedule:
    """Represents the complete exam schedule."""
    def __init__(self):
        self.exams = []  # List of Exam objects
        self.seating_arrangements = []  # List of SeatingArrangement objects
    
    def add_exam(self, exam):
        """Add an exam to the schedule."""
        self.exams.append(exam)
    
    def add_seating_arrangement(self, arrangement):
        """Add a seating arrangement."""
        self.seating_arrangements.append(arrangement)
    
    def get_exams_by_date(self, date):
        """Get all exams on a specific date."""
        return [e for e in self.exams if e.date == date]
    
    def get_student_exams(self, student):
        """Get all exams for a specific student."""
        student_exams = []
        for exam in self.exams:
            if student in exam.students:
                student_exams.append(exam)
        return student_exams
    
    def __repr__(self):
        return f"ExamSchedule({len(self.exams)} exams)"