# Automated Timetable Scheduler for IIIT Dharwad

**Team: Byte Me**

A robust, intelligent scheduling system designed to automate the creation and management of academic timetables for the Indian Institute of Information Technology Dharwad.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Format](#data-format)
- [Scheduling Algorithm](#scheduling-algorithm)
- [Output](#output)
- [Testing](#testing)
- [Team Members](#team-members)
- [License](#license)

---

## Problem Statement

Manual timetable creation in educational institutions is time-consuming, error-prone, and leads to:

- Scheduling conflicts (faculty, classrooms, students)
- Overbooked classrooms and uneven faculty workloads
- Difficulty in managing multiple sections and course combinations
- Poor distribution of classes across the week
- Complex cross-referencing between slot codes and course lists

This project provides a fully automated solution that generates optimized, conflict-free timetables while respecting all institutional constraints.

---

## Features

### Core Functionality

- **Automatic Conflict-Free Scheduling**: Generates timetables with zero clashes for faculty, rooms, and student groups
- **Smart Day Distribution**: Evenly distributes classes across Monday-Friday to avoid overloaded days
- **Section Management**: Handles combined sections (A&B) by creating separate schedules for each
- **Constraint Handling**:
  - Respects faculty availability and maximum hours per day
  - Enforces lunch break (1:30 PM - 2:00 PM)
  - Schedules within regular hours (9:00 AM - 6:00 PM)
  - Maximum one lecture per course per day per section
  - Proper room allocation based on type and capacity

### Output & Visualization

- **Color-Coded Excel Export**: Each course gets a unique color for easy identification
- **Multiple Views**: Separate timetables for each section and faculty member
- **Failed Schedule Report**: Lists courses that couldn't be scheduled with reasons
- **Distribution Statistics**: Visual representation of class distribution across days
- **Console Display**: Formatted text output with clear lunch break indicators

### Data Management

- **CSV-Based Input**: Easy-to-edit data files for courses, faculty, and rooms
- **Flexible Course Format**: Supports L-T-P-S-C (Lecture-Tutorial-Practical-Self Study-Credits) format
- **Dynamic Adaptation**: Works with any number of courses, faculty, rooms, and sections

---

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────┐
│                  User Interface                  │
│         (Console / Web Application)              │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────┐
│              Main Controller                     │
│              (main.py)                           │
└──────┬──────────────────────────┬────────────────┘
       │                          │
┌──────┴──────┐          ┌────────┴─────────┐
│ Data Loader │          │    Scheduler     │
│             │          │   (Algorithm)    │
└──────┬──────┘          └────────┬─────────┘
       │                          │
┌──────┴──────────────────────────┴─────────┐
│          Data Models & Structures          │
│  (Course, Faculty, Room, Slot, Timetable)  │
└────────────────────────────────────────────┘
```

### Module Breakdown

1. **models.py**: Core data structures (Course, Faculty, Room, Slot, Assignment, Timetable)
2. **data_loader.py**: CSV parsing and data validation
3. **scheduler.py**: Scheduling algorithm and conflict resolution
4. **main.py**: Main entry point, output generation, and Excel export
5. **web_app.py**: Optional Flask-based web interface

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.8+ |
| Data Handling | Pandas |
| Excel Export | OpenPyXL |
| Testing | pytest |
| Web Interface | Flask (optional) |
| Version Control | Git & GitHub |

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/shriyanssahoo/Byte_Me.git
   cd Byte_Me
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**
   ```bash
   python src/main.py
   ```

---

## Usage

### Console Application

Run the main scheduler:

```bash
python src/main.py
```

### Web Application (Optional)

Start the web server:

```bash
python src/web_app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

### Customizing Input Data

Edit the CSV files in the `data/` folder:

- `courses.csv`: Course details
- `faculty.csv`: Faculty information
- `rooms.csv`: Classroom and lab details

---

## Project Structure

```
Byte_Me/
│
├── data/                      # Input data files
│   ├── courses.csv           # Course information
│   ├── faculty.csv           # Faculty details
│   └── rooms.csv             # Room/lab information
│
├── src/                       # Source code
│   ├── __init__.py           # Package initializer
│   ├── models.py             # Data models
│   ├── data_loader.py        # CSV data loader
│   ├── scheduler.py          # Scheduling algorithm
│   ├── main.py               # Console application
│   └── web_app.py            # Web interface
│
├── output/                    # Generated timetables
│   └── timetable.xlsx        # Excel output
│
├── tests/                     # Unit tests
│   └── test_basic.py         # Basic functionality tests
│
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── ByteMe_Detailed_Project_Report.pdf  # Full documentation
```

---

## Data Format

### courses.csv

| Column | Description | Example |
|--------|-------------|---------|
| code | Course code | CS263 |
| title | Course name | Design Analysis |
| lectures_p | L-T-P-S-C format | 3-0-2-0-4 |
| faculty_id | Faculty identifier | F002 |
| student_group | Target section | 3rdSem-A&B |

**Example:**
```csv
code,title,lectures_p,faculty_id,student_group
CS263,Design Analysis,3-0-2-0-4,F002,3rdSem-A&B
MA261,Differential Equation,2-1-0-0-2,F001,3rdSem
```

### faculty.csv

| Column | Description | Example |
|--------|-------------|---------|
| faculty_id | Unique identifier | F001 |
| name | Faculty name | Dr. Anand |
| max_hours_per_day | Teaching limit | 4 |

**Example:**
```csv
faculty_id,name,max_hours_per_day
F001,Dr. Anand,4
F002,Dr. Somen,4
```

### rooms.csv

| Column | Description | Example |
|--------|-------------|---------|
| room_id | Room identifier | C202 |
| room_type | Type (classroom/lab) | classroom |
| capacity | Max students | 96 |

**Example:**
```csv
room_id,room_type,capacity
C202,classroom,96
L106,lab,40
```

---

## Scheduling Algorithm

### Strategy

The system uses a **greedy scheduling algorithm with intelligent distribution**:

1. **Course Prioritization**: Courses with more lectures per week are scheduled first
2. **Day Load Balancing**: Tracks class count per day and prefers lighter days
3. **Conflict Avoidance**: Real-time checking of faculty, room, and student availability
4. **Section Splitting**: Automatically separates combined sections (A&B) into individual schedules

### Constraints

- Regular class hours: 9:00 AM - 6:00 PM
- Lunch break: 1:30 PM - 2:00 PM (no scheduling)
- Maximum 1 lecture per course per day per section
- Faculty cannot be double-booked
- Rooms cannot be double-booked
- Student groups cannot have overlapping classes

### Algorithm Steps

```python
1. Load all input data (courses, faculty, rooms)
2. Generate time slots (excluding lunch break)
3. Expand combined sections (A&B → A, B)
4. Sort courses by lectures_per_week (descending)
5. For each course and section:
   a. Find available slots (faculty + room + student free)
   b. Sort by day load (prefer lighter days)
   c. Assign to best slot
   d. Mark slot as occupied
6. Validate for conflicts
7. Generate reports and outputs
```

---

## Output

### Console Output

- Timetable for each section (A, B, etc.)
- Faculty schedules showing all their classes
- Day-wise distribution statistics with visual bars
- List of courses that couldn't be scheduled
- Conflict validation report

### Excel Output (`output/timetable.xlsx`)

- Color-coded by course (each course has unique color)
- Sorted by section, day, and time
- Includes columns: Day, Time, Course Code, Title, L-T-P-S-C, Faculty, Room, Section
- Professional formatting with borders and alignment
- Frozen header row for easy scrolling

### Web Interface

- Interactive dashboard with statistics
- Tabbed navigation between sections and faculty
- Color-coded timetable views
- One-click Excel download
- Real-time generation progress

---

### Run Unit Tests

```bash
python tests/test_basic.py
```

or using pytest:

```bash
pytest tests/
```
## Testing

### Test Suite Overview

The project includes comprehensive unit tests covering all major components:

| Test Suite | File | Tests | Purpose |
|------------|------|-------|---------|
| Basic Unit Tests | `test_basic.py` | 7 | Core data models |
| Scheduler Tests | `test_scheduler.py` | 5 | Algorithm validation |
| Data Loader Tests | `test_data_loader.py` | 5 | CSV parsing |
| **Total** | | **17** | **Complete coverage** |

### Running Tests

**Run all tests:**
```bash
python tests/run_all_tests.py

---

### Test Coverage

- Course model creation and L-T-P-S-C parsing
- Faculty availability checking
- Room and slot management
- Data loader functionality
- Basic constraint validation

### Debugging

Run the CSV debug script to check data format:

```bash
python debug_csv.py
```

---

## Configuration

### Time Slots

Modify `data_loader.py` to change time slot definitions:

```python
time_slots = [
    ('09:00', '10:00'),
    ('10:10', '11:10'),
    # Add more slots as needed
]
```

### Scheduling Rules

Adjust constraints in `scheduler.py`:

```python
# Maximum lectures per day per course
if self.daily_course_count.get(key, 0) >= 1:
    continue  # Change 1 to allow multiple per day
```

---

## Known Limitations

1. Does not handle lab sessions that require multiple consecutive slots
2. No support for elective course grouping
3. Cannot optimize for faculty preference of time slots
4. No support for half-semester courses scheduling
5. Exam timetable generation not yet implemented

---

## Future Enhancements

- Web-based admin panel for data management
- Google Calendar integration
- Real-time notifications for schedule changes
- Exam timetable and seating plan generation
- Faculty workload analysis and reporting
- Student-specific timetable views with electives
- Mobile application
- Multi-semester planning
- Room utilization analytics

---

## Team Members

**Team: Byte Me**

- Padala Gnandeep (24BCS095)
- Phanishree N (24BCS101)
- Shriyans S S Sahoo (24BCS142)
- Syed Mahdee Husain (24BCS156)

**Under the guidance of:**
- Dr. Vivekraj V K, Assistant Professor, IIIT Dharwad

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is developed as part of the academic curriculum at IIIT Dharwad.

---

## Acknowledgments

- IIIT Dharwad for providing the problem statement and requirements
- Dr. Vivekraj V K for guidance and mentorship
- Python community for excellent libraries (Pandas, OpenPyXL)

---

## Support

For issues or questions:
- Create an issue on GitHub: [https://github.com/shriyanssahoo/Byte_Me/issues](https://github.com/shriyanssahoo/Byte_Me/issues)
- Contact team members via IIIT Dharwad email

---

## Project Status

**Current Version:** 1.1.0  
**Status:** Active Development  
**Last Updated:** October 2025

---

*Built with dedication by Team Byte_Me at IIIT Dharwad*