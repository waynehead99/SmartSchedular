"""
Database models for the Smart Scheduler application.

This module defines the SQLAlchemy models for:
- Projects: Representing high-level work items with priorities and color coding
- Tasks: Individual work items associated with projects
- Calendar: Events and scheduled tasks

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
        project_id (int): Foreign key to associated project
        estimated_duration (int): Estimated task duration in minutes
        status (str): Current status (Pending, In Progress, Completed)
        priority (int): Task priority (1=High, 2=Medium, 3=Low)
        created_at (datetime): Task creation timestamp
    """
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    estimated_duration = db.Column(db.Integer)  # in minutes
    status = db.Column(db.String(50), default='Pending')
    priority = db.Column(db.Integer, default=2)  # 1: High, 2: Medium, 3: Low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)

    @property
    def priority_label(self):
        """Convert numeric priority to human-readable label"""
        return {1: 'High', 2: 'Medium', 3: 'Low'}.get(self.priority, 'Medium')

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
