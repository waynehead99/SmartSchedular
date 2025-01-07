from app import app, db
import sqlalchemy as sa
from sqlalchemy import inspect

def verify_database():
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("Database Tables and Columns:")
        print("============================")
        
        # Get all tables
        tables = inspector.get_table_names()
        
        for table in tables:
            print(f"\nTable: {table}")
            print("-" * (len(table) + 7))
            
            # Get columns
            columns = inspector.get_columns(table)
            for column in columns:
                nullable = "NULL" if column['nullable'] else "NOT NULL"
                type_name = str(column['type'])
                print(f"  - {column['name']}: {type_name} ({nullable})")
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table)
            if foreign_keys:
                print("\n  Foreign Keys:")
                for fk in foreign_keys:
                    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

if __name__ == '__main__':
    verify_database()
