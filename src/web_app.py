"""
Flask web interface with role-based access for Students, Faculty, and Admin.
Run: python src/web_app.py
Visit: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, send_file, request, session, redirect, url_for
import sys
import os
import secrets

sys.path.insert(0, os.path.dirname(__file__))

from data_loader import DataLoader
from scheduler import Scheduler
import pandas as pd

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global variables
current_timetable = None
current_loader = None

def initialize_timetable():
    """Load and generate timetable on startup."""
    global current_timetable, current_loader
    
    print("\n📊 Initializing timetable system...")
    
    try:
        # Load data
        loader = DataLoader(data_dir='data')
        loader.load_all_data()
        current_loader = loader
        
        if not loader.courses:
            print("⚠️  No courses found - timetable not generated")
            return False
        
        # Generate timetable
        print("🔄 Generating timetable...")
        scheduler = Scheduler(
            courses=loader.courses,
            faculty_dict=loader.faculty,
            rooms=loader.rooms,
            slots=loader.slots
        )
        
        current_timetable = scheduler.generate_timetable()
        is_valid = scheduler.validate_timetable()
        
        if is_valid:
            print(f"✅ Timetable generated successfully!")
            print(f"   Total classes: {len(current_timetable.assignments)}")
            return True
        else:
            print("⚠️  Timetable has conflicts")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing timetable: {e}")
        return False

# HTML Templates
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Timetable System - Login</title>
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
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            width: 100%;
        }
        
        .header {
            background: white;
            padding: 40px;
            border-radius: 15px 15px 0 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            text-align: center;
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
        
        .login-options {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
            padding: 40px;
            background: white;
            border-radius: 0 0 15px 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .login-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 30px;
            border-radius: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .login-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.4);
        }
        
        .login-card.student {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        .login-card.faculty {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        
        .login-card.admin {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }
        
        .login-card .icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        .login-card h2 {
            color: white;
            font-size: 1.8em;
            margin-bottom: 15px;
        }
        
        .login-card p {
            color: rgba(255,255,255,0.9);
            font-size: 1em;
        }
        
        @media (max-width: 768px) {
            .login-options {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Timetable Management System</h1>
            <p>Team: Byte Me | IIIT Dharwad</p>
        </div>
        
        <div class="login-options">
            <div class="login-card student" onclick="location.href='/student'">
                <div class="icon">👨‍🎓</div>
                <h2>Student</h2>
                <p>View your class schedule</p>
            </div>
            
            <div class="login-card faculty" onclick="location.href='/faculty'">
                <div class="icon">👨‍🏫</div>
                <h2>Faculty</h2>
                <p>View your teaching schedule</p>
            </div>
            
            <div class="login-card admin" onclick="location.href='/admin'">
                <div class="icon">👨‍💼</div>
                <h2>Admin</h2>
                <p>Manage timetables & data</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

STUDENT_SELECT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Student Login - Select Section</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 50px auto; }
        .card {
            background: white;
            padding: 50px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            text-align: center;
        }
        h1 { color: #4facfe; font-size: 2.5em; margin-bottom: 20px; }
        p { color: #666; font-size: 1.2em; margin-bottom: 40px; }
        .section-options { display: flex; gap: 30px; justify-content: center; }
        .section-btn {
            flex: 1;
            padding: 40px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 15px;
            font-size: 1.5em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4);
        }
        .section-btn:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(79, 172, 254, 0.6);
        }
        .back-btn {
            margin-top: 30px;
            padding: 15px 30px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
        }
        .back-btn:hover { background: #e0e0e0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>👨‍🎓 Student Portal</h1>
            <p>Select your section to view timetable</p>
            
            <div class="section-options">
                <button class="section-btn" onclick="viewTimetable('3rdSem-A')">
                    Section A
                </button>
                <button class="section-btn" onclick="viewTimetable('3rdSem-B')">
                    Section B
                </button>
            </div>
            
            <button class="back-btn" onclick="location.href='/'">← Back to Home</button>
        </div>
    </div>
    
    <script>
        function viewTimetable(section) {
            window.location.href = '/student/timetable?section=' + section;
        }
    </script>
</body>
</html>
"""

FACULTY_SELECT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Faculty Login - Select Name</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 50px auto; }
        .card {
            background: white;
            padding: 50px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 { color: #43e97b; font-size: 2.5em; margin-bottom: 20px; text-align: center; }
        p { color: #666; font-size: 1.2em; margin-bottom: 30px; text-align: center; }
        .faculty-list { max-height: 400px; overflow-y: auto; }
        .faculty-item {
            padding: 20px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }
        .faculty-item:hover {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            color: white;
            transform: translateX(10px);
        }
        .faculty-name { font-size: 1.2em; font-weight: bold; }
        .faculty-id { font-size: 0.9em; opacity: 0.7; }
        .back-btn {
            margin-top: 30px;
            padding: 15px 30px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            width: 100%;
        }
        .back-btn:hover { background: #e0e0e0; }
        .loading { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>👨‍🏫 Faculty Portal</h1>
            <p>Select your name to view timetable</p>
            
            <div class="faculty-list" id="facultyList">
                <div class="loading">Loading faculty list...</div>
            </div>
            
            <button class="back-btn" onclick="location.href='/'">← Back to Home</button>
        </div>
    </div>
    
    <script>
        fetch('/api/faculty-list')
            .then(response => response.json())
            .then(data => {
                const list = document.getElementById('facultyList');
                if (data.faculty && data.faculty.length > 0) {
                    list.innerHTML = data.faculty.map(f => `
                        <div class="faculty-item" onclick="viewTimetable('${f.id}')">
                            <div class="faculty-name">${f.name}</div>
                            <div class="faculty-id">${f.id}</div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="loading">No faculty found</div>';
                }
            });
        
        function viewTimetable(facultyId) {
            window.location.href = '/faculty/timetable?id=' + facultyId;
        }
    </script>
</body>
</html>
"""

TIMETABLE_VIEW_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: {{ bg_color }};
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 { color: #667eea; font-size: 2em; margin-bottom: 10px; }
        .back-btn {
            margin-top: 15px;
            padding: 10px 25px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
        }
        .back-btn:hover { background: #5568d3; }
        .timetable-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
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
        tr:hover { background: #f8f9fa; }
        .day-header {
            background: #f0f0f0;
            font-weight: bold;
            padding: 15px !important;
            color: #667eea;
            font-size: 1.1em;
        }
        .course-code { font-weight: bold; color: #667eea; }
        .empty-msg {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ header }}</h1>
            <p>{{ subheader }}</p>
            <button class="back-btn" onclick="location.href='{{ back_url }}'">← Back</button>
        </div>
        
        <div class="timetable-content" id="content">
            <div class="empty-msg">Loading timetable...</div>
        </div>
    </div>
    
    <script>
        fetch('{{ api_url }}')
            .then(response => response.json())
            .then(data => {
                const content = document.getElementById('content');
                if (data.success && data.timetable) {
                    content.innerHTML = data.timetable;
                } else {
                    content.innerHTML = '<div class="empty-msg">No timetable generated yet. Please generate timetable first.</div>';
                }
            })
            .catch(error => {
                document.getElementById('content').innerHTML = 
                    '<div class="empty-msg">Error loading timetable. Please try again.</div>';
            });
    </script>
</body>
</html>
"""

ADMIN_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 { color: #fa709a; font-size: 2.5em; margin-bottom: 10px; }
        .actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 20px;
        }
        .action-btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            transition: all 0.3s;
        }
        .action-btn:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(250, 112, 154, 0.4); }
        .action-btn.secondary { background: #667eea; }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #fa709a;
            font-size: 1.5em;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #fee140;
        }
        .stats { display: flex; justify-content: space-around; margin: 20px 0; }
        .stat-box {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #fa709a; }
        .stat-label { color: #666; font-size: 0.9em; margin-top: 5px; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th {
            background: #fa709a;
            color: white;
            padding: 12px;
            text-align: left;
            font-size: 0.9em;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 0.9em;
        }
        tr:hover { background: #fff5f7; }
        .loading { text-align: center; padding: 40px; color: #999; }
        .back-btn {
            padding: 10px 25px;
            background: #f0f0f0;
            color: #333;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
        }
        .back-btn:hover { background: #e0e0e0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👨‍💼 Admin Dashboard</h1>
            <p>Complete system overview and management</p>
            
            <div class="actions">
                <button class="action-btn" onclick="generateTimetable()">🔄 Generate Class Timetable</button>
                <button class="action-btn" onclick="generateExams()">📝 Generate Exam Timetable</button>
                <button class="action-btn secondary" onclick="location.href='/download'">📥 Download Timetable</button>
                <button class="back-btn" onclick="location.href='/'">← Back to Home</button>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <!-- Statistics Card -->
            <div class="card">
                <h2>📊 System Statistics</h2>
                <div class="stats" id="stats">
                    <div class="stat-box">
                        <div class="stat-number">--</div>
                        <div class="stat-label">Courses</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">--</div>
                        <div class="stat-label">Faculty</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">--</div>
                        <div class="stat-label">Rooms</div>
                    </div>
                </div>
            </div>
            
            <!-- Courses Card -->
            <div class="card">
                <h2>📚 Courses</h2>
                <div id="courses" class="loading">Loading...</div>
            </div>
            
            <!-- Faculty Card -->
            <div class="card">
                <h2>👨‍🏫 Faculty Members</h2>
                <div id="faculty" class="loading">Loading...</div>
            </div>
            
            <!-- Rooms Card -->
            <div class="card">
                <h2>🏫 Classrooms & Labs</h2>
                <div id="rooms" class="loading">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        // Load admin data
        fetch('/api/admin-data')
            .then(response => response.json())
            .then(data => {
                // Update stats
                document.querySelector('.stats').innerHTML = `
                    <div class="stat-box">
                        <div class="stat-number">${data.courses_count}</div>
                        <div class="stat-label">Courses</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${data.faculty_count}</div>
                        <div class="stat-label">Faculty</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${data.rooms_count}</div>
                        <div class="stat-label">Rooms</div>
                    </div>
                `;
                
                // Update courses
                if (data.courses && data.courses.length > 0) {
                    document.getElementById('courses').innerHTML = `
                        <table>
                            <tr><th>Code</th><th>Title</th><th>Faculty</th><th>Group</th></tr>
                            ${data.courses.slice(0, 8).map(c => `
                                <tr>
                                    <td>${c.code}</td>
                                    <td>${c.title}</td>
                                    <td>${c.faculty_id}</td>
                                    <td>${c.student_group}</td>
                                </tr>
                            `).join('')}
                        </table>
                        ${data.courses.length > 8 ? `<p style="text-align:center;margin-top:10px;color:#999;">...and ${data.courses.length - 8} more</p>` : ''}
                    `;
                } else {
                    document.getElementById('courses').innerHTML = '<p class="loading">No courses found</p>';
                }
                
                // Update faculty
                if (data.faculty && data.faculty.length > 0) {
                    document.getElementById('faculty').innerHTML = `
                        <table>
                            <tr><th>ID</th><th>Name</th><th>Max Hours/Day</th></tr>
                            ${data.faculty.slice(0, 8).map(f => `
                                <tr>
                                    <td>${f.id}</td>
                                    <td>${f.name}</td>
                                    <td>${f.max_hours}</td>
                                </tr>
                            `).join('')}
                        </table>
                        ${data.faculty.length > 8 ? `<p style="text-align:center;margin-top:10px;color:#999;">...and ${data.faculty.length - 8} more</p>` : ''}
                    `;
                } else {
                    document.getElementById('faculty').innerHTML = '<p class="loading">No faculty found</p>';
                }
                
                // Update rooms
                if (data.rooms && data.rooms.length > 0) {
                    document.getElementById('rooms').innerHTML = `
                        <table>
                            <tr><th>Room ID</th><th>Type</th><th>Capacity</th></tr>
                            ${data.rooms.slice(0, 8).map(r => `
                                <tr>
                                    <td>${r.room_id}</td>
                                    <td>${r.type}</td>
                                    <td>${r.capacity}</td>
                                </tr>
                            `).join('')}
                        </table>
                        ${data.rooms.length > 8 ? `<p style="text-align:center;margin-top:10px;color:#999;">...and ${data.rooms.length - 8} more</p>` : ''}
                    `;
                } else {
                    document.getElementById('rooms').innerHTML = '<p class="loading">No rooms found</p>';
                }
            });
        
        function generateTimetable() {
            if (confirm('Generate new class timetable? This may take a minute.')) {
                fetch('/generate')
                    .then(response => response.json())
                    .then(data => {
                        alert('Timetable generated successfully!\\nTotal classes: ' + data.total_classes);
                        location.reload();
                    })
                    .catch(error => alert('Error generating timetable'));
            }
        }
        
        function generateExams() {
            alert('Exam timetable generation - Please use the console application for now');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Home page with role selection."""
    return LOGIN_PAGE

@app.route('/student')
def student_login():
    """Student section selection page."""
    return STUDENT_SELECT_PAGE

@app.route('/faculty')
def faculty_login():
    """Faculty selection page."""
    return FACULTY_SELECT_PAGE

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard."""
    return ADMIN_DASHBOARD

@app.route('/student/timetable')
def student_timetable():
    """Student timetable view."""
    section = request.args.get('section', '3rdSem-A')
    return render_template_string(
        TIMETABLE_VIEW_TEMPLATE,
        title=f"Timetable - {section}",
        header=f"📚 Timetable for {section}",
        subheader="Your weekly class schedule",
        bg_color="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
        back_url="/student",
        api_url=f"/api/student-timetable?section={section}"
    )

@app.route('/faculty/timetable')
def faculty_timetable():
    """Faculty timetable view."""
    faculty_id = request.args.get('id')
    # Get faculty name
    loader = DataLoader(data_dir='data')
    loader.load_all_data()
    faculty = loader.faculty.get(faculty_id)
    faculty_name = faculty.name if faculty else faculty_id
    
    return render_template_string(
        TIMETABLE_VIEW_TEMPLATE,
        title=f"Timetable - {faculty_name}",
        header=f"👨‍🏫 Timetable for {faculty_name}",
        subheader="Your teaching schedule",
        bg_color="linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
        back_url="/faculty",
        api_url=f"/api/faculty-timetable?id={faculty_id}"
    )

# API Endpoints
@app.route('/api/faculty-list')
def api_faculty_list():
    """Get list of all faculty."""
    loader = DataLoader(data_dir='data')
    loader.load_all_data()
    
    faculty_list = [
        {'id': fid, 'name': f.name}
        for fid, f in sorted(loader.faculty.items())
    ]
    
    return jsonify({'faculty': faculty_list})

@app.route('/api/student-timetable')
def api_student_timetable():
    """Get student timetable HTML."""
    global current_timetable
    
    section = request.args.get('section', '3rdSem-A')
    
    if not current_timetable:
        html = '''<div class="empty-msg">
            ⚠️ No timetable generated yet<br><br>
            Please go to <strong>Admin Dashboard</strong> and click <strong>"Generate Class Timetable"</strong>
        </div>'''
        return jsonify({'success': True, 'timetable': html})
    
    # Get assignments for this section
    assignments = current_timetable.get_assignments_by_group(section)
    
    if not assignments:
        html = f'''<div class="empty-msg">
            📭 No classes found for {section}<br><br>
            This section may not have any courses scheduled yet.
        </div>'''
        return jsonify({'success': True, 'timetable': html})
    
    # Generate HTML table
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    html = '<table>'
    html += '<tr><th>Time</th><th>Course</th><th>Title</th><th>Faculty</th><th>Room</th></tr>'
    
    for day in days:
        day_assignments = [a for a in assignments if a.slot.day == day]
        if day_assignments:
            html += f'<tr><td colspan="5" class="day-header">{day.upper()}</td></tr>'
            day_assignments.sort(key=lambda a: a.slot.start_time)
            
            for assignment in day_assignments:
                html += f'''<tr>
                    <td>{assignment.slot.start_time}-{assignment.slot.end_time}</td>
                    <td class="course-code">{assignment.course.code}</td>
                    <td>{assignment.course.title}</td>
                    <td>{assignment.faculty.name}</td>
                    <td>{assignment.room.room_id}</td>
                </tr>'''
    
    html += '</table>'
    
    return jsonify({'success': True, 'timetable': html})

@app.route('/api/faculty-timetable')
def api_faculty_timetable():
    """Get faculty timetable HTML."""
    global current_timetable
    
    faculty_id = request.args.get('id')
    
    if not current_timetable:
        html = '''<div class="empty-msg">
            ⚠️ No timetable generated yet<br><br>
            Please go to <strong>Admin Dashboard</strong> and click <strong>"Generate Class Timetable"</strong>
        </div>'''
        return jsonify({'success': True, 'timetable': html})
    
    # Get assignments for this faculty
    assignments = current_timetable.get_assignments_by_faculty(faculty_id)
    
    if not assignments:
        html = f'''<div class="empty-msg">
            📭 No classes assigned to this faculty member yet.<br><br>
            They may not be teaching any courses this semester.
        </div>'''
        return jsonify({'success': True, 'timetable': html})
    
    # Generate HTML table
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    html = '<table>'
    html += '<tr><th>Time</th><th>Course</th><th>Title</th><th>Section</th><th>Room</th></tr>'
    
    for day in days:
        day_assignments = [a for a in assignments if a.slot.day == day]
        if day_assignments:
            html += f'<tr><td colspan="5" class="day-header">{day.upper()}</td></tr>'
            day_assignments.sort(key=lambda a: a.slot.start_time)
            
            for assignment in day_assignments:
                html += f'''<tr>
                    <td>{assignment.slot.start_time}-{assignment.slot.end_time}</td>
                    <td class="course-code">{assignment.course.code}</td>
                    <td>{assignment.course.title}</td>
                    <td>{assignment.student_group}</td>
                    <td>{assignment.room.room_id}</td>
                </tr>'''
    
    html += '</table>'
    
    return jsonify({'success': True, 'timetable': html})

@app.route('/api/admin-data')
def api_admin_data():
    """Get all system data for admin dashboard."""
    loader = DataLoader(data_dir='data')
    loader.load_all_data()
    
    courses_data = [
        {
            'code': c.code,
            'title': c.title,
            'faculty_id': c.faculty_id,
            'student_group': c.student_group
        }
        for c in loader.courses
    ]
    
    faculty_data = [
        {
            'id': fid,
            'name': f.name,
            'max_hours': f.max_hours_per_day
        }
        for fid, f in sorted(loader.faculty.items())
    ]
    
    rooms_data = [
        {
            'room_id': r.room_id,
            'type': r.room_type,
            'capacity': r.capacity
        }
        for r in loader.rooms
    ]
    
    return jsonify({
        'courses_count': len(loader.courses),
        'faculty_count': len(loader.faculty),
        'rooms_count': len(loader.rooms),
        'courses': courses_data,
        'faculty': faculty_data,
        'rooms': rooms_data
    })

@app.route('/generate')
def generate():
    """Generate timetable via API."""
    global current_timetable, current_loader
    
    loader = DataLoader(data_dir='data')
    loader.load_all_data()
    current_loader = loader
    
    scheduler = Scheduler(
        courses=loader.courses,
        faculty_dict=loader.faculty,
        rooms=loader.rooms,
        slots=loader.slots
    )
    
    current_timetable = scheduler.generate_timetable()
    is_valid = scheduler.validate_timetable()
    
    return jsonify({
        'success': True,
        'total_classes': len(current_timetable.assignments),
        'total_faculty': len(loader.faculty),
        'conflicts': 0 if is_valid else 1
    })

@app.route('/download')
def download():
    """Download timetable as Excel file."""
    global current_timetable
    
    if not current_timetable:
        return "No timetable generated yet", 400
    
    # Create Excel file
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
    print("🌐 Starting Timetable System Web Interface".center(70))
    print("=" * 70)
    
    # Initialize timetable on startup
    initialize_timetable()
    
    print("\n📍 Open your browser and visit: http://localhost:5000")
    print("⚡ Press Ctrl+C to stop the server\n")
    print("=" * 70)
    app.run(debug=True, port=5000, use_reloader=False)