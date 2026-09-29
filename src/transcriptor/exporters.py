from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document

from .domain import Project
from .timefmt import format_timestamp


def transcript_lines(project: Project) -> list[str]:
    return [f"[{format_timestamp(u.start)}] {project.display_name(u.speaker_id)}: {u.text}" for u in project.utterances]


def export_txt(project: Project, path: str | Path) -> None:
    Path(path).write_text("\n\n".join(transcript_lines(project)) + "\n", encoding="utf-8")


def export_docx(project: Project, path: str | Path) -> None:
    document = Document()
    document.add_heading(project.audio_name, level=0)
    document.add_paragraph(f"Exportado em {datetime.now():%d/%m/%Y %H:%M}")
    for utterance in project.utterances:
        p = document.add_paragraph()
        p.add_run(f"[{format_timestamp(utterance.start)}] {project.display_name(utterance.speaker_id)}: ").bold = True
        p.add_run(utterance.text)
    document.save(str(path))


def export_pdf(project: Project, path: str | Path) -> None:
    from PySide6.QtGui import QTextDocument
    from PySide6.QtPrintSupport import QPrinter
    import html

    body = [f"<h1>{html.escape(project.audio_name)}</h1>"]
    for line in transcript_lines(project):
        body.append(f"<p>{html.escape(line)}</p>")
    document = QTextDocument()
    document.setHtml("".join(body))
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(path))
    document.print_(printer)
