import sys

from PySide6.QtWidgets import QApplication

from app.manager import WidgetManager


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DeskWidget")
    app.setQuitOnLastWindowClosed(False)

    manager = WidgetManager(app)
    manager.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
