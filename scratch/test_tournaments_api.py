import urllib.request
import json

url = "http://127.0.0.1:8000/api/tournaments"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print(f"Total tournaments: {data['total']}")
    for t in data["items"]:
        print(f"[{t['status'].upper():9}] {t['name']}")
        print(f"   Sessions: {t['total_sessions']} (Active: {t['active_sessions']}, Completed: {t['completed_sessions']})")
        print(f"   Archers: {t['total_archers']} | Winner: {t.get('winner_name')} ({t.get('winner_score')} pts)")
        print(f"   Dates: {t['start_date']} to {t['end_date']}")
        print()

print("\n--- Testing Filter: ?status=completed ---")
req_comp = urllib.request.Request(url + "?status=completed")
with urllib.request.urlopen(req_comp) as resp:
    data_comp = json.loads(resp.read().decode("utf-8"))
    print(f"Completed tournaments: {data_comp['total']}")
    for t in data_comp["items"]:
        print(f" - {t['name']} (Winner: {t.get('winner_name')})")

print("\n--- Testing Filter: ?status=ongoing ---")
req_ong = urllib.request.Request(url + "?status=ongoing")
with urllib.request.urlopen(req_ong) as resp:
    data_ong = json.loads(resp.read().decode("utf-8"))
    print(f"Ongoing tournaments: {data_ong['total']}")
    for t in data_ong["items"]:
        print(f" - {t['name']} (Active sessions: {t['active_sessions']})")

print("\n--- Testing Filter: ?status=upcoming ---")
req_up = urllib.request.Request(url + "?status=upcoming")
with urllib.request.urlopen(req_up) as resp:
    data_up = json.loads(resp.read().decode("utf-8"))
    print(f"Upcoming tournaments: {data_up['total']}")
    for t in data_up["items"]:
        print(f" - {t['name']}")
