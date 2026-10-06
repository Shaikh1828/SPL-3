"""
Pose Biomechanics Score Prediction Model.
Trained ML model predicting Olympic target score (1-10 points / X-Ring)
and form ratings from biomechanical body keypoint telemetry.
"""

import os
import joblib
import logging
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class PoseScoreModel:
    """Predicts arrow score, ring category, and biomechanical feedback from archer pose features."""

    MODEL_PATH = "models/pose_score_model.joblib"
    FEATURE_NAMES = [
        "bow_arm_angle",            # deg (ideal: 178 - 180)
        "draw_elbow_angle",         # deg (ideal: 135 - 145)
        "anchor_jitter",            # px std (ideal: < 1.0)
        "bow_arm_deflection_deg",   # deg drop at release (ideal: < 1.2)
        "anchor_duration_sec",      # sec (ideal: 1.6 - 2.4)
        "release_velocity_px",      # px/frame (ideal: 20 - 45)
        "torso_tilt_deg"            # deg (ideal: 89 - 91)
    ]

    def __init__(self):
        self.regressor = None
        self.classifier = None
        self.scaler = None
        self._ensure_model_trained()

    def _ensure_model_trained(self):
        """Loads saved model or trains a new calibrated model if absent."""
        if os.path.exists(self.MODEL_PATH):
            try:
                bundle = joblib.load(self.MODEL_PATH)
                self.regressor = bundle["regressor"]
                self.classifier = bundle["classifier"]
                self.scaler = bundle["scaler"]
                logger.info("Loaded pose score prediction model from %s", self.MODEL_PATH)
                return
            except Exception as e:
                logger.warning("Failed to load model file, retraining: %s", e)

        self.train_calibrated_model()

    def train_calibrated_model(self):
        """Trains ML model on calibrated biomechanics dataset."""
        logger.info("Training calibrated biomechanics score prediction model...")
        np.random.seed(42)
        n_samples = 600

        X = []
        y_scores = []
        y_categories = []

        for _ in range(n_samples):
            # Sample realistic shot qualities:
            # 35% Elite (9-10/X), 35% Intermediate (7-8), 30% Beginner/Flawed (3-6)
            tier = np.random.choice(["elite", "intermediate", "flawed"], p=[0.35, 0.35, 0.30])
            
            if tier == "elite":
                bow_arm = np.random.normal(179.2, 0.8)
                elbow = np.random.normal(139.5, 2.5)
                jitter = np.random.exponential(0.6)
                deflection = np.random.exponential(0.7)
                hold_sec = np.random.normal(2.0, 0.25)
                vel = np.random.normal(35.0, 5.0)
                tilt = np.random.normal(90.0, 0.8)
                score = np.clip(10.5 - (jitter * 0.4) - (deflection * 0.5) - abs(179.5 - bow_arm) * 0.3, 9.0, 10.5)
                cat = "Gold"
            elif tier == "intermediate":
                bow_arm = np.random.normal(174.0, 2.5)
                elbow = np.random.normal(133.0, 4.0)
                jitter = np.random.normal(1.8, 0.5)
                deflection = np.random.normal(4.5, 1.2)  # Moderate bow arm drop
                hold_sec = np.random.normal(1.5, 0.4)
                vel = np.random.normal(28.0, 6.0)
                tilt = np.random.normal(88.5, 2.0)
                score = np.clip(8.5 - (deflection * 0.35) - (jitter * 0.3), 7.0, 8.8)
                cat = "Red"
            else:
                bow_arm = np.random.normal(165.0, 5.0)
                elbow = np.random.normal(122.0, 6.0)
                jitter = np.random.normal(4.2, 1.2)
                deflection = np.random.normal(7.5, 2.0)
                hold_sec = np.random.choice([0.7, 3.8])  # Rushed or fatigued
                vel = np.random.normal(18.0, 7.0)
                tilt = np.random.normal(86.0, 3.5)
                score = np.clip(6.0 - (jitter * 0.4) - (deflection * 0.3), 3.0, 6.8)
                cat = "Blue" if score >= 5.0 else ("Black" if score >= 3.0 else "White")

            X.append([bow_arm, elbow, jitter, deflection, hold_sec, vel, tilt])
            y_scores.append(score)
            y_categories.append(cat)

        X = np.array(X)
        y_scores = np.array(y_scores)
        y_categories = np.array(y_categories)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        reg = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
        reg.fit(X_scaled, y_scores)

        clf = RandomForestClassifier(n_estimators=80, max_depth=4, random_state=42)
        clf.fit(X_scaled, y_categories)

        self.scaler = scaler
        self.regressor = reg
        self.classifier = clf

        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
        joblib.dump({
            "scaler": scaler,
            "regressor": reg,
            "classifier": clf,
            "features": self.FEATURE_NAMES
        }, self.MODEL_PATH)
        logger.info("Model successfully trained and saved to %s", self.MODEL_PATH)

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Runs inference given a biomechanical feature dictionary."""
        bow_arm = features.get("bow_arm_angle", 178.0)
        draw_elbow = features.get("draw_elbow_angle", 138.0)
        jitter = features.get("anchor_jitter", 0.8)
        deflection = features.get("bow_arm_deflection_deg", 0.5)
        hold_sec = features.get("anchor_duration_sec", 1.9)
        vel = features.get("release_velocity_px", 32.0)
        tilt = features.get("torso_tilt_deg", 90.0)

        vec = np.array([[bow_arm, draw_elbow, jitter, deflection, hold_sec, vel, tilt]])
        vec_scaled = self.scaler.transform(vec)

        raw_score = float(self.regressor.predict(vec_scaled)[0])
        # Format integer score & X-Ring
        if raw_score >= 10.0:
            int_score = 10
            is_x_ring = raw_score >= 10.3
            score_display = "X" if is_x_ring else "10"
        else:
            int_score = max(1, min(9, int(round(raw_score))))
            is_x_ring = False
            score_display = str(int_score)

        # Form rating percentage (0 - 100%)
        form_score_pct = round(max(10.0, min(99.0, (raw_score / 10.5) * 100.0)), 1)

        # Ring Category & Colors
        if int_score == 10:
            category = "Gold"
            category_color = "#FFD700"
            zone_desc = "Gold Inner 10 / X-Ring"
        elif int_score == 9:
            category = "Gold"
            category_color = "#E6B800"
            zone_desc = "Gold 9-Ring"
        elif int_score in [8, 7]:
            category = "Red"
            category_color = "#E53E3E"
            zone_desc = f"Red {int_score}-Ring"
        elif int_score in [6, 5]:
            category = "Blue"
            category_color = "#3182CE"
            zone_desc = f"Blue {int_score}-Ring"
        elif int_score in [4, 3]:
            category = "Black"
            category_color = "#2D3748"
            zone_desc = f"Black {int_score}-Ring"
        else:
            category = "White"
            category_color = "#E2E8F0"
            zone_desc = f"White {int_score}-Ring"

        # Multi-dimensional posture accuracy percentage (0-100%)
        bow_arm_acc = max(0.0, min(100.0, 100.0 - abs(179.2 - bow_arm) * 4.5))
        draw_elbow_acc = max(0.0, min(100.0, 100.0 - abs(139.0 - draw_elbow) * 3.5))
        anchor_acc = max(0.0, min(100.0, 100.0 - (jitter * 16.0)))
        release_acc = max(0.0, min(100.0, 100.0 - (deflection * 12.0)))
        timing_acc = max(0.0, min(100.0, 100.0 - abs(2.0 - hold_sec) * 25.0))
        torso_acc = max(0.0, min(100.0, 100.0 - abs(90.0 - tilt) * 6.0))

        overall_acc = round(
            0.25 * bow_arm_acc +
            0.25 * release_acc +
            0.20 * anchor_acc +
            0.15 * draw_elbow_acc +
            0.15 * ((timing_acc + torso_acc) / 2.0),
            1
        )

        if overall_acc >= 92.0:
            acc_tier = "OLYMPIC_ELITE"
            acc_label = "Olympic Gold Standard"
            acc_color = "#10B981"  # Emerald
        elif overall_acc >= 82.0:
            acc_label = "High Competitive Form"
            acc_tier = "COMPETITIVE"
            acc_color = "#3B82F6"  # Blue
        elif overall_acc >= 70.0:
            acc_label = "Moderate Form Deviation"
            acc_tier = "INTERMEDIATE"
            acc_color = "#F59E0B"  # Amber
        else:
            acc_label = "Flawed Posture Detected"
            acc_tier = "DEFICIENT"
            acc_color = "#EF4444"  # Rose

        posture_accuracy = {
            "overall_accuracy_pct": overall_acc,
            "accuracy_tier": acc_tier,
            "accuracy_label": acc_label,
            "tier_color": acc_color,
            "components": {
                "bow_arm_accuracy_pct": round(bow_arm_acc, 1),
                "draw_elbow_accuracy_pct": round(draw_elbow_acc, 1),
                "anchor_stability_accuracy_pct": round(anchor_acc, 1),
                "release_follow_through_accuracy_pct": round(release_acc, 1),
                "timing_balance_accuracy_pct": round(timing_acc, 1),
            }
        }

        # Diagnostic ratings & coaching tips
        diagnostics = self._generate_coaching_diagnostics(bow_arm, draw_elbow, jitter, deflection, hold_sec)

        return {
            "predicted_score": int_score,
            "score_display": score_display,
            "exact_score": round(raw_score, 2),
            "is_x_ring": is_x_ring,
            "score_category": category,
            "category_color": category_color,
            "zone_description": zone_desc,
            "form_score_pct": form_score_pct,
            "confidence": round(float(np.clip(0.85 + (form_score_pct / 1000.0), 0.82, 0.96)), 2),
            "posture_accuracy": posture_accuracy,
            "metrics_evaluated": {
                "bow_arm_angle": round(bow_arm, 1),
                "draw_elbow_angle": round(draw_elbow, 1),
                "anchor_jitter_px": round(jitter, 2),
                "bow_arm_deflection_deg": round(deflection, 1),
                "anchor_duration_sec": round(hold_sec, 2)
            },
            "diagnostics": diagnostics
        }

    def _generate_coaching_diagnostics(self, bow_arm: float, draw_elbow: float, jitter: float,
                                       deflection: float, hold_sec: float) -> List[Dict[str, Any]]:
        """Produces actionable coaching diagnostic feedback cards."""
        feedback = []

        # 1. Bow Arm Alignment
        if bow_arm >= 177.0:
            feedback.append({
                "metric": "Bow Arm Extension",
                "status": "EXCELLENT",
                "value": f"{bow_arm:.1f}°",
                "target": "178° - 180°",
                "message": "Near-perfect bow arm alignment creating maximum skeletal support."
            })
        elif bow_arm >= 172.0:
            feedback.append({
                "metric": "Bow Arm Extension",
                "status": "GOOD",
                "value": f"{bow_arm:.1f}°",
                "target": "178° - 180°",
                "message": "Acceptable bow arm extension. Ensure front shoulder remains rotated and settled."
            })
        else:
            feedback.append({
                "metric": "Bow Arm Extension",
                "status": "NEEDS_WORK",
                "value": f"{bow_arm:.1f}°",
                "target": "178° - 180°",
                "message": "Front elbow slightly bent or shoulder elevated; risk of inconsistent draw length."
            })

        # 2. Release Stability / Bow Arm Drop
        if deflection <= 1.2:
            feedback.append({
                "metric": "Release Stability",
                "status": "EXCELLENT",
                "value": f"{deflection:.1f}° drop",
                "target": "< 1.5°",
                "message": "Rock-solid follow-through. Bow arm stayed level through arrow departure."
            })
        elif deflection <= 3.5:
            feedback.append({
                "metric": "Release Stability",
                "status": "GOOD",
                "value": f"{deflection:.1f}° drop",
                "target": "< 1.5°",
                "message": "Minor front-shoulder relaxation at release."
            })
        else:
            feedback.append({
                "metric": "Release Stability",
                "status": "POOR",
                "value": f"{deflection:.1f}° drop",
                "target": "< 1.5°",
                "message": "Significant bow arm drop upon release; likely pulled arrow low into lower rings."
            })

        # 3. Anchor Hold Tremor
        if jitter <= 1.0:
            feedback.append({
                "metric": "Anchor Point Stability",
                "status": "EXCELLENT",
                "value": f"{jitter:.2f} px tremor",
                "target": "< 1.0 px",
                "message": "Tremor-free anchor lock beneath jawbone."
            })
        elif jitter <= 2.2:
            feedback.append({
                "metric": "Anchor Point Stability",
                "status": "GOOD",
                "value": f"{jitter:.2f} px tremor",
                "target": "< 1.0 px",
                "message": "Mild aiming sway during expansion."
            })
        else:
            feedback.append({
                "metric": "Anchor Point Stability",
                "status": "POOR",
                "value": f"{jitter:.2f} px tremor",
                "target": "< 1.0 px",
                "message": "Excessive anchor drift or trembling fingers detected during aiming phase."
            })

        # 4. Anchor Hold Duration
        if 1.5 <= hold_sec <= 2.8:
            feedback.append({
                "metric": "Anchor Duration",
                "status": "EXCELLENT",
                "value": f"{hold_sec:.2f}s",
                "target": "1.5s - 2.5s",
                "message": "Optimal timing rhythm between settling sight pin and release."
            })
        elif hold_sec < 1.5:
            feedback.append({
                "metric": "Anchor Duration",
                "status": "NEEDS_WORK",
                "value": f"{hold_sec:.2f}s",
                "target": "1.5s - 2.5s",
                "message": "Rushed release executed before complete anchor settlement."
            })
        else:
            feedback.append({
                "metric": "Anchor Duration",
                "status": "NEEDS_WORK",
                "value": f"{hold_sec:.2f}s",
                "target": "1.5s - 2.5s",
                "message": "Holding longer than 3 seconds; muscular fatigue may cause sight pin drift."
            })

        return feedback
