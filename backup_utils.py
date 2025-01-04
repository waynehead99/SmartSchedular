"""
Utility functions for backing up and restoring the Smart Scheduler database.

This module provides functions to:
- Create database backups with timestamps
- Restore database from backup files
- List available backups
"""

import os
import shutil
from datetime import datetime
import json
from models import db, Project, Task, Calendar
from flask import current_app

def create_backup():
    """
    Create a backup of the current database state.
    Returns the backup filename on success.
    """
    # Ensure backups directory exists with absolute path
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = os.path.join(backup_dir, f'backup_{timestamp}.json')

    try:
        # Collect data from all tables within the application context
        backup_data = {
            'projects': [],
            'tasks': [],
            'calendar': []
        }

        # Explicitly get all records within a transaction
        with db.session.begin():
            # Backup projects
            projects = db.session.query(Project).all()
            for project in projects:
                backup_data['projects'].append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'status': project.status,
                    'color': project.color,
                    'priority': project.priority,
                    'created_at': project.created_at.isoformat() if project.created_at else None
                })

            # Backup tasks
            tasks = db.session.query(Task).all()
            for task in tasks:
                backup_data['tasks'].append({
                    'id': task.id,
                    'project_id': task.project_id,
                    'title': task.title,
                    'description': task.description,
                    'estimated_duration': task.estimated_duration,
                    'status': task.status,
                    'priority': task.priority,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'scheduled_start': task.scheduled_start.isoformat() if task.scheduled_start else None,
                    'scheduled_end': task.scheduled_end.isoformat() if task.scheduled_end else None
                })

            # Backup calendar events
            calendar_events = db.session.query(Calendar).all()
            for event in calendar_events:
                backup_data['calendar'].append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'start_time': event.start_time.isoformat() if event.start_time else None,
                    'end_time': event.end_time.isoformat() if event.end_time else None,
                    'project_id': event.project_id,
                    'event_type': event.event_type
                })

        # Write backup to file
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)

        current_app.logger.info(f"Successfully created backup: {backup_filename}")
        return os.path.basename(backup_filename)  # Return only the filename, not the full path

    except Exception as e:
        current_app.logger.error(f"Error creating backup: {str(e)}")
        if os.path.exists(backup_filename):
            os.remove(backup_filename)
        raise

def restore_backup(backup_filename):
    """
    Restore database from a backup file.
    Returns True on success, False on failure.
    """
    if not os.path.exists(backup_filename):
        current_app.logger.error(f"Backup file not found: {backup_filename}")
        return False

    try:
        # Read backup data
        with open(backup_filename, 'r') as f:
            backup_data = json.load(f)

        # Clear existing data
        Calendar.query.delete()
        Task.query.delete()
        Project.query.delete()
        db.session.commit()

        # Restore projects
        for project_data in backup_data['projects']:
            project = Project(
                id=project_data['id'],
                name=project_data['name'],
                description=project_data['description'],
                status=project_data['status'],
                color=project_data['color'],
                priority=project_data['priority']
            )
            if project_data['created_at']:
                project.created_at = datetime.fromisoformat(project_data['created_at'])
            db.session.add(project)

        # Restore tasks
        for task_data in backup_data['tasks']:
            task = Task(
                id=task_data['id'],
                project_id=task_data['project_id'],
                title=task_data['title'],
                description=task_data['description'],
                estimated_duration=task_data['estimated_duration'],
                status=task_data['status'],
                priority=task_data['priority']
            )
            if task_data['created_at']:
                task.created_at = datetime.fromisoformat(task_data['created_at'])
            if task_data['scheduled_start']:
                task.scheduled_start = datetime.fromisoformat(task_data['scheduled_start'])
            if task_data['scheduled_end']:
                task.scheduled_end = datetime.fromisoformat(task_data['scheduled_end'])
            db.session.add(task)

        # Restore calendar events
        for event_data in backup_data['calendar']:
            event = Calendar(
                id=event_data['id'],
                title=event_data['title'],
                description=event_data['description'],
                project_id=event_data['project_id'],
                event_type=event_data['event_type']
            )
            if event_data['start_time']:
                event.start_time = datetime.fromisoformat(event_data['start_time'])
            if event_data['end_time']:
                event.end_time = datetime.fromisoformat(event_data['end_time'])
            db.session.add(event)

        db.session.commit()
        current_app.logger.info(f"Successfully restored backup: {backup_filename}")
        return True

    except Exception as e:
        current_app.logger.error(f"Error restoring backup: {str(e)}")
        db.session.rollback()
        return False

def list_backups():
    """
    List all available backup files.
    Returns a list of dictionaries containing backup information.
    """
    if not os.path.exists('backups'):
        os.makedirs('backups')
        return []

    backups = []
    for filename in os.listdir('backups'):
        if filename.startswith('backup_') and filename.endswith('.json'):
            filepath = os.path.join('backups', filename)
            timestamp = filename[7:-5]  # Remove 'backup_' prefix and '.json' suffix
            try:
                datetime_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                formatted_date = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
                backups.append({
                    'filename': filename,
                    'path': filepath,
                    'timestamp': formatted_date,
                    'size': os.path.getsize(filepath)
                })
            except ValueError:
                continue

    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
