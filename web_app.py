"""
Flask web interface with role-based access for the
Automated Time Table Scheduler.

Run: python web_app.py
Visit: http://localhost:5000
"""

import sys
import os
import secrets
import random
import re
import copy
import io
from typing import List, Dict, Set, Optional
from flask import Flask, render_template_string, jsonify, send_file, request, url_for

# --- Absolute Imports from the 'src' package ---
try:
    import src.utils as utils
    from src.models import Section, Classroom, Course, Timetable
    from src.data_loader import load_classrooms, load_and_process_courses
    from src.scheduler import Scheduler
    from src.validators import validate_all
    from src.excel_exporter import ExcelExporter
except ImportError as e:
    print(f"FATAL ERROR: Could not import 'src' modules: {e}")
    print("Please ensure 'src/__init__.py' exists and this script is in the root folder.")
    print("Your project structure should be:")
    print("  Byte_Me/ (your root folder)")
    print("  ├── web_app.py (this file)")
    print("  └── src/")
    print("      ├── __init__.py")
    print("      ├── data_loader.py")
    print("      └── ... (all other .py files)")
    sys.exit(1)


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# --- Global Cache for Generated Timetables ---
g_is_generated: bool = False
g_all_sections: List[Section] = []
g_all_faculty_schedules: Dict[str, Timetable] = {}
g_all_classrooms: List[Classroom] = []
g_course_color_map: Dict[str, str] = {}
g_course_db: Dict[str, Course] = {} # For admin data


def generate_color_map(sections: List[Section]) -> Dict[str, str]:
    """Generates a unique hex color for each course code."""
    course_codes: Set[str] = set()
    for section in sections:
        for day_schedule in section.timetable.grid:
            for slot in day_schedule:
                if slot and slot.course.course_code not in ["LUNCH", "BREAK"]:
                    course_codes.add(slot.course.course_code)
    
    color_map = {}
    for code in course_codes:
        r = random.randint(180, 240)
        g = random.randint(180, 240)
        b = random.randint(180, 240)
        color_map[code] = f"{r:02X}{g:02X}{b:02X}"
    
    color_map["LUNCH"] = "F0F0F0"
    color_map["BREAK"] = "FFFFFF"
    return color_map

def run_generation_pipeline() -> bool:
    """
    This is the core logic from main.py, refactored as a function.
    It runs all 8 scheduling passes and populates the global variables.
    """
    global g_is_generated, g_all_sections, g_all_faculty_schedules, g_all_classrooms, g_course_color_map, g_course_db
    
    print("--- RUNNING FULL TIMETABLE GENERATION ---")
    
    # --- 1. Load Data ---
    all_classrooms = load_classrooms("data/classroom_data.csv")
    if not all_classrooms:
        print("Fatal Error: No classrooms loaded.")
        return False
        
    pre_midsem_courses, post_midsem_courses = load_and_process_courses("data/courses.csv")
    if not pre_midsem_courses and not post_midsem_courses:
        print("Fatal Error: No courses loaded (check data_loader).")
        return False
    
    g_course_db.clear()
    for c in pre_midsem_courses + post_midsem_courses:
        if c.course_code not in g_course_db:
            g_course_db[c.course_code] = c

    # --- 2. Master Loop ---
    master_pre_faculty_schedules: Dict[str, Timetable] = {}
    master_pre_room_schedules: Dict[str, Timetable] = {}
    master_post_faculty_schedules: Dict[str, Timetable] = {}
    master_post_room_schedules: Dict[str, Timetable] = {}
    
    all_generated_sections_list: List[Section] = []
    overflow_courses_to_post: List[Course] = []

    for semester in [1, 3, 5]:
        # --- PRE-MIDSEM RUN (Sem 1, 3, 5) ---
        pre_sections = create_sections(semester, "PRE")
        pre_courses_for_sem = filter_courses_for_run(pre_midsem_courses, semester)
        
        if pre_courses_for_sem:
            pre_scheduler = Scheduler(
                all_classrooms, "PRE",
                master_pre_room_schedules, master_pre_faculty_schedules
            )
            populated_pre_sections, overflow_from_pre = pre_scheduler.run(pre_courses_for_sem, pre_sections)
            all_generated_sections_list.extend(populated_pre_sections)
            overflow_courses_to_post.extend(overflow_from_pre)
        else:
            print(f"\n--- No PRE courses for Sem {semester}. Skipping PRE run. ---")
            
        # --- POST-MIDSEM RUN (Sem 1, 3, 5) ---
        post_sections = create_sections(semester, "POST")
        post_courses_for_sem = filter_courses_for_run(post_midsem_courses, semester)
        
        overflow_for_this_sem = [c for c in overflow_courses_to_post if c.semester == semester]
        if overflow_for_this_sem:
            print(f"Adding {len(overflow_for_this_sem)} overflow electives to POST run for Sem {semester}")
            post_courses_for_sem.extend(overflow_for_this_sem)
        
        if post_courses_for_sem:
            post_scheduler = Scheduler(
                all_classrooms, "POST",
                master_post_room_schedules, master_post_faculty_schedules
            )
            populated_post_sections, _ = post_scheduler.run(post_courses_for_sem, post_sections)
            all_generated_sections_list.extend(populated_post_sections)
        else:
            print(f"\n--- No POST courses for Sem {semester}. Skipping POST run. ---")

    # --- Schedule Sem 7 (PRE-MIDSEM ONLY) ---
    sem_7_pre_sections_list = create_sections(7, "PRE")
    sem_7_courses = filter_courses_for_run(pre_midsem_courses, 7)
    
    if sem_7_courses:
        sem_7_scheduler = Scheduler(
            all_classrooms, "PRE",
            master_pre_room_schedules, master_pre_faculty_schedules
        )
        populated_sem_7_pre_sections, _ = sem_7_scheduler.run(sem_7_courses, sem_7_pre_sections_list)
        all_generated_sections_list.extend(populated_sem_7_pre_sections)
        
        sem_7_post_sections = copy_sem7_to_post(
            populated_sem_7_pre_sections,
            master_post_faculty_schedules, master_post_room_schedules
        )
        all_generated_sections_list.extend(sem_7_post_sections)
    else:
        print("\n--- No Sem 7 courses found in PRE list. Skipping Sem 7. ---")

    print(f"\n--- All Scheduling Runs Complete ---")

    # --- 3. Run Validators ---
    print("\nValidating PRE-Midsem master schedule...")
    validate_all(
        [s for s in all_generated_sections_list if s.period == "PRE"],
        master_pre_faculty_schedules
    )
    print("\nValidating POST-Midsem master schedule...")
    validate_all(
        [s for s in all_generated_sections_list if s.period == "POST"],
        master_post_faculty_schedules
    )

    # --- 4. Populate Global Cache ---
    g_all_sections = all_generated_sections_list
    g_all_faculty_schedules = {**master_pre_faculty_schedules, **master_post_faculty_schedules}
    g_all_classrooms = all_classrooms
    g_course_color_map = generate_color_map(g_all_sections)
    g_is_generated = True
    
    print("--- Timetable Generation and Caching Complete ---")
    return True

# --- Helper Functions (from main.py) ---

def create_sections(semester: int, period: str) -> List[Section]:
    sections = []
    for dept in ["CSE", "DSAI", "ECE"]:
        if dept == "CSE":
            sections.append(Section(id=f"CSE-Sem{semester}-{period}-A", department="CSE", semester=semester, period=period, section_name="A"))
            sections.append(Section(id=f"CSE-Sem{semester}-{period}-B", department="CSE", semester=semester, period=period, section_name="B"))
        else:
            sections.append(Section(id=f"{dept}-Sem{semester}-{period}", department=dept, semester=semester, period=period, section_name=""))
    return sections

def filter_courses_for_run(all_courses: List[Course], semester: int) -> List[Course]:
    return [course for course in all_courses if course.semester == semester]

def copy_sem7_to_post(
    sem_7_pre_sections: List[Section],
    master_post_faculty_schedules: Dict[str, Timetable],
    master_post_room_schedules: Dict[str, Timetable]
) -> List[Section]:
    print("\n--- COPYING Sem 7 PRE to POST (as per rule) ---")
    sem_7_post_sections: List[Section] = []
    
    for pre_sec in sem_7_pre_sections:
        post_sec = Section(
            id=pre_sec.id.replace("PRE", "POST"),
            department=pre_sec.department,
            semester=pre_sec.semester,
            period="POST",
            section_name=pre_sec.section_name
        )
        post_sec.timetable = copy.deepcopy(pre_sec.timetable)
        post_sec.timetable.owner_id = post_sec.id
        sem_7_post_sections.append(post_sec)

    for sec in sem_7_pre_sections:
        for day in range(len(utils.DAYS)):
            for slot in range(utils.TOTAL_SLOTS_PER_DAY):
                s_class = sec.timetable.grid[day][slot]
                is_start = (slot == 0) or (sec.timetable.grid[day][slot-1] != s_class)
                if s_class and s_class.course.course_code not in ["LUNCH", "BREAK"] and is_start:
                    duration = s_class.course.get_session_duration(s_class.session_type)
                    if duration == 0: duration = 1
                    
                    for instructor in s_class.instructors:
                        if instructor == "TBD": continue
                        faculty_tt = master_post_faculty_schedules.setdefault(instructor, Timetable(instructor, -1))
                        for i in range(duration):
                            if slot+i < utils.TOTAL_SLOTS_PER_DAY: faculty_tt.grid[day][slot+i] = s_class
                    
                    for room_id in s_class.room_ids:
                        room_tt = master_post_room_schedules.setdefault(room_id, Timetable(room_id, -1))
                        for i in range(duration):
                            if slot+i < utils.TOTAL_SLOTS_PER_DAY: room_tt.grid[day][slot+i] = s_class
                            
    print(f"Successfully copied {len(sem_7_post_sections)} Sem 7 POST sections.")
    return sem_7_post_sections

# --- HTML Generation ---

def _build_timetable_html(timetable: Timetable, view_type: str = 'section') -> str:
    """
    Generates the HTML table for a given Timetable object.
    Matches the (Days x Times) layout.
    """
    global g_course_color_map
    
    html = '<table class="timetable-grid">'
    
    html += '<thead><tr><th>Time / Day</th>'
    time_slots = utils.get_time_slots_list()
    for time_str in time_slots:
        html += f'<th>{time_str}</th>'
    html += '</tr></thead>'
    
    html += '<tbody>'
    for day_idx, day_name in enumerate(utils.DAYS):
        html += f'<tr><td class="day-header">{day_name}</td>'
        
        col_idx = 0
        while col_idx < utils.TOTAL_SLOTS_PER_DAY:
            s_class = timetable.grid[day_idx][col_idx]
            
            if not s_class:
                html += '<td class="slot-empty"></td>'
                col_idx += 1
                continue
            
            duration = 1
            while (col_idx + duration < utils.TOTAL_SLOTS_PER_DAY and
                   timetable.grid[day_idx][col_idx + duration] == s_class):
                duration += 1
            
            cell_content = ""
            cell_style = ""
            
            if s_class.course.course_code == "LUNCH":
                cell_content = "LUNCH"
                cell_style = 'background-color: #f0f0f0; color: #888; font-weight: bold;'
            elif s_class.course.course_code == "BREAK":
                cell_content = "BREAK"
                cell_style = 'background-color: #f9f9f9; color: #aaa; font-size: 0.8em;'
            else:
                course_name = s_class.course.course_name
                room_str = ", ".join(s_class.room_ids)
                section_str = s_class.section_id
                
                instructor_str = ", ".join(s_class.instructors)
                session_str = f"({s_class.session_type})"
                
                if s_class.course.is_pseudo_course:
                    instructor_str = ""
                    match = re.search(r'\((.*?)\)', course_name)
                    session_str = f"({match.group(1)})" if match else "(Elective/Basket)"
                
                if view_type == 'section':
                    cell_content = f'<div class="c-name">{course_name}</div><div class="c-session">{session_str}</div><div class="c-details">{instructor_str}<br/>{room_str}</div>'
                elif view_type == 'faculty':
                     cell_content = f'<div class="c-name">{course_name}</div><div class="c-session">{session_str}</div><div class="c-details">{section_str}<br/>{room_str}</div>'
                
                color = g_course_color_map.get(s_class.course.course_code, "#FFFFFF")
                cell_style = f'background-color: {color};'

            html += f'<td colspan="{duration}" style="{cell_style}">{cell_content}</td>'
            col_idx += duration
            
        html += '</tr>'
        
    html += '</tbody></table>'
    return html

# --- HTML Templates ---

SHARED_CSS = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #f4f7f6;
        min-height: 100vh;
        padding: 20px;
    }
    .container { max-width: 95%; margin: 20px auto; }
    .card {
        background: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        text-align: center;
    }
    .header {
        background: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        text-align: center;
    }
    .header h1 { color: #667eea; font-size: 2.5em; margin-bottom: 10px; }
    .header p { color: #666; font-size: 1.2em; }
    .btn {
        padding: 15px 30px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-size: 1em;
        font-weight: bold;
        transition: all 0.3s;
        text-decoration: none;
        display: inline-block;
        margin: 5px;
    }
    .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    .btn-primary:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
    .btn-secondary { background: #f0f0f0; color: #333; }
    .btn-secondary:hover { background: #e0e0e0; }
    
    .timetable-content {
        background: white;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        overflow-x: auto;
    }
    table.timetable-grid {
        width: 100%;
        border-collapse: collapse;
        min-width: 2000px;
    }
    table.timetable-grid th, table.timetable-grid td {
        border: 1px solid #e0e0e0;
        padding: 8px;
        text-align: center;
        vertical-align: top;
        height: 100px;
        font-size: 0.9em;
    }
    table.timetable-grid th {
        background: #667eea;
        color: white;
        font-weight: 600;
        font-size: 0.8em;
        padding: 10px 5px;
        white-space: nowrap;
        min-width: 60px;
    }
    table.timetable-grid td.day-header {
        background: #f4f7f6;
        font-weight: bold;
        color: #667eea;
        font-size: 1.1em;
        text-align: left;
        padding-left: 20px;
        width: 150px;
    }
    table.timetable-grid td {
        background: #fff;
        color: #333;
    }
    table.timetable-grid td.slot-empty { background: #fdfdfd; }
    .c-name { font-weight: bold; font-size: 1.1em; color: #333; margin-bottom: 5px; }
    .c-session { font-style: italic; color: #555; margin-bottom: 8px; }
    .c-details { font-size: 0.9em; color: #777; line-height: 1.4; }
</style>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html><head><title>Timetable System - Login</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        display: flex; align-items: center; justify-content: center; padding: 20px;
    }
    .container { max-width: 1200px; width: 100%; }
    .header {
        background: white; padding: 40px; border-radius: 15px 15px 0 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center;
    }
    .header h1 { color: #667eea; font-size: 2.5em; margin-bottom: 10px; }
    .header p { color: #666; font-size: 1.2em; }
    .login-options {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px;
        padding: 40px; background: white; border-radius: 0 0 15px 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .login-card {
        padding: 40px 30px; border-radius: 15px; text-align: center;
        cursor: pointer; transition: all 0.3s; box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .login-card:hover { transform: translateY(-10px); box-shadow: 0 15px 30px rgba(0,0,0,0.4); }
    .login-card.student { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .login-card.faculty { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .login-card.admin { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    .login-card .icon { font-size: 4em; margin-bottom: 20px; }
    .login-card h2 { color: white; font-size: 1.8em; margin-bottom: 15px; }
    .login-card p { color: rgba(255,255,255,0.9); font-size: 1em; }
    @media (max-width: 768px) { .login-options { grid-template-columns: 1fr; } }
</style>
</head><body>
    <div class="container">
        <div class="header">
            <h1>🎓 Automated Timetable System</h1>
            <p>IIIT Dharwad - Class Scheduler</p>
        </div>
        <div class="login-options">
            <div class="login-card student" onclick="location.href='/student'">
                <div class="icon">👨‍🎓</div> <h2>Student</h2> <p>View class schedule</p>
            </div>
            <div class="login-card faculty" onclick="location.href='/faculty'">
                <div class="icon">👨‍🏫</div> <h2>Faculty</h2> <p>View teaching schedule</p>
            </div>
            <div class="login-card admin" onclick="location.href='/admin'">
                <div class="icon">👨‍💼</div> <h2>Admin</h2> <p>Manage & generate</p>
            </div>
        </div>
    </div>
</body></html>
"""

STUDENT_SELECT_PAGE = """
<!DOCTYPE html>
<html><head><title>Student Portal - Select Section</title>
""" + SHARED_CSS + """
<style>
    body { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .card { text-align: left; }
    h1 { color: #4facfe; text-align: center; }
    p { text-align: center; margin-bottom: 30px; }
    input[type="search"] {
        width: 100%; padding: 15px; font-size: 1.1em;
        border: 2px solid #f0f0f0; border-radius: 8px; margin-bottom: 20px;
    }
    .section-list { max-height: 400px; overflow-y: auto; }
    .section-item {
        padding: 20px; margin: 10px 0; background: #f8f9fa;
        border-radius: 8px; cursor: pointer; transition: all 0.3s;
    }
    .section-item:hover {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white; transform: translateX(10px);
    }
    .section-id { font-size: 1.2em; font-weight: bold; }
    .loading { text-align: center; padding: 40px; color: #666; }
</style>
</head><body>
    <div class="container" style="max-width: 800px;">
        <div class="card">
            <h1>👨‍🎓 Student Portal</h1>
            <p>Select your section to view the timetable</p>
            <input type="search" id="searchBox" onkeyup="filterList()" placeholder="Search (e.g., 'CSE-Sem1-PRE-A')">
            <div class="section-list" id="sectionList">
                <div class="loading">Loading sections...</div>
            </div>
            <button class="btn btn-secondary" style="margin-top: 30px; width: 100%;" onclick="location.href='/'">← Back to Home</button>
        </div>
    </div>
<script>
    let sections = [];
    fetch('/api/section-list')
        .then(response => response.json())
        .then(data => {
            sections = data.sections || [];
            renderList(sections);
        });
    
    function renderList(items) {
        const listEl = document.getElementById('sectionList');
        if (items.length > 0) {
            listEl.innerHTML = items.map(s_id => `
                <div class="section-item" onclick="viewTimetable('${s_id}')">
                    <div class="section-id">${s_id}</div>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<div class="loading">No sections found. Generate timetable from Admin panel.</div>';
        }
    }
    
    function filterList() {
        const query = document.getElementById('searchBox').value.toLowerCase();
        const filtered = sections.filter(s_id => s_id.toLowerCase().includes(query));
        renderList(filtered);
    }
    
    function viewTimetable(sectionId) {
        window.location.href = '/student/timetable?id=' + sectionId;
    }
</script>
</body></html>
"""

FACULTY_SELECT_PAGE = """
<!DOCTYPE html>
<html><head><title>Faculty Portal - Select Name</title>
""" + SHARED_CSS + """
<style>
    body { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .card { text-align: left; }
    h1 { color: #43e97b; text-align: center; }
    p { text-align: center; margin-bottom: 30px; }
    input[type="search"] {
        width: 100%; padding: 15px; font-size: 1.1em;
        border: 2px solid #f0f0f0; border-radius: 8px; margin-bottom: 20px;
    }
    .faculty-list { max-height: 400px; overflow-y: auto; }
    .faculty-item {
        padding: 20px; margin: 10px 0; background: #f8f9fa;
        border-radius: 8px; cursor: pointer; transition: all 0.3s;
    }
    .faculty-item:hover {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white; transform: translateX(10px);
    }
    .faculty-name { font-size: 1.2em; font-weight: bold; }
    .loading { text-align: center; padding: 40px; color: #666; }
</style>
</head><body>
    <div class="container" style="max-width: 800px;">
        <div class="card">
            <h1>👨‍🏫 Faculty Portal</h1>
            <p>Select your name to view your schedule</p>
            <input type="search" id="searchBox" onkeyup="filterList()" placeholder="Search for your name...">
            <div class="faculty-list" id="facultyList">
                <div class="loading">Loading faculty...</div>
            </div>
            <button class="btn btn-secondary" style="margin-top: 30px; width: 100%;" onclick="location.href='/'">← Back to Home</button>
        </div>
    </div>
<script>
    let faculty = [];
    fetch('/api/faculty-list')
        .then(response => response.json())
        .then(data => {
            faculty = data.faculty || [];
            renderList(faculty);
        });
    
    function renderList(items) {
        const listEl = document.getElementById('facultyList');
        if (items.length > 0) {
            listEl.innerHTML = items.map(name => `
                <div class="faculty-item" onclick="viewTimetable('${name}')">
                    <div class="faculty-name">${name}</div>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<div class="loading">No faculty found. Generate timetable from Admin panel.</div>';
        }
    }
    
    function filterList() {
        const query = document.getElementById('searchBox').value.toLowerCase();
        const filtered = faculty.filter(name => name.toLowerCase().includes(query));
        renderList(filtered);
    }
    
    function viewTimetable(facultyName) {
        window.location.href = '/faculty/timetable?name=' + encodeURIComponent(facultyName);
    }
</script>
</body></html>
"""

ADMIN_DASHBOARD = """
<!DOCTYPE html>
<html><head><title>Admin Dashboard</title>
""" + SHARED_CSS + """
<style>
    body { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    h1 { color: #fa709a; }
    .actions { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-top: 20px; }
    .btn-gen { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: #333; }
    .btn-gen:hover { box-shadow: 0 5px 15px rgba(250, 112, 154, 0.4); }
    .dashboard-grid {
        display: grid; grid-template-columns: 1fr 1fr;
        gap: 20px; margin-top: 20px;
    }
    .card { text-align: left; }
    .card h2 {
        color: #fa709a; font-size: 1.5em; margin-bottom: 15px;
        padding-bottom: 10px; border-bottom: 2px solid #fee140;
    }
    .stats { display: flex; justify-content: space-around; margin: 20px 0; }
    .stat-box { text-align: center; padding: 20px; background: #f8f9fa; border-radius: 10px; }
    .stat-number { font-size: 2.5em; font-weight: bold; color: #fa709a; }
    .stat-label { color: #666; font-size: 0.9em; margin-top: 5px; }
    .data-table { max-height: 300px; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th { background: #fdeff4; color: #d16a8d; padding: 12px; text-align: left; font-size: 0.9em; }
    td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; font-size: 0.9em; }
    tr:hover { background: #fff5f7; }
    .loading { text-align: center; padding: 40px; color: #999; }
    
    @media (max-width: 900px) { .dashboard-grid { grid-template-columns: 1fr; } }
</style>
</head><body>
    <div class="container">
        <div class="header">
            <h1>👨‍💼 Admin Dashboard</h1>
            <p>System overview and generation controls</p>
            <div class="actions">
                <button class="btn btn-gen" onclick="generateTimetable()">🔄 Re-Generate Class Timetable</button>
                <button class="btn btn-secondary" onclick="location.href='/download-class-tt'">📥 Download Class Timetables</button>
                <button class="btn btn-secondary" onclick="runExamScheduler()">📝 Run Exam Scheduler</button>
                <button class="btn btn-secondary" onclick="location.href='/'">← Back to Home</button>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h2>📊 System Statistics</h2>
                <div class="stats" id="stats"><div class="loading">Loading...</div></div>
            </div>
            <div class="card">
                <h2>📚 Courses Loaded (from courses.csv)</h2>
                <div id="courses" class="data-table"><div class="loading">Loading...</div></div>
            </div>
            <div class="card">
                <h2>🏫 Classrooms Loaded</h2>
                <div id="rooms" class="data-table"><div class="loading">Loading...</div></div>
            </div>
        </div>
    </div>
<script>
    function loadData() {
        fetch('/api/admin-data')
            .then(response => response.json())
            .then(data => {
                document.getElementById('stats').innerHTML = `
                    <div class="stat-box">
                        <div class="stat-number">${data.sections_count}</div>
                        <div class="stat-label">Sections Generated</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${data.faculty_count}</div>
                        <div class="stat-label">Faculty Schedules</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${data.rooms_count}</div>
                        <div class="stat-label">Total Rooms</div>
                    </div>
                `;
                
                document.getElementById('courses').innerHTML = `
                    <table>
                        <tr><th>Code</th><th>Name</th><th>Dept</th><th>Pref</th></tr>
                        ${data.courses.map(c => `
                            <tr>
                                <td>${c.code}</td>
                                <td>${c.name}</td>
                                <td>${c.dept}</td>
                                <td>${c.pref}</td>
                            </tr>
                        `).join('')}
                    </table>
                `;
                
                document.getElementById('rooms').innerHTML = `
                    <table>
                        <tr><th>Room ID</th><th>Type</th><th>Capacity</th></tr>
                        ${data.rooms.map(r => `
                            <tr>
                                <td>${r.id}</td>
                                <td>${r.type}</td>
                                <td>${r.capacity}</td>
                            </tr>
                        `).join('')}
                    </table>
                `;
            });
    }
    
    function generateTimetable() {
        if (confirm('This will regenerate all timetables. This may take 30-60 seconds. Are you sure?')) {
            alert('Generation started. Please wait for confirmation.');
            fetch('/generate').then(response => response.json()).then(data => {
                if(data.success) {
                    alert('Timetable generation complete! Page will now reload.');
                    location.reload();
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
    }
    
    function runExamScheduler() {
        alert('This will run the separate exam scheduler script in the console. Please check your terminal for output.');
        fetch('/generate-exams').then(r => r.json()).then(data => {
            alert(data.message);
        });
    }
    
    document.addEventListener('DOMContentLoaded', loadData);
</script>
</body></html>
"""

TIMETABLE_VIEW_PAGE = """
<!DOCTYPE html>
<html><head><title>{{ title }}</title>
""" + SHARED_CSS + """
<style>
    .header h1 { color: {{ header_color }}; }
</style>
</head><body>
    <div class="container">
        <div class="header">
            <h1>{{ header }}</h1>
            <p>{{ subheader }}</p>
            <button class="btn btn-secondary" onclick="location.href='{{ back_url }}'">← Back</button>
        </div>
        
        <div class="timetable-content">
            <div id="timetable-html">
                <h2 style="text-align: center; padding: 50px; color: #888;">
                    {% if is_generated %}
                        Loading Timetable...
                    {% else %}
                        No timetable has been generated yet.<br/>
                        Please ask an Admin to generate the schedule.
                    {% endif %}
                </h2>
            </div>
        </div>
    </div>
    
    {% if is_generated %}
    <script>
        fetch('{{ api_url }}')
            .then(response => response.json())
            .then(data => {
                const content = document.getElementById('timetable-html');
                if (data.success) {
                    content.innerHTML = data.html;
                } else {
                    content.innerHTML = `<h2 style="text-align: center; padding: 50px; color: #888;">${data.error}</h2>`;
                }
            })
            .catch(error => {
                document.getElementById('timetable-html').innerHTML = 
                    '<h2 style="text-align: center; padding: 50px; color: #888;">Error loading timetable.</h2>';
            });
    </script>
    {% endif %}
</body></html>
"""

# --- Flask Routes ---

@app.route('/')
def index():
    return LOGIN_PAGE

@app.route('/student')
def student_login():
    return STUDENT_SELECT_PAGE

@app.route('/faculty')
def faculty_login():
    return FACULTY_SELECT_PAGE

@app.route('/admin')
def admin_dashboard():
    return ADMIN_DASHBOARD

@app.route('/generate-exams')
def generate_exams_route():
    """
    Triggers the standalone exam_scheduler_main.py script.
    """
    print("\n--- ADMIN: Triggering Exam Scheduler ---")
    try:
        # Assumes exam_scheduler_main.py is in the root
        os.system(f"{sys.executable} exam_scheduler_main.py")
        return jsonify({'success': True, 'message': 'Exam scheduler script finished. Check console for details.'})
    except Exception as e:
        print(f"Error running exam scheduler: {e}")
        return jsonify({'success': False, 'message': f'Error: {e}'})

@app.route('/student/timetable')
def student_timetable():
    section_id = request.args.get('id', '')
    return render_template_string(
        TIMETABLE_VIEW_PAGE,
        title=f"Timetable - {section_id}",
        header=f"📚 Timetable for {section_id}",
        subheader="Your weekly class schedule",
        header_color="#4facfe",
        back_url="/student",
        api_url=f"/api/student-timetable?id={section_id}",
        is_generated=g_is_generated
    )

@app.route('/faculty/timetable')
def faculty_timetable():
    faculty_name = request.args.get('name', '')
    return render_template_string(
        TIMETABLE_VIEW_PAGE,
        title=f"Timetable - {faculty_name}",
        header=f"👨‍🏫 Timetable for {faculty_name}",
        subheader="Your teaching schedule",
        header_color="#43e97b",
        back_url="/faculty",
        api_url=f"/api/faculty-timetable?name={faculty_name}",
        is_generated=g_is_generated
    )

@app.route('/download-class-tt')
def download_class_tt():
    """
    Generates and sends the Department_Timetables.xlsx file.
    """
    if not g_is_generated:
        return "Timetable has not been generated. Please go to /admin and generate.", 400
        
    try:
        exporter = ExcelExporter(
            all_sections=g_all_sections,
            all_classrooms=g_all_classrooms,
            all_faculty_schedules=g_all_faculty_schedules
        )
        
        dept_buffer = io.BytesIO()
        exporter.export_department_timetables(dept_buffer)
        dept_buffer.seek(0)
        
        return send_file(
            dept_buffer,
            as_attachment=True,
            download_name="Department_Timetables.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return str(e), 500

# --- API ENDPOINTS ---

@app.route('/generate')
def generate():
    """Admin-only: Triggers a full re-generation of the timetable."""
    try:
        run_generation_pipeline()
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR during generation: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/section-list')
def api_section_list():
    if not g_is_generated:
        return jsonify({'sections': []})
        
    section_ids = sorted(list(set(s.id for s in g_all_sections)))
    return jsonify({'sections': section_ids})

@app.route('/api/faculty-list')
def api_faculty_list():
    if not g_is_generated:
        return jsonify({'faculty': []})
        
    faculty_names = sorted(list(g_all_faculty_schedules.keys()))
    return jsonify({'faculty': faculty_names})

@app.route('/api/admin-data')
def api_admin_data():
    """Get all system data for admin dashboard."""
    if not g_is_generated:
        # Load data manually if not generated yet
        global g_all_classrooms, g_course_db
        if not g_all_classrooms:
            g_all_classrooms = load_classrooms("data/classroom_data.csv")
        if not g_course_db:
            pre, post = load_and_process_courses("data/courses.csv")
            for c in pre + post:
                if c.course_code not in g_course_db:
                    g_course_db[c.course_code] = c

    return jsonify({
        'sections_count': len(g_all_sections),
        'faculty_count': len(g_all_faculty_schedules),
        'rooms_count': len(g_all_classrooms),
        'courses': [
            {'code': c.course_code, 'name': c.course_name, 'dept': c.department, 'pref': c.pre_post_preference}
            for c in g_course_db.values()
        ][:100], # Send first 100
        'rooms': [
            {'id': r.room_id, 'type': r.room_type, 'capacity': r.capacity}
            for r in g_all_classrooms
        ]
    })

@app.route('/api/student-timetable')
def api_student_timetable():
    section_id = request.args.get('id')
    if not section_id:
        return jsonify({'success': False, 'error': 'No section ID provided.'})
        
    section = next((s for s in g_all_sections if s.id == section_id), None)
    
    if not section:
        return jsonify({'success': False, 'error': f'Timetable for "{section_id}" not found.'})
        
    html = _build_timetable_html(section.timetable, view_type='section')
    return jsonify({'success': True, 'html': html})

@app.route('/api/faculty-timetable')
def api_faculty_timetable():
    faculty_name = request.args.get('name')
    if not faculty_name:
        return jsonify({'success': False, 'error': 'No faculty name provided.'})
        
    timetable = g_all_faculty_schedules.get(faculty_name)
    
    if not timetable:
        return jsonify({'success': False, 'error': f'Timetable for "{faculty_name}" not found.'})
        
    html = _build_timetable_html(timetable, view_type='faculty')
    return jsonify({'success': True, 'html': html})

# --- Main Execution ---
if __name__ == '__main__':
    print("=" * 70)
    print("🌐 Starting Timetable System Web Interface".center(70))
    print("=" * 70)
    
    # Run the scheduler once on startup
    run_generation_pipeline()
    
    print("\n📍 Open your browser and visit: http://localhost:5000")
    print("⚡ Press Ctrl+C to stop the server\n")
    app.run(debug=True, port=5000, use_reloader=False)