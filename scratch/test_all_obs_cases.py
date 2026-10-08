import requests
import cv2
import json
import base64
import time

BASE = 'http://localhost:3000'

def run_all_cases():
    print('===============================================================')
    print('          RUNNING ALL TEST CASES FOR OBS VIRTUAL CAMERA         ')
    print('===============================================================')

    # Login to get admin token
    auth_resp = requests.post(f'{BASE}/api/auth/login', json={'username': 'admin', 'password': 'admin123!'})
    assert auth_resp.status_code == 200, f'Login failed: {auth_resp.text}'
    token = auth_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print('[+] Logged in as admin successfully')

    # Get active session from tournaments
    tourn_resp = requests.get(f'{BASE}/api/tournaments', headers=headers)
    assert tourn_resp.status_code == 200, f'Tournaments failed: {tourn_resp.text}'
    tournaments = tourn_resp.json().get('items', [])
    assert len(tournaments) > 0, 'No tournaments found'
    tourn_id = tournaments[0]['id']
    
    sess_resp = requests.get(f'{BASE}/api/tournaments/{tourn_id}/sessions', headers=headers)
    assert sess_resp.status_code == 200, f'Sessions failed: {sess_resp.text}'
    sessions = sess_resp.json().get('items', [])
    assert len(sessions) > 0, 'No sessions found'
    session_id = sessions[0]['id']
    print(f'[+] Using Tournament {tourn_id}, Session ID: {session_id}')

    # -------------------------------------------------------------
    # CASE 1: Direct capture from Host OBS Virtual Camera via OpenCV
    # -------------------------------------------------------------
    print('\n--- CASE 1: Direct capture from Host OBS Virtual Camera (Index 1) ---')
    cap = cv2.VideoCapture(1)
    assert cap.isOpened(), 'Could not open Camera index 1 (OBS Virtual Camera)'
    ret, obs_frame = cap.read()
    cap.release()
    assert ret and obs_frame is not None, 'Could not read frame from OBS Virtual Camera'
    print(f'Captured frame from OBS Virtual Camera: shape={obs_frame.shape}')

    # Encode to JPEG
    _, encoded = cv2.imencode('.jpg', obs_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    obs_bytes = encoded.tobytes()

    # Send to pose analysis endpoint
    res = requests.post(
        f'{BASE}/api/pose/analyze-image',
        files={'file': ('obs_frame.jpg', obs_bytes, 'image/jpeg')},
        data={'lane_number': 1, 'archer_name': 'OBS Archer', 'camera_source': 'OBS Virtual Camera'}
    )
    assert res.status_code == 200, f'Pose analysis on OBS camera failed: {res.text}'
    data = res.json()
    assert data.get('success') is True
    landmarks_count = len(data.get('landmarks', []))
    score = data.get('prediction', {}).get('score_display')
    accuracy = data.get('posture_accuracy', {}).get('overall_accuracy_pct')
    handedness = data.get('handedness_label')
    bio = data.get('biomechanics', {})
    print(f'CASE 1 RESULT: PASSED!')
    print(f'  - Landmarks Detected: {landmarks_count}/33')
    print(f'  - Predicted Score: {score}')
    print(f'  - Posture Accuracy: {accuracy}%')
    print(f'  - Handedness: {handedness}')
    print(f'  - Bow Arm Angle: {bio.get("bow_arm_angle")}° | Draw Elbow Angle: {bio.get("draw_elbow_angle")}°')
    assert landmarks_count == 33, 'Expected 33 landmarks detected from OBS virtual camera'

    # -------------------------------------------------------------
    # CASE 2: Base64 Snapshot Analysis via /api/pose/analyze-snapshot
    # -------------------------------------------------------------
    print('\n--- CASE 2: Analyze Base64 Camera Snapshot (/api/pose/analyze-snapshot) ---')
    b64_str = f'data:image/jpeg;base64,{base64.b64encode(obs_bytes).decode("utf-8")}'
    res2 = requests.post(
        f'{BASE}/api/pose/analyze-snapshot',
        json={
            'image_base64': b64_str,
            'filename': 'obs_live_snapshot.jpg',
            'lane_number': 1,
            'archer_name': 'Robin Hood (OBS)',
            'camera_source': 'OBS Virtual Camera'
        }
    )
    assert res2.status_code == 200, f'Snapshot analysis failed: {res2.text}'
    data2 = res2.json()
    assert data2.get('success') is True
    assert len(data2.get('landmarks', [])) == 33
    print(f'CASE 2 RESULT: PASSED! (Score: {data2.get("prediction", {}).get("score_display")}, Accuracy: {data2.get("posture_accuracy", {}).get("overall_accuracy_pct")}%)')

    # -------------------------------------------------------------
    # CASE 3: Camera Section: Add OBS Virtual Camera & Assign to Lane
    # -------------------------------------------------------------
    print('\n--- CASE 3: Add OBS Virtual Camera in Camera Section (/api/cameras) ---')
    # 3a. Test stream connection
    test_stream_res = requests.post(
        f'{BASE}/api/cameras/test-stream',
        json={'url': 'browser://obs', 'camera_type': 'USB'},
        headers=headers
    )
    assert test_stream_res.status_code == 200, f'Test stream failed: {test_stream_res.text}'
    test_stream_data = test_stream_res.json()
    assert test_stream_data.get('connected') is True, f'Expected connected True: {test_stream_data}'
    print(f'  - Test Stream probe: {test_stream_data.get("message")}')

    # 3b. Register new OBS Virtual Camera
    cam_name = f'OBS Virtual Camera Lane 1 ({int(time.time())})'
    create_cam_res = requests.post(
        f'{BASE}/api/cameras',
        json={
            'name': cam_name,
            'camera_type': 'USB',
            'url': 'browser://obs'
        },
        headers=headers
    )
    if create_cam_res.status_code in [200, 201]:
        new_cam = create_cam_res.json()
        cam_id = new_cam['id']
    else:
        all_cams = requests.get(f'{BASE}/api/cameras', headers=headers).json()
        target = [c for c in all_cams if 'obs' in c['name'].lower()][0]
        cam_id = target['id']
    print(f'  - Registered / Active Camera ID: {cam_id}')

    # 3c. Assign to Lane 1 in session
    assign_res = requests.post(
        f'{BASE}/api/sessions/{session_id}/cameras/assign',
        json={'camera_id': cam_id, 'lane': 1},
        headers=headers
    )
    assert assign_res.status_code in [200, 201], f'Assign camera failed: {assign_res.text}'
    print(f'  - Assigned Camera {cam_id} to Session {session_id} Lane 1')
    print('CASE 3 RESULT: PASSED!')

    # -------------------------------------------------------------
    # CASE 4: Push Frame from OBS Virtual Camera for Lane 1
    # -------------------------------------------------------------
    print('\n--- CASE 4: Push Frame to Backend for Lane 1 ---')
    push_res = requests.post(
        f'{BASE}/api/sessions/{session_id}/lanes/1/push-frame',
        json={'image_base64': base64.b64encode(obs_bytes).decode('utf-8')},
        headers=headers
    )
    assert push_res.status_code == 200, f'Push lane frame failed: {push_res.text}'
    print(f'  - Push frame response: {push_res.json()}')
    print('CASE 4 RESULT: PASSED!')

    # -------------------------------------------------------------
    # CASE 5: Lane Camera Posture Analysis (/api/pose/lane/1/analyze-camera)
    # -------------------------------------------------------------
    print('\n--- CASE 5: Direct Posture Analysis from Lane 1 Assigned Camera ---')
    lane_cam_res = requests.post(
        f'{BASE}/api/pose/lane/1/analyze-camera',
        params={'session_id': session_id}
    )
    assert lane_cam_res.status_code == 200, f'Lane camera posture analysis failed: {lane_cam_res.text}'
    lane_cam_data = lane_cam_res.json()
    assert lane_cam_data.get('success') is True
    assert len(lane_cam_data.get('landmarks', [])) == 33
    score5 = lane_cam_data.get('prediction', {}).get('score_display')
    acc5 = lane_cam_data.get('posture_accuracy', {}).get('overall_accuracy_pct')
    print(f'CASE 5 RESULT: PASSED! (Score: {score5}, Accuracy: {acc5}%, Landmarks: {len(lane_cam_data.get("landmarks", []))})')

    print('\n===============================================================')
    print('       ALL 5 OBS VIRTUAL CAMERA TEST CASES PASSED 100%!        ')
    print('===============================================================')

if __name__ == '__main__':
    run_all_cases()
