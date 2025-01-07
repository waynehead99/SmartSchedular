"""
Database models for the Smart Scheduler application.

This module defines the SQLAlchemy models for:
- Projects: Representing high-level work items with priorities and color coding
- Tasks: Individual work items associated with projects
- Calendar: Events and scheduled tasks
- Status Updates: Task status updates

Each model includes priority handling and proper relationship definitions.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Task Dependencies Association Table
task_dependencies = db.Table('task_dependencies',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), primary_key=True),
    db.Column('dependency_id', db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), primary_key=True)
)

class Project(db.Model):
    """
    Project model representing a high-level work item.
    
    Attributes:
        id (int): Primary key
        name (str): Project name
        description (str): Project description
        status (str): Current status (Planning, In Progress, Completed)
        priority (int): Project priority (1=High, 2=Medium, 3=Low)
        color (str): Hex color code for visual representation
        created_at (datetime): Project creation timestamp
        tasks (relationship): Related tasks
    """
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='In Progress')
    priority = db.Column(db.Integer, default=2)  # 1: High, 2: Medium, 3: Low
    color = db.Column(db.String(20))  # Add color field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('Task', back_populates='project', cascade='all, delete-orphan', lazy=True)
    
    @property
    def priority_label(self):
        """Convert numeric priority to human-readable label"""
        return {1: 'High', 2: 'Medium', 3: 'Low'}.get(self.priority, 'Medium')
    
    def to_dict(self):
        """Convert project to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'priority_label': self.priority_label,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'task_count': len(self.tasks)
        }

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Not Started')
    current_status = db.Column(db.Text)  # New field for detailed status updates
    priority = db.Column(db.Integer, default=0)
    estimated_minutes = db.Column(db.Integer)
    actual_duration = db.Column(db.Float)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    ticket_number = db.Column(db.String(50))

    # Relationships
    project = db.relationship('Project', back_populates='tasks')
    status_updates = db.relationship('StatusUpdate', back_populates='task', cascade='all, delete-orphan')
    
    # Many-to-many relationship for task dependencies
    dependencies = db.relationship(
        'Task',
        secondary=task_dependencies,
        primaryjoin=(id == task_dependencies.c.task_id),
        secondaryjoin=(id == task_dependencies.c.dependency_id),
        backref=db.backref('dependent_tasks', lazy='dynamic')
    )

    @property
    def priority_label(self):
        labels = {1: 'High', 2: 'Medium', 3: 'Low'}
        return labels.get(self.priority, 'Medium')

    @property
    def progress(self):
        if self.status == 'Completed':
            return 100
        elif self.status == 'In Progress':
            return 50
        elif self.status == 'On Hold':
            return 25
        return 0

    def to_dict(self):
        """Convert task to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'current_status': self.current_status,
            'priority': self.priority,
            'priority_label': self.priority_label,
            'estimated_minutes': self.estimated_minutes,
            'actual_duration': self.actual_duration,
            'project_id': self.project_id,
            'project': {
                'id': self.project.id,
                'name': self.project.name,
                'color': self.project.color
            } if self.project else None,
            'project_name': self.project.name if self.project else None,
            'ticket_number': self.ticket_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'dependencies': [dep.id for dep in self.dependencies],
            'dependent_tasks': [dep.id for dep in self.dependent_tasks]
        }

class StatusUpdate(db.Model):
    """Model for task status updates"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    task = db.relationship('Task', back_populates='status_updates')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

class Calendar(db.Model):
    """
    Calendar model representing scheduled events and tasks.
    
    Attributes:
        id (int): Primary key
        title (str): Event title
        description (str): Event description
        start_time (datetime): Event start time
        end_time (datetime): Event end time
        project_id (int): Optional foreign key to associated project
        task_id (int): Optional foreign key to associated task
        event_type (str): Type of event ('task' or 'meeting' or other types)
    """
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    event_type = db.Column(db.String(50))  # 'task' or 'meeting' or other types
    
    project = db.relationship('Project', backref='calendar_events')
    task = db.relationship('Task', backref='calendar_events')

    def to_dict(self):
        """Convert calendar event to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'description': self.description,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'task_id': self.task_id,
            'event_type': self.event_type,
            'backgroundColor': self.project.color if self.project else None,
            'borderColor': self.project.color if self.project else None
        }
