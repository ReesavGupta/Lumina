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
                self._sync_once()
            except Exception:
                # if fails then we would want this to fail silently lol; so it can try again next cycle
                pass
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def _sync_once(self):
        if not self.user.token:
            return

        rows = local_db.get_unsynced_blinks(self.user.email)
        if not rows:
            return

        payload = [
            {"timestamp": ts, "count": count}
            for (_id, ts, count) in rows
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