# Transcriptor

Transcriptor is a Windows desktop application that transcribes local audio, identifies speakers, and provides an editable transcript. Processing uses `faster-whisper` and `sherpa-onnx`; no account, paid API, or external transcription service is required.

## Current features

- Open WAV, MP3, M4A, MP4, FLAC, and OGG files through PyAV/Qt.
- Small, Medium, and Large (`large-v3`) Whisper choices.
- Automatic speaker count or a fixed count from 2 to 6.
- Word timestamps merged with speaker intervals without dropping text.
- Inline transcript and speaker editing, global speaker renaming, and per-utterance reassignment.
- Audio play/pause, seek bar, and double-click-to-play an utterance.
- Versioned `.transcriptor` projects with unsaved-change protection.
- Export edited content to Unicode TXT, DOCX, and PDF.
- Background model downloads and processing, with automatic CUDA attempt and CPU fallback.

## Requirements

- Windows 10 or 11 x64
- Python 3.11 x64
- Internet access for initial model downloads
- Enough disk space for the selected Whisper model and the diarization models

## Development setup

From PowerShell in the project directory:

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

Or run directly after setup:

```powershell
.\.venv\Scripts\python.exe -m transcriptor
```

Run tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Models and privacy

The selected Whisper model is downloaded by `faster-whisper` when first used. Official sherpa-onnx speaker segmentation and embedding models are also downloaded on first transcription. Files are stored under the current user's local application-data directory (normally `%LOCALAPPDATA%\Transcriptor\models`), independently of the source code and executable. Downloads use temporary `.part` files, and archives are checked before extraction.

After these downloads, transcription and speaker identification run locally and can work offline. Audio is not uploaded by Transcriptor.

## Known limitations

- The first transcription requires large model downloads and can take significant time.
- CPU transcription and diarization can be slow for long recordings.
- Speaker identification is probabilistic and may need manual correction, especially with overlapping speech or poor audio.
- This V1 does not include an installer or waveform view.
