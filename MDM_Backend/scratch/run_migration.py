import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from signalmdm.database import DATABASE_URL

print(f"Connecting to {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

sql_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "audit_log_approval_migration.sql")

with open(sql_file, "r") as f:
    sql = f.read()

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()

print("Migration successful.")
