import requests

BASE = 'http://localhost:3000'

# Login as admin
login_res = requests.post(
    f'{BASE}/api/auth/login',
    json={'username': 'admin', 'password': 'admin123!'}
)
print('Login status:', login_res.status_code)
token = login_res.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

# List cameras
cams_res = requests.get(f'{BASE}/api/cameras', headers=headers)
print('Cameras count:', len(cams_res.json()))

# Test stream with browser://
res_browser = requests.post(
    f'{BASE}/api/cameras/test-stream',
    json={'url': 'browser://obs_virtual_cam', 'camera_type': 'USB'},
    headers=headers
)
print('Test browser:// stream:', res_browser.status_code, res_browser.json())

# Test stream with camera://1
res_cam1 = requests.post(
    f'{BASE}/api/cameras/test-stream',
    json={'url': 'camera://1', 'camera_type': 'USB'},
    headers=headers
)
print('Test camera://1 stream:', res_cam1.status_code, res_cam1.json())
