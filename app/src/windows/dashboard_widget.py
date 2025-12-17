import psutil
from datetime import datetime
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QWidget, QFrame
from PyQt6.QtCore import QTimer, Qt
from threaded.tracker import EyeTrackerThread
from threaded.sync_worker import SyncWorker
from services.auth_service import User
import services.local_db as local_db 

class DashboardWidget(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user

        # ahh this will be an in-memory buffer for batching blink writes
        self._pending_samples: list[tuple[str, int]] = []  # (timestamp, count)
        self._batch_size = 10  # flush when buffer reaches this size

        self.setStyleSheet("background-color: #0F0F0F; color: #FFFFFF;")
        self._init_ui()

        # initialize and start silent tracker
        self.tracker = EyeTrackerThread()
        self.tracker.blink_detected.connect(self.update_blinks)
        self.tracker.start()

        # start background sync worker
        self.sync_worker = SyncWorker(user=self.user)
        self.sync_worker.start()

        # cpu and memory [erformance Timer
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

        # flush buffer timer (every 5 seconds, even if batch isn't full)
        self.flush_timer = QTimer(self)
        self.flush_timer.timeout.connect(self._flush_local_blinks)
        self.flush_timer.start(5000)

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 40, 30, 40)
        main_layout.setSpacing(20)

        # status badge
        self.status_label = QLabel("●  MONITORING ACTIVE")
        self.status_label.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # logged-in user label
        user_label = QLabel(f"Signed in as {self.user.email}")
        user_label.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(user_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # blink counter section
        blink_box = QFrame()
        blink_box.setStyleSheet("background-color: #1A1A1A; border-radius: 15px;")
        blink_layout = QVBoxLayout(blink_box)

        title = QLabel("TOTAL BLINKS")
        title.setStyleSheet("color: #888; font-size: 12px; letter-spacing: 1px;")
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("font-size: 80px; font-weight: 800; border: none;")

        blink_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        blink_layout.addWidget(self.count_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(blink_box)

        # system metrics section
        self.cpu_label = QLabel("CPU USAGE: 0%")
        self.mem_label = QLabel("MEMORY: 0 MB")
        for lbl in [self.cpu_label, self.mem_label]:
            lbl.setStyleSheet("color: #AAA; font-size: 13px; font-family: monospace;")
            main_layout.addWidget(lbl)

        self.setLayout(main_layout)

    def update_blinks(self, count: int):
        self.count_label.setText(str(count))
        # Add to in-memory buffer instead of writing immediately
        ts = datetime.now().isoformat()
        self._pending_samples.append((ts, count))
        
        # Flush if buffer reaches batch size
        if len(self._pending_samples) >= self._batch_size:
            self._flush_local_blinks()

    def _flush_local_blinks(self):
        """here we are flushing pending blink samples to local DB in a single batch."""
        if not self._pending_samples:
            return
        
        # Convert to format expected by save_blinks_batch: (timestamp, count)
        samples = [(ts if ts else None, cnt) for ts, cnt in self._pending_samples]
        local_db.save_blinks_batch(self.user.email, samples)
        self._pending_samples.clear()

    def update_stats(self):
        cpu = psutil.cpu_percent()
        mem = psutil.Process().memory_info().rss / (1024 * 1024)
        self.cpu_label.setText(f"CPU USAGE: {cpu:>5}%")
        self.mem_label.setText(f"MEMORY: {int(mem):>6} MB")

    def closeEvent(self, event):
        """flush any remaining samples before closing."""
        self._flush_local_blinks()
        # Stop timers and threads
        self.flush_timer.stop()
        self.stats_timer.stop()
        if hasattr(self, 'tracker'):
            self.tracker.stop()
        if hasattr(self, 'sync_worker'):
            self.sync_worker.stop()
        event.accept()