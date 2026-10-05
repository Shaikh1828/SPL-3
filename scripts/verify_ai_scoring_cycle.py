"""
End-to-end cycle verification script for AI Camera Scoring, Scorer Review/Override, and Round Progression.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def main():
    print("🎯 Starting E2E AI Scoring Cycle Verification...")

    # 1. Login
    auth_res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "admin123!"})
    assert auth_res.status_code == 200, f"Login failed: {auth_res.text}"
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ [1/5] Admin Login Successful")

    # 2. Get active tournament and session
    t_res = requests.get(f"{BASE_URL}/api/tournaments", headers=headers)
    assert t_res.status_code == 200, t_res.text
    t_data = t_res.json()
    tournaments = t_data if isinstance(t_data, list) else t_data.get("items", [])
    first_t = tournaments[0]
    print(f"✅ [2/5] Selected Tournament: {first_t['name']} (ID: {first_t['id']})")

    s_res = requests.get(f"{BASE_URL}/api/tournaments/{first_t['id']}/sessions", headers=headers)
    assert s_res.status_code == 200, s_res.text
    s_data = s_res.json()
    sessions = s_data if isinstance(s_data, list) else s_data.get("items", [])
    active_session = sessions[0]
    print(f"✅ [3/5] Selected Active Session: {active_session['name']} (ID: {active_session['id']})")

    # 3. Trigger AI Round Scoring
    ai_res = requests.post(
        f"{BASE_URL}/api/sessions/{active_session['id']}/ai-score-round",
        json={"round": 1},
        headers=headers,
    )
    assert ai_res.status_code == 200, f"AI Scoring failed: {ai_res.text}"
    ai_data = ai_res.json()
    print(f"✅ [4/5] AI Multi-Lane Detection Executed: {len(ai_data['lanes'])} lanes scored for End {ai_data['round']}")
    for lane in ai_data["lanes"]:
        arrows_summary = " ".join([str(a["points"]) for a in lane["detected_arrows"]])
        has_ann_img = "Preview Image Generated" if lane.get("annotated_image") else "No Image"
        print(f"   - Lane {lane['lane_number']} ({lane['archer_name']}): [{arrows_summary}] -> Total: {lane['end_total']} pts (Conf: {lane['avg_confidence']*100:.1f}%) [{has_ann_img}]")

    # 4. Scorer Override on Lane 1 Arrow #3
    lanes = ai_data["lanes"]
    lanes[0]["detected_arrows"][2]["points"] = 10
    lanes[0]["detected_arrows"][2]["zone"] = "X"
    lanes[0]["detected_arrows"][2]["is_x"] = True
    lanes[0]["detected_arrows"][2]["is_override"] = True
    lanes[0]["detected_arrows"][2]["override_reason"] = "Line judge ruling"
    print("   -> Scorer applied override: Lane 1, Arrow #3 changed to 10 (X)")

    # 5. Confirm & Commit Round Batch
    confirm_res = requests.post(
        f"{BASE_URL}/api/sessions/{active_session['id']}/scores/batch-confirm-round",
        json={
            "round": 1,
            "lane_submissions": [
                {
                    "session_archer_id": l["session_archer_id"],
                    "lane_number": l["lane_number"],
                    "arrows": l["detected_arrows"],
                }
                for l in lanes
            ]
        },
        headers=headers,
    )
    assert confirm_res.status_code == 200, f"Batch confirm failed: {confirm_res.text}"
    confirm_data = confirm_res.json()
    print(f"✅ [5/5] Round 1 Confirmed & Committed: {confirm_data['scores_recorded_count']} arrows saved to database. Advanced to End {confirm_data['next_round']}.")

    # 6. Verify Database Score Records
    scores_res = requests.get(f"{BASE_URL}/api/sessions/{active_session['id']}/scores?round=1", headers=headers)
    assert scores_res.status_code == 200
    scores_list = scores_res.json()
    print(f"✅ Verified: {len(scores_list)} score records retrieved from database for Round 1.")
    print("🏆 Full AI Scoring and Round Progression Cycle Verified Successfully!")

if __name__ == "__main__":
    main()
