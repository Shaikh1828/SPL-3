"""
Database initialization script.
Creates all tables and seeds initial data.
"""
import sys
sys.path.insert(0, '/app')

from src.models.base import Base
from src.database import engine, SessionLocal
from src.models import user, tournament, scoring, camera  # noqa: F401
from src.security import hash_password
from src.models.user import User

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")

# Seed users
db = SessionLocal()
try:
    users_to_seed = [
        {"username": "admin",      "email": "admin@archery.local",      "password": "admin123!",    "role": "admin"},
        {"username": "scorer",     "email": "scorer@archery.local",     "password": "scorer123!",   "role": "scorer"},
        {"username": "scorer2",    "email": "scorer2@archery.local",    "password": "scorer123!",   "role": "scorer"},
        {"username": "archer1",    "email": "archer1@archery.local",    "password": "Archer123!",   "role": "archer"},
        {"username": "spectator1", "email": "spectator1@archery.local", "password": "Spectator123!","role": "spectator"},
    ]

    for u in users_to_seed:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            new_user = User(
                username=u["username"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                is_active=True,
            )
            db.add(new_user)
            print(f"  Created user: {u['username']} ({u['role']})")
        else:
            print(f"  User already exists: {u['username']}")

    db.commit()
    print("\nSeed data complete!")
    print("\nDemo credentials:")
    print("  admin     / admin123!")
    print("  scorer    / scorer123!")
    print("  archer1   / Archer123!")

except Exception as e:
    print(f"Error: {e}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
