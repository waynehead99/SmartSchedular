"""Add ticket numbers and status updates

This migration adds:
1. ticket_number field to tasks
2. status_updates table for tracking task status history
"""

from app import db
from models import Task, StatusUpdate
from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    # Create status_updates table
    op.create_table(
        'status_update',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add ticket_number column to tasks
    op.add_column('task', sa.Column('ticket_number', sa.String(length=50), nullable=True))
    
    # Create initial status updates from existing tasks
    connection = op.get_bind()
    tasks = connection.execute(sa.text('SELECT id, status, created_at FROM task')).fetchall()
    
    for task in tasks:
        connection.execute(
            sa.text('INSERT INTO status_update (task_id, status, created_at) VALUES (:task_id, :status, :created_at)'),
            {'task_id': task[0], 'status': task[1], 'created_at': task[2]}
        )

def downgrade():
    op.drop_table('status_update')
    op.drop_column('task', 'ticket_number')
