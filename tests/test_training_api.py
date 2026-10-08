"""
Integration tests for YOLO Model Training API endpoints.
"""

from fastapi.testclient import TestClient


class TestTrainingAPI:
    """Integration tests for /api/training routes."""

    def test_get_training_status(self, test_client: TestClient):
        """GET /api/training/status returns current training status."""
        res = test_client.get("/api/training/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "progress" in data

    def test_get_dataset_info(self, test_client: TestClient):
        """GET /api/training/dataset returns dataset splits and classes."""
        res = test_client.get("/api/training/dataset")
        assert res.status_code == 200
        data = res.json()
        assert "classes" in data
        assert "train_images" in data

    def test_get_training_history(self, test_client: TestClient):
        """GET /api/training/history returns epoch metrics."""
        res = test_client.get("/api/training/history")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data

    def test_reload_weights(self, test_client: TestClient):
        """POST /api/training/reload reloads best weights into detector."""
        res = test_client.post("/api/training/reload")
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "ok"
