"""
Integration tests for Pose Biomechanics & Score Prediction API endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient

class TestPoseAPI:
    """Integration tests for /api/pose routes."""

    def test_list_sample_videos(self, test_client: TestClient):
        """GET /api/pose/sample-videos returns the 3 generated sample videos."""
        res = test_client.get("/api/pose/sample-videos")
        assert res.status_code == 200
        data = res.json()
        assert "videos" in data
        assert data["total"] >= 3
        ids = [v["id"] for v in data["videos"]]
        assert "gold_form_10" in ids
        assert "bow_arm_drop_7" in ids
        assert "unstable_anchor_5" in ids

    def test_get_sample_video_details(self, test_client: TestClient):
        """GET /api/pose/sample-videos/{id} returns details for a valid video."""
        res = test_client.get("/api/pose/sample-videos/gold_form_10")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "gold_form_10"
        assert data["expected_score"] == 10

    def test_get_sample_video_not_found(self, test_client: TestClient):
        """GET /api/pose/sample-videos/unknown returns 404."""
        res = test_client.get("/api/pose/sample-videos/non_existent_video")
        assert res.status_code == 404

    def test_analyze_sample_video(self, test_client: TestClient):
        """POST /api/pose/sample-videos/{id}/analyze runs kinematics and ML prediction."""
        res = test_client.post("/api/pose/sample-videos/gold_form_10/analyze")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "phases" in data
        assert "prediction" in data
        assert data["prediction"]["predicted_score"] >= 9
        assert data["prediction"]["score_category"] == "Gold"

    def test_predict_metrics_endpoint(self, test_client: TestClient):
        """POST /api/pose/predict-metrics performs direct feature inference."""
        res = test_client.post(
            "/api/pose/predict-metrics",
            json={
                "bow_arm_angle": 179.5,
                "draw_elbow_angle": 139.0,
                "anchor_jitter": 0.5,
                "bow_arm_deflection_deg": 0.4,
                "anchor_duration_sec": 2.1
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["prediction"]["predicted_score"] in [9, 10]
        assert data["prediction"]["score_category"] == "Gold"

    def test_stream_sample_video(self, test_client: TestClient):
        """GET /api/pose/sample-videos/{id}/stream returns video/mp4 stream."""
        res = test_client.get("/api/pose/sample-videos/gold_form_10/stream")
        assert res.status_code in [200, 206]
        assert "video/mp4" in res.headers.get("content-type", "")

    def test_stream_sample_video_range(self, test_client: TestClient):
        """GET /api/pose/sample-videos/{id}/stream with HTTP Range header returns 206."""
        res = test_client.get(
            "/api/pose/sample-videos/gold_form_10/stream",
            headers={"Range": "bytes=0-1023"}
        )
        assert res.status_code == 206
        assert "bytes 0-1023/" in res.headers.get("content-range", "")

    def test_evaluate_posture_endpoint(self, test_client: TestClient):
        """POST /api/pose/evaluate-posture computes posture accuracy % and diagnostic tiers."""
        payload = {
            "bow_arm_angle": 179.0,
            "draw_elbow_angle": 138.5,
            "anchor_jitter": 0.5,
            "bow_arm_deflection_deg": 0.4,
            "anchor_duration_sec": 1.95,
            "camera_source": "archer_posture_cam"
        }
        res = test_client.post("/api/pose/evaluate-posture", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "overall_accuracy_pct" in data
        assert data["overall_accuracy_pct"] >= 90.0
        assert data["accuracy_tier"] in ["OLYMPIC_ELITE", "COMPETITIVE"]
        assert "bow_arm_accuracy_pct" in data["components"]
        assert "draw_elbow_accuracy_pct" in data["components"]
        assert len(data["diagnostics"]) > 0
        assert data["camera_source"] == "archer_posture_cam"

    def test_list_lanes_and_archers(self, test_client: TestClient):
        """GET /api/pose/lanes-and-archers returns range lanes with assigned archers."""
        res = test_client.get("/api/pose/lanes-and-archers")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["lanes"]) >= 6
        lane1 = data["lanes"][0]
        assert lane1["lane_number"] == 1
        assert "archer" in lane1
        assert "camera" in lane1
        assert lane1["archer"]["name"] == "Rumman Shafi"

    def test_analyze_live_camera_frame(self, test_client: TestClient):
        """POST /api/pose/analyze-live-frame generates 33 landmarks, joint angles, and accuracy."""
        payload = {
            "lane_number": 1,
            "archer_id": 101,
            "archer_name": "Rumman Shafi",
            "bow_arm_angle": 179.2,
            "draw_elbow_angle": 139.0,
            "anchor_jitter": 0.45,
            "bow_arm_deflection_deg": 0.35,
            "anchor_duration_sec": 1.95,
            "phase": "anchor"
        }
        res = test_client.post("/api/pose/analyze-live-frame", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["landmarks"]) == 33
        assert data["metrics"]["bow_arm_angle"] == 179.2
        assert data["posture_accuracy"]["overall_accuracy_pct"] >= 90.0
        assert data["predicted_score"] in [9, 10]
