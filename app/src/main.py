import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from services.auth_service import AuthService, User
from windows.login_window import LoginWidget
from windows.dashboard_widget import DashboardWidget

class AppWindow(QMainWindow):
    """
    this is a single top-level window that behaves like an "spa":
    - shows LoginWidget if no valid session.
    - switches centralWidget to DashboardWidget after login.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lumina Wellness")
        self.setFixedSize(350, 500)
        self.setStyleSheet("background-color: #0F0F0F; color: #FFFFFF;")

        self.auth_service = AuthService()

        # yaha the initial view is decided based on stored session
        user = self.auth_service.load_session()
        if user and user.token:
            self.show_dashboard(user)
        else:
            self.show_login()

    def show_login(self):
        login_widget = LoginWidget(self.auth_service)
        login_widget.authenticated.connect(self.show_dashboard)
        self.setCentralWidget(login_widget)

    def show_dashboard(self, user: User):
        dashboard = DashboardWidget(user=user)
        self.setCentralWidget(dashboard)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())