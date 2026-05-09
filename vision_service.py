"""
Vision Service — Ko'rish va vizual tahlil moduli
1. Vizual Defektoskopiya — uskunadagi nosozliklarni rasmdan aniqlash
2. HSE Audit       — xavfsizlik jihozlarini rasmdan tekshirish
3. Sensor Tahlil   — datchik ma'lumotlarini tahlil qilish + prognoz
4. Chertyo'j Tahlil — engineering drawing o'qish (kengaytirilgan)
"""

import os
import logging
import tempfile
import google.generativeai as genai

log = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OWNER_NAME   = os.getenv("OWNER_NAME", "O'tkirbek")

# ── HSE kiyim-kechak talablari ────────────────────────────────
HSE_REQUIRED_PPE = {
    "umumiy": ["kaska (helmet)", "ko'zgu ko'zoynak (safety glasses)",
               "maxsus ish kiyimi (coverall)", "xavfsizlik poyabzali (steel-toe boots)"],
    "kimyoviy": ["respirator/gaz niqobi", "kimyoviy himoya qo'lqop",
                 "plastik yuz qalqoni (face shield)", "kimyoviy himoya kombinezon"],
    "elektr":   ["dielektrik qo'lqop", "dielektrik galosh/botinka",
                 "izolyatsiya vositasi", "IQ himoya ko'zoynagi"],
    "balandlik": ["to'liq tana xavfsizlik tizmasi (full body harness)",
                  "karabin va halqa", "kaska"],
    "payvandlash": ["payvandlash niqobi (welding mask)", "charm qo'lqop",
                    "maxsus kiyim (alangaga chidamli)", "kiyim uchun qalqon"],
}

# ── Sensor chegara qiymatlari (MBF-3 uchun) ──────────────────
SENSOR_LIMITS = {
    "vibration_mms": {
        "nasos":      {"warn": 4.5,  "crit": 7.1},
        "tegirmon":   {"warn": 7.1,  "crit": 11.2},
        "kompressor": {"warn": 4.5,  "crit": 7.1},
        "default":    {"warn": 4.5,  "crit": 7.1},
    },
    "temperature_c": {
        "podshipnik": {"warn": 75.0,  "crit": 90.0},
        "motor":      {"warn": 80.0,  "crit": 100.0},
        "moy":        {"warn": 60.0,  "crit": 75.0},
        "default":    {"warn": 70.0,  "crit": 85.0},
    },
    "pressure_bar": {
        "gidravlik":  {"warn": 0.85,  "crit": 0.70},   # min limit (pasaysa xavfli)
        "havo":       {"warn": 6.0,   "crit": 5.0},
        "default":    {"warn": 0.8,   "crit": 0.6},
    },
}


class VisionService:
    """Gemini Vision orqali barcha vizual tahlil funksiyalari"""

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def _load_image(self, image_bytes: bytes) -> tuple:
        """Rasmni vaqtinchalik faylga saqlash va Gemini'ga yuklash"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_bytes)
            tmp = f.name
        img_file = genai.upload_file(tmp, mime_type="image/jpeg")
        return img_file, tmp

    async def defect_analysis(self, image_bytes: bytes,
                               equipment_name: str = "",
                               extra_question: str = "") -> str:
        """
        Vizual Defektoskopiya:
        Real uskunaning rasmida nosozliklarni aniqlash
        — moy oqishi, korroziya, bo'shashgan boltlar, yeyilish va h.k.
        """
        eq_ctx = f"Uskuna: {equipment_name}" if equipment_name else "Uskuna nomi noma'lum"
        prompt = f"""Sen MBF-3 (AGMK 3-mis boyitish fabrika) ning tajribali texnik eksperti va vizual defektoskopisisan.

{eq_ctx}. Ushbu sanoat uskunasining rasmini professional ko'z bilan ko'rib chiq.

📋 TAHLIL STRUKTURASI (O'zbek tilida):

1. 🔍 **ANIQLANGAN NOSOZLIKLAR:**
   Har bir nosozlikni ko'rsat:
   - Nosozlik turi (moy oqishi / korroziya / yeyilish / bo'shashgan bolt / deformatsiya / chiqindi / boshqa)
   - Joylashuvi (rasmda qayerda)
   - Og'irlik darajasi: 🟢 Kuzatib boring | 🟡 Tez ta'mirlash | 🔴 DARHOL to'xtating

2. ⚠️ **XAVFSIZLIK XATARLARI:**
   Ko'rinayotgan xavflar va qoidabuzarliklar

3. 🔧 **TAVSIYA ETILADIGAN CHORA:**
   - Darhol bajariladigan (bu smena)
   - Rejalashtirilgan (PPR doirasida)
   - Zarur ehtiyot qismlar

4. 📊 **UMUMIY HOLAT BAHOSI:**
   ✅ Yaxshi (85-100%) | ⚠️ O'rtacha (60-84%) | 🔴 Yomon (<60%)

5. 📌 **TEGISHLI GOST/ISO:**
   Aniqlangan nosozliklarga tegishli standartlar

{f"Qo'shimcha savol: {extra_question}" if extra_question else ""}

Rasmda hech qanday nosozlik ko'rinmasa, bu haqda ham aniq yoz."""

        try:
            img_file, tmp = self._load_image(image_bytes)
            response = self.model.generate_content([img_file, prompt])
            os.unlink(tmp)
            return f"🔬 *Vizual Defektoskopiya Natijasi*\n_{equipment_name or 'Uskuna'}_\n\n{response.text.strip()}"
        except Exception as e:
            log.error(f"Defekt tahlil xatosi: {e}")
            return f"❌ Vizual tahlil amalga oshmadi: {e}"

    async def hse_audit(self, image_bytes: bytes,
                         work_zone: str = "",
                         extra_check: str = "") -> str:
        """
        Aqlli HSE Auditi:
        Rasmda xavfsizlik jihozlari (PPE) bor-yo'qligini tekshirish.
        Ish ruxsatnomasi berish yoki rad etish.
        """
        zone_ctx = f"Ish zonasi: {work_zone}" if work_zone else "Ish zonasi: aniqlang"

        # Ish zonasiga mos talab tanlash
        required = HSE_REQUIRED_PPE.get("umumiy", [])
        for key in HSE_REQUIRED_PPE:
            if key in (work_zone or "").lower():
                required = HSE_REQUIRED_PPE[key]
                break

        required_str = "\n".join(f"  - {r}" for r in required)

        prompt = f"""Sen AGMK MBF-3 ning HSE (Health, Safety, Environment) mutaxassisisan.
{zone_ctx}. Bu ish zonasida ishlash uchun quyidagi himoya vositalari MAJBURIY:
{required_str}

Ushbu rasmni professional ko'z bilan ko'rib chiq va xavfsizlik auditini o'tkaz.

📋 HSE AUDIT NATIJASI (O'zbek tilida):

1. ✅ **MAVJUD HIMOYA VOSITALARI:**
   Rasmda ko'rinayotgan har bir PPE elementini sanab o't

2. ❌ **YETISHMAYOTGAN YOKI NOTO'G'RI KIYILGAN:**
   Har biri uchun:
   - Nima yetishmayapti
   - Bu qaysi xavfga olib keladi
   - GOST/ISO talabi

3. 🚦 **RUXSATNOMA QARORI:**
   ✅ RUXSAT BERILADI — barcha talablar bajarilgan
   ⚠️ SHARTLI RUXSAT — kichik kamchilik, tuzatish kerak
   🔴 RUXSAT YO'Q — xavfli, ishni boshlash mumkin emas

4. 📝 **TUZATISH KO'RSATMASI:**
   Ruxsat uchun nima qilish kerak (aniq ro'yxat)

5. 📌 Tegishli standart: GOST 12.4, ISO 45001, OHSAS 18001

{f"Qo'shimcha tekshirish: {extra_check}" if extra_check else ""}"""

        try:
            img_file, tmp = self._load_image(image_bytes)
            response = self.model.generate_content([img_file, prompt])
            os.unlink(tmp)

            result_text = response.text.strip()

            # Avtomatik qaror aniqlash
            if "RUXSAT YO'Q" in result_text or "RUXSAT YOQ" in result_text.upper():
                verdict = "🔴 RUXSAT YO'Q"
            elif "SHARTLI RUXSAT" in result_text:
                verdict = "⚠️ SHARTLI RUXSAT"
            else:
                verdict = "✅ RUXSAT BERILADI"

            return (
                f"🦺 *HSE Xavfsizlik Auditi*\n"
                f"_{work_zone or 'Ish zonasi'}_\n\n"
                f"**Qaror: {verdict}**\n\n"
                f"{result_text}"
            )
        except Exception as e:
            log.error(f"HSE audit xatosi: {e}")
            return f"❌ HSE audit amalga oshmadi: {e}"

    async def sensor_analysis(self, data_input: str,
                               equipment_name: str = "",
                               image_bytes: bytes = None) -> str:
        """
        Sensor Ma'lumotlari Tahlili + Prognoz:
        Vibratsiya, harorat, bosim ma'lumotlarini tahlil qilish.
        Avariyagacha qolgan vaqtni prognoz qilish.
        """
        eq = equipment_name.lower() if equipment_name else "default"

        # Chegaralarni olish
        vib_lim  = SENSOR_LIMITS["vibration_mms"].get(eq, SENSOR_LIMITS["vibration_mms"]["default"])
        temp_lim = SENSOR_LIMITS["temperature_c"].get(eq, SENSOR_LIMITS["temperature_c"]["default"])

        if image_bytes:
            # Rasm (skrinshot) bo'lsa — Gemini ko'radi
            prompt = f"""Sen sanoat uskunalari datchiklar ma'lumotlarini tahlil qiluvchi ekspertsiz.
Uskuna: {equipment_name or "Noma'lum"}

MBF-3 me'yoriy qiymatlar:
- Vibratsiya: ⚠️ >{vib_lim['warn']} mm/s, 🔴 >{vib_lim['crit']} mm/s
- Podshipnik harorati: ⚠️ >{temp_lim['warn']}°C, 🔴 >{temp_lim['crit']}°C

Bu skrinshot/rasm yoki jadvaldan barcha sensor qiymatlarni o'qib chiq va:

📊 **SENSOR TAHLILI** (O'zbek tilida):

1. 📈 **O'QILGAN QIYMATLAR:**
   Har bir parametr: nomi — joriy qiymat — holat (🟢/🟡/🔴)

2. 🚨 **KRITIK PARAMETRLAR:**
   Me'yordan chiqib ketgan qiymatlar va sababi

3. ⏱️ **PROGNOZ (Predictive Maintenance):**
   Hozirgi trend asosida:
   - Avariyagacha taxminiy vaqt
   - Eng ko'p xavf tug'dirayotgan parametr
   - O'zgarish tezligi (sekin/tez deterioratsiya)

4. 🔧 **TAVSIYA:**
   - Darhol (bu smena)
   - Rejalashtirilgan ta'mirlash muddati

5. 📌 ISO 13373 (vibratsiya) / ISO 13374 (monitoring) standartlari

{f"Qo'shimcha: {data_input}" if data_input else ""}"""

            try:
                img_file, tmp = self._load_image(image_bytes)
                response = self.model.generate_content([img_file, prompt])
                os.unlink(tmp)
                return f"📊 *Sensor Ma'lumotlari Tahlili*\n_{equipment_name}_\n\n{response.text.strip()}"
            except Exception as e:
                return f"❌ Sensor tahlil xatosi: {e}"

        else:
            # Matn (qo'lda kiritilgan qiymatlar) bo'lsa
            return await self._analyze_sensor_text(data_input, equipment_name,
                                                    vib_lim, temp_lim)

    async def _analyze_sensor_text(self, data_text: str, equipment_name: str,
                                    vib_lim: dict, temp_lim: dict) -> str:
        """Matndan sensor qiymatlarini ajratib tahlil qilish"""
        import re

        lines = ["📊 *Sensor Tahlili*"]
        if equipment_name:
            lines.append(f"_Uskuna: {equipment_name}_\n")

        warnings = []
        criticals = []

        # Vibratsiya
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

        # Harorat
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

        # Bosim
        press = re.search(r'bosim[=:\s]+(\d+[\d.,]*)', data_text, re.IGNORECASE)
        if press:
            val = float(press.group(1).replace(',', '.'))
            lines.append(f"📊 Bosim: {val} bar")

        if criticals:
            lines.append(f"\n🚨 *DARHOL CHORA KO'RISH KERAK:*")
            for c in criticals:
                lines.append(f"  🔴 {c}")
            lines.append("\n⛔ Ish joyini to'xtatib tekshiring!")
        elif warnings:
            lines.append(f"\n⚠️ *Diqqat talab qiladigan parametrlar:*")
            for w in warnings:
                lines.append(f"  🟡 {w}")
            lines.append("\n📅 Navbatdagi smenada tekshirish rejalashtiring.")
        else:
            lines.append("\n✅ *Barcha ko'rsatkichlar me'yor doirasida*")

        lines.append(f"\n📌 _ISO 13373-1 | GOST ISO 10816_")
        return "\n".join(lines)

    async def drawing_analysis(self, image_bytes: bytes,
                                extra_prompt: str = "",
                                drawing_type: str = "") -> str:
        """
        Kengaytirilgan Chertyo'j Tahlili:
        O'lchamlar, GOST, materiallar, toleranslar, qavslar
        """
        dtype_ctx = f"Chertyo'j turi: {drawing_type}" if drawing_type else ""

        prompt = f"""Sen AGMK MBF-3 tajribali konstruktor-mexanigisan.
{dtype_ctx}

Bu texnik chertyo'j yoki sxemani chuqur professional tahlil qil:

📐 **CHERTYO'J TAHLILI** (O'zbek tilida):

1. 📋 **UMUMIY MA'LUMOT:**
   - Detal/yig'ma nomi
   - Proyeksiyalar soni va turi (old, yon, yuqori ko'rinish)
   - Masshtab (agar ko'rinsa)
   - Chertyo'j raqami/belgisi

2. 📏 **O'LCHAMLAR va TOLERANSLAR:**
   - Asosiy o'lchamlar (mm)
   - Tolerans/qiyshiqlik belgilari (IT seriyasi, agar bor bo'lsa)
   - Yuzaning tozaligi Ra (agar ko'rinsa)

3. 🔩 **MATERIAL va ISHLOV:**
   - Ko'rsatilgan material markasi (GOST, DIN, AISI)
   - Termik ishlov (kalitlash, sepish va h.k. agar bor bo'lsa)
   - Qoplama (nikel, xrom va h.k.)

4. 🔤 **TEXNIK BELGILAR va QISQARTMALAR:**
   - Barcha ramzlar va ulardagi ma'no
   - Payvandlash belgilari (agar bor bo'lsa)
   - Rezbalar (M, G, Tr formatida)

5. 📌 **STANDARTLAR:**
   - GOST / ISO / DIN ko'rsatkichlari
   - Chertyo'jda keltirilgan normativ hujjatlar

6. ⚙️ **MEXANIK NUQTAI NAZARDAN:**
   - Bu detal/yig'ma qayerda ishlatiladi (taxminan)
   - O'rnatish/montaj bo'yicha diqqat talab qiladigan joylar
   - Kuzatuv va almashtirish muddati (agar aniqlanса)

7. ❓ **TUSHUNARSIZ JOYLAR:**
   Yaxshi ko'rinmagan yoki aniqlanmagan elementlar

{f"Maxsus savol: {extra_prompt}" if extra_prompt else ""}"""

        try:
            img_file, tmp = self._load_image(image_bytes)
            response = self.model.generate_content([img_file, prompt])
            os.unlink(tmp)
            return f"📐 *Kengaytirilgan Chertyo'j Tahlili*\n\n{response.text.strip()}"
        except Exception as e:
            log.error(f"Chertyo'j tahlil xatosi: {e}")
            return f"❌ Chertyo'j tahlil amalga oshmadi: {e}"

    async def multi_image_compare(self, image_bytes_list: list,
                                   compare_type: str = "before_after") -> str:
        """
        Bir nechta rasmni solishtirish:
        - before/after (ta'mirdan oldin/keyin)
        - damage_progression (zararlanish rivojlanishi)
        """
        prompt_map = {
            "before_after": "Ta'mirlash OLDIN va KEYIN rasmlarini solishtir. Qanday yaxshilanish bo'ldi?",
            "damage_progression": "Bu rasmlar bir xil nosozlikning rivojlanishini ko'rsatadi. Qanday tez yomonlashmoqda?"
        }
        prompt = f"""Sen vizual defektoskopiya ekspertisan.
{prompt_map.get(compare_type, compare_type)}

O'zbek tilida qisqa va aniq tahlil ber:
1. Har bir rasmda ko'rinayotgan holat
2. Asosiy farqlar
3. Xulosa va tavsiya"""

        try:
            content = [prompt]
            tmps = []
            for img_b in image_bytes_list[:3]:  # Max 3 ta
                img_file, tmp = self._load_image(img_b)
                content.append(img_file)
                tmps.append(tmp)
            response = self.model.generate_content(content)
            for t in tmps:
                try:
                    os.unlink(t)
                except Exception:
                    pass
            return f"🔄 *Rasm Taqqoslash Tahlili*\n\n{response.text.strip()}"
        except Exception as e:
            return f"❌ Taqqoslash tahlili xatosi: {e}"
