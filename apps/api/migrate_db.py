import sqlite3
import os
import uuid
import datetime

db_path = r"C:\Users\ASUS\ai-interview-platform\apps\api\interview.db"

def audit_and_migrate():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. It will be created by the app on startup.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Current Schema Audit ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Existing Tables: {tables}")

    # Check 'resumes' table
    if 'resumes' in tables:
        cursor.execute("PRAGMA table_info(resumes);")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Resumes Columns: {columns}")
        
        if 'analysis_result' not in columns:
            print("Migration: Adding 'analysis_result' column to 'resumes' table...")
            try:
                cursor.execute("ALTER TABLE resumes ADD COLUMN analysis_result JSON;")
                conn.commit()
                print("SUCCESS: 'analysis_result' added.")
            except Exception as e:
                print(f"FAILED to add column: {e}")
    else:
        print("Table 'resumes' missing. Application will create it on restart.")

    # Check 'interviews' table
    if 'interviews' in tables:
        cursor.execute("PRAGMA table_info(interviews);")
        columns = [col[1] for col in cursor.fetchall()]
        if 'job_role' not in columns:
            print("Migration: Adding 'job_role' column to 'interviews' table...")
            cursor.execute("ALTER TABLE interviews ADD COLUMN job_role VARCHAR;")
        if 'transcript' not in columns:
            print("Migration: Adding 'transcript' column to 'interviews' table...")
            cursor.execute("ALTER TABLE interviews ADD COLUMN transcript JSON;")
        conn.commit()

    print("--- Audit Complete ---")
    conn.close()

if __name__ == "__main__":
    audit_and_migrate()
