from __future__ import annotations

import traceback

from PySide6.QtCore import QObject, Signal, Slot


class FunctionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str, str)
    progress = Signal(int, str)

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        try:
            result = self.function(*self.args, progress=self.progress.emit, **self.kwargs)
            self.finished.emit(result)
        except Exception as error:
            self.failed.emit(str(error), traceback.format_exc())

