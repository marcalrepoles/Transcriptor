from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFileDialog,
    QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSlider, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .audio import audio_duration
from .diarization import diarize
from .domain import Project
from .downloads import download_diarization, download_whisper
from .exporters import export_docx, export_pdf, export_txt
from .merge import merge_transcript
from .model_registry import WHISPER_MODELS, diarization_installed, whisper_installed
from .projects import load_project, save_project
from .timefmt import format_timestamp
from .transcription import transcribe
from .workers import FunctionWorker

log = logging.getLogger(__name__)
AUDIO_FILTER = "Audio (*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self._updating = False
        self._threads: list[QThread] = []
        self.setWindowTitle("Transcriptor")
        self.resize(1050, 700)
        self._build_ui()
        self._setup_player()
        self._update_ui()

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        self.open_button = QPushButton("Open Audio"); self.open_button.clicked.connect(self.open_audio)
        self.transcribe_button = QPushButton("Transcribe"); self.transcribe_button.clicked.connect(self.start_transcription)
        self.save_button = QPushButton("Save Project"); self.save_button.clicked.connect(self.save)
        self.model_combo = QComboBox(); self.model_combo.addItems(WHISPER_MODELS)
        self.speaker_combo = QComboBox(); self.speaker_combo.addItems(["Auto", "2", "3", "4", "5", "6"])
        for widget in (self.open_button, self.transcribe_button, self.save_button, QLabel("Model:"),
                       self.model_combo, QLabel("Speakers:"), self.speaker_combo): toolbar.addWidget(widget)
        toolbar.addStretch(); layout.addLayout(toolbar)
        info = QHBoxLayout(); self.file_label = QLabel("No audio selected")
        self.hardware_label = QLabel("Processing: —"); self.status_label = QLabel("Ready.")
        info.addWidget(self.file_label, 1); info.addWidget(self.hardware_label); info.addWidget(self.status_label); layout.addLayout(info)
        self.progress = QProgressBar(); self.progress.setVisible(False); layout.addWidget(self.progress)
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["Timestamp", "Speaker", "Text"])
        self.table.horizontalHeader().setStretchLastSection(True); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(0, 110); self.table.setColumnWidth(1, 170)
        self.table.itemChanged.connect(self._item_changed); self.table.cellDoubleClicked.connect(self._seek_to_utterance)
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        rename = QPushButton("Rename Speaker"); rename.clicked.connect(self.rename_speaker)
        reassign = QPushButton("Change This Speaker"); reassign.clicked.connect(self.reassign_speaker)
        for label, handler in (("Export Word", self.export_word), ("Export PDF", self.export_pdf), ("Export TXT", self.export_txt)):
            button = QPushButton(label); button.clicked.connect(handler); actions.addWidget(button)
        actions.addStretch(); actions.addWidget(rename); actions.addWidget(reassign); layout.addLayout(actions)
        player = QHBoxLayout(); self.play_button = QPushButton("Play"); self.play_button.clicked.connect(self.toggle_play)
        self.position = QSlider(Qt.Orientation.Horizontal); self.position.sliderMoved.connect(self.media_player_set_position)
        self.time_label = QLabel("00:00:00 / 00:00:00")
        player.addWidget(self.play_button); player.addWidget(self.position, 1); player.addWidget(self.time_label); layout.addLayout(player)
        open_project = QAction("Open Project", self); open_project.triggered.connect(self.open_project)
        self.menuBar().addMenu("File").addAction(open_project)

    def _setup_player(self):
        self.audio_output = QAudioOutput(self); self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output); self.audio_output.setVolume(0.8)
        self.media_player.positionChanged.connect(self._player_position); self.media_player.durationChanged.connect(self._player_duration)
        self.media_player.playbackStateChanged.connect(lambda s: self.play_button.setText("Pause" if s == QMediaPlayer.PlaybackState.PlayingState else "Play"))

    def _update_ui(self):
        self.file_label.setText(f"{self.project.audio_name}  •  {format_timestamp(self.project.duration)}" if self.project.audio_path else "No audio selected")
        self.setWindowTitle(("*" if self.project.dirty else "") + "Transcriptor")

    def open_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Audio", "", AUDIO_FILTER)
        if not path: return
        try: duration = audio_duration(path)
        except Exception as error: return self._error("Could not open this audio file.", str(error))
        self.project = Project(audio_path=path, duration=duration, dirty=True)
        self.media_player.setSource(QUrl.fromLocalFile(path)); self._populate(); self._update_ui(); self.status_label.setText("Audio loaded.")

    def start_transcription(self):
        if not self.project.audio_path: return self._error("Open an audio file first.")
        model = WHISPER_MODELS[self.model_combo.currentText()].model_id
        if not whisper_installed(model):
            self._run(download_whisper, (model,), lambda _: self._ensure_diarization(model), "Downloading model...")
        else: self._ensure_diarization(model)

    def _ensure_diarization(self, model):
        if not diarization_installed(): self._run(download_diarization, (), lambda _: self._do_transcribe(model), "Downloading speaker models...")
        else: self._do_transcribe(model)

    def _do_transcribe(self, model):
        self._run(transcribe, (self.project.audio_path, model), lambda result: self._do_diarize(model, result), "Transcribing...")

    def _do_diarize(self, model, result):
        words, language, hardware = result; self.hardware_label.setText(f"Processing: {hardware}")
        count = None if self.speaker_combo.currentText() == "Auto" else int(self.speaker_combo.currentText())
        self._run(diarize, (self.project.audio_path, count), lambda intervals: self._finish_transcription(model, language, words, intervals), "Identifying speakers...")

    def _finish_transcription(self, model, language, words, intervals):
        self.project.model = model; self.project.language = language; self.project.speakers = self.speaker_combo.currentText()
        self.project.utterances = merge_transcript(words, intervals); self.project.dirty = True
        self._populate(); self._update_ui(); self.status_label.setText("Complete.")

    def _run(self, function, args, callback, status):
        self._set_busy(True, status); thread = QThread(self); worker = FunctionWorker(function, *args); worker.moveToThread(thread)
        thread.started.connect(worker.run); worker.progress.connect(self._progress)
        def completed(result):
            self._cleanup_thread(thread, worker)
            callback(result)
        def failed(message, trace):
            self._cleanup_thread(thread, worker)
            self._worker_error(message, trace)
        worker.finished.connect(completed)
        worker.failed.connect(failed)
        self._threads.append(thread); thread.start()

    def _cleanup_thread(self, thread, worker):
        self._set_busy(False, self.status_label.text()); thread.quit(); thread.wait(); worker.deleteLater(); thread.deleteLater()
        if thread in self._threads: self._threads.remove(thread)

    def _progress(self, value, text):
        self.status_label.setText(text); self.progress.setRange(0, 0) if value < 0 else self.progress.setRange(0, 100)
        if value >= 0: self.progress.setValue(value)

    def _set_busy(self, busy, text):
        self.status_label.setText(text); self.progress.setVisible(busy); self.progress.setRange(0, 0)
        for widget in (self.open_button, self.transcribe_button, self.save_button, self.model_combo, self.speaker_combo): widget.setEnabled(not busy)

    def _worker_error(self, message, trace): log.error(trace); self._error("Operation failed.", message)
    def _error(self, message, detail=""): QMessageBox.critical(self, "Transcriptor", message + (f"\n\n{detail}" if detail else ""))

    def _populate(self):
        self._updating = True; self.table.setRowCount(len(self.project.utterances))
        for row, u in enumerate(self.project.utterances):
            ts = QTableWidgetItem(format_timestamp(u.start)); ts.setFlags(ts.flags() & ~Qt.ItemFlag.ItemIsEditable); ts.setData(Qt.ItemDataRole.UserRole, u.start)
            speaker = QTableWidgetItem(self.project.display_name(u.speaker_id)); speaker.setData(Qt.ItemDataRole.UserRole, u.speaker_id)
            self.table.setItem(row, 0, ts); self.table.setItem(row, 1, speaker); self.table.setItem(row, 2, QTableWidgetItem(u.text))
        self._updating = False

    def _item_changed(self, item):
        if self._updating: return
        row = item.row()
        if item.column() == 2: self.project.utterances[row].text = item.text()
        elif item.column() == 1: self.project.reassign_utterance(row, item.text().strip() or "Person A")
        self.project.dirty = True; self._update_ui()

    def rename_speaker(self):
        row = self.table.currentRow()
        if row < 0: return self._error("Select an utterance first.")
        speaker_id = self.project.utterances[row].speaker_id
        name, ok = QInputDialog.getText(self, "Rename Speaker", "Name:", text=self.project.display_name(speaker_id))
        if ok: self.project.rename_speaker(speaker_id, name); self._populate(); self._update_ui()

    def reassign_speaker(self):
        row = self.table.currentRow()
        if row < 0: return self._error("Select an utterance first.")
        known = sorted({u.speaker_id for u in self.project.utterances})
        choice, ok = QInputDialog.getItem(self, "Change This Speaker", "Speaker:", known, editable=True)
        if ok and choice.strip(): self.project.reassign_utterance(row, choice.strip()); self._populate(); self._update_ui()

    def save(self):
        path = self.project.project_path
        if not path: path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "Transcriptor Project (*.transcriptor)")
        if path: save_project(self.project, path if path.endswith(".transcriptor") else path + ".transcriptor"); self._update_ui(); self.status_label.setText("Project saved.")

    def open_project(self):
        if not self._confirm_discard(): return
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Transcriptor Project (*.transcriptor)")
        if not path: return
        try: project = load_project(path)
        except Exception as error: return self._error("Could not open project.", str(error))
        if project.audio_path and not Path(project.audio_path).exists():
            replacement, _ = QFileDialog.getOpenFileName(self, "Locate the audio file", "", AUDIO_FILTER)
            if replacement: project.audio_path = replacement; project.dirty = True
        self.project = project
        self.model_combo.setCurrentText(next((x.label for x in WHISPER_MODELS.values() if x.model_id == project.model), "Small")); self.speaker_combo.setCurrentText(project.speakers)
        if project.audio_path and Path(project.audio_path).exists(): self.media_player.setSource(QUrl.fromLocalFile(project.audio_path))
        self._populate(); self._update_ui()

    def _export(self, suffix, function):
        if not self.project.utterances: return self._error("There is no transcript to export.")
        path, _ = QFileDialog.getSaveFileName(self, "Export", "", f"{suffix.upper()} (*.{suffix})")
        if path:
            try: function(self.project, path if path.lower().endswith('.' + suffix) else path + '.' + suffix); self.status_label.setText("Export complete.")
            except Exception as error: log.exception("Export failed"); self._error("Export failed.", str(error))
    def export_word(self): self._export("docx", export_docx)
    def export_pdf(self): self._export("pdf", export_pdf)
    def export_txt(self): self._export("txt", export_txt)
    def toggle_play(self): self.media_player.pause() if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState else self.media_player.play()
    def media_player_set_position(self, value): self.media_player.setPosition(value)
    def _seek_to_utterance(self, row, _): self.media_player.setPosition(int(self.project.utterances[row].start * 1000)); self.media_player.play()
    def _player_duration(self, value): self.position.setRange(0, value)
    def _player_position(self, value): self.position.setValue(value); self.time_label.setText(f"{format_timestamp(value/1000)} / {format_timestamp(self.media_player.duration()/1000)}")
    def _confirm_discard(self):
        if not self.project.dirty: return True
        answer = QMessageBox.question(self, "Unsaved changes", "Discard unsaved changes?", QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Discard
    def closeEvent(self, event: QCloseEvent): event.accept() if self._confirm_discard() else event.ignore()
