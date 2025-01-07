from app import app, db
import sqlalchemy as sa

def migrate():
    with app.app_context():
        # Create new tables
        db.create_all()
        print("Database tables created successfully")
        
        # Add new columns using raw SQL
        with db.engine.connect() as conn:
            try:
                conn.execute(sa.text("""
                    ALTER TABLE calendar ADD COLUMN task_id INTEGER REFERENCES task(id);
                """))
                conn.commit()
                print("Added task_id column to calendar table")
            except Exception as e:
                if "duplicate column" not in str(e):
                    raise e
                print("task_id column already exists in calendar table")

if __name__ == '__main__':
    migrate()
