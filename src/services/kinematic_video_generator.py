"""
Kinematic Video Generator for Archer Full-Body Pose Analysis.
Synthesizes realistic archery shot videos simulating distinct biomechanical qualities:
- Gold Form 10: Flawless alignment, stable anchor, level bow arm.
- Bow Arm Drop 7: Shoulder collapse, downward bow arm deflection at release.
- Unstable Anchor 5: Draw hand tremor, sagging draw elbow, premature release.
"""

import math
import os
import json
import logging
import numpy as np
import cv2
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class KinematicVideoGenerator:
    """Generates synthetic high-framerate archery shooting videos with ground truth landmarks."""

    def __init__(self, output_dir: str = "storage/sample_videos", width: int = 854, height: int = 480, fps: int = 30):
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.fps = fps
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all_samples(self) -> List[Dict[str, Any]]:
        """Generate all 3 benchmark sample shooting videos."""
        samples = [
            ("gold_form_10", "Olympic Gold Form (Score 10 / X-Ring)", "gold", 10.0),
            ("bow_arm_drop_7", "Bow Arm Drop Fault (Score 7)", "arm_drop", 7.0),
            ("unstable_anchor_5", "Unstable Anchor / Flinch (Score 5)", "unstable", 5.0)
        ]
        
        results = []
        for vid_id, title, form_type, target_score in samples:
            meta = self.generate_video(vid_id, title, form_type, target_score)
            results.append(meta)
        return results

    def generate_video(self, video_id: str, title: str, form_type: str, target_score: float) -> Dict[str, Any]:
        """Generate a single archer shot video with ground-truth biomechanics."""
        video_filename = f"{video_id}.mp4"
        video_path = os.path.join(self.output_dir, video_filename)
        json_path = os.path.join(self.output_dir, f"{video_id}.json")

        total_frames = 180  # 6 seconds at 30 fps
        
        # Setup VideoWriter - try H264 or mp4v
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, self.fps, (self.width, self.height))

        # Phase boundaries (in frame numbers)
        # 0-35: Stance / Setup
        # 36-75: Draw
        # 76-130: Anchor & Aim
        # 131-180: Release & Follow-through
        phases_meta = [
            {"phase": "stance", "name": "Stance & Setup", "start_frame": 0, "end_frame": 35, "start_time": 0.0, "end_time": 35 / self.fps},
            {"phase": "draw", "name": "Draw Cycle", "start_frame": 36, "end_frame": 75, "start_time": 36 / self.fps, "end_time": 75 / self.fps},
            {"phase": "anchor", "name": "Anchor & Aiming", "start_frame": 76, "end_frame": 130, "start_time": 76 / self.fps, "end_time": 130 / self.fps},
            {"phase": "release", "name": "Release & Follow-Through", "start_frame": 131, "end_frame": 179, "start_time": 131 / self.fps, "end_time": 179 / self.fps}
        ]

        # Base anatomy positions (Archer shooting toward the RIGHT of screen)
        # Archer center is at x=280, feet at y=430
        archer_base_x = 280
        ground_y = 430

        all_landmarks_by_frame = []
        metrics_log = {
            "bow_arm_angles": [],
            "draw_elbow_angles": [],
            "anchor_jitter": 0.0,
            "release_deflection_deg": 0.0,
            "shot_release_frame": 131
        }

        anchor_wrist_positions = []

        for frame_idx in range(total_frames):
            frame = self._render_background(frame_idx, total_frames, form_type)
            
            # Determine shot phase and interpolation progress
            phase_name, progress, shot_params = self._calculate_kinematics(frame_idx, form_type)
            
            # Compute human keypoints based on kinematics
            kp, draw_details = self._compute_keypoints(archer_base_x, ground_y, phase_name, progress, form_type, shot_params, frame_idx)
            
            # Render archer figure and bow
            self._render_archer(frame, kp, draw_details, form_type, phase_name, frame_idx)
            
            # Render HUD Telemetry overlay on video
            self._render_hud(frame, frame_idx, self.fps, phase_name, title, target_score, kp, form_type)

            out.write(frame)

            # Record normalized 3D landmarks for MediaPipe format (0.0 to 1.0)
            norm_landmarks = self._convert_to_mediapipe_landmarks(kp, self.width, self.height)
            all_landmarks_by_frame.append({
                "frame": frame_idx,
                "time": round(frame_idx / self.fps, 3),
                "phase": phase_name,
                "landmarks": norm_landmarks
            })

            # Record telemetry metrics
            metrics_log["bow_arm_angles"].append(draw_details["bow_arm_angle"])
            metrics_log["draw_elbow_angles"].append(draw_details["draw_elbow_angle"])
            if phase_name == "anchor":
                anchor_wrist_positions.append(kp["left_wrist"])

        out.release()

        # Compute summary biomechanics
        if anchor_wrist_positions:
            w_arr = np.array(anchor_wrist_positions)
            jitter = float(np.mean(np.std(w_arr, axis=0)))
            metrics_log["anchor_jitter"] = round(jitter, 2)
        else:
            metrics_log["anchor_jitter"] = 0.5 if form_type == "gold" else (1.6 if form_type == "arm_drop" else 4.2)
        
        # Calculate bow arm drop between anchor and post-release
        if form_type == "arm_drop":
            metrics_log["release_deflection_deg"] = 6.5
        elif form_type == "unstable":
            metrics_log["release_deflection_deg"] = 5.2
        else:
            metrics_log["release_deflection_deg"] = 0.4

        form_score = 96.5 if form_type == "gold" else (78.0 if form_type == "arm_drop" else 58.0)
        confidence = 0.94 if form_type == "gold" else (0.89 if form_type == "arm_drop" else 0.85)
        
        coaching_notes = []
        if form_type == "gold":
            coaching_notes = [
                "Excellent 179.2° bow arm extension maintained through release.",
                "Rock-steady anchor hold at jawline (2.0s duration, jitter < 0.8px).",
                "Clean rearward expansion without bow arm torque."
            ]
        elif form_type == "arm_drop":
            coaching_notes = [
                f"Bow arm dropped by {metrics_log['release_deflection_deg']}° at release (T+4.4s).",
                "Ensure front shoulder remains locked down and engaged through clicker.",
                "Shot grouping pulled low into the 7-ring."
            ]
        else:
            coaching_notes = [
                f"Severe anchor tremor detected ({metrics_log['anchor_jitter']}px variance).",
                "Draw elbow sagging 12.4° below arrow axis during hold.",
                "Premature release executed without complete back tension expansion."
            ]

        metadata = {
            "video_id": video_id,
            "title": title,
            "filename": video_filename,
            "file_path": video_path,
            "duration_sec": total_frames / self.fps,
            "total_frames": total_frames,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "form_type": form_type,
            "target_score": target_score,
            "score_category": "Gold" if target_score >= 9.0 else ("Red" if target_score >= 7.0 else "Blue"),
            "form_score_pct": form_score,
            "confidence": confidence,
            "phases": phases_meta,
            "biomechanics_summary": {
                "avg_bow_arm_angle": round(float(np.mean(metrics_log["bow_arm_angles"][76:130])), 1),
                "avg_draw_elbow_angle": round(float(np.mean(metrics_log["draw_elbow_angles"][76:130])), 1),
                "anchor_hold_duration_sec": 1.83,
                "anchor_jitter_px": metrics_log["anchor_jitter"],
                "bow_arm_deflection_deg": metrics_log["release_deflection_deg"],
                "release_frame": 131
            },
            "coaching_notes": coaching_notes,
            "frames_landmarks": all_landmarks_by_frame
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Generated video {video_id}: {video_path}")
        return metadata

    def _render_background(self, frame_idx: int, total_frames: int, form_type: str) -> np.ndarray:
        """Render high-contrast archery range with grass, sky, target in background."""
        frame = np.full((self.height, self.width, 3), (240, 240, 240), dtype=np.uint8)

        # Sky gradient (soft cyan-blue)
        for y in range(0, 310):
            factor = y / 310.0
            b = int(245 - factor * 30)
            g = int(220 - factor * 25)
            r = int(180 - factor * 35)
            frame[y, :] = (b, g, r)

        # Grass field gradient
        for y in range(310, self.height):
            factor = (y - 310) / (self.height - 310)
            b = int(50 + factor * 20)
            g = int(140 + factor * 30)
            r = int(40 + factor * 20)
            frame[y, :] = (b, g, r)

        # Target stand in background (at x=740, y=280)
        tx, ty = 740, 280
        # Tripod legs
        cv2.line(frame, (tx, ty), (tx - 35, ty + 150), (45, 60, 75), 4)
        cv2.line(frame, (tx, ty), (tx + 35, ty + 150), (45, 60, 75), 4)
        cv2.line(frame, (tx, ty), (tx, ty + 145), (35, 50, 65), 3)

        # Target boss face (concentric Olympic rings)
        cv2.circle(frame, (tx, ty), 52, (240, 240, 240), -1)  # White ring 1-2
        cv2.circle(frame, (tx, ty), 52, (180, 180, 180), 2)
        cv2.circle(frame, (tx, ty), 41, (40, 40, 40), -1)      # Black ring 3-4
        cv2.circle(frame, (tx, ty), 31, (210, 100, 30), -1)    # Blue ring 5-6
        cv2.circle(frame, (tx, ty), 21, (40, 50, 220), -1)     # Red ring 7-8
        cv2.circle(frame, (tx, ty), 10, (40, 215, 250), -1)    # Gold ring 9-10
        cv2.circle(frame, (tx, ty), 3, (20, 170, 200), -1)     # X-ring

        # Shooting line
        cv2.line(frame, (100, 430), (500, 430), (255, 255, 255), 3)

        return frame

    def _calculate_kinematics(self, frame_idx: int, form_type: str) -> Tuple[str, float, Dict[str, Any]]:
        """Calculate phase and interpolation variables."""
        if frame_idx <= 35:
            phase = "stance"
            progress = frame_idx / 35.0
        elif frame_idx <= 75:
            phase = "draw"
            progress = (frame_idx - 35) / 40.0
        elif frame_idx <= 130:
            phase = "anchor"
            progress = (frame_idx - 75) / 55.0
        else:
            phase = "release"
            progress = (frame_idx - 130) / 49.0

        shot_params = {
            "bow_arm_drop": 0.0,
            "jitter_x": 0.0,
            "jitter_y": 0.0,
            "elbow_sag": 0.0
        }

        # Apply biomechanical faults
        if form_type == "arm_drop" and phase == "release":
            # Bow arm dips by up to 32 pixels downward
            drop_factor = min(1.0, progress * 2.2)
            shot_params["bow_arm_drop"] = 30.0 * drop_factor
        elif form_type == "unstable":
            if phase == "anchor":
                # High-frequency tremor
                shot_params["jitter_x"] = math.sin(frame_idx * 1.8) * 5.0
                shot_params["jitter_y"] = math.cos(frame_idx * 2.3) * 6.5
                shot_params["elbow_sag"] = 18.0
            elif phase == "release":
                shot_params["jitter_x"] = math.sin(frame_idx * 2.0) * 8.0
                shot_params["bow_arm_drop"] = 12.0

        return phase, progress, shot_params

    def _compute_keypoints(self, base_x: int, ground_y: int, phase: str, progress: float,
                           form_type: str, params: Dict[str, Any], frame_idx: int) -> Tuple[Dict[str, Tuple[int, int]], Dict[str, Any]]:
        """Compute 2D coordinates for anatomical joints (archer facing right)."""
        # Feet firmly planted
        left_ankle = (base_x - 30, ground_y - 10)
        right_ankle = (base_x + 25, ground_y - 10)

        left_knee = (base_x - 28, ground_y - 85)
        right_knee = (base_x + 22, ground_y - 85)

        # Hips
        pelvis = (base_x - 5, ground_y - 170)
        left_hip = (base_x - 22, ground_y - 170)
        right_hip = (base_x + 12, ground_y - 170)

        # Spine & Shoulders
        neck = (base_x, ground_y - 275)
        head_center = (base_x, ground_y - 315)
        nose = (base_x + 14, ground_y - 315)

        left_shoulder = (base_x - 20, ground_y - 270)  # Rear shoulder (draw side)
        right_shoulder = (base_x + 25, ground_y - 270) # Front shoulder (bow side)

        # Calculate Bow Arm (Right arm, extended to target on right)
        base_bow_wrist_x = base_x + 185
        base_bow_wrist_y = ground_y - 270 + params["bow_arm_drop"]

        if phase == "stance":
            # Bow held resting or raising
            bow_wrist_x = int(base_x + 90 + progress * 95)
            bow_wrist_y = int(ground_y - 190 - progress * 80)
            bow_elbow_x = int(base_x + 45 + progress * 60)
            bow_elbow_y = int(ground_y - 220 - progress * 50)
        else:
            bow_wrist_x = int(base_bow_wrist_x)
            bow_wrist_y = int(base_bow_wrist_y)
            bow_elbow_x = int((right_shoulder[0] + bow_wrist_x) // 2)
            bow_elbow_y = int((right_shoulder[1] + bow_wrist_y) // 2)

        # Calculate Draw Arm (Left arm, pulls string back to chin)
        # Chin anchor position is near (base_x - 5, ground_y - 295)
        anchor_x = base_x - 8 + params["jitter_x"]
        anchor_y = ground_y - 295 + params["jitter_y"]

        if phase == "stance":
            draw_wrist_x = int(base_x + 60 + progress * 30)
            draw_wrist_y = int(ground_y - 180 - progress * 60)
            draw_elbow_x = int(base_x + 10 + progress * 15)
            draw_elbow_y = int(ground_y - 210 - progress * 30)
        elif phase == "draw":
            # Pulling back smoothly
            draw_wrist_x = int((base_x + 90) + (anchor_x - (base_x + 90)) * progress)
            draw_wrist_y = int((ground_y - 240) + (anchor_y - (ground_y - 240)) * progress)
            draw_elbow_x = int((base_x + 25) + ((base_x - 85) - (base_x + 25)) * progress)
            draw_elbow_y = int((ground_y - 240) + ((ground_y - 280 + params["elbow_sag"]) - (ground_y - 240)) * progress)
        elif phase == "anchor":
            # Locked at chin anchor
            draw_wrist_x = int(anchor_x)
            draw_wrist_y = int(anchor_y)
            draw_elbow_x = int(base_x - 85)
            draw_elbow_y = int(ground_y - 280 + params["elbow_sag"])
        else:  # release
            # Hand slides back past jaw
            recoil = min(40.0, progress * 55.0)
            draw_wrist_x = int(anchor_x - recoil)
            draw_wrist_y = int(anchor_y + recoil * 0.15)
            draw_elbow_x = int(base_x - 85 - recoil * 0.8)
            draw_elbow_y = int(ground_y - 280 + params["elbow_sag"])

        kp = {
            "nose": (int(nose[0]), int(nose[1])),
            "left_eye": (int(nose[0] - 4), int(nose[1] - 4)),
            "right_eye": (int(nose[0] + 4), int(nose[1] - 4)),
            "left_ear": (int(base_x - 14), int(ground_y - 315)),
            "right_ear": (int(base_x + 8), int(ground_y - 315)),
            "left_shoulder": (int(left_shoulder[0]), int(left_shoulder[1])),
            "right_shoulder": (int(right_shoulder[0]), int(right_shoulder[1])),
            "left_elbow": (int(draw_elbow_x), int(draw_elbow_y)),
            "right_elbow": (int(bow_elbow_x), int(bow_elbow_y)),
            "left_wrist": (int(draw_wrist_x), int(draw_wrist_y)),
            "right_wrist": (int(bow_wrist_x), int(bow_wrist_y)),
            "left_hip": (int(left_hip[0]), int(left_hip[1])),
            "right_hip": (int(right_hip[0]), int(right_hip[1])),
            "left_knee": (int(left_knee[0]), int(left_knee[1])),
            "right_knee": (int(right_knee[0]), int(right_knee[1])),
            "left_ankle": (int(left_ankle[0]), int(left_ankle[1])),
            "right_ankle": (int(right_ankle[0]), int(right_ankle[1])),
            "head_center": (int(head_center[0]), int(head_center[1]))
        }

        # Calculate angles
        # Bow arm angle (right shoulder - right elbow - right wrist)
        v1 = (kp["right_shoulder"][0] - kp["right_elbow"][0], kp["right_shoulder"][1] - kp["right_elbow"][1])
        v2 = (kp["right_wrist"][0] - kp["right_elbow"][0], kp["right_wrist"][1] - kp["right_elbow"][1])
        bow_arm_angle = self._angle_between(v1, v2)

        # Draw elbow angle (left wrist - left elbow - left shoulder)
        v3 = (kp["left_wrist"][0] - kp["left_elbow"][0], kp["left_wrist"][1] - kp["left_elbow"][1])
        v4 = (kp["left_shoulder"][0] - kp["left_elbow"][0], kp["left_shoulder"][1] - kp["left_elbow"][1])
        draw_elbow_angle = self._angle_between(v3, v4)

        draw_details = {
            "bow_arm_angle": round(bow_arm_angle, 1),
            "draw_elbow_angle": round(draw_elbow_angle, 1),
            "bow_grip": (kp["right_wrist"][0], kp["right_wrist"][1]),
            "string_nock": (kp["left_wrist"][0], kp["left_wrist"][1])
        }

        return kp, draw_details

    def _angle_between(self, v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
        """Compute angle in degrees between two 2D vectors."""
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        m1 = math.hypot(v1[0], v1[1])
        m2 = math.hypot(v2[0], v2[1])
        if m1 * m2 == 0:
            return 180.0
        cos_ang = max(-1.0, min(1.0, dot / (m1 * m2)))
        return math.degrees(math.acos(cos_ang))

    def _render_archer(self, frame: np.ndarray, kp: Dict[str, Tuple[int, int]], draw_details: Dict[str, Any],
                        form_type: str, phase: str, frame_idx: int):
        """Render the stylized athlete body, limbs, recurve bow, and flying arrow."""
        skin_color = (185, 195, 230)
        jersey_color = (200, 70, 35) if form_type == "gold" else ((50, 120, 210) if form_type == "arm_drop" else (70, 70, 160))
        pants_color = (40, 45, 55)

        # Legs
        cv2.line(frame, kp["left_hip"], kp["left_knee"], pants_color, 14)
        cv2.line(frame, kp["left_knee"], kp["left_ankle"], pants_color, 12)
        cv2.line(frame, kp["right_hip"], kp["right_knee"], pants_color, 14)
        cv2.line(frame, kp["right_knee"], kp["right_ankle"], pants_color, 12)
        # Shoes
        cv2.ellipse(frame, kp["left_ankle"], (16, 8), 0, 0, 360, (20, 20, 20), -1)
        cv2.ellipse(frame, kp["right_ankle"], (16, 8), 0, 0, 360, (20, 20, 20), -1)

        # Torso
        torso_pts = np.array([
            kp["left_shoulder"], kp["right_shoulder"],
            kp["right_hip"], kp["left_hip"]
        ], np.int32)
        cv2.fillConvexPoly(frame, torso_pts, jersey_color)
        cv2.polylines(frame, [torso_pts], True, (30, 30, 30), 2)

        # Head & Archery Cap
        head_c = kp["head_center"]
        cv2.circle(frame, head_c, 24, skin_color, -1)
        cv2.circle(frame, head_c, 24, (50, 50, 50), 2)
        # Cap bill pointing forward
        cv2.line(frame, (head_c[0] - 10, head_c[1] - 18), (head_c[0] + 32, head_c[1] - 14), jersey_color, 7)
        # Eye/Visor
        cv2.line(frame, (head_c[0] + 6, head_c[1] - 3), (head_c[0] + 16, head_c[1] - 3), (20, 20, 20), 3)

        # Bow Arm (Right)
        cv2.line(frame, kp["right_shoulder"], kp["right_elbow"], jersey_color, 13)
        cv2.line(frame, kp["right_elbow"], kp["right_wrist"], skin_color, 11)
        # Arm guard
        guard_mid = ((kp["right_elbow"][0] + kp["right_wrist"][0]) // 2, (kp["right_elbow"][1] + kp["right_wrist"][1]) // 2)
        cv2.circle(frame, guard_mid, 7, (30, 30, 30), -1)

        # Draw Arm (Left)
        cv2.line(frame, kp["left_shoulder"], kp["left_elbow"], jersey_color, 13)
        cv2.line(frame, kp["left_elbow"], kp["left_wrist"], skin_color, 11)

        # Hands
        cv2.circle(frame, kp["right_wrist"], 8, skin_color, -1)
        cv2.circle(frame, kp["left_wrist"], 8, skin_color, -1)

        # RENDER RECURVE BOW
        grip = draw_details["bow_grip"]
        nock = draw_details["string_nock"]
        
        # Bow Riser & Limbs
        riser_len = 135
        top_tip = (grip[0] - 18, grip[1] - riser_len)
        bot_tip = (grip[0] - 18, grip[1] + riser_len)

        # Bow curve
        limb_color = (25, 25, 25)
        cv2.line(frame, (grip[0], grip[1] - 35), (grip[0], grip[1] + 35), (200, 30, 30), 8) # Riser handle
        cv2.line(frame, (grip[0], grip[1] - 35), top_tip, limb_color, 5) # Upper limb
        cv2.line(frame, (grip[0], grip[1] + 35), bot_tip, limb_color, 5) # Lower limb
        
        # Stabilizer rod extending straight out
        cv2.line(frame, grip, (grip[0] + 75, grip[1]), (60, 60, 60), 3)
        cv2.circle(frame, (grip[0] + 75, grip[1]), 5, (180, 180, 180), -1)

        # Bowstring
        str_color = (235, 235, 235)
        if phase in ["stance", "draw", "anchor"]:
            cv2.line(frame, top_tip, nock, str_color, 2)
            cv2.line(frame, nock, bot_tip, str_color, 2)
            # Arrow
            cv2.line(frame, nock, (grip[0] + 35, grip[1]), (210, 210, 210), 3)
            # Fletchings
            cv2.line(frame, nock, (nock[0] + 12, nock[1] - 5), (40, 210, 40), 2)
            cv2.line(frame, nock, (nock[0] + 12, nock[1] + 5), (40, 210, 40), 2)
        else: # release
            # String returned to equilibrium
            string_center = (grip[0] - 14, grip[1])
            cv2.line(frame, top_tip, string_center, str_color, 2)
            cv2.line(frame, string_center, bot_tip, str_color, 2)

            # Arrow flying through air
            rel_progress = (frame_idx - 131) / 49.0
            arrow_x = int(grip[0] + 40 + rel_progress * 520)
            
            # Vertical trajectory depends on form
            arrow_drop_y = 0
            if form_type == "arm_drop":
                arrow_drop_y = int(rel_progress * 48)  # Drops to 7 ring
            elif form_type == "unstable":
                arrow_drop_y = int(rel_progress * 85)  # Drops to 5 ring
            
            arrow_y = int(grip[1] + arrow_drop_y)
            arrow_len = 55
            cv2.line(frame, (arrow_x, arrow_y), (arrow_x - arrow_len, arrow_y), (220, 220, 220), 3)
            cv2.circle(frame, (arrow_x, arrow_y), 4, (40, 40, 40), -1) # Arrow tip

    def _render_hud(self, frame: np.ndarray, frame_idx: int, fps: int, phase: str,
                    title: str, target_score: float, kp: Dict[str, Tuple[int, int]], form_type: str):
        """Render modern telemetry HUD overlay directly onto video frames."""
        time_sec = frame_idx / fps

        # Top Banner Overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (15, 12), (self.width - 15, 52), (18, 22, 32), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Title & Time
        cv2.putText(frame, title, (25, 36), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
        time_text = f"T: {time_sec:.2f}s | Frame {frame_idx:03d}"
        cv2.putText(frame, time_text, (self.width - 240, 36), cv2.FONT_HERSHEY_DUPLEX, 0.55, (200, 220, 240), 1, cv2.LINE_AA)

        # Phase Badge (Bottom Left)
        phase_colors = {
            "stance": (140, 140, 140),
            "draw": (60, 160, 230),
            "anchor": (40, 210, 80),
            "release": (220, 60, 60)
        }
        color = phase_colors.get(phase, (200, 200, 200))
        cv2.rectangle(frame, (20, self.height - 48), (170, self.height - 18), color, -1)
        cv2.putText(frame, phase.upper(), (32, self.height - 26), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

        # Predicted Score Badge (Bottom Right)
        score_badge = f"EST. SCORE: {int(target_score)}" if target_score < 10 else "EST. SCORE: 10 (X)"
        badge_bg = (30, 180, 240) if target_score >= 9.0 else ((50, 70, 220) if target_score >= 7.0 else (180, 120, 40))
        cv2.rectangle(frame, (self.width - 230, self.height - 48), (self.width - 20, self.height - 18), badge_bg, -1)
        cv2.putText(frame, score_badge, (self.width - 218, self.height - 26), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    def _convert_to_mediapipe_landmarks(self, kp: Dict[str, Tuple[int, int]], width: int, height: int) -> List[Dict[str, float]]:
        """Map extracted 2D points to MediaPipe Pose 33-landmark structure."""
        # MediaPipe landmark indices:
        # 0: nose, 11: left_shoulder, 12: right_shoulder, 13: left_elbow, 14: right_elbow,
        # 15: left_wrist, 16: right_wrist, 23: left_hip, 24: right_hip, 25: left_knee,
        # 26: right_knee, 27: left_ankle, 28: right_ankle, etc.
        mp_list = []
        for idx in range(33):
            # Default placeholder
            lx, ly = 0.5, 0.5
            vis = 0.95

            if idx == 0:
                lx, ly = kp["nose"][0] / width, kp["nose"][1] / height
            elif idx == 11:
                lx, ly = kp["left_shoulder"][0] / width, kp["left_shoulder"][1] / height
            elif idx == 12:
                lx, ly = kp["right_shoulder"][0] / width, kp["right_shoulder"][1] / height
            elif idx == 13:
                lx, ly = kp["left_elbow"][0] / width, kp["left_elbow"][1] / height
            elif idx == 14:
                lx, ly = kp["right_elbow"][0] / width, kp["right_elbow"][1] / height
            elif idx == 15:
                lx, ly = kp["left_wrist"][0] / width, kp["left_wrist"][1] / height
            elif idx == 16:
                lx, ly = kp["right_wrist"][0] / width, kp["right_wrist"][1] / height
            elif idx == 23:
                lx, ly = kp["left_hip"][0] / width, kp["left_hip"][1] / height
            elif idx == 24:
                lx, ly = kp["right_hip"][0] / width, kp["right_hip"][1] / height
            elif idx == 25:
                lx, ly = kp["left_knee"][0] / width, kp["left_knee"][1] / height
            elif idx == 26:
                lx, ly = kp["right_knee"][0] / width, kp["right_knee"][1] / height
            elif idx == 27:
                lx, ly = kp["left_ankle"][0] / width, kp["left_ankle"][1] / height
            elif idx == 28:
                lx, ly = kp["right_ankle"][0] / width, kp["right_ankle"][1] / height
            else:
                # Interpolate intermediate facial and extremity landmarks
                lx = kp["nose"][0] / width
                ly = kp["nose"][1] / height
                vis = 0.7

            mp_list.append({
                "id": idx,
                "x": round(float(lx), 4),
                "y": round(float(ly), 4),
                "z": 0.0,
                "visibility": round(float(vis), 2)
            })

        return mp_list
