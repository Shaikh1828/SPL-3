"""
Quick script to create all DB tables and seed demo users.
"""
import os
os.environ.setdefault("DATABASE_URL", "postgresql://archery:archery_pass@db:5432/archery_db")

from src.models.base import Base
from src.database import engine, SessionLocal

# Import all models so they register with Base
from src.models import user as _user
from src.models import tournament as _tournament
from src.models import scoring as _scoring
from src.models import camera as _camera
from src.models import audit as _audit

from src.security import hash_password
from src.models.user import User

print("Creating tables...")
Base.metadata.create_all(engine)
print("Tables created!")

db = SessionLocal()
try:
    demo_users = [
        {"username": "admin", "email": "admin@archery.local", "password": "admin123!", "role": "admin"},
        {"username": "scorer", "email": "scorer@archery.local", "password": "scorer123!", "role": "scorer"},
        {"username": "scorer2", "email": "scorer2@archery.local", "password": "scorer123!", "role": "scorer"},
        {"username": "spectator1", "email": "spectator1@archery.local", "password": "Spectator123!", "role": "spectator"},
    ]
    for u in demo_users:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if existing:
            existing.password_hash = hash_password(u["password"])
            existing.role = u["role"]
            print(f"Updated user: {u['username']}")
        else:
            new_user = User(
                username=u["username"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                is_active=True,
            )
            db.add(new_user)
            print(f"Created user: {u['username']}")
    db.commit()
    print("=== Demo users ready ===")
    print("  admin   / admin123!")
    print("  scorer  / scorer123!")
    print("  scorer2 / scorer123!")
finally:
    db.close()
