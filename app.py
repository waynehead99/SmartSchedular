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
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from models import db, Project, Task, Calendar, StatusUpdate
import openai
from backup_utils import create_backup, restore_backup, list_backups
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__, static_folder='static')
CORS(app)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///smart_scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize database
db.init_app(app)

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def is_working_hours(dt):
    """Check if a datetime is within working hours (7 AM to 4 PM MST) on weekdays"""
    # Convert to MST
    mst_dt = dt.astimezone(pytz.timezone('America/Denver'))
    # Check if it's a weekend
    if mst_dt.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
        return False
    # Check if it's between 7 AM and 4 PM MST
    return 7 <= mst_dt.hour < 16

def generate_schedule_suggestions(tasks, calendar_events):
    """Generate AI-powered schedule suggestions based on tasks and existing calendar"""
    try:
        # Sort calendar events by start time
        calendar_events = sorted(calendar_events, key=lambda x: x.start_time)
        
        # Find available time slots
        available_slots = []
        current_time = datetime.now(pytz.UTC)  # Make current time timezone-aware
        
        if calendar_events:
            # Convert event times to UTC for comparison
            calendar_events = [
                {
                    'start_time': event.start_time.replace(tzinfo=pytz.UTC) if event.start_time.tzinfo is None else event.start_time.astimezone(pytz.UTC),
                    'end_time': event.end_time.replace(tzinfo=pytz.UTC) if event.end_time.tzinfo is None else event.end_time.astimezone(pytz.UTC),
                    'title': event.title
                }
                for event in calendar_events
            ]
            
            # Check for slot before first event
            if current_time < calendar_events[0]['start_time']:
                duration = int((calendar_events[0]['start_time'] - current_time).total_seconds() / 60)
                if duration >= 15 and not is_working_hours(current_time):  # Only include slots of 15 minutes or more
                    available_slots.append({
                        'start': current_time,
                        'end': calendar_events[0]['start_time'],
                        'duration': duration
                    })
            
            # Check for slots between events
            for i in range(len(calendar_events) - 1):
                slot_start = calendar_events[i]['end_time']
                slot_end = calendar_events[i + 1]['start_time']
                if slot_start < slot_end and not is_working_hours(slot_start):
                    duration = int((slot_end - slot_start).total_seconds() / 60)
                    if duration >= 15:  # Only include slots of 15 minutes or more
                        available_slots.append({
                            'start': slot_start,
                            'end': slot_end,
                            'duration': duration
                        })
            
            # Check for slot after last event
            last_event = calendar_events[-1]
            if last_event['end_time'] > current_time and not is_working_hours(last_event['end_time']):
                available_slots.append({
                    'start': last_event['end_time'],
                    'end': last_event['end_time'] + timedelta(hours=8),  # Consider next 8 hours
                    'duration': 480  # 8 hours in minutes
                })
        else:
            # If no events, consider next 8 hours if not during working hours
            if not is_working_hours(current_time):
                available_slots.append({
                    'start': current_time,
                    'end': current_time + timedelta(hours=8),
                    'duration': 480
                })

        # Filter slots that are too short for the tasks
        min_duration_needed = min(task.estimated_duration or 30 for task in tasks)  # Default to 30 minutes if not specified
        available_slots = [slot for slot in available_slots if slot['duration'] >= min_duration_needed]

        # Further filter slots to ensure they don't overlap with working hours
        filtered_slots = []
        for slot in available_slots:
            start_time = slot['start']
            end_time = slot['end']
            current = start_time
            
            while current < end_time:
                if not is_working_hours(current):
                    # Find the next time that would be during working hours
                    next_work_time = current + timedelta(hours=1)
                    while next_work_time < end_time and not is_working_hours(next_work_time):
                        next_work_time += timedelta(hours=1)
                    
                    duration = int((min(next_work_time, end_time) - current).total_seconds() / 60)
                    if duration >= min_duration_needed:
                        filtered_slots.append({
                            'start': current,
                            'end': min(next_work_time, end_time),
                            'duration': duration
                        })
                
                current += timedelta(hours=1)
        
        available_slots = filtered_slots

        if not available_slots:
            return []  # No suitable slots found

        # Format tasks and slots for the prompt
        tasks_text = "\n".join([
            f"Task: {task.title} (Priority: {task.priority_label}, Duration: {task.estimated_duration or 30}min)"
            for task in tasks if task.status != 'Completed'
        ])
        
        slots_text = "\n".join([
            f"Available Slot: {slot['start'].strftime('%Y-%m-%d %H:%M')} to {slot['end'].strftime('%Y-%m-%d %H:%M')} ({slot['duration']} minutes)"
            for slot in available_slots
        ])
        
        events_text = "\n".join([
            f"Busy: {event['title']} ({event['start_time'].strftime('%Y-%m-%d %H:%M')} - {event['end_time'].strftime('%Y-%m-%d %H:%M')})"
            for event in calendar_events
        ])
        
        system_prompt = """You are an AI scheduling assistant that helps optimize task scheduling around existing calendar events.
Your goal is to create an efficient schedule by fitting tasks into available time slots while considering task priorities, durations, and dependencies.
For each suggestion, you must specify an exact start time that falls within an available slot and ensure there is enough time for the task.
IMPORTANT: Only suggest times outside of working hours (before 7 AM or after 4 PM MST) on weekdays, or any time on weekends."""

        user_prompt = f"""Given these unfinished tasks and available time slots, suggest an optimal schedule that:
1. Fits tasks into available time slots (never during busy periods)
2. Ensures each slot has enough duration for the task
3. Prioritizes high-priority tasks
4. Groups related tasks in adjacent slots when possible
5. Only schedules outside working hours (before 7 AM or after 4 PM MST) on weekdays, or any time on weekends

Tasks to schedule:
{tasks_text}

Available time slots (already filtered for non-working hours):
{slots_text}

Busy periods:
{events_text}

For each task, provide:
1. Task name
2. Exact start time (YYYY-MM-DD HH:MM format)
3. Brief reason for the slot choice

Format each suggestion exactly like this:
SUGGESTION
Task: [Task Name]
Time: [YYYY-MM-DD HH:MM]
Reason: [Your reasoning]
END"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
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
                
                # Validate the suggested time falls within an available slot
                try:
                    suggested_time = datetime.strptime(time_line, '%Y-%m-%d %H:%M')
                    suggested_time = pytz.timezone('America/Denver').localize(suggested_time)
                    suggested_time_utc = suggested_time.astimezone(pytz.UTC)
                    
                    # Double-check that the suggested time is outside working hours
                    if not is_working_hours(suggested_time):
                        task = next((t for t in tasks if t.title == task_line), None)
                        if task:
                            duration = task.estimated_duration or 30
                            # Check if the suggestion fits in any available slot
                            for slot in available_slots:
                                if (slot['start'] <= suggested_time_utc and 
                                    suggested_time_utc + timedelta(minutes=duration) <= slot['end']):
                                    suggestions.append({
                                        'task': task_line,
                                        'suggested_time': time_line,
                                        'reason': reason_line,
                                        'duration': duration
                                    })
                                    break
                except (ValueError, TypeError):
                    continue  # Skip invalid time formats
        
        return suggestions
    except Exception as e:
        app.logger.error(f"Error generating schedule suggestions: {str(e)}")
        return []

def generate_scheduling_reason(task, dependencies, suggested_time):
    """Generate a human-readable reason for the scheduling suggestion"""
    reasons = []
    
    # Check dependencies
    if dependencies:
        incomplete_deps = [d for d in dependencies if d.status != 'Completed']
        if incomplete_deps:
            dep_names = ', '.join([d.title for d in incomplete_deps])
            reasons.append(f"Waiting for dependencies to complete: {dep_names}")
        else:
            reasons.append("All dependencies are completed")
    
    # Consider priority
    if task.priority == 3:
        reasons.append("High priority task")
    elif task.priority == 2:
        reasons.append("Medium priority task")
    
    # Consider estimated duration
    if task.estimated_duration:
        hours = task.estimated_duration / 60
        reasons.append(f"Task requires approximately {hours:.1f} hours")
    
    # Consider current status
    if task.status == 'Not Started':
        reasons.append("Task hasn't been started yet")
    elif task.status == 'In Progress':
        reasons.append("Task is already in progress")
    
    # Format the suggested time
    local_time = suggested_time.astimezone()
    time_str = local_time.strftime("%I:%M %p on %B %d")
    reasons.append(f"Suggested start time: {time_str}")
    
    return " | ".join(reasons)

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
    event = db.session.get(Calendar, event_id)
    
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
    project = db.session.get(Project, project_id)
    
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
def handle_tasks():
    if request.method == 'POST':
        data = request.json
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'message': 'Title is required'}), 400
        if not data.get('project_id'):
            return jsonify({'message': 'Project is required'}), 400
            
        # Validate project exists
        project = Project.query.get(data['project_id'])
        if not project:
            return jsonify({'message': 'Selected project does not exist'}), 400
        
        new_task = Task(
            title=data['title'],
            description=data.get('description', ''),
            status=data.get('status', 'Not Started'),
            priority=data.get('priority', 2),
            estimated_duration=data.get('estimated_duration'),
            project_id=data['project_id']
        )
        
        # Handle dependencies
        if 'dependencies' in data:
            for dep_id in data['dependencies']:
                dep_task = Task.query.get(dep_id)
                if dep_task:
                    new_task.dependencies.append(dep_task)
        
        db.session.add(new_task)
        db.session.commit()
        return jsonify({'message': 'Task created successfully', 'id': new_task.id}), 201
    
    tasks = Task.query.all()
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'priority_label': task.priority_label,
        'estimated_duration': task.estimated_duration,
        'project_id': task.project_id,
        'project_name': task.project.name if task.project else None,
        'created_at': task.created_at.isoformat(),
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'actual_duration': task.actual_duration,
        'progress': task.progress,
        'dependencies': [dep.id for dep in task.dependencies],
        'dependent_tasks': [dep.id for dep in task.dependent_tasks]
    } for task in tasks])

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted successfully'})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    
    data = request.get_json()
    
    # Update task fields
    for field in ['title', 'description', 'status', 'priority', 'project_id', 'estimated_duration', 'ticket_number']:
        if field in data:
            setattr(task, field, data[field])
    
    # Handle completion status
    if data.get('status') == 'Completed' and not task.completed_at:
        task.completed_at = datetime.now(pytz.UTC)
    elif data.get('status') != 'Completed':
        task.completed_at = None
    
    # Update dependencies
    if 'dependencies' in data:
        # Clear existing dependencies
        task.dependencies = []
        # Add new dependencies
        for dep_id in data['dependencies']:
            dependency = db.session.get(Task, dep_id)
            if dependency:
                task.dependencies.append(dependency)
    
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>/status', methods=['POST'])
def update_task_status(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    # Create status update
    status_update = StatusUpdate(
        task_id=task_id,
        status=new_status,
        notes=notes,
        created_at=datetime.now(pytz.UTC)
    )
    
    # Update task status
    task.status = new_status
    if new_status == 'Completed':
        task.completed_at = datetime.now(pytz.UTC)
    elif task.completed_at:  # If task is being un-completed
        task.completed_at = None
    
    db.session.add(status_update)
    db.session.commit()
    
    return jsonify({
        'message': 'Status updated successfully',
        'status_update': status_update.to_dict()
    })

@app.route('/api/tasks/<int:task_id>/status-history', methods=['GET'])
def get_task_status_history(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    
    status_updates = StatusUpdate.query.filter_by(task_id=task_id).order_by(StatusUpdate.created_at.desc()).all()
    return jsonify([update.to_dict() for update in status_updates])

@app.route('/api/schedule/suggest', methods=['POST'])
def get_schedule_suggestions():
    data = request.get_json()
    task_id = data.get('task_id')
    
    if task_id:
        task = db.session.get(Task, task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        tasks = [task]
    else:
        tasks = Task.query.filter(Task.status != 'Completed').all()
    
    if not tasks:
        return jsonify({'message': 'No tasks to schedule', 'suggestions': []})
    
    try:
        suggestions = []
        for task in tasks:
            # Consider dependencies
            dependencies = task.dependencies
            earliest_start = datetime.now(pytz.UTC)
            
            if dependencies:
                # Find the latest completion time among dependencies
                latest_dependency = max(
                    (d.completed_at or datetime.now(pytz.UTC) + timedelta(days=d.estimated_duration/24/60) 
                     for d in dependencies),
                    default=earliest_start
                )
                earliest_start = max(earliest_start, latest_dependency)
            
            # Calculate suggested time slot
            duration_hours = task.estimated_duration / 60 if task.estimated_duration else 2
            suggested_time = earliest_start + timedelta(hours=1)  # Add buffer
            
            # Format the suggestion
            suggestions.append({
                'task': task.title,
                'task_id': task.id,
                'suggested_time': suggested_time.isoformat(),
                'duration': duration_hours,
                'reason': generate_scheduling_reason(task, dependencies, suggested_time)
            })
        
        return jsonify({'suggestions': suggestions})
        
    except Exception as e:
        app.logger.error(f"Error generating schedule suggestions: {str(e)}")
        return jsonify({'error': 'Failed to generate schedule suggestions'}), 500

@app.route('/api/tasks/analyze', methods=['GET'])
def analyze_tasks():
    try:
        # Get all incomplete tasks
        tasks = Task.query.filter(Task.status != 'Completed').all()
        if not tasks:
            return jsonify({
                'message': 'No tasks to analyze',
                'suggestions': []
            })
        
        # Prepare task data for analysis
        task_data = []
        for task in tasks:
            dependencies = [db.session.get(Task, dep.id) for dep in task.dependencies]
            task_info = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'estimated_duration': task.estimated_duration,
                'ticket_number': task.ticket_number,
                'dependencies': [dep.title for dep in dependencies if dep],
                'project': task.project.name if task.project else None
            }
            task_data.append(task_info)
        
        # Generate AI analysis
        analysis = analyze_task_dependencies(task_data)
        
        return jsonify(analysis)
        
    except Exception as e:
        app.logger.error(f"Error analyzing tasks: {str(e)}")
        return jsonify({'error': 'Failed to analyze tasks'}), 500

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
        # Get task by ID
        task_id = data.get('task_id')
        if not task_id:
            return jsonify({'error': 'Task ID is required'}), 400
            
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        suggested_time = data.get('suggested_time')
        duration = int(data.get('duration', 60))  # Default to 60 minutes if not specified
        
        if not suggested_time:
            return jsonify({'error': 'Suggested time is required'}), 400

        # Parse the suggested time
        start_time = datetime.strptime(suggested_time, '%Y-%m-%d %H:%M')
        end_time = start_time + timedelta(minutes=duration)

        # Create a new calendar event from the suggestion
        event = Calendar(
            title=task.title,
            start_time=start_time,
            end_time=end_time,
            project_id=task.project_id,
            event_type='task'
        )
        
        # Update task status to scheduled
        task.scheduled_start = start_time
        task.scheduled_end = end_time
        
        # Add and commit changes
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'message': 'Task scheduled successfully',
            'event': {
                'id': event.id,
                'title': event.title,
                'start': event.start_time.isoformat(),
                'end': event.end_time.isoformat()
            }
        })
        
    except ValueError as e:
        app.logger.error(f"Error parsing date/time: {str(e)}")
        return jsonify({'error': 'Invalid date/time format'}), 400
    except Exception as e:
        app.logger.error(f"Error approving schedule suggestion: {str(e)}")
        return jsonify({'error': 'Failed to schedule task'}), 500

@app.route('/api/backups', methods=['GET'])
def get_backups():
    """List all available database backups."""
    try:
        backups = list_backups()
        app.logger.info(f"Found {len(backups)} backups")
        return jsonify({'backups': backups})
    except Exception as e:
        app.logger.error(f"Error listing backups: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups', methods=['POST'])
def create_backup_endpoint():
    """Create a new database backup."""
    try:
        app.logger.info("Starting backup creation...")
        with app.app_context():
            backup_file = create_backup()
            app.logger.info(f"Backup created successfully: {backup_file}")
            return jsonify({
                'message': 'Backup created successfully',
                'backup_file': backup_file
            })
    except Exception as e:
        app.logger.error(f"Error creating backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups/restore/<filename>', methods=['POST'])
def restore_backup_endpoint(filename):
    """Restore database from a specific backup file."""
    try:
        app.logger.info(f"Attempting to restore backup: {filename}")
        backup_path = os.path.join('backups', filename)
        if not os.path.exists(backup_path):
            app.logger.error(f"Backup file not found: {backup_path}")
            return jsonify({'error': 'Backup file not found'}), 404

        success = restore_backup(backup_path)
        if success:
            app.logger.info("Database restored successfully")
            return jsonify({'message': 'Database restored successfully'})
        else:
            app.logger.error("Failed to restore database")
            return jsonify({'error': 'Failed to restore database'}), 500
    except Exception as e:
        app.logger.error(f"Error restoring backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status-report', methods=['GET'])
def generate_status_report():
    """Generate an AI-powered status report for all projects and tasks"""
    try:
        # Get all projects with their tasks
        projects = Project.query.all()
        project_data = []
        
        for project in projects:
            tasks = Task.query.filter_by(project_id=project.id).all()
            
            # Calculate project metrics
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == 'Completed'])
            in_progress_tasks = len([t for t in tasks if t.status == 'In Progress'])
            not_started_tasks = len([t for t in tasks if t.status == 'Not Started'])
            on_hold_tasks = len([t for t in tasks if t.status == 'On Hold'])
            
            # Get task details including latest status updates
            task_details = []
            for task in tasks:
                latest_update = StatusUpdate.query.filter_by(task_id=task.id).order_by(StatusUpdate.created_at.desc()).first()
                task_details.append({
                    'title': task.title,
                    'ticket_number': task.ticket_number,
                    'status': task.status,
                    'priority': task.priority_label,
                    'latest_update': latest_update.notes if latest_update else None,
                    'latest_update_time': latest_update.created_at.isoformat() if latest_update else None
                })
            
            project_data.append({
                'name': project.name,
                'metrics': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'in_progress_tasks': in_progress_tasks,
                    'not_started_tasks': not_started_tasks,
                    'on_hold_tasks': on_hold_tasks,
                    'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
                },
                'tasks': task_details
            })
        
        app.logger.info(f"Collected data for {len(project_data)} projects")
        
        if not project_data:
            return jsonify({
                'report': "No projects or tasks found to generate a report.",
                'raw_data': []
            })
        
        # Generate AI summary using project data
        system_prompt = """You are an AI project management assistant that creates clear and concise status reports.
Your goal is to analyze project data and create a well-structured status report that highlights:
1. Overall project health and progress
2. Key metrics and completion rates
3. Important status updates and potential blockers
4. Recommendations for next steps"""

        user_prompt = f"""Create a detailed status report based on the following project data:

{json.dumps(project_data, indent=2)}

Format the report with these sections:
1. Executive Summary
2. Project-by-Project Breakdown
3. Key Metrics & Progress
4. Recent Updates & Status Changes
5. Recommendations

Use markdown formatting for better readability."""

        app.logger.info("Generating AI report...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        report_content = response.choices[0].message.content.strip()
        app.logger.info("AI report generated successfully")
        
        return jsonify({
            'report': report_content,
            'raw_data': project_data
        })
        
    except Exception as e:
        app.logger.error(f"Error generating status report: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001)