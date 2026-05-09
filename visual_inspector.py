"""
Visual Inspector — Vizual Defektoskopiya Moduli
Uskunaning rasmida ko'rinadigan nosozliklarni aniqlash:
moy oqishi, korroziya, bo'shashgan boltlar, yeyilish va h.k.
"""

import os
import logging
import tempfile
import google.generativeai as genai

log = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

VISUAL_INSPECTION_PROMPT = """
Sen sanoat uskunalarini vizual tekshirish bo'yicha ekspert mexaniksан.
AGMK 3-mis boyitish fabrikasidagi uskunalarni tahlil qilasan.

Rasmni quyidagi tartibda tahlil qil (O'zbek tilida, professional):

🔍 **VIZUAL DEFEKTOSKOPIYA HISOBOTI**

1. 🏭 **Uskunа turi:** (nima ekanligini aniqlash: nasos, motor, reduktor, ventilyator va h.k.)

2. 🔴 **KRITIK nosozliklar** (darhol to'xtatish kerak):
   - Har bir nuqsonni alohida sanab chiq
   - Joylashuvi va darajasi

3. 🟡 **O'rtacha darajali muammolar** (5 kun ichida ta'mirlash):
   - Moy oqishi, kichik korroziya, bo'shashgan boltlar va h.k.

4. 🟢 **Kuzatish kerak** (keyingi PPRda tekshirish):
   - Kichik yeyilishlar, ahamiyatsiz nuqsonlar

5. 📊 **Umumiy holat bahosi:** [YAXSHI / QONIQARLI / YOMON / KRITIK]

6. 🔧 **Tavsiyalar:**
   - Darhol bajarilishi kerak bo'lgan ishlar
   - Kerakli ehtiyot qismlar (taxminan)

7. ⚠️ **Xavfsizlik ogohlantirishlari:**
   - Ushbu nosozlik bilan ishlash xavflimi?

GOST 18322-2016 (Texnik xizmat ko'rsatish tizimi) asosida baholа.
"""

HSE_AUDIT_PROMPT = """
Sen HSE (Health, Safety, Environment) auditori sifatida rasmni tekshirasan.
AGMK OHSAS 18001 / ISO 45001 talablari asosida.

🦺 **HSE VIZUAL AUDIT**

Rasmda quyidagilarni tekshir:

1. 👷 **Shaxsiy himoya vositalari (PPE):**
   ✅/❌ Kaska (xavfli hududda)
   ✅/❌ Maxsus kiyim (kombinezon/yetik)
   ✅/❌ Xavfsizlik poyabzali
   ✅/❌ Ko'zoynak (kerak bo'lsa)
   ✅/❌ Qo'lqop
   ✅/❌ Respirator/niqob (kerak bo'lsa)
   ✅/❌ Xavfsizlik kamari (balandlikda)

2. 🚧 **Ish maydoni xavfsizligi:**
   ✅/❌ To'siq va ogohlantirishlar
   ✅/❌ Ish joyi tartibi (yo'llar bo'sh)
   ✅/❌ Yoritish yetarli
   ✅/❌ Xavfli materiallar to'g'ri saqlangan

3. 🔴 **Aniqlanган xavflar:**
   (har bir xavfni sanab chiq)

4. 📊 **HSE Baholash:** [RUXSAT / EHTIYOT BILAN / RUXSAT YO'Q]

5. 📋 **Zarur choralar:**
   (ruxsat berish uchun nima kerak)

AGMK va OHSAS 18001 talablariga asoslangan.
"""

SENSOR_ANALYSIS_PROMPT = """
Sen sanoat uskunalari diagnostika mutaxassisisаn.
Quyidagi sensor/o'lchov ma'lumotlarini tahlil qil:

{data}

Ushbu uskunа: {equipment}
Normal ishlash parametrlari: {normal_params}

📈 **SENSOR MA'LUMOTLARI TAHLILI**

1. 📊 **Hozirgi holat:**
   - Qaysi parametrlar normada
   - Qaysi parametrlar normadan chetga chiqqan (qancha %)

2. ⚠️ **Anomaliyalar:**
   - Muammo ko'rinishi sababi
   - Qaysi komponent ta'sir qilingan

3. 🔮 **Prognoz:**
   - Hozirgi tendensiyaga ko'ra uskuna qancha vaqt ishlaydi?
   - Avariya holati taxminan qachon bo'lishi mumkin?

4. 🔧 **Tavsiyalar:**
   - Darhol: nima qilish kerak
   - Rejali: qachon, nima tekshirish kerak

5. 🚨 **Avariya darajasi:** [XAVFSIZ / DIQQAT / OGOHLANISH / KRITIK]

ISO 13374 (Mashina diagnostikasi) va ISO 10816 (Tebranish normlari) asosida.
"""


class VisualInspector:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini = genai.GenerativeModel(GEMINI_MODEL)

    async def inspect_equipment(self, image_bytes: bytes, extra_info: str = "") -> str:
        """
        Uskuna rasmini vizual defektoskopiya qilish.
        extra_info: foydalanuvchi qo'shimcha ma'lumot bersa
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")

            prompt = VISUAL_INSPECTION_PROMPT
            if extra_info:
                prompt += f"\n\n📝 Foydalanuvchi qo'shimchasi: {extra_info}"

            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            return response.text.strip()

        except Exception as e:
            log.error(f"Vizual tekshiruv xatosi: {e}")
            return f"❌ Rasm tahlil qilib bo'lmadi: {e}"

    async def hse_audit(self, image_bytes: bytes, location: str = "") -> str:
        """
        HSE auditi — PPE va xavfsizlik vositalarini tekshirish.
        Ishchi yoki ish maydoni rasmini tahlil qiladi.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")

            prompt = HSE_AUDIT_PROMPT
            if location:
                prompt += f"\n\n📍 Joylashuv: {location}"

            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)

            result = response.text.strip()

            # Ruxsat/rad qarorini aniqlash
            decision = "⚠️ Tekshirildi"
            if "RUXSAT YO'Q" in result.upper() or "RUXSAT_YOQ" in result.upper():
                decision = "🔴 KIRISH TAQIQLANGAN"
            elif "EHTIYOT BILAN" in result.upper():
                decision = "🟡 EHTIYOT BILAN KIRISH MUMKIN"
            elif "RUXSAT" in result.upper():
                decision = "🟢 KIRISH RUXSAT ETILGAN"

            return f"🦺 *HSE AUDIT NATIJASI: {decision}*\n\n{result}"

        except Exception as e:
            log.error(f"HSE audit xatosi: {e}")
            return f"❌ HSE audit xatosi: {e}"

    async def analyze_sensor_data(self, data_text: str,
                                   equipment: str = "noma'lum uskuna",
                                   normal_params: str = "") -> str:
        """
        Sensor/o'lchov ma'lumotlarini matn yoki rasm ko'rinishida tahlil qilish.
        Vibratsiya, harorat, bosim, tok va h.k.
        """
        # Standart normal parametrlar (agar berilmasa)
        if not normal_params:
            normal_params = self._get_default_params(equipment)

        prompt = SENSOR_ANALYSIS_PROMPT.format(
            data=data_text,
            equipment=equipment,
            normal_params=normal_params
        )

        try:
            import google.generativeai as genai2
            model = genai2.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            log.error(f"Sensor tahlil xatosi: {e}")
            return f"❌ Sensor tahlil xatosi: {e}"

    async def analyze_sensor_screenshot(self, image_bytes: bytes,
                                         equipment: str = "") -> str:
        """
        Sensor ekranining skrinshotini tahlil qilish (vizual + matn birgalikda).
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")

            prompt = f"""
Bu sanoat uskunasining sensor/monitoring ekrani rasmi.
Uskuna: {equipment if equipment else 'aniqlang'}

Rasmdan barcha o'lchov qiymatlarini o'qib, quyidagi tahlilni bajaring (O'zbek tilida):

📈 **SENSOR EKRANI TAHLILI**

1. 📊 **O'qilgan qiymatlar:**
   (har bir parametr va qiymati)

2. 🔴 **Normadan chetga chiqqanlar:**
   (alarm yoki ogohlanish holatlari)

3. 🔮 **Holat prognoezi:**
   - Kritik holatga qancha vaqt qolgan (taxminan)?
   - Ehtimoliy nosozlik sababi?

4. 🔧 **Tavsiya:**
   - Darhol nima qilish kerak?

5. 🚨 **Xavf darajasi:** [XAVFSIZ / DIQQAT / OGOHLANISH / KRITIK]
"""
            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            return response.text.strip()

        except Exception as e:
            log.error(f"Sensor skrinshot xatosi: {e}")
            return f"❌ Sensor ekran tahlil xatosi: {e}"

    def _get_default_params(self, equipment: str) -> str:
        """Uskuna turiga qarab standart normal parametrlar"""
        equipment_lower = equipment.lower()
        defaults = {
            "nasos": "Tebranish: ≤4.5 mm/s (ISO 10816-7), Harorat podshipnik: ≤80°C, Bosim: texnik pasportga qarab",
            "tegirmon": "Tebranish: ≤7.1 mm/s (ISO 10816), Moy bosimi: 0.1-0.3 MPa, Harorat podshipnik: ≤90°C",
            "motor": "Harorat: ≤105°C (sinf F), Tebranish: ≤4.5 mm/s, Tok: nominal±10%",
            "kompressor": "Harorat chiqish: ≤120°C, Bosim: pasportga qarab, Moy bosimi: 0.15-0.35 MPa",
            "reduktor": "Tebranish: ≤4.5 mm/s, Harorat moy: ≤80°C, Shovqin: ≤85 dB",
        }
        for key, val in defaults.items():
            if key in equipment_lower:
                return val
        return "Uskuna pasportiga ko'ra normal diapazon"
