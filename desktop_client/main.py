import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QLabel
from api_client import CloudAPI
from gui import MainWindow


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.api = CloudAPI()
        self.setWindowTitle("Cloud Auth")
        self.resize(300, 200)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Login or Register</h2>"))

        self.u = QLineEdit(placeholderText="Username")
        self.p = QLineEdit(placeholderText="Password", echoMode=QLineEdit.EchoMode.Password)

        btn_login = QPushButton("Login")
        btn_login.clicked.connect(self.do_login)

        btn_reg = QPushButton("Register")
        btn_reg.clicked.connect(self.do_reg)

        layout.addWidget(self.u)
        layout.addWidget(self.p)
        layout.addWidget(btn_login)
        layout.addWidget(btn_reg)
        self.setLayout(layout)

    def do_login(self):
        if self.api.login(self.u.text(), self.p.text()):
            # Передаємо self.show як callback для logout
            self.main = MainWindow(self.api, self.u.text(), self.show)
            self.main.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")

    def do_reg(self):
        self.api.register(self.u.text(), self.p.text())
        QMessageBox.information(self, "Info", "Registered! Now login.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Стилізуємо десктоп під темну тему, як і веб
    app.setStyle("Fusion")
    w = LoginWindow()
    w.show()
    sys.exit(app.exec())