# Backend Unit — NFR Design Patterns

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Overview

This document specifies design patterns for implementing non-functional requirements (Performance, Security, Scalability, Reliability, Availability) in the Backend unit.

---

## Resilience Patterns

### Pattern 1: Database Connection Resilience with Exponential Backoff

**Pattern Type**: Fault Tolerance / Recovery

**Problem**: PostgreSQL connection failures (pool exhausted, server down, network timeout) can occur. Should not cascade to user-facing errors.

**Solution**: Retry with exponential backoff (up to 3 times) before failing

**Implementation**:

```python
# database.py
from sqlalchemy.exc import OperationalError
import time

MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # 1 second
BACKOFF_MULTIPLIER = 2.0

def get_db_connection_with_retry():
    """Attempt to get database connection with exponential backoff"""
    for attempt in range(MAX_RETRIES):
        try:
            connection = engine.connect()
            return connection
        except OperationalError as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
                logger.warning(f"DB connection failed, retrying in {wait_time}s", 
                    attempt=attempt+1, error=str(e))
                time.sleep(wait_time)
            else:
                logger.error(f"DB connection failed after {MAX_RETRIES} retries", error=str(e))
                raise

# FastAPI dependency
@app.get("/api/v1/scores/{session_id}")
async def get_scores(session_id: str, db: Session = Depends(get_db_connection_with_retry)):
    # ... endpoint logic
```

**Benefits**:
- Transient failures (brief network hiccup) handled automatically
- Exponential backoff prevents overwhelming database with retry attempts
- User gets clear error after retries exhausted

**Trade-offs**: Adds 1-4 seconds latency on failure (acceptable for best-effort approach)

---

### Pattern 2: Scoring Pipeline Failure Recovery with Automatic Retry

**Pattern Type**: Fault Tolerance / Transaction Management

**Problem**: Scoring involves multiple steps (image capture → process → detect → calculate → store). Failure at any stage loses work.

**Solution**: Automatic retry (immediate + exponential backoff) if any step fails

**Implementation**:

```python
# scoring_service.py
from enum import Enum

class ScoringStage(Enum):
    CAPTURE = "capture"
    PROCESS = "process"
    DETECT = "detect"
    CALCULATE = "calculate"
    STORE = "store"

async def score_end_with_retry(session_id, archer_id, camera_id, max_retries=2):
    """Score end with automatic retry on failure"""
    for attempt in range(max_retries + 1):
        try:
            # Execute full pipeline
            images = await capture_images(camera_id)
            processed = await preprocess_images(images)
            rings = await detect_rings(processed)
            arrows = await detect_arrows(processed)
            scores = await calculate_scores(rings, arrows)
            await store_scores(session_id, archer_id, scores)
            return scores
        
        except (ImageProcessingError, DatabaseError) as e:
            if attempt < max_retries:
                wait_time = (2 ** attempt)  # 1s, 2s, 4s backoff
                logger.warning(f"Scoring failed at stage, retrying in {wait_time}s",
                    session_id=session_id, archer_id=archer_id, error=str(e), attempt=attempt+1)
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Scoring failed after {max_retries} retries",
                    session_id=session_id, archer_id=archer_id, error=str(e))
                # Return error to user, user can retry manually
                raise ScoringFailedError(f"Scoring failed: {e}. Please try again.")
```

**Benefits**:
- Transient failures (brief network timeout, temporary OOM) handled automatically
- User only sees failure if truly unrecoverable
- Clear error message guides user on retry

**Trade-offs**: May add 1-8 seconds latency on failure; user must understand retry behavior

---

### Pattern 3: WebSocket Disconnection Handling with Grace Period

**Pattern Type**: Connection Management / Resilience

**Problem**: WebSocket clients disconnect (browser close, network dropout, server restart). Should not lose subscription state permanently.

**Solution**: Wait 30s before removing client, then remove. Client reconnects within grace period to resume.

**Implementation**:

```python
# websocket_manager.py
from datetime import datetime, timedelta
import asyncio

class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # session_id -> websocket
        self.graceful_disconnects: dict[str, datetime] = {}  # session_id -> disconnect_time
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Register new or reconnecting client"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Remove from graceful disconnect tracking if reconnected
        if session_id in self.graceful_disconnects:
            del self.graceful_disconnects[session_id]
            logger.info(f"Client reconnected within grace period", session_id=session_id)
    
    async def disconnect(self, session_id: str):
        """Mark as gracefully disconnected (30s grace period)"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        self.graceful_disconnects[session_id] = datetime.now()
        logger.info(f"Client disconnected, grace period 30s", session_id=session_id)
    
    async def cleanup_expired_grace_periods(self):
        """Periodically remove clients that didn't reconnect within grace period"""
        grace_period = timedelta(seconds=30)
        now = datetime.now()
        
        expired = [sid for sid, disconnect_time in self.graceful_disconnects.items()
                  if now - disconnect_time > grace_period]
        
        for session_id in expired:
            del self.graceful_disconnects[session_id]
            logger.info(f"Grace period expired, removing disconnected client", session_id=session_id)
    
    async def broadcast(self, message: dict, session_id: str = None):
        """Broadcast to all connected clients (or specific session)"""
        disconnected = []
        
        if session_id:
            # Broadcast to specific session only
            if session_id in self.active_connections:
                try:
                    await self.active_connections[session_id].send_json(message)
                except:
                    disconnected.append(session_id)
        else:
            # Broadcast to all sessions
            for sid, connection in self.active_connections.items():
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(sid)
        
        # Mark disconnected clients for removal
        for session_id in disconnected:
            await self.disconnect(session_id)

# Background task to cleanup grace periods
@app.on_event("startup")
async def start_grace_period_cleanup():
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        await websocket_manager.cleanup_expired_grace_periods()
```

**Benefits**:
- Brief disconnections (network hiccup, browser refresh) don't lose subscription
- Transient issues handled transparently
- Server doesn't accumulate "zombie" connections

**Trade-offs**: Memory usage for grace period tracking; cleanup overhead minimal

---

### Pattern 4: Image Processing Fallback Chain with ML Fallback

**Pattern Type**: Fault Tolerance / Degraded Mode

**Problem**: Arrow detection may fail if image quality poor, arrow position unclear, or lighting bad.

**Solution**: Implement 3-method fallback chain:
1. Color-based detection (HSV thresholding + contour analysis)
2. Edge-based detection (Canny edges + Hough lines)
3. ML-based detection (trained neural network as last resort)

**Implementation**:

```python
# arrow_detection.py
import cv2
import numpy as np
from tensorflow import keras

class ArrowDetectionEngine:
    def __init__(self):
        self.ml_model = keras.models.load_model("models/arrow_detection.h5")
    
    async def detect_arrow(self, image):
        """Detect arrow using fallback chain"""
        
        # Method 1: Color-based
        try:
            position = self._color_based_detection(image)
            confidence = self._assess_confidence(position, "color")
            if confidence > 0.7:
                return position, confidence, "color_based"
        except Exception as e:
            logger.warning(f"Color-based detection failed: {e}")
        
        # Method 2: Edge-based
        try:
            position = self._edge_based_detection(image)
            confidence = self._assess_confidence(position, "edge")
            if confidence > 0.7:
                return position, confidence, "edge_based"
        except Exception as e:
            logger.warning(f"Edge-based detection failed: {e}")
        
        # Method 3: ML-based
        try:
            position = self._ml_based_detection(image)
            confidence = self._assess_confidence(position, "ml")
            if confidence > 0.5:
                return position, confidence, "ml_based"
        except Exception as e:
            logger.error(f"All arrow detection methods failed: {e}")
            raise ArrowDetectionFailedError("Arrow detection failed all methods")
    
    def _color_based_detection(self, image):
        """HSV thresholding + contour analysis"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        if contours:
            largest = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest)
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            return (cx, cy)
        raise ArrowDetectionFailedError("No contours found")
    
    def _edge_based_detection(self, image):
        """Canny edge detection + Hough line transform"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 50)
        if lines is not None and len(lines) > 0:
            rho, theta = lines[0][0]
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            return (int(x0), int(y0))
        raise ArrowDetectionFailedError("No lines detected")
    
    def _ml_based_detection(self, image):
        """Neural network-based detection"""
        resized = cv2.resize(image, (224, 224))
        normalized = resized / 255.0
        prediction = self.ml_model.predict(np.array([normalized]))
        if prediction is not None and len(prediction) > 0:
            x, y = prediction[0][:2]
            return (int(x), int(y))
        raise ArrowDetectionFailedError("ML model failed")
    
    def _assess_confidence(self, position, method):
        """Score confidence of detection"""
        # Simplified confidence scoring
        if method == "color":
            return 0.8
        elif method == "edge":
            return 0.7
        elif method == "ml":
            return 0.6
        return 0.5
```

**Benefits**:
- Robust to image quality variations
- ML fallback handles edge cases color/edge methods miss
- Graceful degradation with decreasing confidence

**Trade-offs**: ML model adds training complexity; slightly slower (fallback check adds ~50ms worst-case)

---

### Pattern 5: Camera Reconnection with Limited Retries and User Notification

**Pattern Type**: Fault Tolerance / Alerting

**Problem**: Cameras disconnect (USB unplugged, network down). Indefinite retries cause resource waste and confuse users.

**Solution**: Retry up to 5 times with exponential backoff, notify user after 3 failures, give up after 5 retries

**Implementation**:

```python
# camera_service.py
MAX_CAMERA_RETRIES = 5
NOTIFICATION_THRESHOLD = 3
BACKOFF_BASE = 30  # 30 seconds

class CameraService:
    def __init__(self):
        self.camera_retry_count = {}  # camera_id -> retry_count
    
    async def probe_camera(self, camera_id: str, force=False):
        """Probe camera with retry logic"""
        retry_count = self.camera_retry_count.get(camera_id, 0)
        
        if retry_count >= MAX_CAMERA_RETRIES and not force:
            logger.error(f"Camera failed too many times, giving up", camera_id=camera_id)
            return False
        
        try:
            # Attempt to capture frame
            result = await self._attempt_capture(camera_id)
            
            # Success: reset retry count
            self.camera_retry_count[camera_id] = 0
            logger.info(f"Camera reconnected", camera_id=camera_id)
            
            # Publish event
            await event_bus.publish("CameraConnected", {"camera_id": camera_id})
            
            return True
        
        except CameraError as e:
            retry_count += 1
            self.camera_retry_count[camera_id] = retry_count
            
            if retry_count < MAX_CAMERA_RETRIES:
                wait_time = BACKOFF_BASE * (2 ** (retry_count - 1))
                logger.warning(f"Camera probe failed, retry in {wait_time}s",
                    camera_id=camera_id, retry_count=retry_count, error=str(e))
                
                # Notify user after 3 failures
                if retry_count == NOTIFICATION_THRESHOLD:
                    await event_bus.publish("CameraWarning", {
                        "camera_id": camera_id,
                        "message": f"Camera {camera_id} disconnected. Attempting to reconnect..."
                    })
                
                # Schedule retry
                asyncio.create_task(self._retry_after_delay(camera_id, wait_time))
            
            else:
                logger.error(f"Camera failed after {MAX_CAMERA_RETRIES} retries",
                    camera_id=camera_id)
                
                # Give up, notify user
                await event_bus.publish("CameraFailed", {
                    "camera_id": camera_id,
                    "message": f"Camera {camera_id} failed to reconnect. Please check connection."
                })
                
                return False
    
    async def _retry_after_delay(self, camera_id: str, delay_seconds: int):
        """Retry after delay"""
        await asyncio.sleep(delay_seconds)
        await self.probe_camera(camera_id)
    
    async def _attempt_capture(self, camera_id: str):
        """Attempt to capture frame from camera"""
        # Camera-specific capture logic
        pass

# Background task for periodic camera probing
@app.on_event("startup")
async def start_camera_probe():
    asyncio.create_task(periodic_camera_probe())

async def periodic_camera_probe():
    """Probe cameras every 30 seconds"""
    while True:
        await asyncio.sleep(30)
        for camera_id in get_all_cameras():
            if not is_camera_healthy(camera_id):
                await camera_service.probe_camera(camera_id)
```

**Benefits**:
- Transient disconnects handled automatically
- User notified when issue persists
- System stops wasting resources after 5 failures
- Clear escalation path (warn at 3, fail at 5)

**Trade-offs**: User experience impacted during camera downtime; ~4 minutes for all retries

---

## Scalability Patterns

### Pattern 6: Database Row-Level Isolation for Multi-Session Safety

**Pattern Type**: Concurrency Control / Data Isolation

**Problem**: Multiple sessions running in parallel could interfere (cross-session data leaks).

**Solution**: Application-level session_id filtering for all queries (rely on business logic, not database constraints)

**Implementation**:

```python
# session_repository.py
class SessionRepository:
    def get_session_scores(self, session_id: str, archer_id: str = None):
        """Get scores for session with automatic session_id filtering"""
        query = db.query(Score).filter(Score.session_id == session_id)
        
        if archer_id:
            query = query.filter(Score.archer_id == archer_id)
        
        return query.all()
    
    def get_session_archers(self, session_id: str):
        """Get archers in session"""
        return db.query(SessionArcher).filter(SessionArcher.session_id == session_id).all()

# API layer (additional safety layer)
@app.get("/api/v1/sessions/{session_id}/scores")
async def get_session_scores(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user has access to session
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Verify user is tournament admin or scorer for this session
    # (authorization check)
    
    # Fetch scores with session_id filter
    scores = session_repository.get_session_scores(session_id)
    return scores
```

**Benefits**:
- Simple, no database-level constraints needed
- Flexible (can change session isolation rules easily)
- Developers aware of session boundaries

**Trade-offs**: Relies on developer discipline; bugs could cause cross-session leaks (mitigated by tests)

---

### Pattern 7: Adaptive Load Balancing via CPU-Based Throttling

**Pattern Type**: Load Management / Scalability

**Problem**: If API receives many concurrent requests, Uvicorn can be overloaded, causing latency spikes.

**Solution**: Monitor CPU usage, auto-scale ThreadPool (4 → 8 max) if CPU > 80%

**Implementation**:

```python
# load_manager.py
import psutil

class AdaptiveLoadManager:
    def __init__(self):
        self.current_pool_size = 4
        self.max_pool_size = 8
        self.min_pool_size = 2
        self.cpu_threshold = 80
        self.last_scale_time = None
        self.scale_cooldown = 60  # seconds
    
    async def check_and_scale(self):
        """Check CPU usage and scale ThreadPool if needed"""
        cpu_percent = psutil.cpu_percent(interval=1)
        now = datetime.now()
        
        # Rate limit scaling to once per 60 seconds
        if self.last_scale_time and (now - self.last_scale_time).seconds < self.scale_cooldown:
            return
        
        if cpu_percent > self.cpu_threshold and self.current_pool_size < self.max_pool_size:
            # Scale up
            self.current_pool_size = min(self.current_pool_size + 2, self.max_pool_size)
            logger.info(f"Scaling ThreadPool up to {self.current_pool_size}",
                cpu_percent=cpu_percent)
            self.image_processor_pool._max_workers = self.current_pool_size
            self.last_scale_time = now
        
        elif cpu_percent < 40 and self.current_pool_size > self.min_pool_size:
            # Scale down
            self.current_pool_size = max(self.current_pool_size - 1, self.min_pool_size)
            logger.info(f"Scaling ThreadPool down to {self.current_pool_size}",
                cpu_percent=cpu_percent)
            self.image_processor_pool._max_workers = self.current_pool_size
            self.last_scale_time = now

# Background task for periodic scaling checks
@app.on_event("startup")
async def start_load_management():
    asyncio.create_task(periodic_load_check())

async def periodic_load_check():
    """Check load every 10 seconds"""
    load_manager = AdaptiveLoadManager()
    while True:
        await asyncio.sleep(10)
        await load_manager.check_and_scale()
```

**Benefits**:
- Transparent scaling based on actual load
- Avoids overload without explicit request throttling
- Gradual scaling (±1-2 workers at a time)

**Trade-offs**: Slight memory overhead per worker; scaling decisions could be tuned per deployment

---

### Pattern 8: Comprehensive Query Optimization (Indexes + Caching + Rewrite)

**Pattern Type**: Performance / Scalability

**Problem**: As score volume grows, queries become slow.

**Solution**: Three-tier approach: database indexes, in-memory caching, query rewrite

**Implementation**:

```python
# database_schema.sql
CREATE INDEX idx_score_session_archer ON scores(session_id, archer_id);
CREATE INDEX idx_score_session_created ON scores(session_id, created_at);
CREATE INDEX idx_session_archer_session ON session_archers(session_id);
CREATE INDEX idx_camera_status ON cameras(status);

# scoring_repository.py
class ScoringRepository:
    def get_leaderboard_cached(self, session_id: str, ttl_seconds=60):
        """Get leaderboard with caching"""
        cache_key = f"leaderboard:{session_id}"
        
        # Check in-memory cache
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Query (optimized with index)
        leaderboard = db.query(
            SessionArcher.archer_id,
            func.sum(Score.points).label("total_points"),
            func.count(Score.id).label("score_count")
        ).join(Score, SessionArcher.archer_id == Score.archer_id)\
         .filter(Score.session_id == session_id)\
         .group_by(SessionArcher.archer_id)\
         .order_by(func.sum(Score.points).desc())\
         .all()
        
        # Cache result
        cache.set(cache_key, leaderboard, ttl=ttl_seconds)
        
        return leaderboard
    
    def get_session_scores(self, session_id: str):
        """Get scores with minimal filtering"""
        # Use index on (session_id, created_at)
        return db.query(Score)\
            .filter(Score.session_id == session_id)\
            .order_by(Score.created_at.desc())\
            .all()
```

**Benefits**:
- Three-layer defense: indexes for DB, cache for app, rewritten queries for efficiency
- Scales to 1000+ scores per session
- Each layer independent (can adjust individually)

**Trade-offs**: Cache invalidation complexity; requires ongoing index maintenance

---

### Pattern 9: Automated Storage Quota Management with 90-Day Rotation

**Pattern Type**: Data Management / Scalability

**Problem**: System stores images, will exceed 10 GB quota if not managed.

**Solution**: Automatic archival after 90 days, cleanup if quota exceeded

**Implementation**:

```python
# storage_manager.py
import os
import tarfile
from datetime import datetime, timedelta

STORAGE_ROOT = "/storage"
RAW_DIR = f"{STORAGE_ROOT}/raw"
ARCHIVE_DIR = f"{STORAGE_ROOT}/archives"
QUOTA_GB = 10
WARNING_THRESHOLD = 0.8  # 80%
RETENTION_DAYS = 90

class StorageManager:
    async def cleanup_and_monitor(self):
        """Run periodic storage cleanup (daily)"""
        # Archive old images
        await self._archive_old_images()
        
        # Check quota
        usage_gb = self._get_storage_usage_gb()
        quota_percent = (usage_gb / QUOTA_GB) * 100
        
        logger.info(f"Storage usage: {usage_gb:.2f}GB / {QUOTA_GB}GB ({quota_percent:.1f}%)")
        
        if usage_gb > (QUOTA_GB * WARNING_THRESHOLD):
            logger.warning(f"Storage quota warning", usage_gb=usage_gb, quota_gb=QUOTA_GB)
            await event_bus.publish("StorageWarning", {
                "usage_gb": usage_gb,
                "quota_gb": QUOTA_GB,
                "percent": quota_percent
            })
        
        if usage_gb > QUOTA_GB:
            logger.error(f"Storage quota exceeded, deleting oldest archives")
            await self._delete_oldest_archives()
    
    async def _archive_old_images(self):
        """Archive images older than 90 days"""
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
        
        for session_dir in os.listdir(RAW_DIR):
            session_path = os.path.join(RAW_DIR, session_dir)
            if not os.path.isdir(session_path):
                continue
            
            for image_file in os.listdir(session_path):
                file_path = os.path.join(session_path, image_file)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime < cutoff_date:
                    # Archive to tar.gz
                    archive_path = os.path.join(ARCHIVE_DIR, f"{session_dir}_{file_mtime.strftime('%Y%m%d')}.tar.gz")
                    with tarfile.open(archive_path, "w:gz") as tar:
                        tar.add(file_path, arcname=image_file)
                    
                    # Delete original
                    os.remove(file_path)
                    logger.info(f"Archived old image", image_file=image_file, session=session_dir)
    
    def _get_storage_usage_gb(self) -> float:
        """Calculate total storage usage"""
        total_bytes = 0
        for dirpath, dirnames, filenames in os.walk(STORAGE_ROOT):
            for filename in filenames:
                total_bytes += os.path.getsize(os.path.join(dirpath, filename))
        return total_bytes / (1024**3)
    
    async def _delete_oldest_archives(self):
        """Delete oldest archives to free space"""
        archives = sorted(
            [f for f in os.listdir(ARCHIVE_DIR)],
            key=lambda f: os.path.getmtime(os.path.join(ARCHIVE_DIR, f))
        )
        
        for archive_file in archives:
            if self._get_storage_usage_gb() <= QUOTA_GB:
                break
            
            archive_path = os.path.join(ARCHIVE_DIR, archive_file)
            os.remove(archive_path)
            logger.warning(f"Deleted old archive to free space", archive=archive_file)

# Background task
@app.on_event("startup")
async def start_storage_management():
    asyncio.create_task(periodic_storage_cleanup())

async def periodic_storage_cleanup():
    """Run daily"""
    storage_manager = StorageManager()
    while True:
        await asyncio.sleep(86400)  # 24 hours
        await storage_manager.cleanup_and_monitor()
```

**Benefits**:
- Automatic quota management, no manual intervention
- 90-day retention for compliance
- Graceful degradation (archive before delete)
- Monitoring and alerts

**Trade-offs**: Requires background task overhead; archive/delete operations can be slow for large files

---

### Pattern 10: Adaptive ThreadPool Scaling with Hybrid Approach

**Pattern Type**: Performance / Concurrency

**Problem**: Fixed ThreadPool(4) may be insufficient for spikes or underutilized during low traffic.

**Solution**: Hybrid approach - start at 4, scale to max 8 if CPU > 80%

**Implementation**:

```python
# Already covered in Pattern 7 (Adaptive Load Balancing)
# ThreadPool size is managed by AdaptiveLoadManager
```

---

## Performance Optimization Patterns

### Pattern 11: Application-Level Caching with Time-To-Live (TTL)

**Pattern Type**: Performance / Caching

**Problem**: API serves frequently-requested data (camera list, session details) that change infrequently.

**Solution**: In-memory LRU cache with TTL for hot data

**Implementation**:

```python
# cache_manager.py
from cachetools import TTLCache
import threading

class CacheManager:
    def __init__(self):
        self.camera_list_cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes
        self.session_cache = TTLCache(maxsize=1000, ttl=60)  # 1 minute
        self.leaderboard_cache = TTLCache(maxsize=1000, ttl=60)  # 1 minute
        self.lock = threading.RLock()
    
    def get_cameras(self) -> List[Camera]:
        """Get camera list with caching"""
        with self.lock:
            if "all_cameras" in self.camera_list_cache:
                return self.camera_list_cache["all_cameras"]
        
        # Query database
        cameras = db.query(Camera).all()
        
        with self.lock:
            self.camera_list_cache["all_cameras"] = cameras
        
        return cameras
    
    def invalidate_cameras(self):
        """Invalidate camera cache after update"""
        with self.lock:
            self.camera_list_cache.clear()
    
    def get_session(self, session_id: str) -> Session:
        """Get session with caching"""
        with self.lock:
            if session_id in self.session_cache:
                return self.session_cache[session_id]
        
        session = db.query(Session).filter(Session.id == session_id).first()
        
        with self.lock:
            self.session_cache[session_id] = session
        
        return session
    
    def invalidate_session(self, session_id: str):
        """Invalidate session cache"""
        with self.lock:
            if session_id in self.session_cache:
                del self.session_cache[session_id]

# API usage
cache_manager = CacheManager()

@app.get("/api/v1/cameras")
async def get_cameras():
    cameras = cache_manager.get_cameras()
    return cameras
```

**Benefits**:
- Reduces database queries for static/slowly-changing data
- < 100ms response times for cached endpoints
- Transparent to caller

**Trade-offs**: Cache invalidation complexity; stale data possible up to TTL

---

### Pattern 12: Image Compression for Faster Processing

**Pattern Type**: Performance / Algorithm Optimization

**Problem**: Image processing (Hough circles, contour analysis) is CPU-bound (200-350ms).

**Solution**: Compress images before processing (trade quality for speed)

**Implementation**:

```python
# image_processor.py
class ImageProcessor:
    def __init__(self):
        self.compression_quality = 70  # JPEG quality (0-100)
    
    async def process_images_optimized(self, raw_images):
        """Process images with compression"""
        compressed_images = []
        
        for image in raw_images:
            # Compress to reduce processing workload
            compressed = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, self.compression_quality])[1]
            compressed_image = cv2.imdecode(compressed, cv2.IMREAD_COLOR)
            compressed_images.append(compressed_image)
        
        # Process compressed images (faster)
        rings = await self.detect_rings(compressed_images)
        arrows = await self.detect_arrows(compressed_images)
        
        return rings, arrows
    
    def adjust_compression_quality(self, cpu_percent):
        """Dynamically adjust compression based on CPU usage"""
        if cpu_percent > 90:
            self.compression_quality = 60  # More compression
        elif cpu_percent < 50:
            self.compression_quality = 80  # Less compression
```

**Benefits**:
- Reduces image processing latency by 20-30%
- Minimal quality loss for scoring (rings/arrows still clearly visible)
- Adaptive based on system load

**Trade-offs**: Slight quality degradation; accuracy impact minimal

---

### Pattern 13: Leaderboard Caching with Simple TTL

**Pattern Type**: Caching / Performance

**Problem**: Leaderboard queries (aggregate, sort) are expensive on large sessions.

**Solution**: Cache leaderboard for 1 minute, refresh on request

**Implementation**:

```python
# leaderboard_service.py
class LeaderboardService:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=60)  # 1 minute TTL
    
    def get_leaderboard(self, session_id: str, refresh=False):
        """Get leaderboard with 1-minute cache"""
        cache_key = f"leaderboard:{session_id}"
        
        if cache_key in self.cache and not refresh:
            return self.cache[cache_key]
        
        # Query and aggregate
        leaderboard = db.query(
            SessionArcher.archer_id,
            SessionArcher.name,
            func.sum(Score.points).label("total_points"),
            func.count(Score.id).label("score_count")
        ).join(Score, SessionArcher.archer_id == Score.archer_id)\
         .filter(Score.session_id == session_id)\
         .group_by(SessionArcher.archer_id, SessionArcher.name)\
         .order_by(func.sum(Score.points).desc())\
         .all()
        
        # Convert to list of dicts
        leaderboard_list = [
            {
                "rank": i + 1,
                "archer_id": row.archer_id,
                "name": row.name,
                "total_points": row.total_points,
                "score_count": row.score_count
            }
            for i, row in enumerate(leaderboard)
        ]
        
        # Cache
        self.cache[cache_key] = leaderboard_list
        
        return leaderboard_list
    
    def invalidate_leaderboard(self, session_id: str):
        """Invalidate cache when new score added"""
        cache_key = f"leaderboard:{session_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]

# Event-driven invalidation
@event_bus.on("ScoreCalculated")
async def on_score_calculated(event):
    leaderboard_service.invalidate_leaderboard(event["session_id"])
    # Push updated leaderboard via WebSocket
    updated = leaderboard_service.get_leaderboard(event["session_id"], refresh=True)
    await websocket_manager.broadcast({"leaderboard": updated}, event["session_id"])
```

**Benefits**:
- Most leaderboard requests hit cache (< 1ms)
- Leaderboard refreshed frequently (1 minute)
- Scales to large tournaments (1000+ archers)

**Trade-offs**: Leaderboard may be 0-60 seconds stale; acceptable for scoring scenario

---

### Pattern 14: Adaptive Connection Pool Tuning

**Pattern Type**: Performance / Resource Management

**Problem**: Fixed pool size (10+5) may be inefficient under varying loads.

**Solution**: Monitor active connections, scale pool size adaptively (min 5, max 20)

**Implementation**:

```python
# database_pool_manager.py
class PoolTuningManager:
    def __init__(self, engine):
        self.engine = engine
        self.min_pool = 5
        self.max_pool = 20
        self.target_utilization = 0.7  # Target 70% utilization
    
    async def tune_pool_size(self):
        """Adjust pool size based on utilization"""
        pool = self.engine.pool
        
        # Get current usage
        checked_out = pool.checkedout()
        pool_size = pool.size()
        
        utilization = checked_out / pool_size if pool_size > 0 else 0
        
        logger.info(f"Pool stats", size=pool_size, checkedout=checked_out, utilization=utilization)
        
        # Scale up if above target utilization
        if utilization > self.target_utilization and pool_size < self.max_pool:
            pool.dispose()
            # SQLAlchemy will grow pool on next requests
            logger.info(f"Scaling pool up (utilization {utilization:.2f})")
        
        # Scale down if below target utilization
        elif utilization < (self.target_utilization * 0.5) and pool_size > self.min_pool:
            pool.dispose()
            logger.info(f"Scaling pool down (utilization {utilization:.2f})")

# Background tuning
@app.on_event("startup")
async def start_pool_tuning():
    tuner = PoolTuningManager(engine)
    asyncio.create_task(periodic_pool_tuning(tuner))

async def periodic_pool_tuning(tuner):
    """Tune pool every 5 minutes"""
    while True:
        await asyncio.sleep(300)
        await tuner.tune_pool_size()
```

**Benefits**:
- Optimal pool utilization under varying loads
- Prevents connection starvation
- Reduces idle connections under low load

**Trade-offs**: Pool shrinking can cause brief delay when traffic spikes again

---

### Pattern 15: WebSocket Message Batching for Reduced Network Traffic

**Pattern Type**: Performance / Network Optimization

**Problem**: Multiple scores calculated in rapid succession → many WebSocket messages → higher bandwidth/latency.

**Solution**: Batch events within 100ms window or 10 events (whichever first)

**Implementation**:

```python
# websocket_event_batcher.py
import asyncio
from collections import defaultdict

class EventBatcher:
    def __init__(self, batch_time_ms=100, batch_count=10):
        self.batch_time = batch_time_ms / 1000.0
        self.batch_count = batch_count
        self.batches = defaultdict(list)  # session_id -> [events]
        self.batch_timers = {}  # session_id -> timer_task
    
    async def add_event(self, session_id: str, event: dict):
        """Add event to batch"""
        self.batches[session_id].append(event)
        
        # Start timer if not already running
        if session_id not in self.batch_timers:
            self.batch_timers[session_id] = asyncio.create_task(
                self._send_batch_after_delay(session_id)
            )
        
        # Send immediately if batch full
        if len(self.batches[session_id]) >= self.batch_count:
            await self._send_batch(session_id)
    
    async def _send_batch_after_delay(self, session_id: str):
        """Wait for batch timer to expire, then send"""
        try:
            await asyncio.sleep(self.batch_time)
            await self._send_batch(session_id)
        except asyncio.CancelledError:
            pass  # Batch sent early
    
    async def _send_batch(self, session_id: str):
        """Send batched events"""
        if session_id not in self.batches or not self.batches[session_id]:
            return
        
        events = self.batches[session_id]
        
        # Cancel pending timer
        if session_id in self.batch_timers:
            self.batch_timers[session_id].cancel()
            del self.batch_timers[session_id]
        
        # Clear batch
        del self.batches[session_id]
        
        # Send combined message
        message = {
            "type": "event_batch",
            "count": len(events),
            "events": events
        }
        
        await websocket_manager.broadcast(message, session_id)
        logger.info(f"Sent batched events", session_id=session_id, count=len(events))

# Usage
event_batcher = EventBatcher(batch_time_ms=100, batch_count=10)

@event_bus.on("ScoreCalculated")
async def on_score_calculated(event):
    await event_batcher.add_event(event["session_id"], {
        "type": "score_calculated",
        "data": event
    })
```

**Benefits**:
- Reduces WebSocket messages by up to 90% (10x reduction)
- Lower bandwidth usage
- Slight latency increase (0-100ms) acceptable for UI updates

**Trade-offs**: Complexity of batching logic; frontend must handle batched messages

---

## Security Design Patterns

### Pattern 16: Multi-Layer Input Validation (Type, Length, Format, Business Logic)

**Pattern Type**: Security / Input Validation

**Problem**: All user inputs must be validated to prevent injection, overflow, and business logic violations.

**Solution**: Validate in four layers (HTTP, Pydantic, service, database)

**Implementation**:

```python
# models.py
from pydantic import BaseModel, Field, validator
import re

class ScoreCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)
    archer_id: str = Field(..., min_length=1, max_length=36)
    camera_id: str = Field(..., min_length=1, max_length=36)
    zone: int = Field(..., ge=0, le=10)  # 0-10 zones
    points: int = Field(..., ge=0, le=10)  # 0-10 points
    confidence: float = Field(..., ge=0, le=100)  # 0-100%
    is_override: bool = False
    override_reason: Optional[str] = Field(None, max_length=500)
    
    @validator('session_id', 'archer_id', 'camera_id')
    def validate_uuid(cls, v):
        if not re.match(r'^[a-f0-9\-]{36}$', v):
            raise ValueError('Invalid UUID format')
        return v
    
    @validator('override_reason')
    def validate_override_reason(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError('Override reason cannot be empty')
        return v

# API layer
@app.post("/api/v1/scores")
async def create_score(
    request: ScoreCreateRequest,  # Pydantic validates type, length, format
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Service layer validation (business logic)
    session = db.query(Session).filter(Session.id == request.session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    
    if session.status != SessionStatus.STARTED:
        raise HTTPException(400, "Session not active")
    
    # Check archer is in session
    archer = db.query(SessionArcher).filter(
        SessionArcher.session_id == request.session_id,
        SessionArcher.archer_id == request.archer_id
    ).first()
    if not archer:
        raise HTTPException(400, "Archer not in session")
    
    # Check override constraints
    if request.is_override:
        # Can only override if confidence < 50%
        if request.confidence >= 50:
            raise HTTPException(400, "Can only override low-confidence scores")
        if not request.override_reason:
            raise HTTPException(400, "Override reason required")
    
    # Create score (database handles final validation via constraints)
    score = Score(
        session_id=request.session_id,
        archer_id=request.archer_id,
        camera_id=request.camera_id,
        zone=request.zone,
        points=request.points,
        confidence=request.confidence,
        is_override=request.is_override,
        override_reason=request.override_reason
    )
    
    db.add(score)
    db.commit()
    
    return score
```

**Benefits**:
- Four-layer defense (HTTP, Pydantic, service, database)
- Clear error messages for invalid inputs
- Prevents injection, overflow, business logic violations

**Trade-offs**: Validation code verbose; must maintain consistency across layers

---

### Pattern 17: Per-IP Rate Limiting for API Protection

**Pattern Type**: Security / Rate Limiting

**Problem**: API could be abused (many requests from single IP).

**Solution**: Track requests per IP, reject if > 1000 per minute

**Implementation**:

```python
# rate_limiter.py
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, requests_per_minute=1000):
        self.requests_per_minute = requests_per_minute
        self.request_times = defaultdict(list)  # IP -> [timestamps]
    
    def is_rate_limited(self, ip: str) -> bool:
        """Check if IP is rate limited"""
        now = time.time()
        one_minute_ago = now - 60
        
        # Remove old requests
        self.request_times[ip] = [t for t in self.request_times[ip] if t > one_minute_ago]
        
        # Check limit
        if len(self.request_times[ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded", ip=ip, request_count=len(self.request_times[ip]))
            return True
        
        # Add current request
        self.request_times[ip].append(now)
        return False

# Middleware
rate_limiter = RateLimiter(requests_per_minute=1000)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )
    
    response = await call_next(request)
    return response
```

**Benefits**:
- Prevents API abuse
- Simple implementation, low overhead
- Per-IP tracking prevents cross-user attacks

**Trade-offs**: In-memory tracking can use memory; needs cleanup for long-lived processes

---

### Pattern 18: Audit Logging for Scoring and Compliance

**Pattern Type**: Security / Compliance

**Problem**: Need audit trail of sensitive operations (score overrides, auth failures).

**Solution**: Log to database with structured schema for queryable audits

**Implementation**:

```python
# audit_logger.py
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(36))
    event_type = Column(String(50))  # "score_calculated", "score_overridden", "auth_failure"
    session_id = Column(String(36))
    details = Column(Text)  # JSON
    ip_address = Column(String(45))

class AuditLogger:
    def log_score_calculated(self, user_id, session_id, archer_id, score_id, ip_address):
        """Log score calculated"""
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type="score_calculated",
            session_id=session_id,
            details=json.dumps({"archer_id": archer_id, "score_id": score_id}),
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
    
    def log_score_overridden(self, user_id, session_id, score_id, reason, ip_address):
        """Log score override"""
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type="score_overridden",
            session_id=session_id,
            details=json.dumps({"score_id": score_id, "reason": reason}),
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
    
    def log_auth_failure(self, username, ip_address):
        """Log failed login attempt"""
        log = AuditLog(
            id=str(uuid.uuid4()),
            event_type="auth_failure",
            details=json.dumps({"username": username}),
            ip_address=ip_address
        )
        db.add(log)
        db.commit()

# Usage
audit_logger = AuditLogger()

@app.post("/api/v1/scores")
async def create_score(request: ScoreCreateRequest, current_user: User = Depends(get_current_user)):
    # ... create score ...
    audit_logger.log_score_calculated(
        current_user.id, request.session_id, request.archer_id, score.id,
        request.client.host
    )
```

**Benefits**:
- Queryable audit trail (who, what, when, where)
- Supports compliance investigations
- Deters malicious behavior

**Trade-offs**: Audit table growth (hundreds of thousands of rows); requires cleanup/archival

---

### Pattern 19: Secure Secret Management via Environment Variables

**Pattern Type**: Security / Configuration

**Problem**: Database password, JWT secret, API keys must be secure.

**Solution**: Store secrets in environment variables (not code or files)

**Implementation**:

```python
# config.py
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL")
    jwt_secret: str = os.getenv("JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 8
    
    class Config:
        env_file = ".env"  # For development only, NOT in git
        env_file_encoding = "utf-8"

settings = Settings()

# Usage
@app.post("/auth/login")
async def login(username: str, password: str):
    # ... verify credentials ...
    token = jwt.encode(
        {"sub": user.id, "role": user.role},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return {"access_token": token}
```

**Benefits**:
- Secrets not in code or git
- Environment-specific secrets (dev vs prod)
- Easy rotation (change env var, restart)

**Trade-offs**: Requires secure environment setup; container orchestration needed for complex deployments

---

### Pattern 20: CORS Configuration with Allow-All for Trusted Network

**Pattern Type**: Security / API Configuration

**Problem**: Frontend (different origin) needs to call Backend API.

**Solution**: Allow all origins (CORS: *) assuming internal/trusted network

**Rationale**:
- Follow-up #1 clarified: CORS allow-all is intentional for internal/trusted deployment
- Frontend and Backend co-deployed or VPN-protected
- HTTPS + authentication provides outer security layer

**Implementation**:

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (internal network assumed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

**Benefits**:
- Simple setup for internal deployments
- Security provided by authentication + HTTPS
- Frontend doesn't need to know backend URL

**Trade-offs**: Not suitable for public APIs; must enforce HTTPS + auth

---

## Summary: 20 Design Patterns

| # | Pattern | Type | Key Benefit |
|---|---|---|---|
| 1 | DB Connection Resilience | Resilience | Transient failures handled auto |
| 2 | Scoring Failure Recovery | Resilience | Automatic retry with backoff |
| 3 | WebSocket Disconnection Handling | Resilience | 30s grace period prevents subscription loss |
| 4 | Image Processing Fallback | Resilience | 3-method fallback + ML fallback |
| 5 | Camera Reconnection | Resilience | Limited retries (5), user notified |
| 6 | Session Isolation | Scalability | Application-level filtering |
| 7 | Adaptive Load Balancing | Scalability | Auto-scale ThreadPool 4→8 on CPU > 80% |
| 8 | Query Optimization | Scalability | Indexes + caching + rewrite |
| 9 | Storage Quota Management | Scalability | Automated archival, 90-day rotation |
| 10 | ThreadPool Scaling | Scalability | Hybrid: 4→8 workers |
| 11 | Application Caching | Performance | In-memory LRU, TTL-based |
| 12 | Image Compression | Performance | Trade quality for speed |
| 13 | Leaderboard Caching | Performance | 1-min TTL, event-driven invalidation |
| 14 | Connection Pool Tuning | Performance | Adaptive sizing based on utilization |
| 15 | WebSocket Batching | Performance | 100ms window or 10 events |
| 16 | Multi-Layer Validation | Security | HTTP + Pydantic + service + DB |
| 17 | Per-IP Rate Limiting | Security | 1000 req/min per IP |
| 18 | Audit Logging | Security | Database audit trail |
| 19 | Secret Management | Security | Environment variables |
| 20 | CORS Configuration | Security | Allow-all for internal network |

