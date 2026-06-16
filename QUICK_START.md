# Quick Start Guide

This guide provides step-by-step instructions to get the **Automated Archery Scoring System** (Frontend + Backend) running on a completely new device.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Python 3.11+**: Required for the FastAPI backend.
2. **Node.js 20+ & npm**: Required for the React frontend.
3. **PostgreSQL 15+**: The primary relational database.
4. **Redis 7+**: Used for high-performance caching and WebSocket pub/sub.
5. **Git**: To clone the repository.

*Note: If you prefer Docker, you can use the provided `docker-compose.yml` to spin up the database and Redis instantly. The instructions below assume local manual execution for development purposes.*

---

## 🖥️ Part 1: Backend Setup (FastAPI)

The backend handles all database operations, AI scoring logic, and WebSocket routing.

### 1. Clone the Repository
```bash
git clone <your-repository-url> SPL-3
cd SPL-3
```

### 2. Configure Environment Variables
Copy the example environment file and edit it if your local PostgreSQL/Redis credentials differ from the defaults.
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```
Ensure your `.env` contains valid connection strings:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/archery_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your_super_secret_key_here
```

### 3. Setup Python Environment
We recommend using [Poetry](https://python-poetry.org/) (as defined in `pyproject.toml`) or standard `venv`.

**Using standard pip & venv:**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies (if a requirements.txt exists)
pip install -r requirements.txt

# Or using Poetry:
pip install poetry
poetry install
```

### 4. Initialize the Database
Ensure your PostgreSQL server is running and the database specified in your `.env` (e.g., `archery_db`) exists.

Run Alembic migrations to create all tables:
```bash
alembic upgrade head
```

Seed the database with initial testing data (admin users, mock tournaments):
```bash
python -m scripts.seed_data
```
*Note: The default seeded admin credentials are usually `admin` / `admin123!` or `testuser` / `TestPassword123!` (Check `scripts/seed_data.py` for exact details).*

### 5. Start the Backend Server
Start the FastAPI server with hot-reloading enabled:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
**Success Check:** Open your browser and navigate to `http://localhost:8000/docs` to see the interactive Swagger API documentation.

---

## 🎨 Part 2: Frontend Setup (React + Vite)

The frontend is a modern SPA that connects to the backend API.

### 1. Navigate to the Frontend Directory
Open a **new terminal window** (keep the backend running in the first one) and navigate to the frontend folder:
```bash
cd SPL-3/frontend
```

### 2. Install Dependencies
Install all required Node modules (React, Tailwind, Zustand, Radix UI, etc.):
```bash
npm install
```

### 3. Start the Development Server
Launch the Vite development server:
```bash
npm run dev
```

**Success Check:** Vite will output a local URL, typically `http://localhost:5173`. Open this URL in your browser.

---

## 🎯 Part 3: Using the Application

With both the backend and frontend running, you are ready to use the system!

1. **Login**: Go to `http://localhost:5173/login`. Use the seeded credentials (e.g., `admin` / `admin123!`) to sign in.
2. **Dashboard**: Upon login, you will see the system dashboard. It will show "System Health: Healthy" if the frontend successfully connected to your backend, database, and Redis.
3. **Tournaments**: Navigate to the Tournaments page to create a new Tournament and Session.
4. **Scoring**: Once a session is "Active", navigate to the Scoring page. The WebSocket connection will automatically establish, and you can trigger "Calculate" commands to simulate scoring.
5. **Real-Time Updates**: Open the application in two different browser windows. Record a score in one, and watch the Leaderboard instantly update in the other via WebSockets!

## 🛑 Stopping the System

To stop the system, simply press `Ctrl + C` in both terminal windows.
