import psutil
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QWidget, QFrame
from PyQt6.QtCore import QTimer, Qt
from threaded.tracker import EyeTrackerThread
from services.auth_service import User


class DashboardWidget(QWidget):
    def __init__(self, user: User):
        super().__init__()
        self.user = user

        self.setStyleSheet("background-color: #0F0F0F; color: #FFFFFF;")
        self._init_ui()

        # Initialize and start silent tracker
        self.tracker = EyeTrackerThread()
        self.tracker.blink_detected.connect(self.update_blinks)
        self.tracker.start()

        # Performance Timer
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 40, 30, 40)
        main_layout.setSpacing(20)

        # Status Badge
        self.status_label = QLabel("●  MONITORING ACTIVE")
        self.status_label.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Logged-in user label
        user_label = QLabel(f"Signed in as {self.user.email}")
        user_label.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(user_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Blink Counter Section
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

        # System Metrics Section
        self.cpu_label = QLabel("CPU USAGE: 0%")
        self.mem_label = QLabel("MEMORY: 0 MB")
        for lbl in [self.cpu_label, self.mem_label]:
            lbl.setStyleSheet("color: #AAA; font-size: 13px; font-family: monospace;")
            main_layout.addWidget(lbl)

        self.setLayout(main_layout)

    def update_blinks(self, count: int):
        self.count_label.setText(str(count))

    def update_stats(self):
        cpu = psutil.cpu_percent()
        mem = psutil.Process().memory_info().rss / (1024 * 1024)
        self.cpu_label.setText(f"CPU USAGE: {cpu:>5}%")
        self.mem_label.setText(f"MEMORY: {int(mem):>6} MB")