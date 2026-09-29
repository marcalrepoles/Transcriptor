import sys
from PySide6.QtWidgets import QApplication
from .config import configure_logging
from .main_window import MainWindow


def main() -> int:
    configure_logging()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Transcriptor")
    window = MainWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
