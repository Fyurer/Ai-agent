"""
Vision Service v2.0 — OpenRouter (Gemini o'rniga)
1. Vizual Defektoskopiya — uskunadagi nosozliklarni rasmdan aniqlash
2. HSE Audit       — xavfsizlik jihozlarini rasmdan tekshirish
3. Sensor Tahlil   — datchik ma'lumotlarini tahlil + prognoz
4. Chertyo'j Tahlil — engineering drawing o'qish
"""

import os
import re
import base64
import logging
import tempfile
import aiohttp

log = logging.getLogger(__name__)

OWNER_NAME       = os.getenv("OWNER_NAME", "O'tkirbek")
OPENROUTER_KEY   = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
VISION_MODEL     = os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-exp:free")

# ── HSE PPE talablari ─────────────────────────────────────────
HSE_REQUIRED_PPE = {
    "umumiy":    ["kaska", "ko'zoynak (safety glasses)", "ish kiyimi", "xavfsizlik poyabzali"],
    "kimyoviy":  ["respirator/gaz niqobi", "kimyoviy himoya qo'lqop", "yuz qalqoni", "kombinezon"],
    "elektr":    ["dielektrik qo'lqop", "dielektrik galosh", "izolyatsiya vositasi"],
    "balandlik": ["to'liq tana xavfsizlik tizmasi (harness)", "karabin", "kaska"],
    "payvandlash": ["payvandlash niqobi", "charm qo'lqop", "alangaga chidamli kiyim"],
}

# ── Sensor chegara qiymatlari ─────────────────────────────────
SENSOR_LIMITS = {
    "vibration_mms": {
        "nasos":      {"warn": 4.5,  "crit": 7.1},
        "tegirmon":   {"warn": 7.1,  "crit": 11.2},
        "kompressor": {"warn": 4.5,  "crit": 7.1},
        "default":    {"warn": 4.5,  "crit": 7.1},
    },
    "temperature_c": {
        "podshipnik": {"warn": 75.0, "crit": 90.0},
        "motor":      {"warn": 80.0, "crit": 100.0},
        "moy":        {"warn": 60.0, "crit": 75.0},
        "default":    {"warn": 70.0, "crit": 85.0},
    },
    "pressure_bar": {
        "gidravlik":  {"warn": 0.85, "crit": 0.70},
        "havo":       {"warn": 6.0,  "crit": 5.0},
        "default":    {"warn": 0.8,  "crit": 0.6},
    },
}


class VisionService:
    """OpenRouter Vision orqali barcha vizual tahlil funksiyalari"""

    def __init__(self):
        self._key = OPENROUTER_KEY

    async def _vision_request(self, image_bytes: bytes, prompt: str) -> str:
        """OpenRouter Vision API ga so'rov"""
        if not self._key:
            return "❌ OPENROUTER_API_KEY sozlanmagan."

        b64 = base64.b64encode(image_bytes).decode()
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/agmk-bot",
            "X-Title":       "AGMK MBF-3 Bot",
        }
        payload = {
            "model": VISION_MODEL,
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(OPENROUTER_URL, json=payload, headers=headers,
                                  timeout=aiohttp.ClientTimeout(total=40)) as r:
                    data = await r.json()
                    if "error" in data:
                        return f"❌ OpenRouter: {data['error'].get('message','')}"
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log.error(f"Vision request xatosi: {e}")
            return f"❌ Vision tahlil xatosi: {e}"

    async def defect_analysis(self, image_bytes: bytes,
                               equipment_name: str = "",
                               extra_question: str = "") -> str:
        """Vizual Defektoskopiya — uskunadagi nosozliklarni aniqlash"""
        eq_ctx = f"Uskuna: {equipment_name}" if equipment_name else "Uskuna nomi noma'lum"
        prompt = f"""Sen AGMK 3-MBF tajribali texnik defektoskopistisan.
{eq_ctx}. Ushbu sanoat uskunasi rasmini professional ko'rib chiq.

TAHLIL (O'zbek tilida):

1. ANIQLANGAN NOSOZLIKLAR:
   - Nosozlik turi (moy oqishi/korroziya/yeyilish/bo'shashgan bolt/deformatsiya)
   - Joylashuvi
   - Og'irlik: Kuzatib boring | Tez ta'mirlash | DARHOL to'xtating

2. XAVFSIZLIK XATARLARI:
   Ko'rinayotgan xavflar

3. TAVSIYA:
   - Darhol bajariladigan (bu smena)
   - Rejalashtirilgan (PPR)
   - Zarur ehtiyot qismlar

4. UMUMIY HOLAT: Yaxshi (85-100%) | O'rtacha (60-84%) | Yomon (<60%)

5. TEGISHLI GOST/ISO

{f"Qo'shimcha savol: {extra_question}" if extra_question else ""}"""

        result = await self._vision_request(image_bytes, prompt)
        return f"🔬 *Vizual Defektoskopiya*\n_{equipment_name or 'Uskuna'}_\n\n{result}"

    async def hse_audit(self, image_bytes: bytes,
                         work_zone: str = "",
                         extra_check: str = "") -> str:
        """HSE Auditi — xavfsizlik jihozlarini rasmdan tekshirish"""
        required = HSE_REQUIRED_PPE.get("umumiy", [])
        for key in HSE_REQUIRED_PPE:
            if key in (work_zone or "").lower():
                required = HSE_REQUIRED_PPE[key]
                break

        required_str = "\n".join(f"- {r}" for r in required)
        prompt = f"""Sen AGMK MBF-3 HSE mutaxassisisan.
Ish zonasi: {work_zone or 'Aniqlang'}

MAJBURIY himoya vositalari:
{required_str}

HSE AUDIT NATIJASI (O'zbek tilida):

1. MAVJUD HIMOYA VOSITALARI: (ro'yxat)

2. YETISHMAYOTGAN YOKI NOTO'G'RI KIYILGAN:
   - Nima yetishmayapti
   - Qaysi xavfga olib keladi
   - GOST/ISO talabi

3. RUXSATNOMA QARORI:
   RUXSAT BERILADI | SHARTLI RUXSAT | RUXSAT YO'Q

4. TUZATISH KO'RSATMASI

GOST 12.4, ISO 45001, OHSAS 18001
{f"Qo'shimcha: {extra_check}" if extra_check else ""}"""

        result = await self._vision_request(image_bytes, prompt)

        if "RUXSAT YO'Q" in result.upper() or "RUXSAT YOQ" in result.upper():
            verdict = "🔴 RUXSAT YO'Q"
        elif "SHARTLI RUXSAT" in result.upper():
            verdict = "⚠️ SHARTLI RUXSAT"
        else:
            verdict = "✅ RUXSAT BERILADI"

        return f"🦺 *HSE Xavfsizlik Auditi*\n_{work_zone or 'Ish zonasi'}_\n*Qaror: {verdict}*\n\n{result}"

    async def sensor_analysis(self, data_input: str,
                               equipment_name: str = "",
                               image_bytes: bytes = None) -> str:
        """Sensor ma'lumotlari tahlili + prognoz"""
        eq = equipment_name.lower() if equipment_name else "default"
        vib_lim  = SENSOR_LIMITS["vibration_mms"].get(eq, SENSOR_LIMITS["vibration_mms"]["default"])
        temp_lim = SENSOR_LIMITS["temperature_c"].get(eq, SENSOR_LIMITS["temperature_c"]["default"])

        if image_bytes:
            prompt = f"""Sen sanoat datchiklari ma'lumotlarini tahlil qiluvchi ekspertsiz.
Uskuna: {equipment_name or "Noma'lum"}

MBF-3 me'yoriy qiymatlar:
- Vibratsiya: diqqat >{vib_lim['warn']} mm/s, kritik >{vib_lim['crit']} mm/s
- Harorat: diqqat >{temp_lim['warn']}°C, kritik >{temp_lim['crit']}°C

SENSOR TAHLILI (O'zbek tilida):

1. O'QILGAN QIYMATLAR: (har bir parametr: nomi — qiymat — holat)
2. KRITIK PARAMETRLAR: (me'yordan chiqib ketganlar)
3. PROGNOZ: avariyagacha taxminiy vaqt, eng xavfli parametr
4. TAVSIYA: darhol va rejalashtirilgan choralar
ISO 13373, ISO 13374, GOST ISO 10816
{f"Qo'shimcha: {data_input}" if data_input else ""}"""

            result = await self._vision_request(image_bytes, prompt)
            return f"📊 *Sensor Tahlili*\n_{equipment_name}_\n\n{result}"
        else:
            return await self._analyze_sensor_text(data_input, equipment_name, vib_lim, temp_lim)

    async def _analyze_sensor_text(self, data_text: str, equipment_name: str,
                                    vib_lim: dict, temp_lim: dict) -> str:
        lines = ["📊 *Sensor Tahlili*"]
        if equipment_name:
            lines.append(f"_Uskuna: {equipment_name}_\n")

        warnings, criticals = [], []

        vib = re.search(r'vib(?:ratsiya)?[=:\s]+(\d+[\d.,]*)', data_text, re.IGNORECASE)
        if vib:
            val = float(vib.group(1).replace(',', '.'))
            if val >= vib_lim['crit']:
                status = f"🔴 KRITIK ({val} mm/s)"
                criticals.append(f"Vibratsiya: {val} mm/s > {vib_lim['crit']} mm/s")
            elif val >= vib_lim['warn']:
                status = f"🟡 DIQQAT ({val} mm/s)"
                warnings.append(f"Vibratsiya: {val} mm/s")
            else:
                status = f"🟢 NORMAL ({val} mm/s)"
            lines.append(f"📳 Vibratsiya: {status}")

        temp = re.search(r'(?:haror|temp)[=:\s]+(\d+[\d.,]*)', data_text, re.IGNORECASE)
        if temp:
            val = float(temp.group(1).replace(',', '.'))
            if val >= temp_lim['crit']:
                status = f"🔴 KRITIK ({val}°C)"
                criticals.append(f"Harorat: {val}°C > {temp_lim['crit']}°C")
            elif val >= temp_lim['warn']:
                status = f"🟡 DIQQAT ({val}°C)"
                warnings.append(f"Harorat: {val}°C")
            else:
                status = f"🟢 NORMAL ({val}°C)"
            lines.append(f"🌡 Harorat: {status}")

        press = re.search(r'bosim[=:\s]+(\d+[\d.,]*)', data_text, re.IGNORECASE)
        if press:
            lines.append(f"📊 Bosim: {press.group(1)} bar")

        if criticals:
            lines.append("\n🚨 *DARHOL CHORA KO'RISH KERAK:*")
            for c in criticals:
                lines.append(f"  🔴 {c}")
            lines.append("⛔ Ish joyini to'xtating!")
        elif warnings:
            lines.append("\n⚠️ *Diqqat talab qiladigan parametrlar:*")
            for w in warnings:
                lines.append(f"  🟡 {w}")
            lines.append("📅 Navbatdagi smenada tekshiring.")
        else:
            lines.append("\n✅ *Barcha ko'rsatkichlar me'yor doirasida*")

        lines.append("\n📌 _ISO 13373-1 | GOST ISO 10816_")
        return "\n".join(lines)

    async def drawing_analysis(self, image_bytes: bytes,
                                extra_prompt: str = "",
                                drawing_type: str = "") -> str:
        """Kengaytirilgan chertyo'j tahlili"""
        prompt = f"""Sen AGMK MBF-3 tajribali konstruktor-mexanigisan.
{f"Chertyo'j turi: {drawing_type}" if drawing_type else ""}

Bu texnik chertyo'j yoki sxemani professional tahlil qil (O'zbek tilida):

1. UMUMIY: detal/yig'ma nomi, proyeksiyalar, masshtab, raqam
2. O'LCHAMLAR va TOLERANSLAR: asosiy o'lchamlar (mm), toleranslar, yuzaning tozaligi Ra
3. MATERIAL va ISHLOV: material markasi (GOST/DIN/AISI), termik ishlov, qoplama
4. TEXNIK BELGILAR: ramzlar, payvandlash belgilari, rezbalar (M, G, Tr)
5. STANDARTLAR: GOST / ISO / DIN
6. MEXANIK NUQTAI NAZARDAN: ishlatilishi, montaj diqqat, almashtirish muddati
7. TUSHUNARSIZ JOYLAR

{f"Maxsus savol: {extra_prompt}" if extra_prompt else ""}"""

        result = await self._vision_request(image_bytes, prompt)
        return f"📐 *Kengaytirilgan Chertyo'j Tahlili*\n\n{result}"

    async def analyze_technical_image(self, image_bytes: bytes,
                                       caption: str = "") -> str:
        """Umumiy texnik rasm tahlili"""
        prompt = (
            f"Bu sanoat rasmini mexanik nuqtai nazaridan tahlil qil. "
            f"Nosozlik, xavfli holat, eskirish belgilari bormi? "
            f"O'zbek tilida aniq va qisqa javob. "
            f"{f'Savol: {caption}' if caption else ''}"
        )
        return await self._vision_request(image_bytes, prompt)
