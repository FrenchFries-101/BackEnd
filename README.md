# Speaking Service with full audio upload, faster-whisper, and Qwen API

This project provides:
- browser microphone recording
- 15-second thinking timer
- 60-second speaking timer
- one full audio upload after recording stops
- server-side transcription with faster-whisper
- final scoring with the Qwen API
- a single demo GUI page plus FastAPI endpoints for integration

## Why this version is more stable

The browser records multiple short media segments locally, but the backend does **not** transcribe each short segment separately.
Instead, the frontend combines the recorded chunks into one complete audio file and uploads that full recording once.
This avoids common `webm` chunk decoding errors during transcription.

## Architecture

Frontend browser page:
- gets microphone permission
- runs the thinking and speaking timers
- records audio locally
- uploads one full audio file at the end
- shows the transcript and final score

Backend FastAPI:
- manages speaking sessions
- stores the uploaded full recording
- transcribes the full recording with faster-whisper
- scores the transcript with the Qwen API
- returns transcript and final result

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- network access to the Qwen API endpoint

## Setup

### 1. Create a virtual environment

PowerShell:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
py -m venv .venv
.venv\Scriptsctivate.bat
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the template file:

PowerShell:

```powershell
Copy-Item .env.example .env
```

Command Prompt:

```cmd
copy .env.example .env
```

Edit `.env` and set:

```env
QWEN_API_KEY=your_real_qwen_api_key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

### 4. Start the service

```bash
python -m uvicorn app:app --reload
```

Open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs

## API endpoints

### GET /api/health
Returns local service configuration.

### POST /api/speaking/start
Starts a speaking session.

Request body:

```json
{
  "student_id": "student_001",
  "topic": "Do you prefer eating at home or eating out? Why?",
  "think_seconds": 15,
  "answer_seconds": 60
}
```

### POST /api/speaking/finalize
Uploads the full recorded audio and returns the final score.

Form fields:
- `session_id`
- `audio`

### POST /api/speaking/abort
Aborts a session.

### GET /api/speaking/session/{session_id}
Returns session state.

### GET /api/speaking/session/{session_id}/result
Returns transcript and final result.

## Notes

- Scoring is transcript-based.
- This service does not produce a true pronunciation score from raw audio.
- The browser page is a demo UI. You can keep it or replace it with your own frontend.
- This version is designed for one-page integration: the user records once, uploads once, then receives the transcript and final score.

## Recommended defaults

For most laptops:

```env
WHISPER_MODEL_SIZE=small.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
QWEN_MODEL=qwen-plus
```
