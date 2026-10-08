import requests

for idx in [0, 1]:
    path = f'scratch/cam_test/cam_{idx}.jpg'
    with open(path, 'rb') as f:
        r = requests.post(
            'http://localhost:3000/api/pose/analyze-image',
            files={'file': (f'cam_{idx}.jpg', f, 'image/jpeg')},
            data={'lane_number': idx + 1, 'archer_name': f'Archer on Cam {idx}', 'camera_source': f'Camera {idx}'}
        )
    print(f'Cam {idx} status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        landmarks_count = len(data.get('landmarks', []))
        score_disp = data.get('prediction', {}).get('score_display')
        accuracy = data.get('posture_accuracy', {}).get('overall_accuracy_pct')
        handedness = data.get('handedness_label')
        bio = data.get('biomechanics', {})
        print(f'Cam {idx} -> Landmarks: {landmarks_count}, Score: {score_disp}, Accuracy: {accuracy}%, Handedness: {handedness}')
        print(f'Cam {idx} Biomechanics -> Bow arm angle: {bio.get("bow_arm_angle")}°, Draw elbow: {bio.get("draw_elbow_angle")}°')
    else:
        print(f'Cam {idx} error:', r.text)
