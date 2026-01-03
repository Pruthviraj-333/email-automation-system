# Test script - save as test_db.py
from db import Database

db = Database()
print("✓ Database connected successfully!")
stats = db.get_stats()
print(f"Stats: {stats}")