"""
Smart Scheduler - AI-Powered Task Management System (Beta)

This is the main application file that sets up the Flask server and defines all API endpoints.
It handles project and task management, calendar operations, and AI-powered scheduling suggestions.

Features:
- Project management with priorities and color coding
- Task management with estimated durations
- AI-powered scheduling suggestions
- Calendar integration
- Working hours and weekend awareness

Environment Variables Required:
- OPENAI_API_KEY: Your OpenAI API key
- FLASK_APP: Set to app.py
- FLASK_ENV: development or production
- SECRET_KEY: Flask secret key
- DATABASE_URL: SQLite database URL
"""

import os
from datetime import datetime, timedelta
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import openai
from models import db, Project, Task, Calendar

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__, static_folder='static')
CORS(app)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///smart_scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize database
db.init_app(app)

# Configure OpenAI
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_schedule_suggestions(tasks, calendar_events):
    """Generate AI-powered schedule suggestions based on tasks and existing calendar"""
    
    # Format tasks and events for the AI
    tasks_text = "\n".join([
        f"Task: {task.title} (Duration: {task.estimated_duration}min, "
        f"Project: {Project.query.get(task.project_id).name}, "
        f"Status: {task.status})"
        for task in tasks
    ])
    
    events_text = "\n".join([
        f"Event: {event.title} (Start: {event.start_time}, End: {event.end_time})"
        for event in calendar_events
    ])
    
    # Create AI prompt
    prompt = f"""Given these tasks and calendar events, suggest an optimal schedule.
For each suggestion, provide:
1. Task name
2. Suggested start time (in format YYYY-MM-DD HH:MM)
3. Brief reasoning for the suggestion

Format each suggestion exactly like this example:
SUGGESTION
Task: Complete project proposal
Time: 2025-01-04 09:00
Reason: Early morning is ideal for focused writing tasks, and this slot is free
END

Current tasks to schedule:
{tasks_text}

Existing calendar events:
{events_text}

Consider:
1. Task durations and priorities
2. Available time slots between events
3. Project deadlines and dependencies
4. Optimal time of day for different task types"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "You are a smart scheduling assistant. Provide suggestions in the exact format specified."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse the suggestions into a structured format
        suggestions = []
        content = response.choices[0].message.content
        suggestion_blocks = content.split('SUGGESTION\n')[1:]  # Skip the first empty split
        
        for block in suggestion_blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) >= 3 and lines[-1] == 'END':
                task_line = lines[0].replace('Task: ', '')
                time_line = lines[1].replace('Time: ', '')
                reason_line = lines[2].replace('Reason: ', '')
                
                suggestions.append({
                    'task': task_line,
                    'suggested_time': time_line,
                    'reason': reason_line
                })
        
        return suggestions
    except Exception as e:
        return f"Error generating suggestions: {str(e)}"

def analyze_task_dependencies(tasks):
    """Analyze tasks to suggest dependencies and optimal ordering"""
    
    tasks_text = "\n".join([
        f"Task: {task.title} (Project: {Project.query.get(task.project_id).name}, "
        f"Description: {task.description})"
        for task in tasks
    ])
    
    prompt = f"""Analyze these tasks and identify potential dependencies:

{tasks_text}

Consider:
1. Technical dependencies
2. Logical ordering
3. Resource constraints
4. Project relationships

Provide analysis in this format:
1. [Task] depends on [Dependencies] because [Reasoning]"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "You are a project management expert that identifies task dependencies and optimal ordering."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing dependencies: {str(e)}"

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/calendar', methods=['GET'])
def get_calendar_events():
    events = Calendar.query.all()
    return jsonify([{
        'id': event.id,
        'title': event.title,
        'start': event.start_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'end': event.end_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'description': event.description,
        'project_id': event.project_id,
        'project_name': event.project.name if event.project_id else None,
        'event_type': event.event_type,
        'backgroundColor': getattr(event.project, 'color', None) if event.project_id else None,
        'borderColor': getattr(event.project, 'color', None) if event.project_id else None
    } for event in events])

@app.route('/api/calendar', methods=['POST'])
def add_calendar_event():
    data = request.json
    event = Calendar(
        title=data['title'],
        description=data.get('description'),
        start_time=datetime.fromisoformat(data['start']),
        end_time=datetime.fromisoformat(data['end']),
        project_id=data.get('project_id'),
        event_type=data.get('event_type', 'event')
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({
        'id': event.id,
        'title': event.title,
        'start': event.start_time.isoformat(),
        'end': event.end_time.isoformat(),
        'description': event.description,
        'project_id': event.project_id,
        'project_name': event.project.name if event.project_id else None,
        'event_type': event.event_type
    })

@app.route('/api/calendar/<int:event_id>', methods=['PUT', 'DELETE'])
def handle_calendar_event(event_id):
    event = Calendar.query.get_or_404(event_id)
    
    if request.method == 'DELETE':
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': 'Event deleted successfully'})
    
    data = request.json
    event.title = data['title']
    event.start_time = datetime.fromisoformat(data['start_time'])
    event.end_time = datetime.fromisoformat(data['end_time'])
    event.description = data.get('description', '')
    
    db.session.commit()
    return jsonify({'message': 'Event updated successfully'})

@app.route('/api/projects', methods=['GET', 'POST'])
def handle_projects():
    if request.method == 'POST':
        data = request.json
        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            status=data.get('status', 'In Progress'),
            priority=data.get('priority', 2),
            color=data.get('color', '#808080')
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'priority': project.priority,
            'priority_label': project.priority_label,
            'color': project.color
        })
    
    projects = Project.query.all()
    return jsonify([{
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'status': project.status,
        'priority': project.priority,
        'priority_label': project.priority_label,
        'color': project.color
    } for project in projects])

@app.route('/api/projects/<int:project_id>', methods=['PUT', 'DELETE'])
def handle_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'DELETE':
        # Delete associated tasks first
        Task.query.filter_by(project_id=project_id).delete()
        db.session.delete(project)
        db.session.commit()
        return jsonify({'message': 'Project and associated tasks deleted successfully'})
    
    data = request.json
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    project.priority = data.get('priority', project.priority)
    project.color = data.get('color', project.color)
    db.session.commit()
    return jsonify({'message': 'Project updated successfully'})

@app.route('/api/tasks', methods=['GET', 'POST'])
def get_tasks():
    if request.method == 'POST':
        data = request.json
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            project_id=data['project_id'],
            estimated_duration=data.get('estimated_duration', 60),
            status=data.get('status', 'Pending'),
            priority=data.get('priority', 2)
        )
        db.session.add(task)
        db.session.commit()
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'project_id': task.project_id,
            'project_name': task.project.name,
            'estimated_duration': task.estimated_duration,
            'status': task.status,
            'priority': task.priority,
            'priority_label': task.priority_label
        })
    
    tasks = Task.query.all()
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'project_id': task.project_id,
        'project_name': task.project.name,
        'estimated_duration': task.estimated_duration,
        'status': task.status,
        'priority': task.priority,
        'priority_label': task.priority_label
    } for task in tasks])

@app.route('/api/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
def handle_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify({'message': 'Task deleted successfully'})
    
    data = request.json
    task.project_id = data['project_id']
    task.title = data['title']
    task.description = data.get('description', '')
    task.estimated_duration = data.get('estimated_duration', 60)
    task.status = data.get('status', 'Pending')
    task.priority = data.get('priority', 2)
    db.session.commit()
    return jsonify({'message': 'Task updated successfully'})

@app.route('/api/schedule/suggest', methods=['GET'])
def get_schedule_suggestions():
    """Get AI-powered schedule suggestions"""
    try:
        # Get all unscheduled tasks
        tasks = Task.query.filter_by(status='Pending').all()
        if not tasks:
            return jsonify({'message': 'No tasks to schedule', 'suggestions': []})

        # Get existing calendar events
        events = Calendar.query.all()
        existing_events = [
            {
                'title': event.title,
                'start': event.start_time.isoformat(),
                'end': event.end_time.isoformat()
            }
            for event in events
        ]

        # Current time rounded to next hour
        current_time = datetime.now()
        start_time = datetime(
            current_time.year, current_time.month, current_time.day, 
            current_time.hour, 0, 0
        ) + timedelta(hours=1)

        # Sort tasks by combined priority (project + task priority)
        tasks.sort(key=lambda x: x.priority + x.project.priority)
        
        suggestions = []
        current_slot = start_time

        def is_weekend(dt):
            """Check if date is weekend (Saturday=5, Sunday=6)"""
            return dt.weekday() >= 5

        def next_workday(dt):
            """Get the next workday, skipping weekends"""
            while is_weekend(dt):
                dt = dt + timedelta(days=1)
            return dt

        # Schedule tasks during working hours (9 AM - 5 PM)
        for task in tasks:
            # Calculate combined priority score (lower is higher priority)
            priority_score = task.priority + task.project.priority
            
            # Find next available time slot
            while True:
                # Skip weekends
                if is_weekend(current_slot):
                    current_slot = next_workday(current_slot).replace(hour=9, minute=0)
                
                # Ensure we're within working hours (9 AM - 5 PM)
                if current_slot.hour < 9:
                    current_slot = current_slot.replace(hour=9, minute=0)
                elif current_slot.hour >= 17:
                    # Move to next workday at 9 AM
                    next_day = current_slot + timedelta(days=1)
                    current_slot = next_workday(next_day).replace(hour=9, minute=0)
                
                # Check for conflicts with existing events
                slot_end = current_slot + timedelta(minutes=task.estimated_duration)
                has_conflict = any(
                    (event.start_time <= current_slot < event.end_time) or
                    (event.start_time < slot_end <= event.end_time)
                    for event in events
                )
                
                if not has_conflict:
                    break
                
                # Try next slot (30-minute increments)
                current_slot += timedelta(minutes=30)
            
            suggestions.append({
                'task': task.title,
                'project_name': task.project.name,
                'suggested_time': current_slot.strftime('%Y-%m-%d %H:%M'),
                'duration': task.estimated_duration,
                'reason': f"Priority: {task.priority_label} (Task) + {task.project.priority_label} (Project)",
                'priority_score': priority_score
            })
            
            # Move time slot to after this task
            current_slot = slot_end + timedelta(minutes=15)  # 15-minute buffer between tasks

        return jsonify({
            'message': 'Schedule suggestions generated',
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/analyze', methods=['GET'])
def analyze_tasks():
    """Get AI analysis of task dependencies"""
    tasks = Task.query.all()
    analysis = analyze_task_dependencies(tasks)
    return jsonify({'analysis': analysis})

@app.route('/api/schedule-tasks', methods=['POST'])
def schedule_tasks():
    # Get free time slots
    calendar_events = Calendar.query.all()
    tasks = Task.query.filter_by(status='Pending').all()
    
    # Format the data for AI processing
    schedule_request = {
        'events': [{
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat()
        } for event in calendar_events],
        'tasks': [{
            'title': task.title,
            'duration': task.estimated_duration,
            'project': Project.query.get(task.project_id).name
        } for task in tasks]
    }
    
    # Use OpenAI to suggest task scheduling
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "You are a scheduling assistant. Given a list of calendar events and tasks, suggest optimal times for completing the tasks."
        }, {
            "role": "user",
            "content": f"Please schedule these tasks around the existing calendar events: {json.dumps(schedule_request)}"
        }],
        temperature=0.7,
        max_tokens=1000
    )
    
    return jsonify({'suggestions': response.choices[0].message.content})

@app.route('/api/project-status', methods=['GET'])
def get_project_status():
    projects = Project.query.all()
    status_data = []
    
    for project in projects:
        tasks = Task.query.filter_by(project_id=project.id).all()
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'Completed'])
        
        status_data.append({
            'project_name': project.name,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'progress': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        })
    
    return jsonify(status_data)

@app.route('/api/schedule/approve', methods=['POST'])
def approve_suggestion():
    """Add an approved AI suggestion to the calendar"""
    data = request.json
    
    try:
        # Find the task to get its project information
        task = Task.query.filter_by(title=data['task']).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Create a new calendar event from the suggestion
        event = Calendar(
            title=data['task'],
            start_time=datetime.strptime(data['suggested_time'], '%Y-%m-%d %H:%M'),
            end_time=datetime.strptime(data['suggested_time'], '%Y-%m-%d %H:%M') + 
                    timedelta(minutes=int(data.get('duration', 60))),
            project_id=task.project_id,
            event_type='task'
        )
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'message': 'Suggestion approved and added to calendar',
            'event': {
                'id': event.id,
                'title': event.title,
                'start': event.start_time.isoformat(),
                'end': event.end_time.isoformat(),
                'project_id': event.project_id,
                'project_name': event.project.name if event.project_id else None,
                'event_type': event.event_type
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)
