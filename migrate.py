from app import app, db
from models import Task, StatusUpdate
import sqlalchemy as sa

def migrate():
    with app.app_context():
        # Create new tables
        db.create_all()
        
        # Add new columns using raw SQL
        with db.engine.connect() as conn:
            # Add ticket_number column if it doesn't exist
            conn.execute(sa.text("""
                ALTER TABLE task ADD COLUMN ticket_number VARCHAR(50);
            """))
            
            conn.commit()
        
        # Get existing tasks
        tasks = Task.query.all()
        
        # Create initial status updates for existing tasks
        for task in tasks:
            status_update = StatusUpdate(
                task_id=task.id,
                status=task.status,
                notes="Initial status"
            )
            db.session.add(status_update)
        
        db.session.commit()

if __name__ == '__main__':
    migrate()
