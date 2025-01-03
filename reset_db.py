"""
Database initialization script for Smart Scheduler.

This script:
1. Drops all existing tables
2. Creates new tables
3. Populates the database with sample data for testing
4. Creates a set of projects with different priorities
5. Creates tasks for each project with varying priorities
6. Sets up initial calendar events

Usage:
    python reset_db.py

Note: This will delete all existing data in the database.
"""

from app import app, db
from models import Project, Task, Calendar
from datetime import datetime, timedelta

def init_db():
    """Initialize the database with sample data."""
    
    # Drop all tables and create new ones
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        print("Creating sample projects...")
        # Create projects with different priority levels
        projects = [
            Project(
                name="Website Redesign",
                description="Modernize company website with new features",
                status="In Progress",
                priority=1,  # High priority
                color="#4CAF50"  # Green
            ),
            Project(
                name="Mobile App Development",
                description="Develop iOS and Android mobile applications",
                status="In Progress",
                priority=2,  # Medium priority
                color="#2196F3"  # Blue
            ),
            Project(
                name="Data Analytics Platform",
                description="Build analytics dashboard for business metrics",
                status="Planning",
                priority=3,  # Low priority
                color="#FF9800"  # Orange
            )
        ]
        
        for project in projects:
            db.session.add(project)
        db.session.commit()

        print("Creating sample tasks...")
        # Create tasks with varying priorities for each project
        tasks = [
            # Website Redesign tasks (High priority project)
            Task(
                title="Design Homepage Mockup",
                description="Create modern homepage design with improved UX",
                project_id=projects[0].id,
                estimated_duration=120,
                status="In Progress",
                priority=1  # High priority task
            ),
            Task(
                title="Implement User Authentication",
                description="Add secure login and registration system",
                project_id=projects[0].id,
                estimated_duration=180,
                status="Pending",
                priority=2  # Medium priority task
            ),
            # Mobile App tasks (Medium priority project)
            Task(
                title="Design App Wireframes",
                description="Create wireframes for key app screens",
                project_id=projects[1].id,
                estimated_duration=240,
                status="In Progress",
                priority=1  # High priority task
            ),
            Task(
                title="Implement Push Notifications",
                description="Add push notification system",
                project_id=projects[1].id,
                estimated_duration=120,
                status="Pending",
                priority=3  # Low priority task
            ),
            # Analytics Platform tasks (Low priority project)
            Task(
                title="Design Database Schema",
                description="Create efficient database structure for analytics",
                project_id=projects[2].id,
                estimated_duration=180,
                status="Pending",
                priority=2  # Medium priority task
            ),
            Task(
                title="Create Data Visualization Components",
                description="Implement charts and graphs for dashboard",
                project_id=projects[2].id,
                estimated_duration=240,
                status="Pending",
                priority=3  # Low priority task
            )
        ]
        
        for task in tasks:
            db.session.add(task)
        
        print("Creating sample calendar events...")
        # Create some sample calendar events for the next week
        start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Weekly team meeting
        calendar_events = [
            Calendar(
                title="Weekly Team Sync",
                description="Regular team status update meeting",
                start_time=start_date + timedelta(days=1, hours=1),
                end_time=start_date + timedelta(days=1, hours=2),
                event_type="event"
            ),
            Calendar(
                title="Project Planning",
                description="Quarterly project planning session",
                start_time=start_date + timedelta(days=2, hours=2),
                end_time=start_date + timedelta(days=2, hours=4),
                event_type="event"
            )
        ]
        
        for event in calendar_events:
            db.session.add(event)
        
        db.session.commit()
        print("Database has been reset and populated with test data!")

if __name__ == '__main__':
    init_db()
