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
    tasks = db.relationship('Task', backref='project', lazy=True)
    
    @property
    def priority_label(self):
        """Convert numeric priority to human-readable label"""
        return {1: 'High', 2: 'Medium', 3: 'Low'}.get(self.priority, 'Medium')

class Task(db.Model):
    """
    Task model representing an individual work item.
    
    Attributes:
        id (int): Primary key
        title (str): Task title
        description (str): Task description
        ticket_number (str): Task ticket number
        status (str): Current status (Not Started, In Progress, Completed)
        priority (int): Task priority (1=High, 2=Medium, 3=Low)
        estimated_duration (int): Estimated duration in minutes
        project_id (int): Foreign key to associated project
        created_at (datetime): Task creation timestamp
        dependencies (relationship): Tasks that must be completed before this one
        actual_duration (int): Actual time spent on task in minutes
        started_at (datetime): When the task was started
        completed_at (datetime): When the task was completed
        status_updates (relationship): Task status updates
    """
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    ticket_number = db.Column(db.String(50))  # New field for ticket numbers
    status = db.Column(db.String(50), default='Not Started')
    priority = db.Column(db.Integer, default=2)  # 1: High, 2: Medium, 3: Low
    estimated_duration = db.Column(db.Integer)  # in minutes
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actual_duration = db.Column(db.Integer, nullable=True)  # in minutes
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Task Dependencies
    dependencies = db.relationship(
        'Task',
        secondary='task_dependencies',
        primaryjoin='Task.id==task_dependencies.c.dependent_task_id',
        secondaryjoin='Task.id==task_dependencies.c.prerequisite_task_id',
        backref='dependent_tasks'
    )
    
    # Add relationship to status updates
    status_updates = db.relationship('StatusUpdate', backref='task', lazy=True, order_by='StatusUpdate.created_at.desc()')
    
    @property
    def priority_label(self):
        """Convert numeric priority to human-readable label"""
        return {1: 'High', 2: 'Medium', 3: 'Low'}.get(self.priority, 'Medium')
    
    @property
    def progress(self):
        """Calculate task progress based on status and time tracking"""
        if self.status == 'Completed':
            return 100
        elif self.status == 'Not Started':
            return 0
        elif self.started_at and not self.completed_at:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds() / 60
            if self.estimated_duration:
                progress = min(95, (elapsed / self.estimated_duration) * 100)
                return round(progress)
        return 50  # Default for "In Progress" without time tracking

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'ticket_number': self.ticket_number,
            'status': self.status,
            'priority': self.priority,
            'priority_label': self.priority_label,
            'estimated_duration': self.estimated_duration,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status_updates': [update.to_dict() for update in self.status_updates]
        }

# Task Dependencies Association Table
task_dependencies = db.Table('task_dependencies',
    db.Column('dependent_task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('prerequisite_task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True)
)

class StatusUpdate(db.Model):
    """Model for task status updates"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
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
        event_type (str): Type of event ('event' or 'task')
    """
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    event_type = db.Column(db.String(20), default='event')  # 'event' or 'task'
    
    # Relationship
    project = db.relationship('Project', backref='calendar_events')
