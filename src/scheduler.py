"""
Core scheduling algorithm using a greedy approach with conflict checking.
"""

from models import Assignment, Timetable
import random


class Scheduler:
    """Generates conflict-free timetables."""
    
    def __init__(self, courses, faculty_dict, rooms, slots):
        self.courses = courses
        self.faculty_dict = faculty_dict
        self.rooms = rooms
        self.slots = slots
        self.timetable = Timetable()
        
        # Track what's already scheduled
        self.slot_usage = {}  # {slot_id: {room_id: True/False}}
        self.faculty_schedule = {}  # {faculty_id: {slot_id: True/False}}
        self.group_schedule = {}  # {student_group: {slot_id: True/False}}
        self.daily_course_count = {}  # {(student_group, course_code, day): count}
        
        # Track failed schedules
        self.failed_schedules = []
        
        self._initialize_tracking()
    
    def _initialize_tracking(self):
        """Initialize tracking dictionaries."""
        for slot in self.slots:
            self.slot_usage[slot.slot_id] = {}
            for room in self.rooms:
                self.slot_usage[slot.slot_id][room.room_id] = False
        
        for faculty_id in self.faculty_dict.keys():
            self.faculty_schedule[faculty_id] = {}
            for slot in self.slots:
                self.faculty_schedule[faculty_id][slot.slot_id] = False
        
        # Get all unique student groups and expand A&B groups
        groups = set()
        for course in self.courses:
            # Split groups like "3rdSem-A&B" into separate sections
            if '&' in course.student_group:
                base = course.student_group.split('&')[0]  # "3rdSem-A"
                groups.add(base)
                # Add section B
                if base.endswith('-A'):
                    groups.add(base[:-1] + 'B')  # "3rdSem-B"
            else:
                groups.add(course.student_group)
        
        for group in groups:
            self.group_schedule[group] = {}
            for slot in self.slots:
                self.group_schedule[group][slot.slot_id] = False
    
    def generate_timetable(self):
        """Main function to generate the timetable."""
        print("\n🔄 Starting timetable generation...")
        
        # Expand courses with A&B into separate courses
        expanded_courses = []
        for course in self.courses:
            if '&' in course.student_group:
                # Create separate course for Section A
                base = course.student_group.split('&')[0]
                expanded_courses.append((course, base))
                
                # Create separate course for Section B
                if base.endswith('-A'):
                    section_b = base[:-1] + 'B'
                    expanded_courses.append((course, section_b))
            else:
                expanded_courses.append((course, course.student_group))
        
        # Sort courses by lectures_per_week (descending) for better packing
        # Courses with more lectures are scheduled first
        expanded_courses.sort(key=lambda x: x[0].lectures_per_week, reverse=True)
        
        successful = 0
        failed = 0
        
        for course, target_group in expanded_courses:
            # Schedule each lecture for this course
            for lecture_num in range(course.lectures_per_week):
                if self._schedule_course(course, target_group, lecture_num):
                    successful += 1
                else:
                    failed += 1
                    self.failed_schedules.append({
                        'course_code': course.code,
                        'course_title': course.title,
                        'student_group': target_group,
                        'lecture_num': lecture_num + 1
                    })
                    print(f"⚠ Could not schedule {course.code} lecture {lecture_num+1} for {target_group}")
        
        print(f"\n✓ Successfully scheduled {successful} lectures")
        if failed > 0:
            print(f"✗ Failed to schedule {failed} lectures")
        
        # Print distribution statistics
        self._print_day_distribution()
        
        return self.timetable
    
    def _print_day_distribution(self):
        """Print how classes are distributed across days."""
        print("\n📊 Day-wise Distribution:")
        
        # Get all unique groups
        groups = set(assignment.student_group for assignment in self.timetable.assignments)
        
        for group in sorted(groups):
            if '&' in group:  # Skip combined groups
                continue
            
            day_count = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0, 'Friday': 0}
            for assignment in self.timetable.assignments:
                if assignment.student_group == group:
                    day_count[assignment.slot.day] += 1
            
            print(f"\n  {group}:")
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                bar = '█' * day_count[day]
                print(f"    {day:10} : {bar} ({day_count[day]} classes)")

    
    def _schedule_course(self, course, target_group, lecture_num):
        """Try to schedule one lecture of a course for a specific group."""
        faculty = self.faculty_dict.get(course.faculty_id)
        if not faculty:
            print(f"⚠ Faculty {course.faculty_id} not found for {course.code}")
            return False
        
        # Try to find a suitable slot
        available_slots = self._find_available_slots(course, target_group, faculty)
        
        if not available_slots:
            return False
        
        # Pick the first available slot
        chosen_slot = available_slots[0]
        
        # Find an available room
        available_room = self._find_available_room(chosen_slot)
        
        if not available_room:
            return False
        
        # Create and record the assignment
        assignment = Assignment(
            course=course,
            faculty=faculty,
            room=available_room,
            slot=chosen_slot,
            student_group=target_group
        )
        
        self.timetable.add_assignment(assignment)
        
        # Mark as used
        self.slot_usage[chosen_slot.slot_id][available_room.room_id] = True
        self.faculty_schedule[faculty.faculty_id][chosen_slot.slot_id] = True
        self.group_schedule[target_group][chosen_slot.slot_id] = True
        
        # Track daily course count
        key = (target_group, course.code, chosen_slot.day)
        self.daily_course_count[key] = self.daily_course_count.get(key, 0) + 1
        
        return True
    
    def _find_available_slots(self, course, target_group, faculty):
        """Find slots that are free for both faculty and student group."""
        available = []
        
        for slot in self.slots:
            # Skip lunch break (1:30 - 2:00 PM is represented by 13:30 - 14:00)
            if slot.start_time >= '13:30' and slot.end_time <= '14:00':
                continue
            
            # Check if slot is free for the student group
            if self.group_schedule.get(target_group, {}).get(slot.slot_id, False):
                continue
            
            # Check if faculty is available
            if self.faculty_schedule[faculty.faculty_id].get(slot.slot_id, False):
                continue
            
            # Check if faculty has marked this slot as unavailable
            if not faculty.is_available(slot.day, slot.slot_id):
                continue
            
            # Check if we already have this course on this day (max 1 per day)
            key = (target_group, course.code, slot.day)
            if self.daily_course_count.get(key, 0) >= 1:
                continue
            
            available.append(slot)
        
        # Sort slots to prefer less loaded days (for even distribution)
        if available:
            available = self._sort_by_day_load(available, target_group)
        
        return available
    
    def _sort_by_day_load(self, slots, target_group):
        """Sort slots by day load to prefer less busy days."""
        # Count how many classes each day already has for this group
        day_load = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0, 'Friday': 0}
        
        for assignment in self.timetable.assignments:
            if assignment.student_group == target_group:
                day_load[assignment.slot.day] += 1
        
        # Sort slots: prefer days with fewer classes
        slots_with_load = [(slot, day_load[slot.day]) for slot in slots]
        slots_with_load.sort(key=lambda x: (x[1], x[0].day, x[0].start_time))
        
        return [slot for slot, _ in slots_with_load]
    
    def _find_available_room(self, slot):
        """Find a room that's free at the given slot."""
        for room in self.rooms:
            if not self.slot_usage[slot.slot_id].get(room.room_id, False):
                return room
        return None
    
    def validate_timetable(self):
        """Check for conflicts in the generated timetable."""
        conflicts = []
        
        # Check for faculty conflicts
        faculty_slots = {}
        for assignment in self.timetable.assignments:
            key = (assignment.faculty.faculty_id, assignment.slot.slot_id)
            if key in faculty_slots:
                conflicts.append(f"Faculty conflict: {assignment.faculty.name} at {assignment.slot}")
            faculty_slots[key] = True
        
        # Check for room conflicts
        room_slots = {}
        for assignment in self.timetable.assignments:
            key = (assignment.room.room_id, assignment.slot.slot_id)
            if key in room_slots:
                conflicts.append(f"Room conflict: {assignment.room.room_id} at {assignment.slot}")
            room_slots[key] = True
        
        # Check for student group conflicts
        group_slots = {}
        for assignment in self.timetable.assignments:
            key = (assignment.student_group, assignment.slot.slot_id)
            if key in group_slots:
                conflicts.append(f"Group conflict: {assignment.student_group} at {assignment.slot}")
            group_slots[key] = True
        
        if conflicts:
            print("\n⚠ Conflicts found:")
            for conflict in conflicts:
                print(f"  - {conflict}")
        else:
            print("\n✓ No conflicts detected!")
        
        return len(conflicts) == 0
    
    def get_failed_schedules(self):
        """Return list of courses that could not be scheduled."""
        return self.failed_schedules