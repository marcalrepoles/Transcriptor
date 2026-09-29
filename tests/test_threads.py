import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QThread, QTimer
from PySide6.QtWidgets import QApplication

from transcriptor.main_window import MainWindow


def test_worker_result_callback_runs_on_gui_thread():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    observed = {}
    loop = QEventLoop()

    def heavy_work(progress=None):
        observed["worker_thread"] = QThread.currentThread()
        return "ok"

    def completed(value):
        observed["value"] = value
        observed["callback_thread"] = QThread.currentThread()
        loop.quit()

    window._run(heavy_work, (), completed, "Testando...")
    QTimer.singleShot(5000, loop.quit)
    loop.exec()

    assert observed["value"] == "ok"
    assert observed["worker_thread"] is not app.thread()
    assert observed["callback_thread"] is app.thread()
    assert window._active_thread is None
    window.close()
