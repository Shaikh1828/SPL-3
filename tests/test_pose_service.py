"""
Unit and Integration Tests for Archer Pose Biomechanics & Score Prediction.
"""

import os
import pytest
from src.services.kinematic_video_generator import KinematicVideoGenerator
from src.services.pose_score_model import PoseScoreModel
from src.services.pose_analysis_service import PoseAnalysisService

class TestKinematicVideoGenerator:
    """Tests for synthetic benchmark video generator."""

    def test_sample_files_exist(self):
        """Ensure benchmark videos and JSON metadata are generated and non-empty."""
        expected_ids = ["gold_form_10", "bow_arm_drop_7", "unstable_anchor_5"]
        for vid_id in expected_ids:
            mp4_path = os.path.join("storage", "sample_videos", f"{vid_id}.mp4")
            json_path = os.path.join("storage", "sample_videos", f"{vid_id}.json")
            assert os.path.exists(mp4_path), f"Missing {mp4_path}"
            assert os.path.exists(json_path), f"Missing {json_path}"
            assert os.path.getsize(mp4_path) > 10000
            assert os.path.getsize(json_path) > 1000

    def test_video_metadata_structure(self):
        """Validate JSON metadata keys and landmark structure."""
        generator = KinematicVideoGenerator()
        service = PoseAnalysisService()
        meta = service.analyze_sample_video("gold_form_10")
        
        assert meta["success"] is True
        assert meta["video_id"] == "gold_form_10"
        assert len(meta["phases"]) == 4
        assert meta["phases"][0]["phase"] == "stance"
        assert meta["phases"][1]["phase"] == "draw"
        assert meta["phases"][2]["phase"] == "anchor"
        assert meta["phases"][3]["phase"] == "release"
        assert len(meta["frames_landmarks"]) > 50
        assert len(meta["frames_landmarks"][0]["landmarks"]) == 33


class TestPoseScoreModel:
    """Tests for Machine Learning Pose Score Model."""

    @pytest.fixture
    def model(self):
        return PoseScoreModel()

    def test_predict_elite_form(self, model):
        """Elite biomechanical parameters should predict high score (9-10/X, Gold)."""
        res = model.predict({
            "bow_arm_angle": 179.5,
            "draw_elbow_angle": 139.0,
            "anchor_jitter": 0.4,
            "bow_arm_deflection_deg": 0.3,
            "anchor_duration_sec": 2.0
        })
        assert res["predicted_score"] >= 9
        assert res["score_category"] == "Gold"
        assert res["form_score_pct"] >= 90.0
        assert len(res["diagnostics"]) > 0

    def test_predict_arm_drop_fault(self, model):
        """Substantial bow arm deflection at release should degrade predicted score to 7-8."""
        res = model.predict({
            "bow_arm_angle": 173.0,
            "draw_elbow_angle": 134.0,
            "anchor_jitter": 1.5,
            "bow_arm_deflection_deg": 6.8,  # Significant drop
            "anchor_duration_sec": 1.5
        })
        assert res["predicted_score"] <= 8
        assert res["score_category"] in ["Red", "Blue"]
        assert any(d["status"] in ["POOR", "NEEDS_WORK"] for d in res["diagnostics"])

    def test_predict_unstable_anchor_fault(self, model):
        """High tremor jitter and sagging elbow should drop score to 4-6."""
        res = model.predict({
            "bow_arm_angle": 165.0,
            "draw_elbow_angle": 120.0,
            "anchor_jitter": 4.5,
            "bow_arm_deflection_deg": 8.0,
            "anchor_duration_sec": 0.7  # Rushed
        })
        assert res["predicted_score"] <= 6
        assert res["form_score_pct"] < 75.0


class TestPoseAnalysisService:
    """Tests for PoseAnalysisService orchestration."""

    def test_list_samples(self):
        service = PoseAnalysisService()
        samples = service.list_sample_videos()
        assert len(samples) >= 3
        ids = [s["id"] for s in samples]
        assert "gold_form_10" in ids
        assert "bow_arm_drop_7" in ids
        assert "unstable_anchor_5" in ids
        assert all(s["is_available"] for s in samples)

    def test_analyze_sample_bow_arm_drop(self):
        service = PoseAnalysisService()
        res = service.analyze_sample_video("bow_arm_drop_7")
        assert res["success"] is True
        assert res["prediction"]["predicted_score"] <= 8
        assert res["biomechanics_summary"]["bow_arm_deflection_deg"] > 3.0
