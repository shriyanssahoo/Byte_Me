"""
Flask web interface for IIIT Dharwad Timetable System
Enhanced with IIIT Dharwad branding and dark mode support

Run: python web_app2_enhanced.py
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
    """Generate subtle color variations for different courses"""
    course_codes: Set[str] = set()
    for section in sections:
        for day_schedule in section.timetable.grid:
            for slot in day_schedule:
                if slot and slot.course.course_code not in ["LUNCH", "BREAK"]:
                    if slot.course.parent_pseudo_name:
                        course_codes.add(slot.course.parent_pseudo_name)
                    else:
                        course_codes.add(slot.course.course_code)
    
    # Professional color palette matching IIIT Dharwad theme
    light_colors = [
        'E3F2FD',  # Light Blue (primary)
        'F3E5F5',  # Light Purple
        'E8F5E9',  # Light Green
        'FFF3E0',  # Light Orange
        'FCE4EC',  # Light Pink
        'E0F2F1',  # Light Teal
        'FFF8E1',  # Light Amber
        'E8EAF6',  # Light Indigo
        'F1F8E9',  # Light Lime
        'FBE9E7',  # Light Deep Orange
        'EDE7F6',  # Light Deep Purple
        'E0F7FA',  # Light Cyan
        'FFFDE7',  # Light Yellow
        'EFEBE9',  # Light Brown
        'ECEFF1',  # Light Blue Grey
    ]
    
    # Dark mode variants
    dark_colors = [
        '1E3A5F',  # Dark Blue
        '4A148C',  # Dark Purple
        '1B5E20',  # Dark Green
        'E65100',  # Dark Orange
        '880E4F',  # Dark Pink
        '004D40',  # Dark Teal
        'FF6F00',  # Dark Amber
        '1A237E',  # Dark Indigo
        '33691E',  # Dark Lime
        'BF360C',  # Dark Deep Orange
        '311B92',  # Dark Deep Purple
        '006064',  # Dark Cyan
        'F57F17',  # Dark Yellow
        '3E2723',  # Dark Brown
        '263238',  # Dark Blue Grey
    ]
    
    color_map = {}
    for i, code in enumerate(sorted(course_codes)):
        idx = i % len(light_colors)
        color_map[code] = {
            'light': light_colors[idx],
            'dark': dark_colors[idx]
        }
    
    color_map["LUNCH"] = {'light': 'FFF9C4', 'dark': '827717'}
    color_map["BREAK"] = {'light': 'FAFAFA', 'dark': '424242'}
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
    
    for day_name in utils.DAYS:
        html += f'<th class="day-header">{day_name}</th>'
    html += '</tr></thead><tbody>'
    
    time_slots = utils.get_time_slots_list()
    rendered = set()
    
    for slot_idx, time_str in enumerate(time_slots):
        html += f'<tr><td class="time-cell">{time_str}</td>'
        
        for day_idx in range(len(utils.DAYS)):
            if (day_idx, slot_idx) in rendered:
                continue
            
            s_class = timetable.grid[day_idx][slot_idx]
            
            if not s_class:
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] is None):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                html += f'<td class="empty-cell" rowspan="{rowspan}"></td>'
            
            elif s_class.course.course_code == "LUNCH":
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] == s_class):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                html += f'<td class="lunch-cell" rowspan="{rowspan}"><div class="cell-content"><span class="lunch-icon">🍽️</span> Lunch Break</div></td>'
            
            elif s_class.course.course_code == "BREAK":
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] == s_class):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                html += f'<td class="break-cell" rowspan="{rowspan}"></td>'
            
            else:
                rowspan = 1
                while (slot_idx + rowspan < utils.TOTAL_SLOTS_PER_DAY and 
                       timetable.grid[day_idx][slot_idx + rowspan] == s_class):
                    rendered.add((day_idx, slot_idx + rowspan))
                    rowspan += 1
                
                course_name = s_class.course.parent_pseudo_name or s_class.course.course_name
                session_type = s_class.session_type.lower()
                
                color_key = s_class.course.parent_pseudo_name if s_class.course.parent_pseudo_name else s_class.course.course_code
                colors = g_course_color_map.get(color_key, {'light': 'E3F2FD', 'dark': '1E3A5F'})
                
                # Session type icons
                session_icons = {
                    'lecture': '📖',
                    'tutorial': '✏️',
                    'practical': '🔬'
                }
                icon = session_icons.get(session_type, '📚')
                
                if view_type == 'section':
                    instructors = ", ".join(s_class.instructors) if s_class.instructors else "TBD"
                    rooms = ", ".join(s_class.room_ids) if s_class.room_ids else "TBD"
                    detail_html = f'<div class="cell-detail"><span class="detail-icon">👨‍🏫</span> {instructors}</div><div class="cell-detail"><span class="detail-icon">🏫</span> {rooms}</div>'
                    tooltip_info = f"{course_name}|||{icon} {session_type.capitalize()}|||👨‍🏫 Instructor: {instructors}|||🏫 Room: {rooms}"
                else:
                    section = s_class.section_id
                    rooms = ", ".join(s_class.room_ids) if s_class.room_ids else "TBD"
                    detail_html = f'<div class="cell-detail"><span class="detail-icon">👥</span> {section}</div><div class="cell-detail"><span class="detail-icon">🏫</span> {rooms}</div>'
                    tooltip_info = f"{course_name}|||{icon} {session_type.capitalize()}|||👥 Section: {section}|||🏫 Room: {rooms}"
                
                html += f'<td class="class-cell" rowspan="{rowspan}" '
                html += f'data-type="{session_type}" data-light-color="{colors["light"]}" data-dark-color="{colors["dark"]}" '
                html += f'data-tooltip="{tooltip_info}">'
                html += f'<div class="cell-content">'
                html += f'<div class="session-badge"><span class="badge-icon">{icon}</span> {session_type.capitalize()}</div>'
                html += f'<div class="course-name">{course_name}</div>'
                html += detail_html
                html += '</div></td>'
        
        html += '</tr>'
    
    html += '</tbody></table>'
    return html

# HTML and CSS with IIIT Dharwad theme and dark mode
MAIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IIIT Dharwad Timetable System</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎓</text></svg>">
    <style>
        :root {
            /* IIIT Dharwad Brand Colors - Light Mode */
            --primary-color: #1976D2;
            --primary-dark: #0D47A1;
            --primary-light: #BBDEFB;
            --accent-color: #FF6F00;
            --accent-light: #FFE0B2;
            
            /* Light Mode Colors */
            --bg-primary: #FAFAFA;
            --bg-secondary: #FFFFFF;
            --bg-tertiary: #F5F5F5;
            --text-primary: #212121;
            --text-secondary: #757575;
            --text-tertiary: #9E9E9E;
            --border-color: #E0E0E0;
            --border-hover: #BDBDBD;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.12);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 25px rgba(0,0,0,0.15);
            
            /* Table Colors */
            --table-header: #E3F2FD;
            --table-border: #BDBDBD;
            --empty-cell: #FAFAFA;
            --break-cell: #F5F5F5;
            --lunch-bg: #FFF9C4;
            --lunch-text: #F57F17;
            
            /* Session Type Colors */
            --lecture-accent: #1976D2;
            --tutorial-accent: #7B1FA2;
            --practical-accent: #388E3C;
        }
        
        [data-theme="dark"] {
            /* Dark Mode Colors */
            --bg-primary: #121212;
            --bg-secondary: #1E1E1E;
            --bg-tertiary: #2C2C2C;
            --text-primary: #E0E0E0;
            --text-secondary: #B0B0B0;
            --text-tertiary: #808080;
            --border-color: #3A3A3A;
            --border-hover: #505050;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
            --shadow-lg: 0 10px 25px rgba(0,0,0,0.5);
            
            /* Dark Table Colors */
            --table-header: #1E3A5F;
            --table-border: #3A3A3A;
            --empty-cell: #1A1A1A;
            --break-cell: #242424;
            --lunch-bg: #4A4A2E;
            --lunch-text: #FFD54F;
            
            /* Dark Session Colors */
            --lecture-accent: #42A5F5;
            --tutorial-accent: #AB47BC;
            --practical-accent: #66BB6A;
        }
        
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        
        /* Header with IIIT Branding */
        .header {
            background: var(--bg-secondary);
            border-bottom: 3px solid var(--primary-color);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: var(--shadow-md);
            transition: all 0.3s ease;
        }
        
        .header-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
        }
        
        .brand-section {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .logo {
            font-size: 32px;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        }
        
        .institute-info {
            display: flex;
            flex-direction: column;
        }
        
        .institute-name {
            font-size: 20px;
            font-weight: 700;
            color: var(--primary-color);
            letter-spacing: -0.5px;
        }
        
        .system-subtitle {
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .header-controls {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .view-selector {
            display: flex;
            gap: 0;
            border: 2px solid var(--primary-color);
            border-radius: 6px;
            overflow: hidden;
            background: var(--bg-secondary);
        }
        
        .view-btn {
            padding: 10px 24px;
            border: none;
            background: var(--bg-secondary);
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
            border-right: 1px solid var(--primary-light);
            transition: all 0.2s;
        }
        
        .view-btn:last-child { border-right: none; }
        .view-btn:hover { background: var(--primary-light); }
        .view-btn.active {
            background: var(--primary-color);
            color: white;
        }
        
        /* Theme Toggle Button */
        .theme-toggle {
            background: var(--bg-tertiary);
            border: 2px solid var(--border-color);
            border-radius: 50%;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 20px;
            transition: all 0.3s;
        }
        
        .theme-toggle:hover {
            background: var(--primary-light);
            border-color: var(--primary-color);
            transform: rotate(180deg);
        }
        
        /* Main Layout */
        .main-container {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            height: calc(100vh - 85px);
        }
        
        /* Enhanced Sidebar */
        .sidebar {
            width: 300px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            overflow-y: auto;
            flex-shrink: 0;
            box-shadow: var(--shadow-sm);
        }
        
        .sidebar-section {
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .sidebar-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--primary-color);
            margin-bottom: 16px;
            letter-spacing: 1px;
        }
        
        .search-box {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            background: var(--bg-primary);
            color: var(--text-primary);
            transition: all 0.2s;
        }
        
        .search-box:focus { 
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
        }
        
        .filter-list {
            list-style: none;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .filter-item {
            padding: 12px 16px;
            margin: 4px 0;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            color: var(--text-primary);
            transition: all 0.2s;
            border: 2px solid transparent;
        }
        
        .filter-item:hover { 
            background: var(--bg-tertiary);
            border-color: var(--border-hover);
        }
        
        .filter-item.selected {
            background: var(--primary-light);
            color: var(--primary-dark);
            font-weight: 600;
            border-color: var(--primary-color);
        }
        
        .filter-checkbox {
            display: flex;
            align-items: center;
            padding: 10px 0;
            cursor: pointer;
            font-size: 14px;
            color: var(--text-primary);
            transition: color 0.2s;
        }
        
        .filter-checkbox:hover {
            color: var(--primary-color);
        }
        
        .filter-checkbox input {
            margin-right: 12px;
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: var(--primary-color);
        }
        
        /* Main Area */
        .main-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-secondary);
        }
        
        .timetable-header {
            padding: 24px 28px;
            border-bottom: 2px solid var(--border-color);
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
        }
        
        .timetable-title {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 6px;
        }
        
        .timetable-subtitle {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .timetable-container {
            flex: 1;
            overflow: auto;
            padding: 28px;
            background: var(--bg-primary);
        }
        
        /* Enhanced Timetable Grid */
        .timetable-grid {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 13px;
            box-shadow: var(--shadow-lg);
            border-radius: 12px;
            overflow: hidden;
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
            background: var(--table-header);
            border: 1px solid var(--table-border);
            padding: 14px;
            font-weight: 700;
            font-size: 13px;
            color: var(--primary-dark);
            min-width: 110px;
        }
        
        .day-header {
            background: var(--table-header);
            border: 1px solid var(--table-border);
            padding: 14px;
            font-weight: 700;
            font-size: 14px;
            color: var(--primary-dark);
            text-align: center;
            min-width: 200px;
            width: 200px;
        }
        
        .time-cell {
            position: sticky;
            left: 0;
            z-index: 5;
            background: var(--table-header);
            border: 1px solid var(--table-border);
            padding: 10px;
            font-size: 11px;
            color: var(--text-secondary);
            text-align: center;
            min-width: 110px;
            font-weight: 600;
        }
        
        .timetable-grid td {
            border: 1px solid var(--table-border);
            vertical-align: top;
            min-height: 70px;
            min-width: 200px;
        }
        
        .empty-cell {
            background: var(--empty-cell);
        }
        
        .break-cell {
            background: var(--break-cell);
            border-style: dashed;
            border-color: var(--border-hover);
        }
        
        .lunch-cell {
            background: var(--lunch-bg);
            text-align: center;
            vertical-align: middle;
            font-weight: 600;
            color: var(--lunch-text);
            font-size: 14px;
        }
        
        .lunch-icon {
            font-size: 20px;
            margin-right: 6px;
        }
        
        .class-cell {
            cursor: pointer;
            position: relative;
            transition: all 0.2s;
        }
        
        .class-cell:hover {
            box-shadow: inset 0 0 0 3px var(--primary-color);
            z-index: 3;
            transform: scale(1.02);
        }
        
        .class-cell[data-type="lecture"] { border-left: 4px solid var(--lecture-accent); }
        .class-cell[data-type="tutorial"] { border-left: 4px solid var(--tutorial-accent); }
        .class-cell[data-type="practical"] { border-left: 4px solid var(--practical-accent); }
        
        .cell-content {
            padding: 12px;
        }
        
        .session-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .class-cell[data-type="lecture"] .session-badge {
            background: rgba(25, 118, 210, 0.15);
            color: var(--lecture-accent);
        }
        
        .class-cell[data-type="tutorial"] .session-badge {
            background: rgba(123, 31, 162, 0.15);
            color: var(--tutorial-accent);
        }
        
        .class-cell[data-type="practical"] .session-badge {
            background: rgba(56, 142, 60, 0.15);
            color: var(--practical-accent);
        }
        
        .badge-icon {
            font-size: 13px;
            margin-right: 4px;
        }
        
        .course-name {
            font-weight: 700;
            font-size: 14px;
            color: var(--text-primary);
            margin-bottom: 8px;
            line-height: 1.4;
        }
        
        .cell-detail {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin-top: 4px;
            display: flex;
            align-items: center;
        }
        
        .detail-icon {
            margin-right: 6px;
            font-size: 13px;
        }
        
        /* Tooltip */
        #tooltip {
            position: fixed;
            background: rgba(33, 37, 41, 0.97);
            color: white;
            padding: 16px 20px;
            border-radius: 10px;
            font-size: 13px;
            pointer-events: none;
            z-index: 1000;
            max-width: 320px;
            display: none;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            border: 2px solid var(--primary-color);
        }
        
        .tooltip-line {
            margin: 6px 0;
            line-height: 1.6;
        }
        
        /* Action Bar */
        .action-bar {
            padding: 20px 28px;
            border-top: 2px solid var(--border-color);
            background: var(--bg-tertiary);
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        
        .btn {
            padding: 12px 24px;
            border: 2px solid var(--border-color);
            background: var(--bg-secondary);
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            color: var(--text-primary);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn:hover {
            background: var(--bg-tertiary);
            border-color: var(--primary-color);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .btn-primary {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }
        
        .btn-primary:hover {
            background: var(--primary-dark);
            border-color: var(--primary-dark);
        }
        
        .loading-state {
            text-align: center;
            padding: 80px 20px;
            color: var(--text-secondary);
            font-size: 16px;
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 200;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.6);
            backdrop-filter: blur(4px);
        }
        
        .modal-content {
            background-color: var(--bg-secondary);
            margin: 8% auto;
            padding: 36px;
            border-radius: 16px;
            width: 560px;
            max-width: 90%;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 2px solid var(--primary-color);
        }
        
        .modal-header {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 24px;
            color: var(--primary-color);
        }
        
        .modal-row {
            padding: 14px 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .modal-row:last-child {
            border-bottom: none;
        }
        
        .modal-label {
            font-size: 11px;
            text-transform: uppercase;
            color: var(--text-tertiary);
            margin-bottom: 6px;
            letter-spacing: 0.8px;
            font-weight: 600;
        }
        
        .modal-value {
            font-size: 15px;
            color: var(--text-primary);
            font-weight: 600;
        }
        
        .close {
            float: right;
            font-size: 32px;
            font-weight: bold;
            color: var(--text-tertiary);
            cursor: pointer;
            line-height: 20px;
            transition: color 0.2s;
        }
        
        .close:hover {
            color: var(--accent-color);
        }
        
        /* Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-tertiary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-hover);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-color);
        }
    </style>
</head>
<body data-theme="light">
    <div class="header">
        <div class="header-content">
            <div class="brand-section">
                <div class="logo">🎓</div>
                <div class="institute-info">
                    <div class="institute-name">IIIT Dharwad</div>
                    <div class="system-subtitle">Automated Timetable System</div>
                </div>
            </div>
            <div class="header-controls">
                <div class="view-selector">
                    <button class="view-btn active" data-view="class">📚 Class-wise</button>
                    <button class="view-btn" data-view="faculty">👨‍🏫 Faculty-wise</button>
                </div>
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle Dark Mode">
                    <span class="theme-icon">🌙</span>
                </button>
            </div>
        </div>
    </div>
    
    <div class="main-container">
        <div class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-title">🔍 Search</div>
                <input type="text" class="search-box" id="searchBox" placeholder="Search...">
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-title" id="sidebarTitle">📋 Sections</div>
                <ul class="filter-list" id="filterList">
                    <li class="loading-state">Loading...</li>
                </ul>
            </div>
            
            <div class="sidebar-section">
                <div class="sidebar-title">👁️ Show/Hide</div>
                <label class="filter-checkbox">
                    <input type="checkbox" checked data-filter-type="lecture"> 📖 Lectures
                </label>
                <label class="filter-checkbox">
                    <input type="checkbox" checked data-filter-type="tutorial"> ✏️ Tutorials
                </label>
                <label class="filter-checkbox">
                    <input type="checkbox" checked data-filter-type="practical"> 🔬 Practicals
                </label>
            </div>
        </div>
        
        <div class="main-area">
            <div class="timetable-header">
                <div class="timetable-title" id="timetableTitle">Select from sidebar</div>
                <div class="timetable-subtitle" id="timetableSubtitle">Choose a section or faculty to view their schedule</div>
            </div>
            
            <div class="timetable-container" id="timetableContainer">
                <div class="loading-state">📅 No timetable selected</div>
            </div>
            
            <div class="action-bar">
                <button class="btn" onclick="downloadClassTT()">
                    <span>📥</span> Download Class Timetables
                </button>
                <button class="btn" onclick="downloadFacultyTT()">
                    <span>📥</span> Download Faculty Timetables
                </button>
                <button class="btn btn-primary" onclick="regenerate()">
                    <span>🔄</span> Regenerate
                </button>
            </div>
        </div>
    </div>
    
    <div id="tooltip"></div>
    
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
        
        // Theme Management
        function toggleTheme() {
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            body.setAttribute('data-theme', newTheme);
            
            const themeIcon = document.querySelector('.theme-icon');
            themeIcon.textContent = newTheme === 'light' ? '🌙' : '☀️';
            
            localStorage.setItem('theme', newTheme);
            updateCellColors();
        }
        
        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);
        document.querySelector('.theme-icon').textContent = savedTheme === 'light' ? '🌙' : '☀️';
        
        // Update cell colors based on theme
        function updateCellColors() {
            const theme = document.body.getAttribute('data-theme');
            document.querySelectorAll('.class-cell').forEach(cell => {
                const lightColor = cell.getAttribute('data-light-color');
                const darkColor = cell.getAttribute('data-dark-color');
                cell.style.backgroundColor = theme === 'light' ? '#' + lightColor : '#' + darkColor;
            });
        }
        
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
                'faculty': '/api/faculty-list'
            };
            
            const titles = {
                'class': '📋 Sections',
                'faculty': '👨‍🏫 Faculty'
            };
            
            document.getElementById('sidebarTitle').textContent = titles[currentView];
            document.getElementById('filterList').innerHTML = '<li class="loading-state">Loading...</li>';
            
            fetch(endpoints[currentView])
                .then(r => r.json())
                .then(data => {
                    allData = data.sections || data.faculty || [];
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
                'faculty': '/api/faculty-timetable?name='
            };
            
            document.getElementById('timetableTitle').textContent = id;
            document.getElementById('timetableSubtitle').textContent = 
                currentView === 'class' ? 'Class Schedule' : 'Teaching Schedule';
            
            document.getElementById('timetableContainer').innerHTML = '<div class="loading-state">Loading...</div>';
            
            fetch(endpoints[currentView] + encodeURIComponent(id))
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('timetableContainer').innerHTML = data.html;
                        updateCellColors();
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
                            alert('✅ Timetables regenerated successfully!');
                            location.reload();
                        } else {
                            alert('❌ Error: ' + data.error);
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

# Routes (same as before)
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
    print("IIIT Dharwad Timetable System - Enhanced Edition".center(70))
    print("="*70)
    print("\n🎨 Features:")
    print("  • IIIT Dharwad branded theme")
    print("  • Dark mode support")
    print("  • Enhanced visual design")
    print("  • Session type badges with icons")
    print("\nGenerating timetables...")
    
    success = run_generation_pipeline()
    if success:
        print("✓ Timetables generated successfully")
    else:
        print("✗ Generation failed")
    
    print("\n🌐 Server starting at: http://localhost:5000")
    print("🌙 Click the moon icon to toggle dark mode")
    print("⌨️  Press Ctrl+C to stop\n")
    
    app.run(debug=True, port=5000, use_reloader=False)