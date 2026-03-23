import json
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

APP_TITLE = os.getenv("APP_TITLE", "Speaking Service")
DEMO_PAGE_ENABLED = os.getenv("DEMO_PAGE_ENABLED", "true").lower() == "true"
THINK_SECONDS_DEFAULT = int(os.getenv("THINK_SECONDS", "15"))
ANSWER_SECONDS_DEFAULT = int(os.getenv("ANSWER_SECONDS", "60"))
FINALIZE_GRACE_SECONDS = int(os.getenv("FINALIZE_GRACE_SECONDS", "20"))
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "").strip()
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus").strip()
MAX_AUDIO_MB = int(os.getenv("MAX_AUDIO_MB", "50"))
MAX_TRANSCRIPT_CHARS = int(os.getenv("MAX_TRANSCRIPT_CHARS", "5000"))

app = FastAPI(title=APP_TITLE, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

ASR_MODEL = None
QWEN_CLIENT = None
SESSIONS: Dict[str, "SpeakingSession"] = {}


class StartRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=500)
    think_seconds: int = Field(default=THINK_SECONDS_DEFAULT, ge=0, le=180)
    answer_seconds: int = Field(default=ANSWER_SECONDS_DEFAULT, ge=10, le=300)


class AbortRequest(BaseModel):
    session_id: str = Field(min_length=1)


@dataclass
class SpeakingSession:
    session_id: str
    student_id: str
    topic: str
    think_seconds: int
    answer_seconds: int
    created_at: str
    thinking_deadline: str
    answer_deadline: str
    status: str = "thinking"
    transcript: str = ""
    word_count: int = 0
    duration_seconds: Optional[float] = None
    audio_filename: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None
    finalized_at: Optional[str] = None
    aborted_at: Optional[str] = None
    session_dir: str = ""

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "topic": self.topic,
            "think_seconds": self.think_seconds,
            "answer_seconds": self.answer_seconds,
            "created_at": self.created_at,
            "thinking_deadline": self.thinking_deadline,
            "answer_deadline": self.answer_deadline,
            "status": self.status,
            "transcript": self.transcript,
            "word_count": self.word_count,
            "duration_seconds": self.duration_seconds,
            "audio_filename": self.audio_filename,
            "final_result": self.final_result,
            "finalized_at": self.finalized_at,
            "aborted_at": self.aborted_at,
        }

    def to_storage_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_storage_dict(cls, data: Dict[str, Any]) -> "SpeakingSession":
        return cls(**data)


class ServiceError(Exception):
    pass


@app.on_event("startup")
async def startup_event() -> None:
    load_sessions_from_disk()


@app.get("/")
async def root() -> FileResponse:
    if not DEMO_PAGE_ENABLED:
        raise HTTPException(status_code=404, detail="Demo page is disabled")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": APP_TITLE,
        "whisper_model": WHISPER_MODEL_SIZE,
        "whisper_device": WHISPER_DEVICE,
        "whisper_loaded": ASR_MODEL is not None,
        "qwen_model": QWEN_MODEL,
        "qwen_base_url": QWEN_BASE_URL,
        "qwen_ready": bool(QWEN_API_KEY),
        "qwen_message": "configured" if QWEN_API_KEY else "QWEN_API_KEY is empty",
        "full_upload_mode": True,
    }


@app.get("/api/topics/sample")
async def sample_topics() -> Dict[str, List[str]]:
    return {
        "topics": [
            "Do you prefer eating at home or eating out? Why?",
            "Should university students work part time during the semester?",
            "Is it better to study alone or with a group? Explain your opinion.",
            "Do online courses improve learning efficiency? Why or why not?",
            "What is one habit that helps students become better academic speakers?",
        ]
    }


@app.post("/api/speaking/start")
async def start_session(payload: StartRequest) -> Dict[str, Any]:
    now = utc_now()
    thinking_deadline = now + timedelta(seconds=payload.think_seconds)
    answer_deadline = thinking_deadline + timedelta(seconds=payload.answer_seconds)
    session_id = str(uuid.uuid4())
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    session = SpeakingSession(
        session_id=session_id,
        student_id=payload.student_id.strip(),
        topic=payload.topic.strip(),
        think_seconds=payload.think_seconds,
        answer_seconds=payload.answer_seconds,
        created_at=now.isoformat(),
        thinking_deadline=thinking_deadline.isoformat(),
        answer_deadline=answer_deadline.isoformat(),
        session_dir=str(session_dir),
    )
    SESSIONS[session_id] = session
    persist_session(session)
    return serialize_session(session)


@app.post("/api/speaking/finalize")
async def finalize_session(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
) -> Dict[str, Any]:
    session = get_session(session_id)
    update_status_by_time(session)

    if session.status == "aborted":
        raise HTTPException(status_code=400, detail="Session was aborted")
    if session.final_result is not None:
        return serialize_result(session)

    now = utc_now()
    answer_deadline = parse_iso(session.answer_deadline)
    grace_deadline = answer_deadline + timedelta(seconds=FINALIZE_GRACE_SECONDS)
    if now > grace_deadline:
        raise HTTPException(status_code=400, detail="Submission window is closed")

    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty")
    if len(content) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Audio file is larger than {MAX_AUDIO_MB} MB")

    suffix = get_file_suffix(audio.filename, audio.content_type)
    session_dir = Path(session.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    audio_path = session_dir / f"answer_full{suffix}"
    audio_path.write_bytes(content)
    session.audio_filename = audio_path.name

    try:
        transcript = await run_in_thread(transcribe_audio_file, audio_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Transcription failed: {exc}") from exc

    session.transcript = normalize_text(transcript)
    session.word_count = count_words(session.transcript)
    session.duration_seconds = max(0.0, (min(now, answer_deadline) - parse_iso(session.thinking_deadline)).total_seconds())

    try:
        result = await run_in_thread(score_transcript, session.topic, session.transcript)
    except ServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    result["mode"] = "final"
    result["basis"] = "transcript_only"
    result["word_count"] = session.word_count
    result["transcript"] = session.transcript
    result["session_id"] = session.session_id

    session.status = "finished"
    session.final_result = result
    session.finalized_at = utc_now().isoformat()
    persist_session(session)
    return serialize_result(session)


@app.post("/api/speaking/abort")
async def abort_session(payload: AbortRequest) -> Dict[str, Any]:
    session = get_session(payload.session_id)
    if session.status == "finished":
        raise HTTPException(status_code=400, detail="Finished session cannot be aborted")
    session.status = "aborted"
    session.aborted_at = utc_now().isoformat()
    persist_session(session)
    return serialize_session(session)


@app.get("/api/speaking/session/{session_id}")
async def get_session_state(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    update_status_by_time(session)
    persist_session(session)
    return serialize_session(session)


@app.get("/api/speaking/session/{session_id}/result")
async def get_session_result(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    return serialize_result(session)


async def run_in_thread(func, *args):
    import asyncio
    return await asyncio.to_thread(func, *args)


def get_asr_model_sync():
    global ASR_MODEL
    if ASR_MODEL is None:
        from faster_whisper import WhisperModel
        ASR_MODEL = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            cpu_threads=1,
            num_workers=1,
        )
    return ASR_MODEL


def get_qwen_client_sync() -> OpenAI:
    global QWEN_CLIENT
    if not QWEN_API_KEY:
        raise ServiceError("QWEN_API_KEY is empty")
    if QWEN_CLIENT is None:
        QWEN_CLIENT = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
    return QWEN_CLIENT


def transcribe_audio_file(path: Path) -> str:
    try:
        model = get_asr_model_sync()
        segments, _ = model.transcribe(
            str(path),
            language="en",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        pieces: List[str] = []
        for segment in segments:
            text = (segment.text or "").strip()
            if text:
                pieces.append(text)
        return " ".join(pieces).strip()
    except Exception as exc:
        raise RuntimeError(f"ASR failed for file {path.name}: {exc}") from exc


def score_transcript(topic: str, transcript: str) -> Dict[str, Any]:
    transcript = normalize_text(transcript)
    if not transcript:
        return {
            "overall_score": 0,
            "task_response": 0,
            "fluency_coherence": 0,
            "vocabulary": 0,
            "grammar": 0,
            "strengths": ["No scorable content was detected."],
            "improvements": ["Record a longer and clearer answer."],
            "key_errors": [],
            "sample_better_answer": "Please answer the topic with a complete spoken response.",
        }

    client = get_qwen_client_sync()
    prompt = build_scoring_prompt(topic, transcript)
    schema = {
        "name": "speaking_score",
        "schema": {
            "type": "object",
            "properties": {
                "overall_score": {"type": "number"},
                "task_response": {"type": "number"},
                "fluency_coherence": {"type": "number"},
                "vocabulary": {"type": "number"},
                "grammar": {"type": "number"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "improvements": {"type": "array", "items": {"type": "string"}},
                "key_errors": {"type": "array", "items": {"type": "string"}},
                "sample_better_answer": {"type": "string"},
            },
            "required": [
                "overall_score",
                "task_response",
                "fluency_coherence",
                "vocabulary",
                "grammar",
                "strengths",
                "improvements",
                "key_errors",
                "sample_better_answer",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict academic English speaking examiner. "
                        "Score the transcript and return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_schema", "json_schema": schema},
        )
    except Exception as exc:
        raise ServiceError(f"Qwen scoring request failed: {exc}") from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ServiceError("Qwen scoring returned an empty response")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ServiceError(f"Qwen scoring returned invalid JSON: {exc}") from exc

    return normalize_score_payload(parsed)


def build_scoring_prompt(topic: str, transcript: str) -> str:
    clipped = transcript[:MAX_TRANSCRIPT_CHARS]
    return (
        "Evaluate the student's spoken English response based on the transcript. "
        "Use a 0-100 overall score and 0-25 for each sub-score.\n\n"
        f"Topic:\n{topic}\n\n"
        f"Transcript:\n{clipped}\n\n"
        "Scoring guidance:\n"
        "- Task response: relevance, completeness, examples, support.\n"
        "- Fluency and coherence: organization, logical flow, ease of understanding from transcript.\n"
        "- Vocabulary: range, precision, academic suitability.\n"
        "- Grammar: sentence accuracy and variety.\n\n"
        "Return concise but useful feedback."
    )


def normalize_score_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    def clamp(value: Any, low: float, high: float) -> float:
        try:
            number = float(value)
        except Exception:
            number = low
        return round(max(low, min(high, number)), 1)

    def ensure_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    result = {
        "overall_score": clamp(payload.get("overall_score", 0), 0, 100),
        "task_response": clamp(payload.get("task_response", 0), 0, 25),
        "fluency_coherence": clamp(payload.get("fluency_coherence", 0), 0, 25),
        "vocabulary": clamp(payload.get("vocabulary", 0), 0, 25),
        "grammar": clamp(payload.get("grammar", 0), 0, 25),
        "strengths": ensure_list(payload.get("strengths", []))[:5],
        "improvements": ensure_list(payload.get("improvements", []))[:5],
        "key_errors": ensure_list(payload.get("key_errors", []))[:8],
        "sample_better_answer": normalize_text(payload.get("sample_better_answer", ""))[:1800],
    }
    return result


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def count_words(text: str) -> int:
    return len([part for part in text.split() if part])


def serialize_session(session: SpeakingSession) -> Dict[str, Any]:
    return session.to_public_dict()


def serialize_result(session: SpeakingSession) -> Dict[str, Any]:
    return {
        "session": session.to_public_dict(),
        "result": session.final_result,
    }


def get_session(session_id: str) -> SpeakingSession:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def update_status_by_time(session: SpeakingSession) -> None:
    if session.status in {"finished", "aborted"}:
        return
    now = utc_now()
    thinking_deadline = parse_iso(session.thinking_deadline)
    answer_deadline = parse_iso(session.answer_deadline)
    if now < thinking_deadline:
        session.status = "thinking"
    elif now <= answer_deadline:
        session.status = "answering"
    else:
        session.status = "awaiting_finalize"


def get_file_suffix(filename: Optional[str], content_type: Optional[str]) -> str:
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix:
            return suffix
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
        "audio/aac": ".aac",
        "audio/x-m4a": ".m4a",
        "audio/m4a": ".m4a",
    }
    if content_type and content_type in mapping:
        return mapping[content_type]
    return ".webm"


def persist_session(session: SpeakingSession) -> None:
    session_dir = Path(session.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = session_dir / "session.json"
    metadata_path.write_text(json.dumps(session.to_storage_dict(), ensure_ascii=True, indent=2), encoding="utf-8")


def load_sessions_from_disk() -> None:
    if not SESSIONS_DIR.exists():
        return
    for session_dir in SESSIONS_DIR.iterdir():
        metadata_path = session_dir / "session.json"
        if not metadata_path.exists():
            continue
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            session = SpeakingSession.from_storage_dict(data)
            SESSIONS[session.session_id] = session
        except Exception:
            continue


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)
