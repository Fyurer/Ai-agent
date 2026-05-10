"""Visual Inspector - Vizual Defektoskopiya Moduli"""

import os
import base64
import logging
import aiohttp

log = logging.getLogger(__name__)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
VISION_MODEL   = os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free")

VISUAL_PROMPT = """Sen sanoat uskunalarini vizual tekshirish bo\'yicha ekspert mexaniksing.
AGMK 3-MBF uskunalarini tahlil qilasan.

Rasmni tahlil qil (O\'zbek tilida, professional):
1. ANIQLANGAN NOSOZLIKLAR: tur, joylashuvi, og\'irlik darajasi
2. XAVFSIZLIK XATARLARI
3. TAVSIYA: darhol va PPR doirasida
4. UMUMIY HOLAT (0-100%)
5. TEGISHLI GOST/ISO"""


class VisualInspector:
    """OpenRouter Vision orqali vizual defektoskopiya"""

    def __init__(self):
        self._key = OPENROUTER_KEY

    async def _call(self, image_bytes: bytes, prompt: str) -> str:
        if not self._key:
            return "OPENROUTER_API_KEY sozlanmagan."
        b64 = base64.b64encode(image_bytes).decode()
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agmk-bot",
        }
        payload = {
            "model": VISION_MODEL,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": prompt}
            ]}]
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(OPENROUTER_URL, json=payload, headers=headers,
                                  timeout=aiohttp.ClientTimeout(total=40)) as r:
                    data = await r.json()
                    if "error" in data:
                        return f"OpenRouter xatosi: {data['error'].get('message','')}"
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Vision xatosi: {e}"

    async def inspect(self, image_bytes: bytes,
                      equipment_name: str = "",
                      extra_question: str = "") -> str:
        eq = f"Uskuna: {equipment_name}" if equipment_name else ""
        prompt = VISUAL_PROMPT
        if eq: prompt = f"{eq}\n\n{prompt}"
        if extra_question: prompt += f"\n\nMaxsus savol: {extra_question}"
        result = await self._call(image_bytes, prompt)
        return f"🔬 *Vizual Tekshiruv*\n_{equipment_name or 'Uskuna'}_\n\n{result}"

    async def quick_check(self, image_bytes: bytes) -> str:
        """Tez tekshiruv"""
        prompt = ("Bu sanoat uskunasi rasmini ko\'r. "
                  "Biror nosozlik yoki xavfli holat bormi? "
                  "O\'zbek tilida qisqa javob (2-3 jumla).")
        return await self._call(image_bytes, prompt)
