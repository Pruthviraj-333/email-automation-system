"""
Database Migration: Add Google OAuth columns to users table
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# Parse DATABASE_URL
parts = DATABASE_URL.replace('postgresql://', '').split('@')
user_pass = parts[0].split(':')
host_port_db = parts[1].split('/')
host_port = host_port_db[0].split(':')

conn = psycopg2.connect(
    dbname=host_port_db[1],
    user=user_pass[0],
    password=user_pass[1],
    host=host_port[0],
    port=host_port[1] if len(host_port) > 1 else '5432'
)

cursor = conn.cursor()

try:
    print("📝 Starting Google OAuth migration...")
    
    # Make hashed_password nullable
    print("1. Making hashed_password nullable...")
    cursor.execute("""
        ALTER TABLE users 
        ALTER COLUMN hashed_password DROP NOT NULL;
    """)
    
    # Add google_id column
    print("2. Adding google_id column...")
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;
    """)
    
    # Add picture column
    print("3. Adding picture column...")
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS picture VARCHAR(512);
    """)
    
    # Add auth_provider column
    print("4. Adding auth_provider column...")
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(50) DEFAULT 'email';
    """)
    
    # Update existing users to have 'email' as auth_provider
    print("5. Updating existing users...")
    cursor.execute("""
        UPDATE users 
        SET auth_provider = 'email' 
        WHERE auth_provider IS NULL;
    """)
    
    # Add index on google_id
    print("6. Adding index on google_id...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
    """)
    
    conn.commit()
    print("✅ Migration completed successfully!")
    print("\nYou can now use 'Sign in with Google' feature!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()