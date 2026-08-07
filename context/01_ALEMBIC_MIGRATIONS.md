# Alembic — Database Migration System

## Alembic কী?
**Alembic** হলো SQLAlchemy এর official database migration tool। এটি database schema versioning এবং migration handle করে — যেমন নতুন table তৈরি করা, column add/remove করা, index তৈরি করা ইত্যাদি।

## কেন Alembic ব্যবহার করা হয়েছে?

### Problem যেটা Alembic solve করে:
1. **Schema Versioning**: Database schema র পরিবর্তনগুলো track করা — কে, কখন, কি change করেছে
2. **Safe Migrations**: Production database কে safely update করা (data loss ছাড়া)
3. **Rollback Support**: কোনো migration problem হলে আগের version এ ফিরে যাওয়া (`downgrade`)
4. **Team Collaboration**: Multiple developer একসাথে database schema নিয়ে কাজ করতে পারে
5. **Auto-generate**: SQLAlchemy model থেকে automatically migration script generate করতে পারে

### Alembic ছাড়া কি হতো?
- প্রতিবার schema change হলে manually SQL query লিখে database alter করতে হতো
- Version history থাকতো না
- Multiple environment এ (dev, staging, prod) consistent schema রাখা কঠিন হতো
- Rollback impossible হতো

## Project এ Alembic Folder Structure

```
alembic/
├── __init__.py          # Package initializer
├── env.py               # Migration environment configuration
└── versions/            # Migration scripts (chronological)
    ├── __init__.py
    ├── 001_initial_schema.py      # প্রথম migration — সব table তৈরি
    └── 002_add_missing_fields.py  # পরবর্তী migration — missing fields add
```

## Key Files Explained

### `alembic.ini` (Root directory তে)
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://archery:archery_pass@localhost:5432/archery_db
```
- `script_location`: migration scripts কোথায় আছে
- `sqlalchemy.url`: Database connection URL (env.py তে override হয়)

### `alembic/env.py`
```python
from src.database import Base

# env variable থেকে database URL নেয়
database_url = os.getenv('DATABASE_URL', 'sqlite:///./archery.db')
config.set_main_option('sqlalchemy.url', database_url)

# SQLAlchemy model এর metadata ব্যবহার করে
target_metadata = Base.metadata
```
- এই file Alembic কে বলে দেয় কিভাবে database connect করতে হবে
- `Base.metadata` দিয়ে SQLAlchemy ORM models এর সাথে sync থাকে
- Offline (URL only) এবং Online (live connection) দুইভাবে migration run করতে পারে

### `001_initial_schema.py` — Initial Migration
এই migration system এর সব base table তৈরি করে:

| Table                    | Purpose                                    |
|--------------------------|-------------------------------------------|
| `users`                  | User accounts (admin, scorer, spectator)  |
| `tournaments`            | Archery tournaments/competitions          |
| `sessions`               | Scoring sessions within tournaments       |
| `session_archers`        | Archers participating in each session     |
| `scores`                 | Individual arrow scores with zone/points  |
| `cameras`                | Connected cameras for image capture       |
| `camera_lane_assignments`| Camera-to-lane mapping per session       |
| `audit_logs`             | Audit trail for all actions              |

### `002_add_missing_fields.py` — Second Migration
ORM model update এর পর missing fields add করে (যেমন `archer_id`, `current_round`, `completed_at` ইত্যাদি)

## Alembic Commands

```bash
# নতুন migration generate করা (model change এর পর)
alembic revision --autogenerate -m "description"

# সব migration apply করা
alembic upgrade head

# এক step upgrade
alembic upgrade +1

# এক step rollback
alembic downgrade -1

# Current revision দেখা
alembic current

# Migration history দেখা
alembic history
```

## Database.py তে Alembic Integration
```python
def run_migrations():
    """Run Alembic database migrations."""
    from alembic.config import Config
    from alembic.command import upgrade
    alembic_cfg = Config("alembic.ini")
    upgrade(alembic_cfg, "head")
```
Backend start হওয়ার সময় programmatically migration run করা যায়।

## সারাংশ
Alembic এই project এ **database schema management** এর জন্য ব্যবহৃত হয়েছে। এটি ensure করে যে:
- Database schema সবসময় code এর সাথে sync থাকে
- Schema changes version controlled এবং reversible
- Team এর সবাই same database structure ব্যবহার করে
- Production deployment safely করা যায়
