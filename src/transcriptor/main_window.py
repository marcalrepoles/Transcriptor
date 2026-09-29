from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Slot
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
AUDIO_FILTER = "Áudio (*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self._updating = False
        self._active_thread: QThread | None = None
        self._active_worker: FunctionWorker | None = None
        self._active_callback = None
        self.setWindowTitle("Transcriptor")
        self.resize(1050, 700)
        self._build_ui()
        self._setup_player()
        self._update_ui()

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        self.open_button = QPushButton("Abrir áudio"); self.open_button.clicked.connect(self.open_audio)
        self.transcribe_button = QPushButton("Transcrever"); self.transcribe_button.clicked.connect(self.start_transcription)
        self.save_button = QPushButton("Salvar projeto"); self.save_button.clicked.connect(self.save)
        self.model_combo = QComboBox(); self.model_combo.addItems(WHISPER_MODELS)
        self.speaker_combo = QComboBox(); self.speaker_combo.addItems(["Automático", "2", "3", "4", "5", "6"])
        for widget in (self.open_button, self.transcribe_button, self.save_button, QLabel("Modelo:"),
                       self.model_combo, QLabel("Locutores:"), self.speaker_combo): toolbar.addWidget(widget)
        toolbar.addStretch(); layout.addLayout(toolbar)
        info = QHBoxLayout(); self.file_label = QLabel("Nenhum áudio selecionado")
        self.hardware_label = QLabel("Processamento: —"); self.status_label = QLabel("Pronto.")
        info.addWidget(self.file_label, 1); info.addWidget(self.hardware_label); info.addWidget(self.status_label); layout.addLayout(info)
        self.progress = QProgressBar(); self.progress.setVisible(False); layout.addWidget(self.progress)
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["Tempo", "Locutor", "Texto"])
        self.table.horizontalHeader().setStretchLastSection(True); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(0, 110); self.table.setColumnWidth(1, 170)
        self.table.itemChanged.connect(self._item_changed); self.table.cellDoubleClicked.connect(self._seek_to_utterance)
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        rename = QPushButton("Renomear locutor"); rename.clicked.connect(self.rename_speaker)
        reassign = QPushButton("Alterar locutor desta fala"); reassign.clicked.connect(self.reassign_speaker)
        for label, handler in (("Exportar Word", self.export_word), ("Exportar PDF", self.export_pdf), ("Exportar TXT", self.export_txt)):
            button = QPushButton(label); button.clicked.connect(handler); actions.addWidget(button)
        actions.addStretch(); actions.addWidget(rename); actions.addWidget(reassign); layout.addLayout(actions)
        player = QHBoxLayout(); self.play_button = QPushButton("Reproduzir"); self.play_button.clicked.connect(self.toggle_play)
        self.position = QSlider(Qt.Orientation.Horizontal); self.position.sliderMoved.connect(self.media_player_set_position)
        self.time_label = QLabel("00:00:00 / 00:00:00")
        player.addWidget(self.play_button); player.addWidget(self.position, 1); player.addWidget(self.time_label); layout.addLayout(player)
        open_project = QAction("Abrir projeto", self); open_project.triggered.connect(self.open_project)
        self.menuBar().addMenu("Arquivo").addAction(open_project)

    def _setup_player(self):
        self.audio_output = QAudioOutput(self); self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output); self.audio_output.setVolume(0.8)
        self.media_player.positionChanged.connect(self._player_position); self.media_player.durationChanged.connect(self._player_duration)
        self.media_player.playbackStateChanged.connect(lambda s: self.play_button.setText("Pausar" if s == QMediaPlayer.PlaybackState.PlayingState else "Reproduzir"))

    def _update_ui(self):
        self.file_label.setText(f"{self.project.audio_name}  •  {format_timestamp(self.project.duration)}" if self.project.audio_path else "Nenhum áudio selecionado")
        self.setWindowTitle(("*" if self.project.dirty else "") + "Transcriptor")

    def open_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir áudio", "", AUDIO_FILTER)
        if not path: return
        try: duration = audio_duration(path)
        except Exception as error: return self._error("Não foi possível abrir este arquivo de áudio.", str(error))
        self.project = Project(audio_path=path, duration=duration, dirty=True)
        self.media_player.setSource(QUrl.fromLocalFile(path)); self._populate(); self._update_ui(); self.status_label.setText("Áudio carregado.")

    def start_transcription(self):
        if not self.project.audio_path: return self._error("Abra um arquivo de áudio primeiro.")
        model = WHISPER_MODELS[self.model_combo.currentText()].model_id
        if not whisper_installed(model):
            self._run(download_whisper, (model,), lambda _: self._ensure_diarization(model), "Baixando modelo...")
        else: self._ensure_diarization(model)

    def _ensure_diarization(self, model):
        if not diarization_installed(): self._run(download_diarization, (), lambda _: self._do_transcribe(model), "Baixando modelos de locutores...")
        else: self._do_transcribe(model)

    def _do_transcribe(self, model):
        self._run(transcribe, (self.project.audio_path, model), lambda result: self._do_diarize(model, result), "Transcrevendo...")

    def _do_diarize(self, model, result):
        words, language, hardware = result; self.hardware_label.setText(f"Processamento: {hardware}")
        count = None if self.speaker_combo.currentText() == "Automático" else int(self.speaker_combo.currentText())
        self._run(diarize, (self.project.audio_path, count), lambda intervals: self._finish_transcription(model, language, words, intervals), "Identificando locutores...")

    def _finish_transcription(self, model, language, words, intervals):
        self.project.model = model; self.project.language = language; self.project.speakers = self.speaker_combo.currentText()
        self.project.utterances = merge_transcript(words, intervals); self.project.dirty = True
        self._populate(); self._update_ui(); self.status_label.setText("Concluído.")

    def _run(self, function, args, callback, status):
        if self._active_thread is not None:
            self._error("Já existe uma operação em andamento.")
            return
        self._set_busy(True, status); thread = QThread(self); worker = FunctionWorker(function, *args); worker.moveToThread(thread)
        thread.started.connect(worker.run); worker.progress.connect(self._progress)
        worker.finished.connect(self._on_worker_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._active_thread = thread
        self._active_worker = worker
        self._active_callback = callback
        thread.start()

    @Slot(object)
    def _on_worker_finished(self, result):
        callback = self._active_callback
        self._active_callback = None
        self._pending_result = (callback, result)

    @Slot(str, str)
    def _on_worker_failed(self, message, trace):
        self._active_callback = None
        self._pending_error = (message, trace)

    @Slot()
    def _on_thread_finished(self):
        self._active_thread = None
        self._active_worker = None
        self._set_busy(False, self.status_label.text())
        error = getattr(self, "_pending_error", None)
        self._pending_error = None
        if error:
            self._worker_error(*error)
            return
        pending = getattr(self, "_pending_result", None)
        self._pending_result = None
        if pending:
            callback, result = pending
            if callback:
                callback(result)

    def _progress(self, value, text):
        self.status_label.setText(text); self.progress.setRange(0, 0) if value < 0 else self.progress.setRange(0, 100)
        if value >= 0: self.progress.setValue(value)

    def _set_busy(self, busy, text):
        self.status_label.setText(text); self.progress.setVisible(busy); self.progress.setRange(0, 0)
        for widget in (self.open_button, self.transcribe_button, self.save_button, self.model_combo, self.speaker_combo): widget.setEnabled(not busy)

    def _worker_error(self, message, trace): log.error(trace); self._error("A operação falhou.", message)
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
        elif item.column() == 1: self.project.reassign_utterance(row, item.text().strip() or "Pessoa A")
        self.project.dirty = True; self._update_ui()

    def rename_speaker(self):
        row = self.table.currentRow()
        if row < 0: return self._error("Selecione uma fala primeiro.")
        speaker_id = self.project.utterances[row].speaker_id
        name, ok = QInputDialog.getText(self, "Renomear locutor", "Nome:", text=self.project.display_name(speaker_id))
        if ok: self.project.rename_speaker(speaker_id, name); self._populate(); self._update_ui()

    def reassign_speaker(self):
        row = self.table.currentRow()
        if row < 0: return self._error("Selecione uma fala primeiro.")
        known = sorted({u.speaker_id for u in self.project.utterances})
        choice, ok = QInputDialog.getItem(self, "Alterar locutor desta fala", "Locutor:", known, editable=True)
        if ok and choice.strip(): self.project.reassign_utterance(row, choice.strip()); self._populate(); self._update_ui()

    def save(self):
        path = self.project.project_path
        if not path: path, _ = QFileDialog.getSaveFileName(self, "Salvar projeto", "", "Projeto Transcriptor (*.transcriptor)")
        if path: save_project(self.project, path if path.endswith(".transcriptor") else path + ".transcriptor"); self._update_ui(); self.status_label.setText("Projeto salvo.")

    def open_project(self):
        if not self._confirm_discard(): return
        path, _ = QFileDialog.getOpenFileName(self, "Abrir projeto", "", "Projeto Transcriptor (*.transcriptor)")
        if not path: return
        try: project = load_project(path)
        except Exception as error: return self._error("Não foi possível abrir o projeto.", str(error))
        if project.audio_path and not Path(project.audio_path).exists():
            replacement, _ = QFileDialog.getOpenFileName(self, "Localize o arquivo de áudio", "", AUDIO_FILTER)
            if replacement: project.audio_path = replacement; project.dirty = True
        self.project = project
        self.model_combo.setCurrentText(next((x.label for x in WHISPER_MODELS.values() if x.model_id == project.model), "Small")); self.speaker_combo.setCurrentText(project.speakers)
        if project.audio_path and Path(project.audio_path).exists(): self.media_player.setSource(QUrl.fromLocalFile(project.audio_path))
        self._populate(); self._update_ui()

    def _export(self, suffix, function):
        if not self.project.utterances: return self._error("Não há transcrição para exportar.")
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", "", f"{suffix.upper()} (*.{suffix})")
        if path:
            try: function(self.project, path if path.lower().endswith('.' + suffix) else path + '.' + suffix); self.status_label.setText("Exportação concluída.")
            except Exception as error: log.exception("Falha na exportação"); self._error("Falha na exportação.", str(error))
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
        dialog = QMessageBox(QMessageBox.Icon.Question, "Alterações não salvas",
                             "Descartar as alterações não salvas?", parent=self)
        discard = dialog.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        return dialog.clickedButton() is discard
    def closeEvent(self, event: QCloseEvent):
        if self._active_thread is not None:
            QMessageBox.information(self, "Operação em andamento", "Aguarde a operação terminar antes de fechar o programa.")
            event.ignore()
            return
        event.accept() if self._confirm_discard() else event.ignore()
