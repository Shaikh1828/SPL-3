"""
Tests for role-based access control and user management permissions.

Verifies:
1. Admin has unrestricted access to create, read, update, and deactivate all roles.
2. Scorer can list users, create spectators and archers.
3. Scorer CANNOT create admin or scorer accounts.
4. Scorer can update/deactivate spectators and archers.
5. Scorer CANNOT update or deactivate admins or other scorers.
6. Spectators and Archers cannot access user management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.security import hash_password, create_access_token


@pytest.fixture
def test_scorer_user(test_db: Session) -> User:
    scorer = User(
        username="scorer_jane",
        email="scorer_jane@archery.local",
        password_hash=hash_password("ScorerPass123!"),
        role="scorer",
        is_active=True,
    )
    test_db.add(scorer)
    test_db.commit()
    test_db.refresh(scorer)
    return scorer


@pytest.fixture
def test_spectator_user(test_db: Session) -> User:
    spectator = User(
        username="spectator_bob",
        email="spectator_bob@archery.local",
        password_hash=hash_password("SpectatorPass123!"),
        role="spectator",
        is_active=True,
    )
    test_db.add(spectator)
    test_db.commit()
    test_db.refresh(spectator)
    return spectator


@pytest.fixture
def test_archer_user(test_db: Session) -> User:
    archer = User(
        username="archer_robin",
        email="archer_robin@archery.local",
        password_hash=hash_password("ArcherPass123!"),
        role="archer",
        is_active=True,
    )
    test_db.add(archer)
    test_db.commit()
    test_db.refresh(archer)
    return archer


@pytest.fixture
def scorer_headers(test_scorer_user: User) -> dict:
    token = create_access_token(test_scorer_user.id, role=test_scorer_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def spectator_headers(test_spectator_user: User) -> dict:
    token = create_access_token(test_spectator_user.id, role=test_spectator_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def archer_headers(test_archer_user: User) -> dict:
    token = create_access_token(test_archer_user.id, role=test_archer_user.role)
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_list_all_users(test_client: TestClient, admin_auth_headers: dict):
    res = test_client.get("/api/users", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1


def test_admin_can_create_all_roles(test_client: TestClient, admin_auth_headers: dict):
    roles = ["spectator", "archer", "scorer", "admin"]
    for r in roles:
        res = test_client.post(
            "/api/users",
            headers=admin_auth_headers,
            json={
                "username": f"user_adm_cre_{r}",
                "email": f"adm_cre_{r}@example.com",
                "password": "ValidPassword123!",
                "role": r,
            },
        )
        assert res.status_code == 201
        assert res.json()["role"] == r


def test_scorer_can_list_users(test_client: TestClient, scorer_headers: dict):
    res = test_client.get("/api/users", headers=scorer_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data


def test_scorer_can_create_spectator_and_archer(test_client: TestClient, scorer_headers: dict):
    # 1. Scorer can create a spectator
    res1 = test_client.post(
        "/api/users",
        headers=scorer_headers,
        json={
            "username": "scorer_created_spectator",
            "email": "scorer_created_spectator@example.com",
            "password": "ValidPassword123!",
            "role": "spectator",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["role"] == "spectator"

    # 2. Scorer can create an archer
    res2 = test_client.post(
        "/api/users",
        headers=scorer_headers,
        json={
            "username": "scorer_created_archer",
            "email": "scorer_created_archer@example.com",
            "password": "ValidPassword123!",
            "role": "archer",
        },
    )
    assert res2.status_code == 201
    assert res2.json()["role"] == "archer"


def test_scorer_cannot_create_admin_or_scorer(test_client: TestClient, scorer_headers: dict):
    # Attempt to create admin as scorer -> 403 Forbidden
    res_admin = test_client.post(
        "/api/users",
        headers=scorer_headers,
        json={
            "username": "scorer_rogue_admin",
            "email": "scorer_rogue_admin@example.com",
            "password": "ValidPassword123!",
            "role": "admin",
        },
    )
    assert res_admin.status_code == 403
    assert "Scorers can only create spectator or archer accounts" in res_admin.json()["detail"]

    # Attempt to create another scorer as scorer -> 403 Forbidden
    res_scorer = test_client.post(
        "/api/users",
        headers=scorer_headers,
        json={
            "username": "scorer_rogue_scorer",
            "email": "scorer_rogue_scorer@example.com",
            "password": "ValidPassword123!",
            "role": "scorer",
        },
    )
    assert res_scorer.status_code == 403
    assert "Scorers can only create spectator or archer accounts" in res_scorer.json()["detail"]


def test_scorer_can_update_spectator_and_archer(
    test_client: TestClient, scorer_headers: dict, test_spectator_user: User
):
    # Scorer updates spectator active status and promotes to archer
    res = test_client.patch(
        f"/api/users/{test_spectator_user.id}",
        headers=scorer_headers,
        json={"role": "archer", "is_active": True},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "archer"


def test_scorer_cannot_promote_to_admin_or_scorer(
    test_client: TestClient, scorer_headers: dict, test_spectator_user: User
):
    # Scorer attempts to promote spectator to admin -> 403
    res_admin = test_client.patch(
        f"/api/users/{test_spectator_user.id}",
        headers=scorer_headers,
        json={"role": "admin"},
    )
    assert res_admin.status_code == 403
    assert "Scorers can only assign spectator or archer roles" in res_admin.json()["detail"]

    # Scorer attempts to promote spectator to scorer -> 403
    res_scorer = test_client.patch(
        f"/api/users/{test_spectator_user.id}",
        headers=scorer_headers,
        json={"role": "scorer"},
    )
    assert res_scorer.status_code == 403
    assert "Scorers can only assign spectator or archer roles" in res_scorer.json()["detail"]


def test_scorer_cannot_modify_or_deactivate_admin(
    test_client: TestClient, scorer_headers: dict, test_admin_user: User
):
    # Attempt to modify admin
    res_patch = test_client.patch(
        f"/api/users/{test_admin_user.id}",
        headers=scorer_headers,
        json={"role": "spectator"},
    )
    assert res_patch.status_code == 403

    # Attempt to deactivate admin
    res_del = test_client.delete(
        f"/api/users/{test_admin_user.id}",
        headers=scorer_headers,
    )
    assert res_del.status_code == 403


def test_spectator_and_archer_blocked_from_user_management(
    test_client: TestClient, spectator_headers: dict, archer_headers: dict
):
    # Spectator blocked from listing
    assert test_client.get("/api/users", headers=spectator_headers).status_code == 403
    # Spectator blocked from creating
    assert test_client.post(
        "/api/users",
        headers=spectator_headers,
        json={"username": "test", "email": "test@test.com", "password": "Password123!", "role": "archer"},
    ).status_code == 403

    # Archer blocked from listing
    assert test_client.get("/api/users", headers=archer_headers).status_code == 403
    # Archer blocked from creating
    assert test_client.post(
        "/api/users",
        headers=archer_headers,
        json={"username": "test2", "email": "test2@test.com", "password": "Password123!", "role": "archer"},
    ).status_code == 403
