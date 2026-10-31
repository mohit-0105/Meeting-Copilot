import base64
import logging
import uuid
from typing import Optional
import httpx
from app.models.schemas import TranscriptSegment
from app.core.config import settings

logger = logging.getLogger("meeting-copilot.stt")

class STTService:
    def __init__(self):
        self.provider = settings.STT_PROVIDER
        self.deepgram_key = settings.DEEPGRAM_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        self.sample_dialogue_idx = 0
        self.mock_dialogue = [
            ("Sarah K.", "Welcome everyone to our weekly sync. Let's start with Q4 roadmap updates."),
            ("Dave R.", "The API integration for Project Gamma is underway, but we need to address supply chain bottlenecks."),
            ("Emily W.", "Logistics is facing delays on the international shipments. We may need a fallback vendor."),
            ("Sarah K.", "I agree. Let's schedule a dedicated deep dive tomorrow at 2 PM to finalize the vendor choice."),
            ("Alex M.", "I will prepare the supplier comparative report and share it before tomorrow noon."),
            ("Dave R.", "Great, that gives us the exact figures we need to make a quick decision.")
        ]

    async def transcribe_chunk(
        self,
        audio_data: str,
        current_time_str: str = "00:00",
        audio_format: str = "webm_opus"
    ) -> Optional[TranscriptSegment]:
        """
        Processes an incoming audio chunk (base64 string).
        Supports Deepgram, OpenAI Whisper, and fallback realistic Mock transcription.
        """
        # 1. Deepgram REST transcription
        if (self.provider == "deepgram" or self.provider == "auto") and self.deepgram_key:
            try:
                raw_bytes = base64.b64decode(audio_data)
                url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true"
                headers = {
                    "Authorization": f"Token {self.deepgram_key}",
                    "Content-Type": "audio/webm" if "webm" in audio_format else "audio/wav"
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, content=raw_bytes)
                    if resp.status_code == 200:
                        data = resp.json()
                        channels = data.get("results", {}).get("channels", [])
                        if channels and channels[0].get("alternatives"):
                            alt = channels[0]["alternatives"][0]
                            text = alt.get("transcript", "").strip()
                            if text:
                                speaker = "Speaker 1"
                                words = alt.get("words", [])
                                if words and "speaker" in words[0]:
                                    speaker = f"Speaker {words[0]['speaker'] + 1}"
                                return TranscriptSegment(
                                    id=f"seg_{uuid.uuid4().hex[:6]}",
                                    speaker=speaker,
                                    text=text,
                                    timestamp=current_time_str,
                                    is_final=True
                                )
                    else:
                        logger.warning(f"Deepgram STT responded with {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Deepgram transcription error: {e}")

        # 2. OpenAI Whisper transcription
        if (self.provider == "whisper" or self.provider == "auto") and self.openai_key:
            try:
                raw_bytes = base64.b64decode(audio_data)
                url = "https://api.openai.com/v1/audio/transcriptions"
                headers = {"Authorization": f"Bearer {self.openai_key}"}
                files = {"file": ("audio.webm", raw_bytes, "audio/webm")}
                data = {"model": "whisper-1"}
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(url, headers=headers, files=files, data=data)
                    if resp.status_code == 200:
                        text = resp.json().get("text", "").strip()
                        if text:
                            return TranscriptSegment(
                                id=f"seg_{uuid.uuid4().hex[:6]}",
                                speaker="Participant",
                                text=text,
                                timestamp=current_time_str,
                                is_final=True
                            )
            except Exception as e:
                logger.error(f"Whisper transcription error: {e}")

        # 3. Realistic Mock Dialogue Simulation
        speaker, text = self.mock_dialogue[self.sample_dialogue_idx % len(self.mock_dialogue)]
        self.sample_dialogue_idx += 1

        return TranscriptSegment(
            id=f"seg_{uuid.uuid4().hex[:6]}",
            speaker=speaker,
            text=text,
            timestamp=current_time_str,
            is_final=True
        )

stt_service = STTService()
