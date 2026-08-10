# main.py
import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from views.main_window import IvyNodeWindow

def set_app_id():
    try:
        myappid = 'ivynode.workspace.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

def main():
    set_app_id()
    app = QApplication(sys.argv)
    window = IvyNodeWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()