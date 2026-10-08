import requests

BASE = 'http://localhost:3000'

def run_tests():
    # 1. Health
    r = requests.get(f'{BASE}/api/health')
    assert r.status_code == 200, f'Health failed: {r.status_code}'
    print('1. Health check: PASSED (200)')

    # 2. Posture samples list
    r = requests.get(f'{BASE}/api/pose/posture-samples')
    assert r.status_code == 200, f'Samples failed: {r.status_code}'
    samples = r.json().get('samples', [])
    assert len(samples) > 0, 'No samples found'
    print(f'2. Posture samples list: PASSED ({len(samples)} samples found)')

    # 3. Posture sample analyze
    sample_file = samples[0]['filename']
    r = requests.post(f'{BASE}/api/pose/posture-samples/{sample_file}/analyze')
    assert r.status_code == 200, f'Sample analyze failed: {r.status_code}'
    data = r.json()
    assert data.get('success') is True
    score_disp = data.get("prediction", {}).get("score_display")
    acc = data.get("posture_accuracy", {}).get("overall_accuracy_pct")
    print(f'3. Posture sample analyze ({sample_file}): PASSED (Score: {score_disp}, Accuracy: {acc}%)')

    # 4. Analyze uploaded image (multi-part form)
    with open('Posture/images (9).jpg', 'rb') as f:
        r = requests.post(
            f'{BASE}/api/pose/analyze-image',
            files={'file': ('test.jpg', f, 'image/jpeg')},
            data={'lane_number': 3, 'archer_name': 'Robin Hood', 'camera_source': 'lane_camera_3'}
        )
    assert r.status_code == 200, f'Analyze image failed: {r.status_code}'
    upload_res = r.json()
    assert upload_res.get('success') is True
    print(f'4. Analyze uploaded image: PASSED (Score: {upload_res.get("prediction", {}).get("score_display")})')

    # 5. Analyze live frame
    live_payload = {
        'lane_number': 3,
        'archer_id': 101,
        'archer_name': 'Robin Hood',
        'camera_source': 'Lane 3 Cam',
        'bow_arm_angle': 179.2,
        'draw_elbow_angle': 138.5,
        'anchor_jitter': 0.5,
        'bow_arm_deflection_deg': 0.3,
        'anchor_duration_sec': 2.1,
        'phase': 'anchor'
    }
    r = requests.post(f'{BASE}/api/pose/analyze-live-frame', json=live_payload)
    assert r.status_code == 200, f'Live frame failed: {r.status_code}'
    live_res = r.json()
    assert live_res.get('success') is True
    print(f'5. Analyze live frame: PASSED (Score: {live_res.get("score_display")}, Accuracy: {live_res.get("posture_accuracy", {}).get("overall_accuracy_pct")}%)')

    # 6. Record archer posture
    rec_payload = {
        'archer_id': 101,
        'archer_name': 'Robin Hood',
        'lane_number': 3,
        'camera_source': 'Lane 3 Cam',
        'overall_accuracy_pct': 94.5,
        'accuracy_tier': 'GOLD',
        'predicted_score': 10,
        'bow_arm_angle': 179.2,
        'draw_elbow_angle': 138.5,
        'notes': 'Olympic champion form'
    }
    r = requests.post(f'{BASE}/api/pose/record-archer-posture', json=rec_payload)
    assert r.status_code == 200, f'Record failed: {r.status_code}'
    print('6. Record archer posture: PASSED')

    # 7. Get history
    r = requests.get(f'{BASE}/api/pose/archer/101/history')
    assert r.status_code == 200, f'History failed: {r.status_code}'
    hist = r.json()
    assert hist.get('total_records') >= 1
    print(f'7. Archer posture history: PASSED ({hist.get("total_records")} records)')

    # 8. Benchmark video list
    r = requests.get(f'{BASE}/api/pose/sample-videos')
    assert r.status_code == 200, f'Sample videos failed: {r.status_code}'
    print('8. Benchmark sample videos list: PASSED')

    print('\nALL 8 ENDPOINTS VERIFIED AND PASSING 100% THROUGH NGINX PORT 3000!')

if __name__ == '__main__':
    run_tests()
