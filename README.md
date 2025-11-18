# Automated Timetable Scheduler

An intelligent, constraint-based timetable generation system for IIIT Dharwad, designed to handle complex scheduling requirements for multiple departments, semesters, and resource constraints.

## 🎯 Overview

This project automates the generation of academic timetables for Computer Science & Engineering (CSE), Data Science & AI (DSAI), and Electronics & Communication Engineering (ECE) departments across semesters 1, 3, 5, and 7. It handles both pre-midsem and post-midsem scheduling periods, along with exam scheduling and seating arrangements.

## ✨ Key Features

### Core Scheduling
- **Multi-Department Support**: Handles CSE, DSAI, and ECE departments simultaneously
- **Pre/Post-Midsem Periods**: Separate scheduling for pre and post mid-semester periods
- **Flexible Course Types**: 
  - Core courses (Lecture, Tutorial, Practical)
  - Combined classes (all sections together)
  - Cross-departmental electives
  - Department-specific baskets
- **Smart Resource Allocation**: Automatic classroom and lab assignment based on capacity
- **Faculty Break Management**: Ensures 30-minute breaks between consecutive faculty classes

### Constraint Management
- **One-Class-Per-Day Rule**: Prevents multiple lectures/labs of the same course on a single day
- **LTPSC Fulfillment**: Validates Lecture-Tutorial-Practical hours match requirements
- **Student Break Enforcement**: Automatic 10-minute breaks between consecutive classes
- **Lunch Slot Management**: Semester-specific lunch timings
- **Faculty Conflict Prevention**: No double-booking of instructors

### Exam Scheduling
- **Automated Exam Schedule**: Generates exam dates and time slots
- **Seating Plan Generation**: Creates room-wise seating arrangements
- **Strategic Seating**: Alternating column arrangement to maximize spacing between departments
- **Visual Seating Charts**: Excel sheets with clear seating layouts

### User Interfaces
- **Web Interface**: Role-based access for Students, Faculty, and Admins
- **Command-Line Tool**: Direct Python execution for batch processing
- **Excel Exports**: Professional timetable spreadsheets with color-coding

## 🏗️ Architecture

```
Byte_Me/
├── data/
│   ├── classroom_data.csv      # Room definitions
│   ├── course.csv              # Course catalog
│   ├── students.csv            # Student enrollment data
│   ├── exam_rooms.csv          # Exam venue configuration
│   └── exam_config.csv         # Exam scheduling parameters
├── src/
│   ├── __init__.py
│   ├── models.py               # Core data structures
│   ├── utils.py                # Time slot and helper functions
│   ├── data_loader.py          # CSV parsing and course bundling
│   ├── scheduler.py            # Main scheduling algorithm
│   ├── validators.py           # Constraint validation
│   ├── excel_exporter.py       # Timetable export to Excel
│   └── exam_scheduler_main.py  # Exam scheduling module
├── output/
│   ├── Department_Timetables.xlsx
│   ├── Faculty_Timetables.xlsx
│   └── exams/                  # Exam schedules and seating plans
├── tests/
│   ├── test_loader.py
│   └── test_scheduler.py
├── main.py                     # CLI entry point
├── web_app.py                  # Flask web interface
└── requirements.txt
```

## 📋 Prerequisites

- Python 3.8 or higher
- pip package manager

## 🚀 Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Byte_Me
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Verify data files**
Ensure the following CSV files exist in the `data/` directory:
- `classroom_data.csv`
- `course.csv`
- `students.csv`
- `exam_rooms.csv`
- `exam_config.csv`

## 💻 Usage

### Command-Line Interface

Generate timetables directly:
```bash
python main.py
```

This will:
- Load classroom and course data
- Run scheduling for all semesters (1, 3, 5, 7)
- Generate both PRE and POST midsem schedules
- Validate all constraints
- Export to `output/Department_Timetables.xlsx` and `output/Faculty_Timetables.xlsx`

### Web Interface

Start the Flask web server:
```bash
python web_app.py
```

Then open your browser to `http://localhost:5000`

**Available Portals:**
- **Student Portal**: View section-wise class schedules
- **Faculty Portal**: View teaching schedules by instructor
- **Admin Dashboard**: 
  - Regenerate timetables
  - View system statistics
  - Download Excel exports
  - Monitor loaded courses and rooms

### Exam Scheduling

Generate exam schedules and seating plans:
```bash
python src/exam_scheduler_main.py
```

Outputs:
- `output/exams/Exam_Schedule.csv` - Complete exam calendar
- `output/exams/Exam_<CourseCode><Date><Slot>.xlsx` - Seating plans per exam

## 📊 Data Format

### Course CSV (`course.csv`)
```csv
Course Code,Course Name,Semester,Department,LTPSC,Credits,Instructor,Registered Students,Elective (Yes/No),Half Semester (Yes/No),Combined class,Pre /Post,Basket Code
CS161,Problem Solving with Python,1,CSE,3-0-2-0-4,4,"Sunil P V, Sunil C K",200,No,No,no,full,
```

### Classroom CSV (`classroom_data.csv`)
```csv
Room Number,Type,Capacity,Facilities
C202,Classroom,96,Projector
L105,Lab,40,"Hardware Kits, Computers"
```

### Students CSV (`students.csv`)
```csv
roll_number,name,branch,section,semester
24BCS001,AAKASH BABASAHEB PATHRIKAR,CSE,A,3
```

## 🎨 Scheduling Algorithm

### Phase-Based Approach

1. **Phase 3: Elective/Basket Slots**
   - Books placeholder slots for elective and basket courses
   - Handles both cross-departmental (Type 1) and department-specific (Type 2) courses

2. **Phase 4: Combined Classes**
   - Schedules courses that combine all sections (uses C004 - 240 capacity room)
   - Ensures all departments attend simultaneously

3. **Phase 5/6: Core Courses**
   - Schedules section-specific lectures, tutorials, and practicals
   - Handles CSE split sections (A/B) for half-semester courses

4. **Phase 8: Elective Assignment**
   - Assigns real instructors and rooms to placeholder slots
   - Handles overflow electives that couldn't fit in PRE period

### Key Rules

- **LTPSC Encoding**: `L-T-P-S-C` format (e.g., `3-1-0-0-2`)
  - L=3 → 2 lectures per week
  - L=1 → Converts to 1 tutorial
  - P → Must be even, creates P/2 practicals

- **Session Durations**:
  - Lecture: 1.5 hours (9 slots)
  - Tutorial: 1 hour (6 slots)
  - Practical: 2 hours (12 slots)

- **Break Rules**:
  - Students: 10 minutes after each class
  - Faculty: 30 minutes between consecutive classes

## 🧪 Testing

Run unit tests:
```bash
pytest tests/
```

Tests cover:
- LTPSC parsing logic
- Faculty break enforcement
- Lab adjacency finding
- Course bundling

## 🔧 Configuration

### Time Settings (`src/utils.py`)
```python
SLOT_DURATION_MINS = 10
START_TIME_STR = "09:00"
END_TIME_STR = "18:00"
LECTURE_SLOTS = 9   # 1.5 hours
TUTORIAL_SLOTS = 6  # 1 hour
PRACTICAL_SLOTS = 12  # 2 hours
```

### Lunch Timings
- Semester 1 & 7: 12:30 - 13:00
- Semester 3: 13:00 - 13:30
- Semester 5: 13:30 - 14:00

## 📤 Output Files

### Department Timetables
- Separate sheet per section (e.g., CSE-Sem1-PRE-A)
- Color-coded by course
- Shows: Course name, session type, instructor, room

### Faculty Timetables
- Separate sheet per instructor
- Shows all teaching assignments
- Includes: Course name, session type, section, room

### Exam Files
- **Exam_Schedule.csv**: Date, slot, duration, course details
- **Seating Plans**: Room-wise seating with visual COL1, COL2, COL3 layout

## 🐛 Known Limitations

1. **Hard-coded C004**: Combined classes require the 240-capacity room (C004)
2. **Semester 7 Rule**: POST period is an exact copy of PRE period
3. **CSE Sections**: Assumes exactly 2 sections (A & B) for CSE department
4. **Lab Capacity**: Labs are capped at 40 students for CSE practicals

## 🤝 Contributing

When contributing, please:
1. Follow the existing code structure
2. Add unit tests for new features
3. Update CSV headers documentation if adding new columns
4. Test with real data before committing

## 📝 License

[Add your license information here]

## 👥 Authors

Developed for IIIT Dharwad by the Byte_Me team.

## 📧 Support

For issues or questions, please open an issue in the repository or contact the development team.

---

**Note**: This system is designed specifically for IIIT Dharwad's requirements. Adaptation for other institutions may require modifications to scheduling rules and data formats.