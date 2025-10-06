"""
Flask web interface for the timetable scheduler with live timetable display.
Install Flask: pip install flask
Run: python src/web_app.py
Visit: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, send_file
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from data_loader import DataLoader
from scheduler import Scheduler
import pandas as pd

app = Flask(__name__)

# Global variable to store timetable
current_timetable = None
current_loader = None

# HTML Template with embedded CSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Timetable Scheduler - Byte Me</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.2em;
        }
        
        .controls {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .button {
            background: #4CAF50;
            color: white;
            padding: 15px 40px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 18px;
            font-weight: bold;
            box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
            transition: all 0.3s;
            margin: 10px;
        }
        
        .button:hover {
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(76, 175, 80, 0.6);
        }
        
        .button.download {
            background: #2196F3;
        }
        
        .button.download:hover {
            background: #0b7dda;
        }
        
        .loading {
            display: none;
            color: white;
            font-size: 1.3em;
            text-align: center;
            padding: 20px;
        }
        
        .result-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin-bottom: 20px;
            display: none;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-box h3 {
            font-size: 2em;
            margin-bottom: 5px;
        }
        
        .stat-box p {
            opacity: 0.9;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .tab {
            padding: 12px 25px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .tab:hover {
            background: #e0e0e0;
        }
        
        .tab.active {
            background: #667eea;
            color: white;
        }
        
        .timetable-content {
            display: none;
        }
        
        .timetable-content.active {
            display: block;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .day-header {
            background: #f0f0f0;
            font-weight: bold;
            padding: 15px !important;
            color: #667eea;
            font-size: 1.1em;
        }
        
        .Monday { background-color: #E3F2FD !important; }
        .Tuesday { background-color: #F3E5F5 !important; }
        .Wednesday { background-color: #E8F5E9 !important; }
        .Thursday { background-color: #FFF3E0 !important; }
        .Friday { background-color: #FCE4EC !important; }
        
        .course-code {
            font-weight: bold;
            color: #667eea;
        }
        
        .error {
            background: #f44336;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            display: none;
        }
        
        @media (max-width: 768px) {
            table {
                font-size: 14px;
            }
            
            th, td {
                padding: 8px;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Automated Timetable Scheduler</h1>
            <p>Team: Byte Me | IIIT Dharwad</p>
        </div>
        
        <div class="controls">
            <button class="button" onclick="generateTimetable()">
                🔄 Generate Timetable
            </button>
            <button class="button download" onclick="downloadExcel()" style="display: none;"    id="downloadBtn">
                📥 Download Excel
            </button>
        </div>
        
        <div class="loading" id="loading">
            ⏳ Generating timetable... Please wait...
        </div>
        
        <div class="error" id="error"></div>
        
        <div class="result-card" id="result">
            <h2 style="color: #667eea; margin-bottom: 20px;">📊 Generation Statistics</h2>
            <div class="stats" id="stats"></div>
            
            <h2 style="color: #667eea; margin: 30px 0 20px 0;">📅 View Timetable</h2>
            <div class="tabs" id="tabs"></div>
            
            <div id="timetableContainer"></div>
        </div>
    </div>
    
    <script>
        let currentTimetable = null;
        
        function generateTimetable() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            
            fetch('/generate')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    
                    if (data.success) {
                        currentTimetable = data;
                        displayResults(data);
                        document.getElementById('downloadBtn').style.display = 'inline-block';
                    } else {
                        showError(data.error || 'Failed to generate timetable');
                    }
                })
                .catch(error => {
                    document.getElementById('loading').style.display = 'none';
                    showError('Error: ' + error.message);
                });
        }
        
        function displayResults(data) {
            // Display statistics
            const statsHTML = `
                <div class="stat-box">
                    <h3>${data.total_classes}</h3>
                    <p>Total Classes</p>
                </div>
                <div class="stat-box">
                    <h3>${data.total_faculty}</h3>
                    <p>Faculty Members</p>
                </div>
                <div class="stat-box">
                    <h3>${data.conflicts}</h3>
                    <p>Conflicts</p>
                </div>
                <div class="stat-box">
                    <h3>${data.student_groups.length}</h3>
                    <p>Student Groups</p>
                </div>
            `;
            document.getElementById('stats').innerHTML = statsHTML;
            
            // Create tabs
            let tabsHTML = '';
            data.student_groups.forEach((group, index) => {
                tabsHTML += `<button class="tab ${index === 0 ? 'active' : ''}" 
                             onclick="showTab('group-${index}')">${group}</button>`;
            });
            
            data.faculty.forEach((faculty, index) => {
                tabsHTML += `<button class="tab" 
                             onclick="showTab('faculty-${index}')">${faculty.name}</button>`;
            });
            
            document.getElementById('tabs').innerHTML = tabsHTML;
            
            // Create timetable content
            let contentHTML = '';
            
            // Student group timetables
            data.student_groups.forEach((group, index) => {
                contentHTML += `
                    <div class="timetable-content ${index === 0 ? 'active' : ''}" id="group-${index}">
                        <h3 style="margin-bottom: 15px;">Timetable for ${group}</h3>
                        ${createTimetableHTML(data.timetables.groups[group])}
                    </div>
                `;
            });
            
            // Faculty timetables
            data.faculty.forEach((faculty, index) => {
                contentHTML += `
                    <div class="timetable-content" id="faculty-${index}">
                        <h3 style="margin-bottom: 15px;">Timetable for ${faculty.name}</h3>
                        ${createTimetableHTML(data.timetables.faculty[faculty.id])}
                    </div>
                `;
            });
            
            document.getElementById('timetableContainer').innerHTML = contentHTML;
            document.getElementById('result').style.display = 'block';
        }
        
        function createTimetableHTML(schedule) {
            if (!schedule || schedule.length === 0) {
                return '<p>No classes scheduled</p>';
            }
            
            let html = '<table>';
            html += `
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Course</th>
                        <th>Title</th>
                        <th>Faculty</th>
                        <th>Room</th>
                        <th>Group</th>
                    </tr>
                </thead>
                <tbody>
            `;
            
            const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
            let currentDay = '';
            
            schedule.forEach(item => {
                if (item.day !== currentDay) {
                    currentDay = item.day;
                    html += `<tr class="${item.day}"><td colspan="6" class="day-header">${item.day}</td></tr>`;
                }
                
                html += `
                    <tr class="${item.day}">
                        <td>${item.time}</td>
                        <td class="course-code">${item.course_code}</td>
                        <td>${item.course_title}</td>
                        <td>${item.faculty}</td>
                        <td>${item.room}</td>
                        <td>${item.group}</td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            return html;
        }
        
        function showTab(tabId) {
            // Hide all content
            document.querySelectorAll('.timetable-content').forEach(el => {
                el.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(el => {
                el.classList.remove('active');
            });
            
            // Show selected content
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }
        
        function downloadExcel() {
            window.location.href = '/download';
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = '❌ ' + message;
            errorDiv.style.display = 'block';
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Home page with timetable display."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/generate')
def generate():
    """Generate timetable via API and return formatted data."""
    global current_timetable, current_loader
    
    try:
        # Load data
        loader = DataLoader(data_dir='data')
        loader.load_all_data()
        current_loader = loader
        
        if not loader.courses:
            return jsonify({
                'success': False,
                'error': 'No courses found. Please add courses to data/courses.csv'
            })
        
        # Generate timetable
        scheduler = Scheduler(
            courses=loader.courses,
            faculty_dict=loader.faculty,
            rooms=loader.rooms,
            slots=loader.slots
        )
        
        current_timetable = scheduler.generate_timetable()
        is_valid = scheduler.validate_timetable()
        
        # Prepare response data
        student_groups = sorted(set(course.student_group for course in loader.courses))
        faculty_list = [{'id': fid, 'name': f.name} for fid, f in loader.faculty.items()]
        
        # Organize timetable data
        timetables = {
            'groups': {},
            'faculty': {}
        }
        
        # Group timetables
        for group in student_groups:
            assignments = current_timetable.get_assignments_by_group(group)
            timetables['groups'][group] = format_assignments(assignments)
        
        # Faculty timetables
        for faculty_id, faculty in loader.faculty.items():
            assignments = current_timetable.get_assignments_by_faculty(faculty_id)
            timetables['faculty'][faculty_id] = format_assignments(assignments)
        
        return jsonify({
            'success': True,
            'total_classes': len(current_timetable.assignments),
            'total_faculty': len(loader.faculty),
            'conflicts': 0 if is_valid else 1,
            'student_groups': student_groups,
            'faculty': faculty_list,
            'timetables': timetables
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def format_assignments(assignments):
    """Format assignments for display."""
    formatted = []
    
    # Sort by day and time
    days_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
    assignments_sorted = sorted(assignments, key=lambda a: (days_order.get(a.slot.day, 5), a.slot.start_time))
    
    for assignment in assignments_sorted:
        formatted.append({
            'day': assignment.slot.day,
            'time': f"{assignment.slot.start_time}-{assignment.slot.end_time}",
            'course_code': assignment.course.code,
            'course_title': assignment.course.title,
            'faculty': assignment.faculty.name,
            'room': assignment.room.room_id,
            'group': assignment.student_group
        })
    
    return formatted


@app.route('/download')
def download():
    """Download timetable as Excel file."""
    global current_timetable
    
    if not current_timetable:
        return "No timetable generated yet", 400
    
    # Create Excel file
    import pandas as pd
    
    os.makedirs('output', exist_ok=True)
    filename = 'output/timetable.xlsx'
    
    data = []
    for assignment in current_timetable.assignments:
        data.append({
            'Day': assignment.slot.day,
            'Time': f"{assignment.slot.start_time}-{assignment.slot.end_time}",
            'Course Code': assignment.course.code,
            'Course Title': assignment.course.title,
            'Faculty': assignment.faculty.name,
            'Room': assignment.room.room_id,
            'Student Group': assignment.student_group
        })
    
    df = pd.DataFrame(data)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    df['Day'] = pd.Categorical(df['Day'], categories=day_order, ordered=True)
    df = df.sort_values(['Day', 'Time'])
    df.to_excel(filename, index=False)
    
    return send_file(filename, as_attachment=True, download_name='timetable.xlsx')


if __name__ == '__main__':
    print("=" * 70)
    print("🌐 Starting Timetable Scheduler Web Interface".center(70))
    print("=" * 70)
    print("\n📍 Open your browser and visit: http://localhost:5000")
    print("⚡ Press Ctrl+C to stop the server\n")
    print("=" * 70)
    app.run(debug=True, port=5000)