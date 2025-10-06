"""
Data models for the timetable scheduling system.
These classes represent the core entities in our system.
"""

class Course:
    """Represents a course that needs to be scheduled."""
    def __init__(self, code, title, ltpsc, faculty_id, student_group):
        self.code = code
        self.title = title
        self.ltpsc = ltpsc  # Format: "L-T-P-S-C" e.g., "3-0-2-0-4"
        self.faculty_id = faculty_id
        self.student_group = student_group
        
        # Parse LTPSC to get lectures per week
        self.lectures_per_week = self._parse_lectures(ltpsc)
    
    def _parse_lectures(self, ltpsc):
        """Parse L-T-P-S-C format to get total lectures per week."""
        try:
            parts = ltpsc.split('-')
            lectures = int(parts[0])  # L = Lectures
            tutorials = int(parts[1])  # T = Tutorials
            # For scheduling purposes, count both lectures and tutorials
            return lectures + tutorials
        except:
            return 3  # Default to 3 if parsing fails
    
    def __repr__(self):
        return f"Course({self.code}, {self.title})"


class Faculty:
    """Represents a faculty member who teaches courses."""
    def __init__(self, faculty_id, name, max_hours_per_day=4):
        self.faculty_id = faculty_id
        self.name = name
        self.max_hours_per_day = max_hours_per_day
        self.unavailable_slots = set()  # Set of (day, slot) tuples
    
    def add_unavailable_slot(self, day, slot):
        """Mark a time slot as unavailable for this faculty."""
        self.unavailable_slots.add((day, slot))
    
    def is_available(self, day, slot):
        """Check if faculty is available at given day and slot."""
        return (day, slot) not in self.unavailable_slots
    
    def __repr__(self):
        return f"Faculty({self.faculty_id}, {self.name})"


class Room:
    """Represents a classroom or lab."""
    def __init__(self, room_id, room_type, capacity):
        self.room_id = room_id
        self.room_type = room_type.lower()  # 'classroom' or 'lab'
        self.capacity = capacity
    
    def __repr__(self):
        return f"Room({self.room_id}, {self.room_type}, capacity={self.capacity})"


class Slot:
    """Represents a time slot in the schedule."""
    def __init__(self, slot_id, day, start_time, end_time):
        self.slot_id = slot_id
        self.day = day  # Monday, Tuesday, etc.
        self.start_time = start_time
        self.end_time = end_time
    
    def __repr__(self):
        return f"Slot({self.day} {self.start_time}-{self.end_time})"


class Assignment:
    """Represents a scheduled class - links course, faculty, room, slot, and students."""
    def __init__(self, course, faculty, room, slot, student_group):
        self.course = course
        self.faculty = faculty
        self.room = room
        self.slot = slot
        self.student_group = student_group
    
    def __repr__(self):
        return (f"Assignment({self.course.code}, {self.faculty.name}, "
                f"{self.room.room_id}, {self.slot.day} {self.slot.start_time})")


class Timetable:
    """Represents the complete timetable with all assignments."""
    def __init__(self):
        self.assignments = []
        self.conflicts = []
    
    def add_assignment(self, assignment):
        """Add a class assignment to the timetable."""
        self.assignments.append(assignment)
    
    def get_assignments_by_group(self, student_group):
        """Get all classes for a specific student group."""
        return [a for a in self.assignments if a.student_group == student_group]
    
    def get_assignments_by_faculty(self, faculty_id):
        """Get all classes for a specific faculty member."""
        return [a for a in self.assignments if a.faculty.faculty_id == faculty_id]
    
    def __repr__(self):
        return f"Timetable(assignments={len(self.assignments)})"