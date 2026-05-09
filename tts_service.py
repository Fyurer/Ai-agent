"""
TTS Service — ElevenLabs Text-to-Speech
O'tkirbek nomidan ovozli xabar yuborish
"""

import os
import logging
import tempfile
import aiohttp
import asyncio

log = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam ovozi (default)
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")


class TTSService:
    """ElevenLabs TTS — matnni ovozga aylantirish"""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.api_key = ELEVENLABS_API_KEY
        self.voice_id = ELEVENLABS_VOICE_ID
        self.owner_name = OWNER_NAME

    async def text_to_speech(self, text: str) -> bytes | None:
        """Matnni mp3 baytlarga aylantiradi"""
        if not self.api_key:
            log.warning("ELEVENLABS_API_KEY sozlanmagan!")
            return None
        try:
            url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        err = await resp.text()
                        log.error(f"ElevenLabs xatosi {resp.status}: {err}")
                        return None
        except Exception as e:
            log.error(f"TTS xatosi: {e}")
            return None

    def build_proxy_message(self, original_text: str) -> str:
        """
        Foydalanuvchi matni → vositachi ovozli xabar matni
        Masalan: "kechikmoqdaman" → "Assalomu alaykum, men O'tkirbek ning AI yordamchisiman..."
        """
        return (
            f"Assalomu alaykum! Men {self.owner_name} ning sun'iy intellekt yordamchisiman. "
            f"{self.owner_name} sizga xabar yuborishimni so'radi. "
            f"Xabar matni: {original_text}"
        )

    async def get_voices(self) -> list:
        """Mavjud ovozlar ro'yxatini olish"""
        if not self.api_key:
            return []
        try:
            url = f"{self.BASE_URL}/voices"
            headers = {"xi-api-key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("voices", [])
        except Exception as e:
            log.error(f"Ovozlar xatosi: {e}")
        return []
