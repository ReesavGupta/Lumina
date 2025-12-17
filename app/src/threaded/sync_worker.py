from PyQt6.QtCore import QThread
import time
import requests
from typing import Optional
from services.auth_service import User, API_BASE_URL
from services import local_db

class SyncWorker(QThread):
    def __init__(self, user: User, interval_seconds: int = 60):
        super().__init__()
        self.user = user
        self.interval = interval_seconds
        self.running = True

    def run(self):
        while self.running:
            try:
                self._sync_sessions()
                self._sync_blinks()
            except Exception:
                # yaha pe we are failing silently so it can try again next cycle even if the user is offline
                pass
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def _sync_sessions(self):
        """Sync unsynced sessions to cloud."""
        if not self.user.token:
            return

        sessions = local_db.get_unsynced_sessions(self.user.email)
        if not sessions:
            return

        payload = []
        for (local_id, user_email, name, start_time, end_time) in sessions:
            payload.append({
                "id": local_id,  # We'll use this to map back
                "name": name,
                "start_time": start_time,
                "end_time": end_time,
            })

        resp = requests.post(
            f"{API_BASE_URL}/sync/sessions",
            json=payload,
            headers={"Authorization": f"Bearer {self.user.token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Map local IDs to cloud IDs
            cloud_ids = data.get("ids", [])
            for i, (local_id, _, _, _, _) in enumerate(sessions):
                if i < len(cloud_ids):
                    cloud_id = cloud_ids[i]
                else:
                    cloud_id = None
                local_db.mark_session_synced(local_id, cloud_id)

    def _sync_blinks(self):
        """Sync unsynced blinks to cloud."""
        if not self.user.token:
            return

        rows = local_db.get_unsynced_blinks(self.user.email)
        if not rows:
            return

        payload = [
            {
                "timestamp": ts,
                "count": count,
                "session_id": session_id
            }
            for (_id, ts, count, session_id) in rows
        ]

        resp = requests.post(
            f"{API_BASE_URL}/sync/blinks",
            json=payload,
            headers={"Authorization": f"Bearer {self.user.token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            ids = [row[0] for row in rows]
            local_db.mark_blinks_synced(ids)