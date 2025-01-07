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
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, Project, Task, Calendar, StatusUpdate
import openai
from dotenv import load_dotenv
import pytz
import logging
from openai import OpenAI
from collections import defaultdict
from dateutil import tz

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__, static_url_path='', static_folder='static')

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///smart_scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Enable CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

if not os.getenv('OPENAI_API_KEY'):
    print("Warning: OPENAI_API_KEY not set. AI features will not work.")

def is_working_hours(dt):
    """Check if a datetime is within working hours (7 AM to 4 PM MST) on weekdays"""
    # Convert to MST if not already
    mst = pytz.timezone('America/Denver')
    if dt.tzinfo is None:
        dt = mst.localize(dt)
    elif dt.tzinfo != mst:
        dt = dt.astimezone(mst)
    
    # Check if it's a weekday (Monday = 0, Sunday = 6)
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if it's between 7 AM and 4 PM MST
    return 7 <= dt.hour < 16

def generate_schedule_suggestions(tasks, calendar_events):
    app.logger.debug(f'Generating suggestions for {len(tasks)} tasks')
    
    # Convert all times to MST for consistent scheduling
    mst = pytz.timezone('America/Denver')
    current_time = datetime.now(pytz.UTC)
    current_mst = current_time.astimezone(mst)
    
    # Initialize next available slot time
    slot_time = current_mst
    
    # If current time is after work hours, start tomorrow
    if slot_time.hour >= 17:  # After 5 PM
        slot_time = (slot_time + timedelta(days=1)).replace(hour=7, minute=0)
    elif slot_time.hour < 7:  # Before 7 AM
        slot_time = slot_time.replace(hour=7, minute=0)
    
    # Convert calendar events to MST and sort by start time
    existing_events = []
    for event in calendar_events:
        start = event.start_time.astimezone(mst) if event.start_time.tzinfo else mst.localize(event.start_time)
        end = event.end_time.astimezone(mst) if event.end_time.tzinfo else mst.localize(event.end_time)
        existing_events.append({'start': start, 'end': end})
    existing_events.sort(key=lambda x: x['start'])
    
    suggestions = []
    
    for task in tasks:
        app.logger.debug(f'Considering task: {task.title} (ID: {task.id})')
        
        # Skip completed tasks
        if task.status == 'Completed':
            app.logger.debug(f'Skipping completed task: {task.title}')
            continue
        
        # Get task duration (default to 30 minutes if not specified)
        duration = task.estimated_minutes or 30
        
        # Find next available slot that doesn't overlap with existing events
        while True:
            # Check if slot_time is during working hours (7 AM - 5 PM MST)
            if slot_time.hour < 7:
                slot_time = slot_time.replace(hour=7, minute=0)
            elif slot_time.hour >= 17:
                slot_time = (slot_time + timedelta(days=1)).replace(hour=7, minute=0)
                # Skip weekends
                while slot_time.weekday() >= 5:
                    slot_time += timedelta(days=1)
            
            slot_end = slot_time + timedelta(minutes=duration)
            
            # Check for overlaps with existing events
            has_overlap = False
            for event in existing_events:
                if slot_time < event['end'] and slot_end > event['start']:
                    has_overlap = True
                    # Move slot_time to after this event
                    slot_time = event['end']
                    break
            
            # Also check for overlaps with previously suggested times
            for _, prev_time in suggestions:
                prev_end = prev_time + timedelta(minutes=30)  # Assume 30 min for previous suggestions
                if slot_time < prev_end and slot_end > prev_time:
                    has_overlap = True
                    # Move slot_time to after this suggestion
                    slot_time = prev_end
                    break
            
            if not has_overlap:
                break
        
        app.logger.debug(f'Suggesting slot for task {task.title} at {slot_time}')
        suggestions.append((task, slot_time))
        
        # Move slot_time to after this task for the next iteration
        slot_time = slot_end
    
    return suggestions

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
    if task.estimated_minutes:
        hours = task.estimated_minutes / 60
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

def analyze_task_dependencies(task_data):
    """Analyze task dependencies and generate insights using AI."""
    try:
        if not os.getenv('OPENAI_API_KEY'):
            return "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."

        prompt = f"""Analyze these tasks and their dependencies:
{json.dumps(task_data, indent=2)}

Please provide a concise analysis focusing on:
1. Critical path tasks that need immediate attention
2. Potential bottlenecks in task dependencies
3. Scheduling recommendations based on priorities and dependencies
4. Any risks or issues that need attention

Keep the analysis practical and actionable."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a project management assistant analyzing task dependencies and providing insights."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        app.logger.error(f"Error in AI analysis: {str(e)}")
        return f"Error generating analysis: {str(e)}. Please ensure OPENAI_API_KEY is set correctly."

@app.route('/')
def index():
    app.logger.info('Serving index.html')
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        app.logger.error(f'Error serving index.html: {str(e)}')
        return str(e), 500

@app.route('/static/<path:path>')
def serve_static(path):
    app.logger.info(f'Serving static file: {path}')
    try:
        return send_from_directory('static', path)
    except Exception as e:
        app.logger.error(f'Error serving static file {path}: {str(e)}')
        return str(e), 404

@app.route('/api/calendar', methods=['GET'])
def get_calendar_events():
    events = Calendar.query.all()
    return jsonify([{
        'id': event.id,
        'title': event.title,
        'start': event.start_time.astimezone(pytz.timezone('America/Denver')).isoformat(),
        'end': event.end_time.astimezone(pytz.timezone('America/Denver')).isoformat(),
        'description': event.description,
        'project_id': event.project_id,
        'project_name': event.project.name if event.project_id else None,
        'task_id': event.task_id,
        'event_type': event.event_type,
        'backgroundColor': getattr(event.project, 'color', None) if event.project_id else None,
        'borderColor': getattr(event.project, 'color', None) if event.project_id else None
    } for event in events])

@app.route('/api/calendar', methods=['POST'])
def add_calendar_event():
    try:
        data = request.json
        app.logger.debug(f"Received event data: {data}")
        
        try:
            # Parse times and ensure they're in MST
            mst = pytz.timezone('America/Denver')
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            
            # Convert to MST if not already
            if start_time.tzinfo is None:
                start_time = mst.localize(start_time)
            else:
                start_time = start_time.astimezone(mst)
                
            if end_time.tzinfo is None:
                end_time = mst.localize(end_time)
            else:
                end_time = end_time.astimezone(mst)
                
            app.logger.debug(f"Parsed MST start_time: {start_time}, end_time: {end_time}")
            
        except ValueError as e:
            app.logger.error(f"Date parsing error: {str(e)}")
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        event = Calendar(
            title=data['title'],
            description=data.get('description'),
            start_time=start_time,
            end_time=end_time,
            project_id=data.get('project_id'),
            task_id=data.get('task_id'),
            event_type=data.get('event_type', 'event')
        )
        db.session.add(event)
        db.session.commit()
        
        app.logger.debug(f"Stored event with MST start_time: {event.start_time}, end_time: {event.end_time}")
        
        return jsonify({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'project_id': event.project_id,
            'project_name': event.project.name if event.project_id else None,
            'task_id': event.task_id,
            'event_type': event.event_type,
            'backgroundColor': getattr(event.project, 'color', None) if event.project_id else None,
            'borderColor': getattr(event.project, 'color', None) if event.project_id else None
        })
    except Exception as e:
        app.logger.error(f"Error adding calendar event: {str(e)}")
        return jsonify({'error': f'Failed to add event: {str(e)}'}), 500

@app.route('/api/calendar/<int:event_id>', methods=['PUT', 'DELETE'])
def handle_calendar_event(event_id):
    event = Calendar.query.get_or_404(event_id)
    
    if request.method == 'DELETE':
        db.session.delete(event)
        db.session.commit()
        return '', 204
    
    try:
        data = request.json
        
        # Parse and convert times to MST
        mst = pytz.timezone('America/Denver')
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        
        if start_time.tzinfo is None:
            start_time = mst.localize(start_time)
        else:
            start_time = start_time.astimezone(mst)
            
        if end_time.tzinfo is None:
            end_time = mst.localize(end_time)
        else:
            end_time = end_time.astimezone(mst)
        
        event.title = data['title']
        event.description = data.get('description')
        event.start_time = start_time
        event.end_time = end_time
        event.project_id = data.get('project_id')
        event.task_id = data.get('task_id')
        event.event_type = data.get('event_type', event.event_type)
        
        db.session.commit()
        
        return jsonify({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'project_id': event.project_id,
            'project_name': event.project.name if event.project_id else None,
            'task_id': event.task_id,
            'event_type': event.event_type,
            'backgroundColor': getattr(event.project, 'color', None) if event.project_id else None,
            'borderColor': getattr(event.project, 'color', None) if event.project_id else None
        })
    except ValueError as e:
        app.logger.error(f"Date parsing error: {str(e)}")
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        app.logger.error(f"Error updating calendar event: {str(e)}")
        return jsonify({'error': f'Failed to update event: {str(e)}'}), 500

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

@app.route('/api/projects/<int:project_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_project(project_id):
    project = db.session.get(Project, project_id)
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'priority': project.priority,
            'color': project.color
        })
    
    if request.method == 'DELETE':
        # Delete associated tasks first
        Task.query.filter_by(project_id=project_id).delete()
        db.session.delete(project)
        db.session.commit()
        return jsonify({'message': 'Project and associated tasks deleted successfully'})
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        project.name = data.get('name', project.name)
        project.description = data.get('description', project.description)
        project.status = data.get('status', project.status)
        project.priority = data.get('priority', project.priority)
        project.color = data.get('color', project.color)
        db.session.commit()
        return jsonify({'message': 'Project updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating project: {str(e)}")
        return jsonify({'error': 'Failed to update project'}), 500

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    try:
        if request.method == 'POST':
            data = request.json
            app.logger.info(f'Creating new task with data: {data}')
            
            # Validate required fields
            if not data.get('title'):
                return jsonify({'error': 'Title is required'}), 400
            if not data.get('project_id'):
                return jsonify({'error': 'Project is required'}), 400
                
            # Validate project exists
            project = db.session.get(Project, data['project_id'])
            if not project:
                return jsonify({'error': 'Selected project does not exist'}), 400
            
            new_task = Task(
                title=data['title'],
                description=data.get('description', ''),
                status=data.get('status', 'Not Started'),
                priority=data.get('priority', 2),
                estimated_minutes=data.get('estimated_minutes'),
                project_id=data['project_id'],
                ticket_number=data.get('ticket_number')
            )
            
            # Handle dependencies
            if 'dependencies' in data:
                for dep_id in data['dependencies']:
                    dep_task = db.session.get(Task, dep_id)
                    if dep_task:
                        new_task.dependencies.append(dep_task)
            
            try:
                db.session.add(new_task)
                db.session.commit()
                app.logger.info(f'Task created successfully with ID: {new_task.id}')
                return jsonify({'message': 'Task created successfully', 'id': new_task.id}), 201
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Database error while creating task: {str(e)}")
                return jsonify({'error': 'Database error occurred while creating task'}), 500
        
        # GET request
        try:
            app.logger.info('Fetching all tasks')
            tasks = Task.query.all()
            app.logger.info(f'Found {len(tasks)} tasks')
            
            # Convert tasks to dictionary and log the first task for debugging
            tasks_dict = [task.to_dict() for task in tasks]
            if tasks_dict:
                app.logger.debug(f'First task data: {tasks_dict[0]}')
            
            return jsonify({'tasks': tasks_dict})
        except Exception as e:
            app.logger.error(f"Error fetching tasks: {str(e)}")
            return jsonify({'error': f'Failed to fetch tasks: {str(e)}'}), 500

    except Exception as e:
        app.logger.error(f"Error in handle_tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_task(task_id):
    try:
        task = db.session.get(Task, task_id)
        if task is None:
            return jsonify({'error': 'Task not found'}), 404

        if request.method == 'GET':
            return jsonify(task.to_dict())
        
        elif request.method == 'DELETE':
            db.session.delete(task)
            db.session.commit()
            return jsonify({'message': 'Task deleted successfully'})
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Validate required fields
            if not data.get('title'):
                return jsonify({'error': 'Title is required'}), 400
            
            # Validate project_id if provided
            if 'project_id' in data:
                project = db.session.get(Project, data['project_id'])
                if not project:
                    return jsonify({'error': 'Selected project does not exist'}), 400
            
            # Update task fields
            fields = ['title', 'description', 'status', 'priority', 'project_id', 'estimated_minutes', 'ticket_number', 'current_status']
            for field in fields:
                if field in data:
                    setattr(task, field, data[field])
            
            # Update dependencies if provided
            if 'dependencies' in data:
                task.dependencies = []  # Clear existing dependencies
                for dep_id in data['dependencies']:
                    dep_task = db.session.get(Task, dep_id)
                    if dep_task:
                        task.dependencies.append(dep_task)
            
            # Update timestamps based on status changes
            if 'status' in data:
                if data['status'] == 'In Progress' and not task.started_at:
                    task.started_at = datetime.utcnow()
                elif data['status'] == 'Completed' and not task.completed_at:
                    task.completed_at = datetime.utcnow()
                    if task.started_at:
                        task.actual_duration = (task.completed_at - task.started_at).total_seconds() / 60
            
            try:
                db.session.commit()
                return jsonify(task.to_dict())
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Database error while updating task: {str(e)}")
                return jsonify({'error': 'Database error occurred while updating task'}), 500

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error handling task: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/schedule/suggestions', methods=['POST'])
def get_schedule_suggestions():
    try:
        data = request.json
        scheduled_task_ids = data.get('scheduled_task_ids', [])
        app.logger.debug(f'Already scheduled task IDs: {scheduled_task_ids}')
        
        # Get all tasks that are not completed and not already scheduled
        tasks = Task.query.filter(
            Task.status != 'Completed',
            ~Task.id.in_([int(id) for id in scheduled_task_ids])  # Convert string IDs to integers
        ).all()
        
        app.logger.debug(f'Found {len(tasks)} unscheduled tasks')
        for task in tasks:
            app.logger.debug(f'Unscheduled task: {task.title} (ID: {task.id}, Status: {task.status})')
        
        if not tasks:
            app.logger.debug('No unscheduled tasks found')
            return jsonify([])
        
        # Get all calendar events for scheduling context
        calendar_events = Calendar.query.all()
        app.logger.debug(f'Found {len(calendar_events)} calendar events')
        
        # Generate suggestions
        suggestions = generate_schedule_suggestions(tasks, calendar_events)
        app.logger.debug(f'Generated {len(suggestions)} suggestions')
        
        # Format suggestions for response
        formatted_suggestions = []
        for task, suggested_time in suggestions:
            suggestion = {
                'task_id': task.id,
                'task_title': task.title,
                'suggested_time': suggested_time.isoformat(),
                'duration': task.estimated_minutes,
                'reason': generate_scheduling_reason(task, [], suggested_time)
            }
            app.logger.debug(f'Formatted suggestion: {suggestion}')
            formatted_suggestions.append(suggestion)
        
        return jsonify(formatted_suggestions)
    except Exception as e:
        app.logger.error(f'Error generating schedule suggestions: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/analyze', methods=['GET'])
@cross_origin()
def analyze_tasks():
    try:
        # Get all incomplete tasks
        tasks = Task.query.filter(Task.status != 'Completed').all()
        if not tasks:
            return jsonify({
                'message': 'No tasks to analyze',
                'analysis': 'No tasks found to analyze.'
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
                'estimated_minutes': task.estimated_minutes,
                'ticket_number': task.ticket_number,
                'dependencies': [dep.title for dep in dependencies if dep],
                'project': task.project.name if task.project else None,
                'current_status': task.current_status
            }
            task_data.append(task_info)
        
        # Generate AI analysis
        analysis = analyze_task_dependencies(task_data)
        
        return jsonify({
            'message': 'Analysis completed successfully',
            'analysis': analysis
        })
        
    except Exception as e:
        app.logger.error(f"Error analyzing tasks: {str(e)}")
        return jsonify({'error': 'Failed to analyze tasks', 'analysis': 'Error generating analysis. Please try again later.'}), 500

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
    data = request.get_json()
    
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

        try:
            # Parse the time and ensure it's in MST
            mst = pytz.timezone('America/Denver')
            start_time = datetime.fromisoformat(suggested_time.replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = mst.localize(start_time)
            start_time = start_time.astimezone(mst)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        end_time = start_time + timedelta(minutes=duration)

        # Create a new calendar event from the suggestion
        event = Calendar(
            title=task.title,
            description=f"Scheduled task: {task.description}" if task.description else None,
            start_time=start_time,
            end_time=end_time,
            project_id=task.project_id,
            task_id=task.id,
            event_type='task'
        )
        
        try:
            # Update task status to scheduled
            task.status = 'In Progress'
            task.started_at = datetime.now(pytz.UTC)
            
            # Add event and commit changes
            db.session.add(event)
            db.session.commit()
            
            # Add a status update
            status_update = StatusUpdate(
                task_id=task.id,
                status='In Progress',
                notes=f'Task scheduled for {start_time.strftime("%Y-%m-%d %H:%M")}'
            )
            db.session.add(status_update)
            db.session.commit()
            
            return jsonify({
                'message': 'Schedule suggestion approved',
                'event': event.to_dict(),
                'task': task.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error while scheduling task: {str(e)}")
            return jsonify({'error': 'Database error occurred while scheduling task'}), 500
            
    except Exception as e:
        app.logger.error(f"Error approving schedule suggestion: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup', methods=['POST'])
def create_backup():
    """Create a backup of the current database state."""
    try:
        # Create timestamp for the backup file
        mst = pytz.timezone('America/Denver')
        timestamp = datetime.now(mst).strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.json'
        
        # Get all data from database
        projects = Project.query.all()
        tasks = Task.query.all()
        calendar_events = Calendar.query.all()
        
        # Create backup data structure
        backup_data = {
            'version': '1.0',
            'timestamp': datetime.now(mst).isoformat(),
            'projects': [],
            'tasks': [],
            'calendar_events': []
        }

        # Add projects
        for project in projects:
            project_data = {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'priority': project.priority,
                'color': project.color,
                'created_at': project.created_at.isoformat() if project.created_at else None
            }
            backup_data['projects'].append(project_data)

        # Add tasks
        for task in tasks:
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'current_status': task.current_status,
                'priority': task.priority,
                'estimated_minutes': task.estimated_minutes,
                'project_id': task.project_id,
                'ticket_number': task.ticket_number,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'dependencies': [dep.id for dep in task.dependencies] if task.dependencies else []
            }
            backup_data['tasks'].append(task_data)

        # Add calendar events
        for event in calendar_events:
            event_data = {
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'start_time': event.start_time.isoformat() if event.start_time else None,
                'end_time': event.end_time.isoformat() if event.end_time else None,
                'project_id': event.project_id,
                'task_id': event.task_id,
                'event_type': event.event_type
            }
            backup_data['calendar_events'].append(event_data)
        
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Save backup file
        backup_path = os.path.join(backup_dir, backup_filename)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        app.logger.info(f"Backup created successfully: {backup_filename}")
        
        # Return backup info without download URL
        return jsonify({
            'message': 'Backup created successfully',
            'filename': backup_filename
        })
    
    except Exception as e:
        app.logger.error(f"Error creating backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/download/<filename>')
def download_backup(filename):
    """Download a specific backup file."""
    try:
        backup_dir = os.path.join(app.root_path, 'backups')
        return send_from_directory(
            backup_dir, 
            filename,
            as_attachment=True,
            mimetype='application/json'
        )
    except Exception as e:
        app.logger.error(f"Error downloading backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups', methods=['GET'])
def list_backups():
    """List all available backups."""
    try:
        backup_dir = os.path.join(app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                backups.append({
                    'filename': filename,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size': stat.st_size
                })
        
        # Sort backups by creation time, newest first
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify(backups)
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

@app.route('/api/backup/restore', methods=['POST'])
def restore_backup_endpoint():
    """Restore database from a specific backup file."""
    try:
        filename = request.args.get('filename')
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
            
        app.logger.info(f"Starting restore of backup: {filename}")
        backup_dir = os.path.join(app.root_path, 'backups')
        backup_path = os.path.join(backup_dir, filename)
        
        app.logger.info(f"Checking backup file: {backup_path}")
        if not os.path.exists(backup_path):
            app.logger.error(f"Backup file not found: {backup_path}")
            return jsonify({'error': 'Backup file not found'}), 404

        app.logger.info("Reading backup file...")
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read()
                app.logger.info(f"File content: {content[:200]}...")  # Log first 200 chars
                backup_data = json.loads(content)
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON decode error: {str(e)}")
            app.logger.error(f"Error at position {e.pos}, line {e.lineno}, column {e.colno}")
            return jsonify({'error': f'Invalid backup format: {str(e)}'}), 400
        except Exception as e:
            app.logger.error(f"Error reading backup file: {str(e)}")
            return jsonify({'error': f'Error reading backup file: {str(e)}'}), 500

        app.logger.info("Verifying backup version...")
        if 'version' not in backup_data:
            app.logger.error("Missing version in backup data")
            return jsonify({'error': 'Invalid backup format: missing version'}), 400
        
        app.logger.info("Clearing existing data...")
        try:
            db.session.query(Project).delete()
            db.session.query(Task).delete()
            db.session.query(Calendar).delete()
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error clearing data: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Error clearing existing data: {str(e)}'}), 500

        app.logger.info("Restoring projects...")
        project_map = {}  # Map old IDs to new projects
        try:
            for project_data in backup_data['projects']:
                project = Project(
                    name=project_data['name'],
                    description=project_data.get('description'),
                    status=project_data.get('status', 'In Progress'),
                    priority=project_data.get('priority', 2),
                    color=project_data.get('color')
                )
                if project_data.get('created_at'):
                    project.created_at = datetime.fromisoformat(project_data['created_at'])
                db.session.add(project)
                db.session.flush()
                project_map[project_data['id']] = project
        except Exception as e:
            app.logger.error(f"Error restoring projects: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Error restoring projects: {str(e)}'}), 500

        app.logger.info("Restoring tasks...")
        task_map = {}  # Map old IDs to new tasks
        try:
            for task_data in backup_data.get('tasks', []):
                task = Task(
                    title=task_data['title'],
                    description=task_data.get('description'),
                    status=task_data.get('status', 'Not Started'),
                    current_status=task_data.get('current_status'),
                    priority=task_data.get('priority', 2),
                    estimated_minutes=task_data.get('estimated_minutes'),
                    project_id=project_map[task_data['project_id']].id if task_data.get('project_id') and task_data['project_id'] in project_map else None,
                    ticket_number=task_data.get('ticket_number')
                )
                if task_data.get('created_at'):
                    task.created_at = datetime.fromisoformat(task_data['created_at'])
                if task_data.get('started_at'):
                    task.started_at = datetime.fromisoformat(task_data['started_at'])
                if task_data.get('completed_at'):
                    task.completed_at = datetime.fromisoformat(task_data['completed_at'])
                
                db.session.add(task)
                db.session.flush()
                task_map[task_data['id']] = task
        except Exception as e:
            app.logger.error(f"Error restoring tasks: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Error restoring tasks: {str(e)}'}), 500

        app.logger.info("Restoring task dependencies...")
        try:
            for task_data in backup_data.get('tasks', []):
                if task_data.get('dependencies'):
                    task = task_map[task_data['id']]
                    for dep_id in task_data['dependencies']:
                        if dep_id in task_map:
                            task.dependencies.append(task_map[dep_id])
        except Exception as e:
            app.logger.error(f"Error restoring task dependencies: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Error restoring task dependencies: {str(e)}'}), 500

        app.logger.info("Restoring calendar events...")
        try:
            for event_data in backup_data.get('calendar_events', []):
                event = Calendar(
                    title=event_data['title'],
                    description=event_data.get('description'),
                    start_time=datetime.fromisoformat(event_data['start_time']) if event_data.get('start_time') else None,
                    end_time=datetime.fromisoformat(event_data['end_time']) if event_data.get('end_time') else None,
                    project_id=project_map[event_data['project_id']].id if event_data.get('project_id') and event_data['project_id'] in project_map else None,
                    task_id=task_map[event_data['task_id']].id if event_data.get('task_id') and event_data['task_id'] in task_map else None,
                    event_type=event_data.get('event_type')
                )
                db.session.add(event)
        except Exception as e:
            app.logger.error(f"Error restoring calendar events: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Error restoring calendar events: {str(e)}'}), 500

        app.logger.info("Committing changes...")
        try:
            db.session.commit()
            app.logger.info("Database restored successfully")
            return jsonify({'message': 'Database restored successfully'})
        except Exception as e:
            app.logger.error(f"Error committing changes: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Error committing changes: {str(e)}'}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error restoring backup: {str(e)}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
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
                    'latest_update_time': latest_update.created_at.isoformat() if latest_update else None,
                    'current_status': task.current_status
                })
            
            project_data.append({
                'name': project.name,
                'metrics': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'in_progress_tasks': in_progress_tasks,
                    'not_started_tasks': not_started_tasks,
                    'on_hold_tasks': on_hold_tasks,
                    'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
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

@app.route('/api/backup/upload', methods=['POST'])
def upload_backup():
    """Upload and validate a backup file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'Only JSON files are allowed'}), 400
            
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Read and validate the backup file
        try:
            backup_data = json.loads(file.read().decode('utf-8'))
            
            # Validate backup structure
            required_keys = ['version', 'timestamp', 'projects', 'tasks', 'calendar_events']
            if not all(key in backup_data for key in required_keys):
                return jsonify({'error': 'Invalid backup format: missing required fields'}), 400
                
            if backup_data.get('version') != '1.0':
                return jsonify({'error': 'Unsupported backup version'}), 400
                
            # Generate a new filename with current timestamp
            mst = pytz.timezone('America/Denver')
            timestamp = datetime.now(mst).strftime('%Y%m%d_%H%M%S')
            filename = f'backup_{timestamp}.json'
            
            # Save the file
            backup_path = os.path.join(backup_dir, filename)
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            app.logger.info(f"Backup file uploaded successfully: {filename}")
            return jsonify({
                'message': 'Backup file uploaded successfully',
                'filename': filename
            })
            
        except json.JSONDecodeError as e:
            app.logger.error(f"Invalid JSON format: {str(e)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
            
        except Exception as e:
            app.logger.error(f"Error validating backup file: {str(e)}")
            return jsonify({'error': 'Invalid backup format'}), 400
            
    except Exception as e:
        app.logger.error(f"Error uploading backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/<filename>', methods=['DELETE'])
def delete_backup(filename):
    """Delete a backup file."""
    try:
        # Validate filename
        if not filename.endswith('.json'):
            return jsonify({'error': 'Invalid backup file'}), 400

        # Ensure the file is in the backups directory
        backup_dir = os.path.join(app.root_path, 'backups')
        backup_path = os.path.join(backup_dir, filename)
        
        # Check if file exists and is within backups directory
        if not os.path.exists(backup_path) or not os.path.isfile(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
            
        # Ensure the file is within the backups directory (security check)
        real_backup_dir = os.path.realpath(backup_dir)
        real_backup_path = os.path.realpath(backup_path)
        if not real_backup_path.startswith(real_backup_dir):
            return jsonify({'error': 'Invalid backup path'}), 400

        # Delete the file
        os.remove(backup_path)
        app.logger.info(f"Backup file deleted: {filename}")
        
        return jsonify({'message': 'Backup deleted successfully'})
        
    except Exception as e:
        app.logger.error(f"Error deleting backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_default_project():
    try:
        app.logger.info('Checking for default project...')
        if not Project.query.first():
            app.logger.info('No projects found, creating default project')
            default_project = Project(
                name='Default Project',
                description='Default project for tasks',
                color='#6c757d'  # Bootstrap secondary color
            )
            db.session.add(default_project)
            db.session.commit()
            app.logger.info('Created default project with ID: %d', default_project.id)
        else:
            app.logger.info('Default project already exists')
    except Exception as e:
        app.logger.error(f'Error creating default project: {str(e)}')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_project()  # Create default project after tables are created
    app.run(host='0.0.0.0', port=5001, debug=True)