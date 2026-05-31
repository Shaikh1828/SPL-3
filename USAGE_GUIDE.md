# Usage Guide - Archery Scoring System

Complete guide to using the Archery Scoring System for tournament management, scoring, and reporting.

## Table of Contents

1. [User Roles & Permissions](#user-roles--permissions)
2. [User Management](#user-management)
3. [Tournament Management](#tournament-management)
4. [Session Management](#session-management)
5. [Scoring Workflow](#scoring-workflow)
6. [Camera Setup & Management](#camera-setup--management)
7. [Real-Time Features](#real-time-features)
8. [Report Generation](#report-generation)
9. [Common Workflows](#common-workflows)
10. [API Best Practices](#api-best-practices)
11. [Troubleshooting](#troubleshooting)

---

## User Roles & Permissions

### Role Hierarchy

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Admin** | Full system access, user management, all operations | System administrator |
| **Scorer** | Create tournaments/sessions, record scores, generate reports | Event operator, scoring official |
| **Spectator** | View leaderboards, reports (read-only) | Audience, commentator |
| **Archer** | View own scores, personal leaderboard rank | Participant |

### Permission Matrix

| Action | Admin | Scorer | Spectator | Archer |
|--------|-------|--------|-----------|--------|
| Create Tournament | ✅ | ✅ | ❌ | ❌ |
| Create Session | ✅ | ✅ | ❌ | ❌ |
| Record Score | ✅ | ✅ | ❌ | ❌ |
| View Leaderboard | ✅ | ✅ | ✅ | ✅ |
| Generate Report | ✅ | ✅ | ✅ | ❌ |
| Manage Cameras | ✅ | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ❌ | ❌ | ❌ |

---

## User Management

### Create Admin User (First Time Setup)

```bash
# Login with default admin credentials
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "AdminPassword123!"
  }'

# Response:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "bearer",
#   "expires_in": 28800
# }
```

### Register New User

**Via API:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newscorer",
    "email": "scorer@tournament.local",
    "password": "SecurePassword123!"
  }'

# Response (201 Created):
# {
#   "id": 6,
#   "username": "newscorer",
#   "email": "scorer@tournament.local",
#   "role": "archer",          # Default role
#   "is_active": true,
#   "created_at": "2026-05-25T18:00:00Z"
# }
```

**Note**: New users default to "archer" role. Admin must update role in database for scorer/admin:
```bash
# Direct database update (admin only)
# UPDATE users SET role = 'scorer' WHERE username = 'newscorer'
```

### Login User

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newscorer",
    "password": "SecurePassword123!"
  }'

# Save token for all subsequent requests
export TOKEN="eyJ..."
```

### Reset Password

```bash
curl -X POST http://localhost:8000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "current_password": "OldPassword123!",
    "new_password": "NewPassword123!"
  }'

# Response (200):
# {
#   "success": true,
#   "message": "Password reset successfully"
# }
```

### Refresh Expired Token

When access token expires (after 8 hours):
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"

# Response (200):
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer",
#   "expires_in": 28800
# }
```

---

## Tournament Management

### Create Tournament

```bash
curl -X POST http://localhost:8000/api/tournaments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Spring Championship 2026",
    "description": "Annual spring qualifying tournament",
    "location": "Olympic Park",
    "start_date": "2026-06-15",
    "end_date": "2026-06-17"
  }'

# Response (201):
# {
#   "id": 1,
#   "name": "Spring Championship 2026",
#   "description": "Annual spring qualifying tournament",
#   "location": "Olympic Park",
#   "start_date": "2026-06-15",
#   "end_date": "2026-06-17",
#   "created_by": 2,
#   "created_at": "2026-05-25T18:05:00Z",
#   "updated_at": "2026-05-25T18:05:00Z"
# }

export TOURNAMENT_ID=1
```

### List Tournaments

**All tournaments:**
```bash
curl -X GET "http://localhost:8000/api/tournaments?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "items": [...],
#   "total": 3,
#   "skip": 0,
#   "limit": 10
# }
```

**Search tournaments:**
```bash
curl -X GET "http://localhost:8000/api/tournaments?search=Spring" \
  -H "Authorization: Bearer $TOKEN"

# Filters by name or location containing "Spring"
```

### Get Tournament Details

```bash
curl -X GET http://localhost:8000/api/tournaments/$TOURNAMENT_ID \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "id": 1,
#   "name": "Spring Championship 2026",
#   "description": "Annual spring qualifying tournament",
#   "location": "Olympic Park",
#   "start_date": "2026-06-15",
#   "end_date": "2026-06-17",
#   "created_by": 2,
#   "created_at": "2026-05-25T18:05:00Z",
#   "updated_at": "2026-05-25T18:05:00Z"
# }
```

---

## Session Management

### Create Session (Scoring Round)

```bash
curl -X POST http://localhost:8000/api/tournaments/$TOURNAMENT_ID/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Round 1 - Morning Session",
    "round_number": 1,
    "num_lanes": 6,
    "arrows_per_round": 6
  }'

# Response (201):
# {
#   "id": 1,
#   "tournament_id": 1,
#   "name": "Round 1 - Morning Session",
#   "round_number": 1,
#   "status": "active",
#   "start_time": "2026-05-25T18:10:00Z",
#   "end_time": null,
#   "num_lanes": 6,
#   "arrows_per_round": 6,
#   "created_at": "2026-05-25T18:10:00Z",
#   "updated_at": "2026-05-25T18:10:00Z"
# }

export SESSION_ID=1
```

### List Sessions for Tournament

```bash
curl -X GET "http://localhost:8000/api/tournaments/$TOURNAMENT_ID/sessions?status=active" \
  -H "Authorization: Bearer $TOKEN"

# Filter by status: active, paused, completed
```

### Get Session Details

```bash
curl -X GET http://localhost:8000/api/sessions/$SESSION_ID \
  -H "Authorization: Bearer $TOKEN"

# Response includes archer count and score count
```

### Update Session Status

**Pause a session:**
```bash
curl -X PATCH http://localhost:8000/api/sessions/$SESSION_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "status": "paused"
  }'

# Valid transitions:
# - active → paused
# - paused → active
# - active → completed
# - paused → completed
```

**Complete a session:**
```bash
curl -X PATCH http://localhost:8000/api/sessions/$SESSION_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "status": "completed"
  }'
```

### Register Archer in Session

```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/archers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "archer_name": "John Smith",
    "lane_number": 1
  }'

# Response (201):
# {
#   "id": 1,
#   "session_id": 1,
#   "archer_name": "John Smith",
#   "lane_number": 1,
#   "total_score": 0,
#   "registered_at": "2026-05-25T18:15:00Z"
# }

export ARCHER_ID=1
```

**Important**: Each lane can have only one archer per session.

---

## Scoring Workflow

### Record Arrow Score

```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/scores \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_archer_id": 1,
    "round_number": 1,
    "arrow_number": 1,
    "zone": 8,
    "points": 8,
    "image_path": "/storage/raw/1/arrow_20260525_001.jpg"
  }'

# Response (201):
# {
#   "id": 1,
#   "session_id": 1,
#   "session_archer_id": 1,
#   "round_number": 1,
#   "arrow_number": 1,
#   "zone": 8,
#   "points": 8,
#   "image_path": "/storage/raw/1/arrow_20260525_001.jpg",
#   "validated_by_ai": false,
#   "confidence": 0.85,
#   "created_at": "2026-05-25T18:20:00Z",
#   "updated_at": "2026-05-25T18:20:00Z"
# }

export SCORE_ID=1
```

**Features**:
- Automatic retry with exponential backoff on database failures
- Validates zone (0-10) and points (0-10)
- Optional image path for computer vision
- AI confidence score included

### Valid Score Ranges

| Field | Min | Max | Notes |
|-------|-----|-----|-------|
| zone | 0 | 10 | 10 = center, 0 = miss |
| points | 0 | 10 | Typically matches zone |
| round_number | 1 | ∞ | Sequential per session |
| arrow_number | 1 | 6 | Per round (configurable) |

### Get Archer Scores

```bash
# All scores for archer in session
curl -X GET "http://localhost:8000/api/sessions/$SESSION_ID/scores?skip=0&limit=100" \
  -H "Authorization: Bearer $TOKEN"

# Filter by round
curl -X GET "http://localhost:8000/api/sessions/$SESSION_ID/scores?round_number=1" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Individual Score

```bash
curl -X GET http://localhost:8000/api/scores/$SCORE_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Validate Score (AI)

Flag score for AI validation or mark as validated:

```bash
curl -X POST http://localhost:8000/api/scores/$SCORE_ID/validate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "validated_by_ai": true,
    "confidence": 0.92
  }'

# Response (200):
# {
#   "id": 1,
#   "session_id": 1,
#   "session_archer_id": 1,
#   "round_number": 1,
#   "arrow_number": 1,
#   "zone": 8,
#   "points": 8,
#   "image_path": "/storage/raw/1/arrow_20260525_001.jpg",
#   "validated_by_ai": true,
#   "confidence": 0.92,
#   "created_at": "2026-05-25T18:20:00Z",
#   "updated_at": "2026-05-25T18:25:00Z"
# }
```

---

## Camera Setup & Management

### List Available Cameras

```bash
curl -X GET http://localhost:8000/api/sessions/$SESSION_ID/cameras \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "items": [
#     {
#       "id": 1,
#       "name": "Lane 1 Camera",
#       "camera_type": "USB",
#       "connection_url": null,
#       "status": "disconnected",
#       "last_heartbeat": null,
#       "created_at": "2026-05-20T10:00:00Z",
#       "updated_at": "2026-05-20T10:00:00Z"
#     }
#   ],
#   "total": 1
# }
```

### Connect Camera

```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/cameras/1/connect \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "id": 1,
#   "name": "Lane 1 Camera",
#   "status": "connected",
#   "last_heartbeat": "2026-05-25T18:30:00Z",
#   ...
# }
```

### Disconnect Camera

```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/cameras/1/disconnect \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "id": 1,
#   "name": "Lane 1 Camera",
#   "status": "disconnected",
#   ...
# }
```

### Auto-Reconnect Camera (Pattern #5)

```bash
curl -X POST http://localhost:8000/api/cameras/1/reconnect \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "camera_id": 1,
#   "status": "connected",
#   "retry_count": 2,
#   "last_attempt": "2026-05-25T18:35:00Z",
#   "message": "Camera reconnected successfully"
# }

# Features:
# - Exponential backoff: 1s → 2s → 4s → 8s
# - Max retries: 4
# - User notification on successful reconnection
# - Automatic retry every 30 seconds if disconnected
```

### Assign Camera to Lane

```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/cameras/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "camera_id": 1,
    "lane_number": 1
  }'

# Response (201):
# {
#   "id": 1,
#   "session_id": 1,
#   "camera_id": 1,
#   "lane_number": 1,
#   "assigned_at": "2026-05-25T18:40:00Z"
# }
```

### Camera Types

Supported camera types:

| Type | Connection | URL Example | Notes |
|------|-----------|-------------|-------|
| **USB** | Direct | (none) | USB camera connected to server |
| **RTSP** | Network | rtsp://192.168.1.10:554/stream | Network camera (stream protocol) |
| **HTTP** | Network | http://192.168.1.11:8080/video | Network camera (HTTP MJPEG) |

---

## Real-Time Features

### WebSocket Connection

Connect to real-time event stream:

```bash
# Using WebSocket protocol
ws://localhost:8000/api/ws/{session_id}

# With authentication:
# Pass access_token via Authorization header
```

**Example (JavaScript):**
```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/api/ws/1`);

ws.onopen = () => {
    console.log('Connected to real-time stream');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Event:', message.event_type, message.data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected from stream');
};
```

### Real-Time Events

Events broadcast to all connected clients:

| Event | Payload | When |
|-------|---------|------|
| **SCORE_RECORDED** | score_id, points, zone | Arrow score entered |
| **SCORE_VALIDATED** | score_id, confidence | Score validated by AI |
| **SESSION_STATE_CHANGED** | session_id, status | Session paused/completed |
| **LEADERBOARD_UPDATED** | session_id, rank_changes | Leaderboard changed |
| **CAMERA_CONNECTED** | camera_id, status | Camera connected |
| **CAMERA_DISCONNECTED** | camera_id, status | Camera disconnected |
| **SESSION_CREATED** | session_id, name | New session created |

**Example Event:**
```json
{
  "event_type": "SCORE_RECORDED",
  "timestamp": "2026-05-25T18:45:00Z",
  "data": {
    "score_id": 1,
    "session_archer_id": 1,
    "points": 8,
    "zone": 8,
    "round_number": 1,
    "arrow_number": 1
  }
}
```

### Get Live Leaderboard (Cached)

```bash
curl -X GET "http://localhost:8000/api/sessions/$SESSION_ID/leaderboard?limit=100" \
  -H "Authorization: Bearer $TOKEN"

# Response (200):
# {
#   "session_id": 1,
#   "total_archers": 6,
#   "items": [
#     {
#       "rank": 1,
#       "archer_id": 1,
#       "archer_name": "John Smith",
#       "lane_number": 1,
#       "total_score": 48,
#       "round_1_score": 24,
#       "round_2_score": 24,
#       "arrows_recorded": 12
#     },
#     {
#       "rank": 2,
#       "archer_name": "Jane Doe",
#       "lane_number": 2,
#       "total_score": 45,
#       ...
#     }
#   ],
#   "cached": true,
#   "cache_ttl": 60,
#   "last_updated": "2026-05-25T18:45:00Z"
# }

# Features:
# - Cached with 1-minute TTL (Pattern #13)
# - Automatically invalidated on score changes
# - Bypass cache: use_cache=false parameter
```

**Skip cache:**
```bash
curl -X GET "http://localhost:8000/api/sessions/$SESSION_ID/leaderboard?use_cache=false" \
  -H "Authorization: Bearer $TOKEN"

# Directly queries database (slower, always current)
```

---

## Report Generation

### Generate Report

**PDF Format:**
```bash
curl -X POST "http://localhost:8000/api/sessions/$SESSION_ID/reports?format=pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -o session_report.pdf

# Downloads file: session_report.pdf
```

**CSV Format:**
```bash
curl -X POST "http://localhost:8000/api/sessions/$SESSION_ID/reports?format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  -o session_report.csv
```

**JSON Format:**
```bash
curl -X POST "http://localhost:8000/api/sessions/$SESSION_ID/reports?format=json" \
  -H "Authorization: Bearer $TOKEN" \
  -o session_report.json
```

### Report Contents

All reports include:

**Header Information:**
- Tournament name, dates, location
- Session name, round number, status
- Report generation timestamp

**Leaderboard:**
- All archers ranked by total_score DESC
- Rank, name, lane, total score, per-round scores
- Arrow count

**Summary Statistics:**
- Total archers
- Total arrows recorded
- Average score
- High score, low score
- Standard deviation

**Per-Archer Breakdown (PDF/JSON only):**
- All scores by round and arrow
- Zone vs points
- Image paths (if available)
- AI validation status

### Retrieve Pre-Generated Report

```bash
curl -X GET "http://localhost:8000/api/sessions/$SESSION_ID/reports/summary" \
  -H "Authorization: Bearer $TOKEN"

# Supported types:
# - summary: Quick leaderboard snapshot
# - detailed: Full score breakdown
# - pdf: Full PDF report
# - csv: CSV leaderboard
# - json: JSON full report
```

---

## Common Workflows

### Workflow 1: Quick Tournament Setup & Scoring

```bash
#!/bin/bash

# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"AdminPassword123!"}' \
  | jq -r '.access_token')

# 2. Create tournament
TOURN=$(curl -s -X POST http://localhost:8000/api/tournaments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Quick Tournament",
    "location": "Arena",
    "start_date": "2026-05-25",
    "end_date": "2026-05-25"
  }')
TOURN_ID=$(echo $TOURN | jq -r '.id')

# 3. Create session
SESSION=$(curl -s -X POST http://localhost:8000/api/tournaments/$TOURN_ID/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Round 1",
    "round_number": 1,
    "num_lanes": 2,
    "arrows_per_round": 3
  }')
SESSION_ID=$(echo $SESSION | jq -r '.id')

# 4. Register archers
for LANE in 1 2; do
  curl -s -X POST http://localhost:8000/api/sessions/$SESSION_ID/archers \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{
      \"archer_name\": \"Archer $LANE\",
      \"lane_number\": $LANE
    }" > /dev/null
done

# 5. Record scores (quick simulation)
ARCHER_IDS=(1 2)
for AID in "${ARCHER_IDS[@]}"; do
  for ROUND in 1 2; do
    for ARROW in 1 2 3; do
      ZONE=$((RANDOM % 10 + 1))
      curl -s -X POST http://localhost:8000/api/sessions/$SESSION_ID/scores \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{
          \"session_archer_id\": $AID,
          \"round_number\": $ROUND,
          \"arrow_number\": $ARROW,
          \"zone\": $ZONE,
          \"points\": $ZONE
        }" > /dev/null
    done
  done
done

# 6. Get final results
echo "=== Final Leaderboard ==="
curl -s -X GET http://localhost:8000/api/sessions/$SESSION_ID/leaderboard \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items | sort_by(.rank)[]'

# 7. Generate PDF report
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/reports?format=pdf \
  -H "Authorization: Bearer $TOKEN" \
  -o tournament_results.pdf

echo "✅ Tournament complete! Report saved to tournament_results.pdf"
```

### Workflow 2: Real-Time Scoring with WebSocket

**Frontend (JavaScript):**
```javascript
// Connect to real-time stream
const socket = new WebSocket('ws://localhost:8000/api/ws/1');

// Listen for score updates
socket.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.event_type === 'SCORE_RECORDED') {
        console.log(`Score recorded: ${msg.data.archer_id} - Zone ${msg.data.zone}`);
        updateScoreboardUI(msg.data);
    } else if (msg.event_type === 'LEADERBOARD_UPDATED') {
        console.log('Leaderboard changed');
        refreshLeaderboard();
    }
};

// Function to update UI when score recorded
function updateScoreboardUI(scoreData) {
    // Update real-time scoreboard
    // Highlight new score
    // Play notification sound
    // Animate leaderboard changes
}

// Function to refresh leaderboard
function refreshLeaderboard() {
    fetch(`/api/sessions/1/leaderboard?use_cache=false`)
        .then(r => r.json())
        .then(data => {
            // Update leaderboard display
            displayLeaderboard(data.items);
        });
}
```

---

## API Best Practices

### Rate Limiting

**Limit**: 1000 requests/minute per IP  
**Headers**: 
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1653491820
```

**When limited (429 Too Many Requests):**
```python
# Wait until X-RateLimit-Reset timestamp
reset_time = int(response.headers['X-RateLimit-Reset'])
wait_seconds = reset_time - time.time()
print(f"Rate limited. Wait {wait_seconds} seconds")
```

### Error Handling

All errors follow standard format:
```json
{
  "detail": "Error message",
  "status": 400,
  "timestamp": "2026-05-25T19:00:00Z"
}
```

**Handle gracefully:**
```python
import requests

def api_call(method, endpoint, data=None, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        response = requests.request(method, endpoint, json=data, headers=headers, timeout=10)
        response.raise_for_status()  # Raise for 4xx/5xx
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limited!")
            # Implement exponential backoff
        elif e.response.status_code == 401:
            print("Unauthorized - refresh token")
            # Get new token
        else:
            print(f"API Error: {e.response.status_code}")
            print(e.response.json())
    except requests.exceptions.Timeout:
        print("Request timeout")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

### Idempotency

For create operations, use idempotent keys (optional):

```bash
# Same request ID for retries
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/scores \
  -H "Idempotency-Key: archer-1-round-1-arrow-1" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_archer_id": 1,
    "round_number": 1,
    "arrow_number": 1,
    "zone": 8,
    "points": 8
  }'

# Same key will return same response (no duplicate)
```

### Pagination

Use skip/limit for list endpoints:

```bash
# First page
curl "http://localhost:8000/api/tournaments?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Next page
curl "http://localhost:8000/api/tournaments?skip=10&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Tip: Use 'total' to calculate max pages
# pages = ceil(total / limit)
```

---

## Troubleshooting

### Common Issues

#### Invalid Token
```
Error: 401 Unauthorized
```
**Solution**: 
1. Login again to get new token
2. Check token hasn't expired (8-hour TTL)
3. Use refresh endpoint if expired

#### Score Validation Failed
```
Error: 400 Bad Request - Zone must be 0-10
```
**Solution**: 
- Verify zone value is 0-10
- Verify points value is 0-10
- Check round_number is positive
- Check arrow_number is 1-6

#### Camera Connection Failed
```
Error: 404 Not Found - Camera not found
```
**Solution**:
- Verify camera ID exists
- Check camera status via list endpoint
- Restart camera connection

#### Leaderboard Empty
```
Response: {"items": [], "total": 0}
```
**Solution**:
- Verify session has archers registered
- Check if scores have been recorded
- Use use_cache=false to bypass cache

#### Database Connection Error
```
Error: 500 Internal Server Error - Database connection failed
```
**Solution**:
1. Check database is running: `docker-compose ps`
2. Restart database: `docker-compose restart db`
3. Check DATABASE_URL in .env
4. Verify connection: `docker-compose exec api psql $DATABASE_URL -c "SELECT 1"`

---

**For more help**: Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) or [API_SPECIFICATION.md](API_SPECIFICATION.md)
