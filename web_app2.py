"""
Flask web interface for IIIT Dharwad Timetable System
Clean, structured, calendar-like interface

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
from flask import Flask, render_template_string, jsonify, send_file, request

try:
    import src.utils as utils
    from src.models import Section, Classroom, Course, Timetable
    from src.data_loader import load_classrooms, load_and_process_courses
    from src.scheduler import Scheduler
    from src.validators import validate_all
    from src.excel_exporter import ExcelExporter
except ImportError as e:
    print(f"FATAL ERROR: Could not import 'src' modules: {e}")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global state
g_is_generated: bool = False
g_all_sections: List[Section] = []
g_all_faculty_schedules: Dict[str, Timetable] = {}
g_all_classrooms: List[Classroom] = []
g_course_color_map: Dict[str, str] = {}
g_course_db: Dict[str, Course] = {}

def generate_color_map(sections: List[Section]) -> Dict[str, str]:
    """Generate subtle color variations for different session types"""
    course_codes: Set[str] = set()
    for section in sections:
        for day_schedule in section.timetable.grid:
            for slot in day_schedule:
                if slot and slot.course.course_code not in ["LUNCH", "BREAK"]:
                    if slot.course.parent_pseudo_name:
                        course_codes.add(slot.course.parent_pseudo_name)
                    else:
                        course_codes.add(slot.course.course_code)
    
    # Expanded professional color palette with distinct colors (no duplicates)
    # Each color is carefully chosen to be distinguishable and professional
    subtle_colors = [
        'E6F0F8',  # Light blue (IIIT theme)
        'F3E5F5',  # Light purple
        'E8F5E9',  # Light green
        'FFF8E1',  # Light amber
        'FCE4EC',  # Light pink
        'E0F2F1',  # Light teal
        'FFF3E0',  # Light orange
        'E8EAF6',  # Light indigo
        'F1F8E9',  # Light lime
        'FBE9E7',  # Light deep orange
        'F3E5F5',  # Light deep purple
        'E0F7FA',  # Light cyan
        'FFFDE7',  # Light yellow
        'EFEBE9',  # Light brown
        'ECEFF1',  # Light blue grey
    ]
    
    color_map = {}
    for i, code in enumerate(sorted(course_codes)):
        color_map[code] = subtle_colors[i % len(subtle_colors)]
    
    color_map["LUNCH"] = "FFF9C4"
    color_map["BREAK"] = "FAFAFA"
    return color_map

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

def copy_sem7_to_post(sem_7_pre_sections, master_post_faculty_schedules, master_post_room_schedules):
    sem_7_post_sections = []
    for pre_sec in sem_7_pre_sections:
        post_sec = Section(id=pre_sec.id.replace("PRE", "POST"), department=pre_sec.department, semester=pre_sec.semester, period="POST", section_name=pre_sec.section_name)
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
    return sem_7_post_sections

def run_generation_pipeline() -> bool:
    global g_is_generated, g_all_sections, g_all_faculty_schedules, g_all_classrooms, g_course_color_map, g_course_db
    
    all_classrooms = load_classrooms("data/classroom_data.csv")
    if not all_classrooms: return False
        
    pre_midsem_courses, post_midsem_courses = load_and_process_courses("data/course.csv")
    if not pre_midsem_courses and not post_midsem_courses: return False
    
    g_course_db.clear()
    for c in pre_midsem_courses + post_midsem_courses:
        if c.course_code not in g_course_db:
            g_course_db[c.course_code] = c

    master_pre_faculty_schedules = {}
    master_pre_room_schedules = {}
    master_post_faculty_schedules = {}
    master_post_room_schedules = {}
    
    all_generated_sections_list = []
    overflow_courses_to_post = []

    for semester in [1, 3, 5]:
        pre_sections = create_sections(semester, "PRE")
        pre_courses_for_sem = filter_courses_for_run(pre_midsem_courses, semester)
        
        if pre_courses_for_sem:
            pre_scheduler = Scheduler(all_classrooms, "PRE", master_pre_room_schedules, master_pre_faculty_schedules)
            populated_pre_sections, overflow_from_pre = pre_scheduler.run(pre_courses_for_sem, pre_sections)
            all_generated_sections_list.extend(populated_pre_sections)
            overflow_courses_to_post.extend(overflow_from_pre)
            
        post_sections = create_sections(semester, "POST")
        post_courses_for_sem = filter_courses_for_run(post_midsem_courses, semester)
        overflow_for_this_sem = [c for c in overflow_courses_to_post if c.semester == semester]
        if overflow_for_this_sem:
            post_courses_for_sem.extend(overflow_for_this_sem)
        
        if post_courses_for_sem:
            post_scheduler = Scheduler(all_classrooms, "POST", master_post_room_schedules, master_post_faculty_schedules)
            populated_post_sections, _ = post_scheduler.run(post_courses_for_sem, post_sections)
            all_generated_sections_list.extend(populated_post_sections)

    sem_7_pre_sections_list = create_sections(7, "PRE")
    sem_7_courses = filter_courses_for_run(pre_midsem_courses, 7)
    
    if sem_7_courses:
        sem_7_scheduler = Scheduler(all_classrooms, "PRE", master_pre_room_schedules, master_pre_faculty_schedules)
        populated_sem_7_pre_sections, _ = sem_7_scheduler.run(sem_7_courses, sem_7_pre_sections_list)
        all_generated_sections_list.extend(populated_sem_7_pre_sections)
        sem_7_post_sections = copy_sem7_to_post(populated_sem_7_pre_sections, master_post_faculty_schedules, master_post_room_schedules)
        all_generated_sections_list.extend(sem_7_post_sections)

    validate_all([s for s in all_generated_sections_list if s.period == "PRE"], master_pre_faculty_schedules)
    validate_all([s for s in all_generated_sections_list if s.period == "POST"], master_post_faculty_schedules)

    g_all_sections = all_generated_sections_list
    g_all_faculty_schedules = {**master_pre_faculty_schedules, **master_post_faculty_schedules}
    g_all_classrooms = all_classrooms
    g_course_color_map = generate_color_map(g_all_sections)
    g_is_generated = True
    return True

def _build_timetable_html(timetable: Timetable, view_type: str = 'section') -> str:
    global g_course_color_map
    
    html = '<table class="timetable-grid">'
    html += '<thead><tr><th class="sticky-corner">Time / Day</th>'
    
    # Days header
    for day_name in utils.DAYS:
        html += f'<th class="day-header">{day_name}</th>'
    html += '</tr></thead><tbody>'
    
    # Time slots
    time_slots = utils.get_time_slots_list()
    
    # Track which cells have been rendered (day_idx, slot_idx) to handle rowspan
    rendered = set()
    
    for slot_idx, time_str in enumerate(time_slots):
        html += f'<tr><td class="time-cell">{time_str}</td>'
        
        for day_idx in range(len(utils.DAYS)):
            # Skip if this cell was already rendered as part of a rowspan
            if (day_idx, slot_idx) in rendered:
                continue
            
            s_class = timetable.grid[day_idx][slot_idx]
            
            if not s_class:
                # Count consecutive empty slots
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] is None):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                
                html += f'<td class="empty-cell" rowspan="{rowspan}"></td>'
            
            elif s_class.course.course_code == "LUNCH":
                # Count lunch duration
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] == s_class):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                
                html += f'<td class="lunch-cell" rowspan="{rowspan}"><div class="cell-content">Lunch Break</div></td>'
            
            elif s_class.course.course_code == "BREAK":
                # Count break duration
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] == s_class):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                
                html += f'<td class="break-cell" rowspan="{rowspan}"></td>'
            
            else:
                # Count class duration
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] == s_class):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                
                course_name = s_class.course.parent_pseudo_name or s_class.course.course_name
                session_type = s_class.session_type.lower()
                
                color_key = s_class.course.parent_pseudo_name if s_class.course.parent_pseudo_name else s_class.course.course_code
                color = g_course_color_map.get(color_key, "E6F0F8")
                
                # Build tooltip data
                if view_type == 'section':
                    instructors = ", ".join(s_class.instructors) if s_class.instructors else "TBD"
                    rooms = ", ".join(s_class.room_ids) if s_class.room_ids else "TBD"
                    detail_html = f'<div class="cell-detail">{instructors}</div><div class="cell-detail">{rooms}</div>'
                    tooltip_info = f"{course_name}|||{session_type.capitalize()}|||Instructor: {instructors}|||Room: {rooms}"
                else:
                    section = s_class.section_id
                    rooms = ", ".join(s_class.room_ids) if s_class.room_ids else "TBD"
                    detail_html = f'<div class="cell-detail">{section}</div><div class="cell-detail">{rooms}</div>'
                    tooltip_info = f"{course_name}|||{session_type.capitalize()}|||Section: {section}|||Room: {rooms}"
                
                html += f'<td class="class-cell" rowspan="{rowspan}" style="background-color: #{color}" '
                html += f'data-type="{session_type}" data-tooltip="{tooltip_info}">'
                html += f'<div class="cell-content">'
                html += f'<div class="course-name">{course_name}</div>'
                html += detail_html
                html += '</div></td>'
        
        html += '</tr>'
    
    html += '</tbody></table>'
    return html

# HTML and CSS
MAIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IIIT Dharwad Timetable</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f9fa;
            color: #212529;
        }
        
        /* Header */
        .header {
            background: white;
            border-bottom: 1px solid #dee2e6;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .institute-name {
            font-size: 18px;
            font-weight: 600;
            color: #212529;
        }
        
        .view-selector {
            display: flex;
            gap: 0;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .view-btn {
            padding: 8px 20px;
            border: none;
            background: white;
            cursor: pointer;
            font-size: 14px;
            color: #495057;
            border-right: 1px solid #dee2e6;
            transition: all 0.15s;
        }
        
        .view-btn:last-child { border-right: none; }
        
        .view-btn:hover { background: #f8f9fa; }
        
        .view-btn.active {
            background: #004B87;
            color: white;
        }
        
        /* Main Layout */
        .main-container {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            height: calc(100vh - 65px);
        }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background: white;
            border-right: 1px solid #dee2e6;
            overflow-y: auto;
            flex-shrink: 0;
        }
        
        .sidebar-section {
            padding: 20px;
            border-bottom: 1px solid #f1f3f5;
        }
        
        .sidebar-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: #868e96;
            margin-bottom: 12px;
            letter-spacing: 0.5px;
        }
        
        .search-box {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
            outline: none;
        }
        
        .search-box:focus { border-color: #004B87; }
        
        .filter-list {
            list-style: none;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .filter-item {
            padding: 10px 12px;
            margin: 2px 0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            color: #495057;
            transition: background 0.1s;
        }
        
        .filter-item:hover { background: #f8f9fa; }
        
        .filter-item.selected {
            background: #E6F0F8;
            color: #004B87;
            font-weight: 500;
        }
        
        .filter-checkbox {
            display: flex;
            align-items: center;
            padding: 8px 0;
            cursor: pointer;
            font-size: 13px;
            color: #495057;
        }
        
        .filter-checkbox input {
            margin-right: 8px;
        }
        
        /* Main Area */
        .main-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
        }
        
        .timetable-header {
            padding: 20px 24px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .timetable-title {
            font-size: 20px;
            font-weight: 600;
            color: #212529;
            margin-bottom: 4px;
        }
        
        .timetable-subtitle {
            font-size: 14px;
            color: #6c757d;
        }
        
        .timetable-container {
            flex: 1;
            overflow: auto;
            padding: 24px;
        }
        
        /* Timetable Grid */
        .timetable-grid {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 13px;
        }
        
        .timetable-grid thead {
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .sticky-corner {
            position: sticky;
            left: 0;
            z-index: 20;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 12px;
            font-weight: 600;
            font-size: 12px;
            color: #495057;
            min-width: 100px;
        }
        
        .day-header {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 12px;
            font-weight: 600;
            font-size: 13px;
            color: #212529;
            text-align: center;
            min-width: 180px;
            width: 180px;
        }
        
        .time-cell {
            position: sticky;
            left: 0;
            z-index: 5;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 8px;
            font-size: 11px;
            color: #6c757d;
            text-align: center;
            min-width: 100px;
            font-weight: 500;
        }
        
        .timetable-grid td {
            border: 1px solid #dee2e6;
            vertical-align: top;
            min-height: 60px;
            min-width: 180px;
        }
        
        .empty-cell {
            background: #fafbfc;
        }
        
        .break-cell {
            background: #f8f9fa;
            border-style: dashed;
            border-color: #ced4da;
        }
        
        .lunch-cell {
            background: #fff9db;
            text-align: center;
            vertical-align: middle;
            font-weight: 500;
            color: #856404;
            border-color: #ffeaa7;
        }
        
        .class-cell {
            cursor: pointer;
            position: relative;
            transition: box-shadow 0.1s;
        }
        
        .class-cell:hover {
            box-shadow: inset 0 0 0 2px #004B87;
            z-index: 3;
        }
        
        .class-cell[data-type="lecture"] { border-left: 3px solid #004B87; }
        .class-cell[data-type="tutorial"] { border-left: 3px solid #6f42c1; }
        .class-cell[data-type="practical"] { border-left: 3px solid #198754; }
        
        .cell-content {
            padding: 10px;
        }
        
        .course-name {
            font-weight: 600;
            font-size: 13px;
            color: #212529;
            margin-bottom: 6px;
            line-height: 1.3;
        }
        
        .cell-detail {
            font-size: 11px;
            color: #6c757d;
            line-height: 1.4;
            margin-top: 2px;
        }
        
        /* Tooltip */
        #tooltip {
            position: fixed;
            background: rgba(33, 37, 41, 0.95);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
            max-width: 280px;
            display: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .tooltip-line {
            margin: 4px 0;
            line-height: 1.5;
        }
        
        .tooltip-line strong {
            color: #adb5bd;
            font-weight: 500;
        }
        
        /* Action Bar */
        .action-bar {
            padding: 16px 24px;
            border-top: 1px solid #dee2e6;
            background: #f8f9fa;
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        
        .btn {
            padding: 8px 16px;
            border: 1px solid #ced4da;
            background: white;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
            color: #495057;
            transition: all 0.15s;
        }
        
        .btn:hover {
            background: #e9ecef;
            border-color: #adb5bd;
        }
        
        .btn-primary {
            background: #004B87;
            color: white;
            border-color: #004B87;
        }
        
        .btn-primary:hover {
            background: #003A6B;
            border-color: #003A6B;
        }
        
        .loading-state {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }
        
        /* Modal for detailed view */
        .modal {
            display: none;
            position: fixed;
            z-index: 200;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: white;
            margin: 10% auto;
            padding: 32px;
            border-radius: 8px;
            width: 500px;
            max-width: 90%;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2);
        }
        
        .modal-header {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #212529;
        }
        
        .modal-row {
            padding: 12px 0;
            border-bottom: 1px solid #f1f3f5;
        }
        
        .modal-row:last-child {
            border-bottom: none;
        }
        
        .modal-label {
            font-size: 11px;
            text-transform: uppercase;
            color: #868e96;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
        }
        
        .modal-value {
            font-size: 14px;
            color: #212529;
            font-weight: 500;
        }
        
        .close {
            float: right;
            font-size: 28px;
            font-weight: bold;
            color: #adb5bd;
            cursor: pointer;
            line-height: 20px;
        }
        
        .close:hover {
            color: #212529;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="institute-name">IIIT Dharwad Timetable</div>
            <div class="view-selector">
                <button class="view-btn active" data-view="class">Class-wise</button>
                <button class="view-btn" data-view="faculty">Faculty-wise</button>
            </div>
        </div>
    </div>
    
    <div class="main-container">
        <div class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-title">Search</div>
                <input type="text" class="search-box" id="searchBox" placeholder="Search...">
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-title" id="sidebarTitle">Sections</div>
                <ul class="filter-list" id="filterList">
                    <li class="loading-state">Loading...</li>
                </ul>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-title">Show/Hide</div>
                <label class="filter-checkbox">
                    <input type="checkbox" checked data-filter-type="lecture"> Lectures
                </label>
                <label class="filter-checkbox">
                    <input type="checkbox" checked data-filter-type="tutorial"> Tutorials
                </label>
                <label class="filter-checkbox">
                    <input type="checkbox" checked data-filter-type="practical"> Practicals
                </label>
            </div>
        </div>
        
        <div class="main-area">
            <div class="timetable-header">
                <div class="timetable-title" id="timetableTitle">Select from sidebar</div>
                <div class="timetable-subtitle" id="timetableSubtitle">Choose a section or faculty to view their schedule</div>
            </div>
            
            <div class="timetable-container" id="timetableContainer">
                <div class="loading-state">No timetable selected</div>
            </div>
            
            <div class="action-bar">
                <button class="btn" onclick="downloadClassTT()">Download Class Timetables</button>
                <button class="btn" onclick="downloadFacultyTT()">Download Faculty Timetables</button>
                <button class="btn btn-primary" onclick="regenerate()">Regenerate</button>
            </div>
        </div>
    </div>
    
    <div id="tooltip"></div>
    
    <!-- Modal for detailed view -->
    <div id="detailModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <div class="modal-header" id="modalHeader">Class Details</div>
            <div id="modalBody"></div>
        </div>
    </div>
    
    <script>
        let currentView = 'class';
        let allData = [];
        let selectedId = null;
        
        // View switcher
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentView = this.dataset.view;
                loadData();
            });
        });
        
        // Load data for current view
        function loadData() {
            const endpoints = {
                'class': '/api/section-list',
                'faculty': '/api/faculty-list',
                'room': '/api/room-list'
            };
            
            const titles = {
                'class': 'Sections',
                'faculty': 'Faculty',
                'room': 'Rooms'
            };
            
            document.getElementById('sidebarTitle').textContent = titles[currentView];
            document.getElementById('filterList').innerHTML = '<li class="loading-state">Loading...</li>';
            
            fetch(endpoints[currentView])
                .then(r => r.json())
                .then(data => {
                    allData = data.sections || data.faculty || data.rooms || [];
                    renderList(allData);
                });
        }
        
        // Render list in sidebar
        function renderList(items) {
            const list = document.getElementById('filterList');
            if (items.length === 0) {
                list.innerHTML = '<li class="loading-state">No data available</li>';
                return;
            }
            
            list.innerHTML = items.map(item => 
                `<li class="filter-item" data-id="${item}">${item}</li>`
            ).join('');
            
            list.querySelectorAll('.filter-item').forEach(item => {
                item.addEventListener('click', function() {
                    document.querySelectorAll('.filter-item').forEach(i => i.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedId = this.dataset.id;
                    loadTimetable(selectedId);
                });
            });
        }
        
        // Load and display timetable
        function loadTimetable(id) {
            const endpoints = {
                'class': '/api/student-timetable?id=',
                'faculty': '/api/faculty-timetable?name=',
                'room': '/api/room-timetable?id='
            };
            
            document.getElementById('timetableTitle').textContent = id;
            document.getElementById('timetableSubtitle').textContent = 
                currentView === 'class' ? 'Class Schedule' : 
                currentView === 'faculty' ? 'Teaching Schedule' : 
                'Room Bookings';
            
            document.getElementById('timetableContainer').innerHTML = '<div class="loading-state">Loading...</div>';
            
            fetch(endpoints[currentView] + encodeURIComponent(id))
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('timetableContainer').innerHTML = data.html;
                        setupInteractivity();
                    } else {
                        document.getElementById('timetableContainer').innerHTML = 
                            '<div class="loading-state">Error: ' + data.error + '</div>';
                    }
                });
        }
        
        // Setup tooltips and modal
        function setupInteractivity() {
            const tooltip = document.getElementById('tooltip');
            const modal = document.getElementById('detailModal');
            const cells = document.querySelectorAll('.class-cell[data-tooltip]');
            
            cells.forEach(cell => {
                // Tooltip on hover
                cell.addEventListener('mouseenter', function(e) {
                    const parts = this.dataset.tooltip.split('|||');
                    tooltip.innerHTML = parts.map(p => `<div class="tooltip-line">${p}</div>`).join('');
                    tooltip.style.display = 'block';
                });
                
                cell.addEventListener('mousemove', function(e) {
                    tooltip.style.left = (e.pageX + 15) + 'px';
                    tooltip.style.top = (e.pageY + 15) + 'px';
                });
                
                cell.addEventListener('mouseleave', function() {
                    tooltip.style.display = 'none';
                });
                
                // Modal on click
                cell.addEventListener('click', function() {
                    const parts = this.dataset.tooltip.split('|||');
                    document.getElementById('modalHeader').textContent = parts[0];
                    document.getElementById('modalBody').innerHTML = parts.slice(1).map(p => {
                        const [label, value] = p.split(': ');
                        return `<div class="modal-row">
                            <div class="modal-label">${label}</div>
                            <div class="modal-value">${value || label}</div>
                        </div>`;
                    }).join('');
                    modal.style.display = 'block';
                });
            });
            
            // Apply filters
            applyFilters();
        }
        
        // Filter checkboxes
        document.querySelectorAll('[data-filter-type]').forEach(checkbox => {
            checkbox.addEventListener('change', applyFilters);
        });
        
        function applyFilters() {
            const filters = {};
            document.querySelectorAll('[data-filter-type]').forEach(cb => {
                filters[cb.dataset.filterType] = cb.checked;
            });
            
            document.querySelectorAll('.class-cell[data-type]').forEach(cell => {
                const type = cell.dataset.type;
                cell.style.display = filters[type] ? '' : 'none';
            });
        }
        
        // Search
        document.getElementById('searchBox').addEventListener('input', function() {
            const query = this.value.toLowerCase();
            const filtered = allData.filter(item => item.toLowerCase().includes(query));
            renderList(filtered);
        });
        
        // Modal close
        document.querySelector('.close').onclick = function() {
            document.getElementById('detailModal').style.display = 'none';
        }
        
        window.onclick = function(event) {
            const modal = document.getElementById('detailModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
        
        // Actions
        function downloadClassTT() {
            window.location.href = '/download-class-tt';
        }
        
        function downloadFacultyTT() {
            window.location.href = '/download-faculty-tt';
        }
        
        function regenerate() {
            if (confirm('Regenerate all timetables? This may take 30-60 seconds.')) {
                fetch('/generate')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            alert('Timetables regenerated successfully!');
                            location.reload();
                        } else {
                            alert('Error: ' + data.error);
                        }
                    });
            }
        }
        
        // Initialize
        loadData();
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    return MAIN_HTML

@app.route('/generate')
def generate():
    try:
        success = run_generation_pipeline()
        return jsonify({'success': success})
    except Exception as e:
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

@app.route('/api/room-list')
def api_room_list():
    if not g_is_generated:
        return jsonify({'rooms': []})
    return jsonify({'rooms': []})  # Room view not implemented

@app.route('/api/student-timetable')
def api_student_timetable():
    section_id = request.args.get('id')
    if not section_id:
        return jsonify({'success': False, 'error': 'No section ID provided'})
    
    section = next((s for s in g_all_sections if s.id == section_id), None)
    if not section:
        return jsonify({'success': False, 'error': f'Section not found'})
    
    html = _build_timetable_html(section.timetable, view_type='section')
    return jsonify({'success': True, 'html': html})

@app.route('/api/faculty-timetable')
def api_faculty_timetable():
    faculty_name = request.args.get('name')
    if not faculty_name:
        return jsonify({'success': False, 'error': 'No faculty name provided'})
    
    timetable = g_all_faculty_schedules.get(faculty_name)
    if not timetable:
        return jsonify({'success': False, 'error': f'Faculty not found'})
    
    html = _build_timetable_html(timetable, view_type='faculty')
    return jsonify({'success': True, 'html': html})

@app.route('/api/room-timetable')
def api_room_timetable():
    return jsonify({'success': False, 'error': 'Room view not implemented'})

@app.route('/download-class-tt')
def download_class_tt():
    if not g_is_generated:
        return "Please generate timetables first", 400
    try:
        exporter = ExcelExporter(g_all_sections, g_all_classrooms, g_all_faculty_schedules)
        buffer = io.BytesIO()
        exporter.export_department_timetables(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="Class_Timetables.xlsx",
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return str(e), 500

@app.route('/download-faculty-tt')
def download_faculty_tt():
    if not g_is_generated:
        return "Please generate timetables first", 400
    try:
        exporter = ExcelExporter(g_all_sections, g_all_classrooms, g_all_faculty_schedules)
        buffer = io.BytesIO()
        exporter.export_faculty_timetables(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="Faculty_Timetables.xlsx",
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    print("\n" + "="*70)
    print("IIIT Dharwad Timetable System".center(70))
    print("="*70)
    print("\nGenerating timetables...")
    
    success = run_generation_pipeline()
    if success:
        print("✓ Timetables generated successfully")
    else:
        print("✗ Generation failed")
    
    print("\nServer starting at: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, port=5000, use_reloader=False)