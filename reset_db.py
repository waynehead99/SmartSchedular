from app import app, db
from models import Project, Task, Calendar, StatusUpdate
from datetime import datetime, timedelta
import pytz

def reset_database():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create test projects with professional colors
        projects = [
            Project(name="Website Redesign", color="#2196F3", description="Modernize company website"),
            Project(name="Mobile App", color="#4CAF50", description="Develop new mobile application"),
            Project(name="Database Migration", color="#9C27B0", description="Upgrade database infrastructure")
        ]
        
        for project in projects:
            db.session.add(project)
        db.session.commit()
        
        # Create test tasks with various statuses and current status updates
        tasks = [
            Task(
                title="Design Homepage",
                description="Create new homepage design",
                status="In Progress",
                current_status="Working on responsive layout, 60% complete",
                priority="high",
                estimated_minutes=240,
                project=projects[0]
            ),
            Task(
                title="Implement User Authentication",
                description="Add secure login system",
                status="Not Started",
                current_status="Researching OAuth providers",
                priority="high",
                estimated_minutes=180,
                project=projects[0]
            ),
            Task(
                title="Setup API Endpoints",
                description="Create RESTful API endpoints",
                status="Completed",
                current_status="All endpoints implemented and tested",
                priority="medium",
                estimated_minutes=120,
                project=projects[1]
            ),
            Task(
                title="Database Schema Design",
                description="Design new database schema",
                status="In Progress",
                current_status="Reviewing data relationships, need input on user table",
                priority="high",
                estimated_minutes=90,
                project=projects[2]
            ),
            Task(
                title="Write Migration Scripts",
                description="Create data migration scripts",
                status="Not Started",
                current_status="Waiting on schema approval",
                priority="medium",
                estimated_minutes=150,
                project=projects[2]
            )
        ]
        
        for task in tasks:
            db.session.add(task)
        db.session.commit()
        
        # Add dependencies
        tasks[1].dependencies.append(tasks[0])  # Auth depends on Homepage
        tasks[4].dependencies.append(tasks[3])  # Migration scripts depend on Schema
        db.session.commit()
        
        # Add status updates
        status_updates = [
            StatusUpdate(
                task_id=tasks[0].id,
                status='In Progress',
                notes='Started working on color palette'
            ),
            StatusUpdate(
                task_id=tasks[0].id,
                status='In Progress',
                notes='Typography system defined'
            )
        ]
        
        for update in status_updates:
            db.session.add(update)
        db.session.commit()
        
        # Create test calendar events
        mst = pytz.timezone('America/Denver')
        now = datetime.now(mst)
        start_of_day = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        events = [
            Calendar(
                title="Team Meeting",
                description="Weekly team sync",
                start_time=start_of_day,
                end_time=start_of_day + timedelta(hours=1),
                event_type="meeting"
            ),
            Calendar(
                title="Code Review",
                description="Review homepage PR",
                start_time=start_of_day + timedelta(hours=2),
                end_time=start_of_day + timedelta(hours=3),
                event_type="review",
                task_id=tasks[0].id
            ),
            Calendar(
                title="Database Planning",
                description="Discuss migration strategy",
                start_time=start_of_day + timedelta(days=1, hours=1),
                end_time=start_of_day + timedelta(days=1, hours=2),
                event_type="meeting",
                task_id=tasks[3].id
            )
        ]
        
        for event in events:
            db.session.add(event)
        db.session.commit()
        
        print("Database reset complete with test data!")

if __name__ == "__main__":
    reset_database()
