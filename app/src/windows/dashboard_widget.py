import psutil
from datetime import datetime
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QWidget, QFrame, QPushButton, QHBoxLayout
from PyQt6.QtCore import QTimer, Qt
from threaded.tracker import EyeTrackerThread
from threaded.sync_worker import SyncWorker
from services.auth_service import User
import services.local_db as local_db 

class DashboardWidget(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self.current_session_id = None

        # this is the in-memory buffer for batching blink writes
        self._pending_samples: list[tuple[str, int]] = []  # (timestamp, count)
        self._batch_size = 10  # flush when buffer reaches this size

        self.setStyleSheet("background-color: #0F0F0F; color: #FFFFFF;")
        self._init_ui()

        # initialize tracker (but don't start it yet)
        self.tracker = EyeTrackerThread()
        self.tracker.blink_detected.connect(self.update_blinks)

        # start background sync worker
        self.sync_worker = SyncWorker(user=self.user)
        self.sync_worker.start()

        # cpu and memory performance timer
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

        # this is the flush buffer timer (every 5 seconds, even if batch isn't full)
        self.flush_timer = QTimer(self)
        self.flush_timer.timeout.connect(self._flush_local_blinks)
        self.flush_timer.start(5000)

        # check if there's an active session on load
        self._check_active_session()

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 40, 30, 40)
        main_layout.setSpacing(20)

        # status badge
        self.status_label = QLabel("●  SESSION INACTIVE")
        self.status_label.setStyleSheet("color: #FF4444; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # logged-in user label
        user_label = QLabel(f"Signed in as {self.user.email}")
        user_label.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(user_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # session control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("START SESSION")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #00FF88;
                color: #000;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #00DD77;
            }
        """)
        self.start_button.clicked.connect(self.start_session)

        self.stop_button = QPushButton("END SESSION")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #FF4444;
                color: #FFF;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #DD3333;
            }
        """)
        self.stop_button.clicked.connect(self.stop_session)
        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)

        # Blink counter section
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

        # System metrics section
        self.cpu_label = QLabel("CPU USAGE: 0%")
        self.mem_label = QLabel("MEMORY: 0 MB")
        for lbl in [self.cpu_label, self.mem_label]:
            lbl.setStyleSheet("color: #AAA; font-size: 13px; font-family: monospace;")
            main_layout.addWidget(lbl)

        self.setLayout(main_layout)

    def _check_active_session(self):
        """Check if there's an active session and restore state."""
        active_id = local_db.get_active_session(self.user.email)
        if active_id:
            self.current_session_id = active_id
            self._start_tracking()

    def start_session(self):
        """Start a new tracking session."""
        if self.current_session_id:
            return  # Already has active session
        
        self.current_session_id = local_db.create_session(self.user.email)
        self._start_tracking()
        self.status_label.setText("●  SESSION ACTIVE")
        self.status_label.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 11px;")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_session(self):
        """End the current tracking session."""
        if not self.current_session_id:
            return
        
        # Flush any pending blinks first
        self._flush_local_blinks()
        
        # Stop tracking
        self._stop_tracking()
        
        # End session
        local_db.end_session(self.current_session_id)
        self.current_session_id = None
        
        # Update UI
        self.status_label.setText("●  SESSION INACTIVE")
        self.status_label.setStyleSheet("color: #FF4444; font-weight: bold; font-size: 11px;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.count_label.setText("0")

    def _start_tracking(self):
        """Start the eye tracker."""
        if not self.tracker.isRunning():
            self.tracker.start()

    def _stop_tracking(self):
        """Stop the eye tracker."""
        if self.tracker.isRunning():
            self.tracker.stop()

    def update_blinks(self, count: int):
        """Update blink count. Only works if session is active."""
        if not self.current_session_id:
            return  # don't track if no active session
        
        self.count_label.setText(str(count))
        # add to in-memory buffer instead of writing immediately
        ts = datetime.now().isoformat()
        self._pending_samples.append((ts, count))
        
        # flush if buffer reaches batch size
        if len(self._pending_samples) >= self._batch_size:
            self._flush_local_blinks()

    def _flush_local_blinks(self):
        """Flush pending blink samples to local DB in a single batch."""
        if not self._pending_samples or not self.current_session_id:
            return
        
        # convert to format expected by save_blinks_batch: (timestamp, count)
        samples = []
        for ts, cnt in self._pending_samples:
            samples.append((ts if ts else None, cnt))
            
        local_db.save_blinks_batch(self.user.email, samples, self.current_session_id)
        self._pending_samples.clear()

    def update_stats(self):
        cpu = psutil.cpu_percent()
        mem = psutil.Process().memory_info().rss / (1024 * 1024)
        self.cpu_label.setText(f"CPU USAGE: {cpu:>5}%")
        self.mem_label.setText(f"MEMORY: {int(mem):>6} MB")

    def closeEvent(self, a0):
        """Flush any remaining samples before closing."""
        if self.current_session_id:
            self._flush_local_blinks()
            # we can optionally end session on close, or leave it active
            local_db.end_session(self.current_session_id)
        
        # stop timers and threads
        self.flush_timer.stop()
        self.stats_timer.stop()
        if hasattr(self, 'tracker'):
            self.tracker.stop()
        if hasattr(self, 'sync_worker'):
            self.sync_worker.stop()
        if a0:
            a0.accept()