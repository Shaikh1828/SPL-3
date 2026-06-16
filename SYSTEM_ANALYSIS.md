# 🏹 Automated Archery Scoring System — সম্পূর্ণ বিশ্লেষণ

## 🗺️ System Overview

এটি একটি **AI-Assisted Archery Tournament Management System**। Real-time camera থেকে arrow detect করে score দেওয়া হয়।

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)               │
│  http://localhost:5173                                    │
│  TypeScript | TailwindCSS | Zustand | Axios | Recharts  │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API + WebSocket
┌─────────────────────▼───────────────────────────────────┐
│                   BACKEND (FastAPI)                      │
│  http://localhost:8000                                   │
│  Python 3.11+ | SQLAlchemy ORM | JWT Auth               │
└──────────┬────────────────────┬────────────────────────-┘
           │                    │
┌──────────▼──────┐   ┌────────▼────────┐
│   PostgreSQL    │   │     Redis        │
│   (Database)    │   │  (Cache/PubSub) │
│   Port: 5432    │   │  Port: 6379     │
└─────────────────┘   └─────────────────┘
```

---

## 📦 Database Tables (8টি)

| Table | কী করে |
|-------|--------|
| `users` | User accounts (admin/scorer/spectator/archer) |
| `tournaments` | Tournament container |
| `sessions` | একটি tournament-এর মধ্যে scoring round |
| `session_archers` | কোন session-এ কোন archer আছে |
| `scores` | Individual arrow scores (zone + points) |
| `cameras` | Physical camera devices (USB/RTSP/HTTP) |
| `camera_lane_assignments` | Camera কোন lane-এ assigned |
| `audit_logs` | System activity logs |

### ER Diagram (সংক্ষেপে)
```
User ──────── Tournament ──────── Session ──────── Score
                                      │
                              SessionArcher ────── Score
                                      │
                           CameraLaneAssignment
                                      │
                                   Camera
```

---

## 👤 User Roles (4টি)

| Role | Permission |
|------|-----------|
| **admin** | সব কিছু করতে পারে |
| **scorer** | Score record করতে পারে, session manage করতে পারে |
| **spectator** | শুধু leaderboard ও result দেখতে পারে |
| **archer** | নিজের score দেখতে পারে (future feature) |

---

## 🔌 Backend API Endpoints (26টি)

### Auth (`/auth`)
| Method | Endpoint | কী করে |
|--------|----------|--------|
| POST | `/auth/register` | নতুন user তৈরি |
| POST | `/auth/login` | Login → JWT token |
| POST | `/auth/refresh` | Token refresh |
| POST | `/auth/reset-password` | Password change |

### Tournaments
| Method | Endpoint | কী করে |
|--------|----------|--------|
| GET | `/tournaments` | Tournament list |
| POST | `/tournaments` | নতুন tournament তৈরি |
| GET | `/tournaments/{id}` | Tournament details |
| PUT | `/tournaments/{id}` | Tournament update |

### Sessions
| Method | Endpoint | কী করে |
|--------|----------|--------|
| GET | `/tournaments/{id}/sessions` | Session list |
| POST | `/tournaments/{id}/sessions` | নতুন session |
| GET | `/sessions/{id}` | Session details |
| PATCH | `/sessions/{id}` | Status update (active/paused/completed) |
| POST | `/sessions/{id}/archers` | Archer add to session |

### Scores
| Method | Endpoint | কী করে |
|--------|----------|--------|
| POST | `/sessions/{id}/scores` | Score record |
| GET | `/sessions/{id}/scores` | Score list |
| GET | `/sessions/scores/{id}` | Single score |
| POST | `/sessions/scores/{id}/validate` | AI validation |

### Cameras
| Method | Endpoint | কী করে |
|--------|----------|--------|
| GET | `/sessions/{id}/cameras` | Camera list |
| POST | `/sessions/{id}/cameras/{cam_id}/connect` | Camera connect |
| POST | `/sessions/{id}/cameras/{cam_id}/disconnect` | Camera disconnect |
| POST | `/cameras/{id}/reconnect` | Auto-reconnect |
| POST | `/sessions/{id}/cameras/assign` | Camera → Lane assign |

### Leaderboard
| Method | Endpoint | কী করে |
|--------|----------|--------|
| GET | `/sessions/{id}/leaderboard` | Live leaderboard (Redis cached) |

### Reports
| Method | Endpoint | কী করে |
|--------|----------|--------|
| GET | `/sessions/{id}/report` | PDF/CSV/JSON report |

### Health
| Method | Endpoint | কী করে |
|--------|----------|--------|
| GET | `/health` | Simple health check |
| GET | `/health/detailed` | DB + Redis + Storage health |

### WebSocket
| Protocol | Endpoint | কী করে |
|----------|----------|--------|
| WS | `/ws/{session_id}` | Real-time score events |

---

## 🎨 Frontend Pages (8টি)

| Page | Route | কী করে |
|------|-------|--------|
| LoginPage | `/login` | JWT login |
| DashboardPage | `/dashboard` | System overview, live leaderboard, health |
| TournamentsPage | `/tournaments` | Tournament CRUD |
| ScoringPage | `/scoring` | Camera feeds + score calculation |
| CamerasPage | `/cameras` | Camera management |
| ReportsPage | `/reports` | Analytics + export |
| UsersPage | `/users` | User management |
| SettingsPage | `/settings` | AI engine + storage config |

---

## 🤖 AI Pipeline (Image Service)

Arrow detection করে **3-tier fallback chain** দিয়ে:

1. **Color Detection** — HSV range দিয়ে red arrow খোঁজে (confidence > 0.7 হলে শেষ)
2. **Edge Detection** — Canny edge + contours দিয়ে (confidence > 0.7 হলে শেষ)
3. **ML Detection** — Placeholder (production-এ YOLO/CNN model থাকবে)

Zone calculation: Target center থেকে distance → Zone 0-10 map করে।

---

## ⚡ Real-Time Flow

```
Camera Image → AI Detection → Score Recording → Event Bus
                                                      │
                                              WebSocket Broadcast
                                                      │
                                            Frontend Leaderboard Update
                                              (Redis cached, 1-min TTL)
```

---

## ❌ যা INCOMPLETE আছে

### 🔴 Critical (সিস্টেম চলবে না এগুলো ছাড়া)

| # | কী incomplete | কোথায় সমস্যা |
|---|--------------|--------------|
| 1 | **User Management API** — Backend-এ কোনো `/users` endpoint নেই | `src/api/` তে কোনো `users.py` নেই। `UsersPage.tsx` mock data দিয়ে চলছে |
| 2 | **Admin: User list/create/role-change** — Admin দিয়ে user manage করার কোনো API নেই | `auth.py`-এ register আছে কিন্তু admin-level user management নেই |
| 3 | **ScoringPage mock data** — Score record করার সময় hardcoded archer_id ব্যবহার করছে | `ScoringPage.tsx` line 131-137: `session_archer_id: laneId` (mock), `zone: 9` (hardcoded) |
| 4 | **CamerasPage "Add Camera" button** — কাজ করে না | `CamerasPage.tsx` line 63: শুধু button আছে, কোনো modal/logic নেই |
| 5 | **Camera Reconnect API call missing** | `CamerasPage.tsx` line 33: API call না করে সরাসরি state update করছে |
| 6 | **SettingsPage "Save Changes"** — কাজ করে না | Static form, কোনো API call নেই |

### 🟡 Medium (Feature incomplete)

| # | কী incomplete | বিস্তারিত |
|---|--------------|-----------|
| 7 | **ML Model** — AI detection step 3 placeholder | `image_service.py` line 181-186: `_detect_arrow_ml()` শুধু `return {zone: None}` |
| 8 | **Archer role** — archer নিজের score দেখার feature নেই | User model-এ role আছে কিন্তু archer-specific endpoint নেই |
| 9 | **Camera Settings/Delete buttons** — কাজ করে না | `CamerasPage.tsx` line 91-96: Settings আর Trash button UI আছে, logic নেই |
| 10 | **UsersPage Edit button** — কাজ করে না | Mock data দিয়ে চলছে, real API নেই |
| 11 | **ScoringPage "End Session" button** — কাজ করে না | `ScoringPage.tsx` line 199: Button আছে, API call নেই |
| 12 | **WebSocket unsubscribe** — Memory leak সম্ভাবনা | `websocket.py` line 164: comment করা "In production, would unsubscribe" |
| 13 | **Frontend `/api/users` client** — নেই | `frontend/src/api/` তে `users.ts` নেই |

### 🟢 Minor (Polish)

| # | কী incomplete |
|---|--------------|
| 14 | SettingsPage-এ confidence threshold/target face type save হয় না |
| 15 | Reports page-এ কিছু chart/export feature placeholder |
| 16 | Audit log viewing endpoint নেই (DB-তে table আছে কিন্তু API নেই) |

---

## 🗄️ Database এ User/Admin List দেখার প্রসেস

### Method 1: pgAdmin (GUI) — সহজ
1. pgAdmin খুলো
2. Connect: `localhost:5432`, database: `archery_db`
3. Left panel → `Schemas` → `public` → `Tables` → `users`
4. Right-click → **View/Edit Data** → **All Rows**

### Method 2: psql (Terminal)
```bash
# Docker চললে
docker exec -it archery-db psql -U archery_user -d archery_db

# Local PostgreSQL হলে
psql -U archery_user -d archery_db

# User list দেখো
SELECT id, username, email, role, is_active, created_at FROM users;

# শুধু admin দেখো
SELECT * FROM users WHERE role = 'admin';

# শুধু active user
SELECT username, email, role FROM users WHERE is_active = true ORDER BY role;
```

### Method 3: FastAPI Swagger UI (Backend চলা অবস্থায়)
1. Browser: `http://localhost:8000/docs`
2. প্রথমে `/auth/login` দিয়ে login করো → token নাও
3. "Authorize" button → token paste করো
4. **⚠️ কিন্তু এখন `/users` endpoint নেই!** তাই এটা দিয়ে user list দেখা সম্ভব না।

### Method 4: SQLite/DB Browser (যদি SQLite ব্যবহার করো)
```bash
# .env দেখো DATABASE_URL
# PostgreSQL হলে: postgresql://user:pass@localhost:5432/archery_db
```

### Method 5: Python Script
```python
# scratch script হিসেবে run করো
from src.database import SessionLocal
from src.models.user import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"ID:{u.id} | {u.username} | {u.role} | Active:{u.is_active}")
db.close()
```

---

## 🔑 Admin User তৈরি করার প্রসেস

Default registration সবাইকে `spectator` role দেয়। Admin তৈরি করতে:

```bash
# psql দিয়ে সরাসরি role change
UPDATE users SET role = 'admin' WHERE username = 'your_username';

# অথবা seed script দিয়ে (যদি থাকে)
python scripts/seed_db.py
```

---

## 📋 System Data Flow (একটি সম্পূর্ণ scoring session)

```
1. Admin login → JWT token পাওয়া
2. Tournament create → POST /tournaments
3. Session create → POST /tournaments/{id}/sessions
4. Archer add → POST /sessions/{id}/archers
5. Camera connect → POST /sessions/{id}/cameras/{cam_id}/connect
6. Camera assign to lane → POST /sessions/{id}/cameras/assign
7. Camera image capture → AI detects arrow → zone + confidence
8. Score record → POST /sessions/{id}/scores
9. Leaderboard update → Redis cache bust → WebSocket broadcast
10. Session complete → PATCH /sessions/{id} (status: completed)
11. Report export → GET /sessions/{id}/report?format=pdf
```
