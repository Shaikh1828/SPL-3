"""
Pytest configuration and fixtures for all tests.

Provides database, cache, and API client fixtures for testing.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from redis import Redis
import structlog
from datetime import datetime

from src.main import app
from src.database import get_db
from src.models.base import Base
from src.cache import cache_manager
from src.models.user import User
from src.models.tournament import Tournament, Session as TournamentSession
from src.models.scoring import SessionArcher, Score
from src.models.camera import Camera, CameraLaneAssignment
from src.security import hash_password

logger = structlog.get_logger()

# Test database URL (in-memory SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """
    Create a test database session.

    Scope: function (new DB for each test)
    """
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    
    # Override dependency
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield db
    
    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(test_db):
    """
    Create a test FastAPI client.

    Scope: function
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def test_user(test_db: Session):
    """
    Create a test user.

    Scope: function
    """
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
        role="scorer",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_admin_user(test_db: Session):
    """
    Create a test admin user.

    Scope: function
    """
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        role="admin",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def auth_headers(test_client: TestClient, test_user: User):
    """
    Get authentication headers for test user.

    Scope: function
    """
    response = test_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "TestPassword123!"},
    )
    
    assert response.status_code == 200
    tokens = response.json()
    
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(scope="function")
def admin_auth_headers(test_client: TestClient, test_admin_user: User):
    """
    Get authentication headers for admin user.

    Scope: function
    """
    response = test_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPassword123!"},
    )
    
    assert response.status_code == 200
    tokens = response.json()
    
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(scope="function")
def test_tournament(test_db: Session, test_user: User):
    """
    Create a test tournament.

    Scope: function
    """
    from datetime import datetime, timedelta
    
    tournament = Tournament(
        name="Test Tournament",
        location="Test Location",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
        created_by_user_id=test_user.id,
    )
    test_db.add(tournament)
    test_db.commit()
    test_db.refresh(tournament)
    
    return tournament


@pytest.fixture(scope="function")
def test_session(test_db: Session, test_tournament: Tournament):
    """
    Create a test session.

    Scope: function
    """
    session = TournamentSession(
        tournament_id=test_tournament.id,
        name="Test Session",
        status="active",
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    return session


@pytest.fixture(scope="function")
def test_session_archer(test_db: Session, test_session: TournamentSession):
    """
    Create a test session archer.

    Scope: function
    """
    archer = SessionArcher(
        session_id=test_session.id,
        archer_id=1,
        archer_name="Test Archer",
        current_round=1,
        total_score=0,
    )
    test_db.add(archer)
    test_db.commit()
    test_db.refresh(archer)
    
    return archer


@pytest.fixture(scope="function")
def test_camera(test_db: Session):
    """
    Create a test camera.

    Scope: function
    """
    camera = Camera(
        name="Test Camera",
        camera_type="USB",
        url="camera://test",
        status="connected",
    )
    test_db.add(camera)
    test_db.commit()
    test_db.refresh(camera)
    
    return camera


@pytest.fixture(scope="function")
def test_score(test_db: Session, test_session: TournamentSession, test_session_archer: SessionArcher):
    """
    Create a test score.

    Scope: function
    """
    score = Score(
        session_id=test_session.id,
        session_archer_id=test_session_archer.id,
        round=1,
        arrow_num=1,
        zone=8,
        points=8,
        validated_by_ai=False,
    )
    test_db.add(score)
    test_db.commit()
    test_db.refresh(score)
    
    return score


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """
    Reset rate limits before each test.

    Scope: function (autouse)
    """
    from src.middleware.rate_limit import reset_rate_limits
    reset_rate_limits()
    yield
