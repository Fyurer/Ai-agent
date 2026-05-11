"""
Misol: AI tomonidan yaratilgan weather.py moduli
Bu modules/weather.py da saqlanadi va dinamik yuklanadi.
"""

import os
import logging
import aiohttp

log = logging.getLogger(__name__)

WEATHER_KEY = os.getenv("WEATHER_API_KEY", "")


async def run(city: str = "Olmaliq", **kwargs) -> str:
    """Ob-havo ma'lumotini qaytaradi"""
    try:
        if not WEATHER_KEY:
            return "❌ WEATHER_API_KEY sozlanmagan."

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={WEATHER_KEY}&units=metric&lang=ru"
        )
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                d = await r.json()

        if d.get("cod") != 200:
            return f"❌ {city} topilmadi."

        return (
            f"🌤 *{d['name']}:* {round(d['main']['temp'])}°C\n"
            f"☁️ {d['weather'][0]['description']}\n"
            f"💧 {d['main']['humidity']}% | 💨 {d['wind']['speed']} m/s"
        )
    except Exception as e:
        log.error(f"Weather module xato: {e}")
        return f"❌ Ob-havo xatosi: {e}"
