from PyQt6.QtWidgets import QVBoxLayout, QLabel, QWidget, QLineEdit, QHBoxLayout, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from services.auth_service import AuthService, User, AuthError

class LoginWindow(QWidget):
    authenticated = pyqtSignal(User)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumina Wellness - Login")
        self.setFixedSize(320, 260)
        self.setStyleSheet("background-color: #0F0F0F; color: #FFFFFF;")

        self.auth_service = AuthService()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Sign in to Lumina")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Use your work email to continue.")
        subtitle.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignLeft)

        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setStyleSheet(
            "background-color: #1A1A1A; border-radius: 8px; "
            "padding: 8px 10px; border: 1px solid #333;"
        )
        layout.addWidget(self.email_input)

        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(
            "background-color: #1A1A1A; border-radius: 8px; "
            "padding: 8px 10px; border: 1px solid #333;"
        )
        layout.addWidget(self.password_input)

        # Error label (inline validation)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF6B6B; font-size: 11px;")
        layout.addWidget(self.error_label)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        login_btn = QPushButton("Sign In")
        login_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #00FF88;
                color: #000;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0EEA7C;
            }
            QPushButton:pressed {
                background-color: #0AC266;
            }
            """
        )
        login_btn.clicked.connect(self.handle_login)
        btn_row.addWidget(login_btn)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    def handle_login(self):
        email = self.email_input.text()
        password = self.password_input.text()

        try:
            user = self.auth_service.login(email, password)
        except AuthError as e:
            self.error_label.setText(str(e))
            return
        except Exception:
            QMessageBox.critical(self, "Login Failed", "An unexpected error occurred.")
            return

        # Clear any previous error and notify the app
        self.error_label.setText("")
        self.authenticated.emit(user)