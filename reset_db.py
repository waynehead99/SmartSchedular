from app import app, db
from models import Project, Task, StatusUpdate
from datetime import datetime, timedelta
import pytz

def reset_database():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create tables
        db.create_all()
        
        # Create test projects
        project1 = Project(name="Website Redesign")
        project2 = Project(name="Mobile App Development")
        project3 = Project(name="Database Migration")
        
        db.session.add_all([project1, project2, project3])
        db.session.commit()
        
        # Create tasks with realistic data and status history
        tasks = []
        
        # Website Redesign Tasks
        task1 = Task(
            title="Design New Homepage Layout",
            description="Create a modern, responsive homepage design with improved user experience",
            project_id=project1.id,
            status="Completed",
            priority=3,
            estimated_duration=240,
            ticket_number="WEB-101",
            completed_at=datetime.now(pytz.UTC) - timedelta(days=5)
        )
        tasks.append(task1)
        
        # Status updates for task1
        status_updates1 = [
            StatusUpdate(
                task_id=1,
                status="Not Started",
                notes="Task created and assigned",
                created_at=datetime.now(pytz.UTC) - timedelta(days=10)
            ),
            StatusUpdate(
                task_id=1,
                status="In Progress",
                notes="Started working on wireframes",
                created_at=datetime.now(pytz.UTC) - timedelta(days=7)
            ),
            StatusUpdate(
                task_id=1,
                status="On Hold",
                notes="Waiting for brand guidelines",
                created_at=datetime.now(pytz.UTC) - timedelta(days=6)
            ),
            StatusUpdate(
                task_id=1,
                status="In Progress",
                notes="Resumed work after receiving guidelines",
                created_at=datetime.now(pytz.UTC) - timedelta(days=5, hours=12)
            ),
            StatusUpdate(
                task_id=1,
                status="Completed",
                notes="Design approved by stakeholders",
                created_at=datetime.now(pytz.UTC) - timedelta(days=5)
            )
        ]
        
        task2 = Task(
            title="Implement Homepage Design",
            description="Convert the approved design into responsive HTML/CSS/JS",
            project_id=project1.id,
            status="In Progress",
            priority=3,
            estimated_duration=480,
            ticket_number="WEB-102"
        )
        tasks.append(task2)
        
        # Status updates for task2
        status_updates2 = [
            StatusUpdate(
                task_id=2,
                status="Not Started",
                notes="Waiting for design completion",
                created_at=datetime.now(pytz.UTC) - timedelta(days=5)
            ),
            StatusUpdate(
                task_id=2,
                status="In Progress",
                notes="Started HTML implementation",
                created_at=datetime.now(pytz.UTC) - timedelta(days=2)
            )
        ]
        
        task3 = Task(
            title="SEO Optimization",
            description="Optimize the new homepage for search engines",
            project_id=project1.id,
            status="Not Started",
            priority=2,
            estimated_duration=180,
            ticket_number="WEB-103"
        )
        tasks.append(task3)
        
        # Mobile App Tasks
        task4 = Task(
            title="User Authentication System",
            description="Implement secure login and registration system",
            project_id=project2.id,
            status="In Progress",
            priority=3,
            estimated_duration=360,
            ticket_number="MOB-201"
        )
        tasks.append(task4)
        
        # Status updates for task4
        status_updates4 = [
            StatusUpdate(
                task_id=4,
                status="Not Started",
                notes="Initial planning phase",
                created_at=datetime.now(pytz.UTC) - timedelta(days=8)
            ),
            StatusUpdate(
                task_id=4,
                status="In Progress",
                notes="Started implementing OAuth",
                created_at=datetime.now(pytz.UTC) - timedelta(days=6)
            ),
            StatusUpdate(
                task_id=4,
                status="On Hold",
                notes="Waiting for security review",
                created_at=datetime.now(pytz.UTC) - timedelta(days=4)
            ),
            StatusUpdate(
                task_id=4,
                status="In Progress",
                notes="Implementing security recommendations",
                created_at=datetime.now(pytz.UTC) - timedelta(days=1)
            )
        ]
        
        task5 = Task(
            title="Push Notification System",
            description="Implement push notifications for mobile app",
            project_id=project2.id,
            status="Not Started",
            priority=2,
            estimated_duration=240,
            ticket_number="MOB-202"
        )
        tasks.append(task5)
        
        # Database Migration Tasks
        task6 = Task(
            title="Schema Design",
            description="Design new database schema with improved performance",
            project_id=project3.id,
            status="Completed",
            priority=3,
            estimated_duration=180,
            ticket_number="DB-301",
            completed_at=datetime.now(pytz.UTC) - timedelta(days=3)
        )
        tasks.append(task6)
        
        # Status updates for task6
        status_updates6 = [
            StatusUpdate(
                task_id=6,
                status="Not Started",
                notes="Initial requirements gathering",
                created_at=datetime.now(pytz.UTC) - timedelta(days=7)
            ),
            StatusUpdate(
                task_id=6,
                status="In Progress",
                notes="Started schema design",
                created_at=datetime.now(pytz.UTC) - timedelta(days=5)
            ),
            StatusUpdate(
                task_id=6,
                status="Completed",
                notes="Schema approved by database team",
                created_at=datetime.now(pytz.UTC) - timedelta(days=3)
            )
        ]
        
        task7 = Task(
            title="Data Migration Scripts",
            description="Write scripts to migrate data to new schema",
            project_id=project3.id,
            status="In Progress",
            priority=3,
            estimated_duration=300,
            ticket_number="DB-302"
        )
        tasks.append(task7)
        
        # Status updates for task7
        status_updates7 = [
            StatusUpdate(
                task_id=7,
                status="Not Started",
                notes="Waiting for schema approval",
                created_at=datetime.now(pytz.UTC) - timedelta(days=3)
            ),
            StatusUpdate(
                task_id=7,
                status="In Progress",
                notes="Writing migration scripts",
                created_at=datetime.now(pytz.UTC) - timedelta(days=1)
            )
        ]
        
        task8 = Task(
            title="Performance Testing",
            description="Test performance of new database schema",
            project_id=project3.id,
            status="Not Started",
            priority=2,
            estimated_duration=240,
            ticket_number="DB-303"
        )
        tasks.append(task8)
        
        # Add all tasks
        db.session.add_all(tasks)
        db.session.commit()
        
        # Add all status updates
        all_status_updates = (
            status_updates1 + status_updates2 + status_updates4 +
            status_updates6 + status_updates7
        )
        db.session.add_all(all_status_updates)
        db.session.commit()
        
        print("Database reset complete with test data!")

if __name__ == "__main__":
    reset_database()
