"""Manual end-to-end validation using the real GUI worker pipeline."""
from __future__ import annotations

import sys
import json
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication

from transcriptor.audio import audio_duration
from transcriptor.domain import Project
from transcriptor.main_window import MainWindow


def main() -> int:
    audio = Path(sys.argv[1])
    if not audio.is_file():
        raise FileNotFoundError(audio)
    app = QApplication([])
    window = MainWindow()
    window.project = Project(audio_path=str(audio), duration=audio_duration(str(audio)), dirty=False)
    window.media_player.setSource(QUrl.fromLocalFile(str(audio)))
    window.model_combo.setCurrentText("Small")
    window.speaker_combo.setCurrentText("Automático")
    window._update_ui()
    window.show()
    timed_out = {"value": False}

    def inspect() -> None:
        if window.status_label.text() == "Concluído.":
            print(f"PIPELINE_OK model={window.project.model} language={window.project.language}", flush=True)
            print(f"WINDOW_VISIBLE_AFTER_COMPLETION={window.isVisible()}", flush=True)
            print(f"UTTERANCES={len(window.project.utterances)}", flush=True)
            print("TRANSCRIPT_JSON=" + json.dumps([
                {"start": u.start, "end": u.end, "speaker": u.speaker_id, "text": u.text}
                for u in window.project.utterances
            ], ensure_ascii=True), flush=True)
            for utterance in window.project.utterances:
                print(f"{utterance.start:.3f}-{utterance.end:.3f} {utterance.speaker_id}: {utterance.text}", flush=True)
            window.project.dirty = False
            window.close()
            app.quit()
        elif timed_out["value"]:
            print(f"PIPELINE_TIMEOUT status={window.status_label.text()}", flush=True)
            app.quit()
        else:
            QTimer.singleShot(100, inspect)

    QTimer.singleShot(0, window.start_transcription)
    QTimer.singleShot(600_000, lambda: timed_out.__setitem__("value", True))
    QTimer.singleShot(100, inspect)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
