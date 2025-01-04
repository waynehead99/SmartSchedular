"""
Migration script to add task dependencies and time tracking.

This script adds:
1. Task dependencies table
2. Time tracking fields to tasks table
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Task
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///smart_scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

def upgrade():
    """
    Upgrade the database schema to include task dependencies and time tracking.
    """
    with app.app_context():
        # Create task_dependencies table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                dependent_task_id INTEGER NOT NULL,
                prerequisite_task_id INTEGER NOT NULL,
                PRIMARY KEY (dependent_task_id, prerequisite_task_id),
                FOREIGN KEY (dependent_task_id) REFERENCES task (id) ON DELETE CASCADE,
                FOREIGN KEY (prerequisite_task_id) REFERENCES task (id) ON DELETE CASCADE
            )
        """))
        
        # Add time tracking columns to tasks table if they don't exist
        try:
            db.session.execute(text("""
                ALTER TABLE task ADD COLUMN actual_duration INTEGER;
            """))
        except Exception:
            pass  # Column might already exist
            
        try:
            db.session.execute(text("""
                ALTER TABLE task ADD COLUMN started_at DATETIME;
            """))
        except Exception:
            pass
            
        try:
            db.session.execute(text("""
                ALTER TABLE task ADD COLUMN completed_at DATETIME;
            """))
        except Exception:
            pass
        
        # Update task status values
        db.session.execute(text("""
            UPDATE task SET status = 'Not Started' WHERE status = 'Pending';
        """))
        
        db.session.commit()

def downgrade():
    """
    Downgrade the database schema by removing task dependencies and time tracking.
    """
    with app.app_context():
        # Drop task_dependencies table
        db.session.execute(text("DROP TABLE IF EXISTS task_dependencies"))
        
        # Remove time tracking columns from tasks table
        try:
            db.session.execute(text("""
                ALTER TABLE task DROP COLUMN actual_duration;
            """))
        except Exception:
            pass
            
        try:
            db.session.execute(text("""
                ALTER TABLE task DROP COLUMN started_at;
            """))
        except Exception:
            pass
            
        try:
            db.session.execute(text("""
                ALTER TABLE task DROP COLUMN completed_at;
            """))
        except Exception:
            pass
        
        # Revert task status values
        db.session.execute(text("""
            UPDATE task SET status = 'Pending' WHERE status = 'Not Started';
        """))
        
        db.session.commit()

if __name__ == '__main__':
    upgrade()
