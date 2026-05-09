"""
AutoPilot Module — Avtomatik Javob Tizimi
O'tkirbekning uslubida kelgan xabarlarga AI javob beradi.
/autopilot_on va /autopilot_off buyruqlari bilan boshqariladi.
"Bandman" rejimi ham shu yerda.
"""

import os
import logging
from groq import Groq
from datetime import datetime

log = logging.getLogger(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")

# O'tkirbekning shaxsiy uslubi va konteksti
OWNER_PERSONA = f"""
Sen {OWNER_NAME} sан — Olmaliq kon-metallurgiya kombinati (AGMK) 3-mis boyitish fabrikasida ishlaydigan mexanik.

Sening shaxsiyating:
- Professional va mas'uliyatli mexanik
- O'zbek tilida gaplashasаn, ba'zan rus texnik atamalarini ishlatasаn
- Qisqa, aniq va samimiy javob berasаn
- Ish paytida band bo'lasаn, shuning uchun ba'zan kech javob berasan
- Hamkasblar bilan do'stona muloqot qilasаn
- Rahbarlarga hurmat bilan murojaat qilasаn

Muhim:
- Siz haqiqatan {OWNER_NAME} siz, AI emassiz
- Shaxsiy sir yoki maxfiy ma'lumot bermang
- Muhim qarorlar uchun "shaxsan gaplashamiz" deng
- Ish jadvali, ta'til, texnik qarorlar haqida aniq ma'lumot bermang (bilmaysiz)
- Suhbatni do'stona, qisqa va professional tuting
"""

BUSY_MODE_TEMPLATE = """
Men hozir {reason}da bandman.
Xabaringizni ko'rdim, imkon topilishi bilan javob beraman.
Shoshilinch bo'lsa: {urgent_contact}
"""


class AutoPilot:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.is_active = False          # /autopilot_on/off
        self.busy_mode = False          # /busy_on/off
        self.busy_reason = "ish"
        self.busy_urgent = "smena boshlig'iga murojaat qiling"
        self.auto_reply_log = []        # so'nggi javoblar logi

    # ── Holat boshqaruvi ──────────────────────────────────────
    def enable(self) -> str:
        self.is_active = True
        return (
            f"🤖 *AutoPilot YOQILDI*\n\n"
            f"Endi barcha kelgan xabarlarga {OWNER_NAME} nomidan\n"
            f"AI javob beradi.\n\n"
            f"⚠️ Muhim: Bot sizning uslubingizda javob beradi.\n"
            f"Barcha javoblar sizga ham ko'rinadi.\n\n"
            f"/autopilot_off — o'chirish"
        )

    def disable(self) -> str:
        self.is_active = False
        count = len(self.auto_reply_log)
        self.auto_reply_log.clear()
        return (
            f"✅ *AutoPilot O'CHIRILDI*\n\n"
            f"Bu sessiyada {count} ta xabarga javob berildi."
        )

    def enable_busy(self, reason: str = "ish", urgent: str = "") -> str:
        self.busy_mode = True
        self.busy_reason = reason
        if urgent:
            self.busy_urgent = urgent
        return (
            f"🔕 *BAND REJIMI YOQILDI*\n\n"
            f"Sabab: {reason}\n"
            f"Shoshilinch: {self.busy_urgent}\n\n"
            f"Kelgan xabarlarga avtomatik javob beriladi.\n"
            f"/busy_off — o'chirish"
        )

    def disable_busy(self) -> str:
        self.busy_mode = False
        return "🔔 *Band rejimi o'chirildi*\n\nXabarlaringizni ko'rishingiz mumkin."

    def get_status(self) -> str:
        ap = "🟢 YOQIQ" if self.is_active else "🔴 O'CHIQ"
        busy = "🔕 YOQIQ" if self.busy_mode else "✅ O'CHIQ"
        return (
            f"🤖 *AutoPilot:* {ap}\n"
            f"🔕 *Band rejimi:* {busy}\n"
            f"📊 Bu sessiyada: {len(self.auto_reply_log)} ta avtomatik javob"
        )

    # ── Javob generatsiyasi ───────────────────────────────────
    async def generate_reply(self, incoming_message: str,
                              sender_name: str = "do'st",
                              context: str = "") -> str:
        """
        Kelgan xabarga O'tkirbek uslubida javob generatsiya qilish.
        """
        try:
            system = OWNER_PERSONA
            if context:
                system += f"\n\nQo'shimcha kontekst: {context}"

            time_str = datetime.now().strftime("%H:%M")
            prompt = f"""
Sana {sender_name} dan xabar keldi (soat {time_str}):
"{incoming_message}"

{OWNER_NAME} sifatida javob ber. Qisqa, samimiy va professional.
Agar savol texnik bo'lsa — mexanik sifatida qisqacha javob ber.
Agar shaxsiy/ijtimoiy bo'lsa — do'stona, lekin qisqa.
Javob 2-3 jumladan ko'p bo'lmasin.
"""
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=200, temperature=0.7
            )
            reply = resp.choices[0].message.content.strip()

            # Logga yozish
            self.auto_reply_log.append({
                "time": time_str,
                "from": sender_name,
                "msg": incoming_message[:50],
                "reply": reply[:50]
            })

            return reply

        except Exception as e:
            log.error(f"AutoPilot javob xatosi: {e}")
            return f"Kechirasiz, hozir band. Keyinroq murojaat qiling."

    async def generate_busy_reply(self, incoming_message: str,
                                   sender_name: str = "") -> str:
        """Band rejimi uchun avtomatik javob"""
        try:
            prompt = f"""
{sender_name} {OWNER_NAME} ga xabar yubordi: "{incoming_message}"

{OWNER_NAME} hozir {self.busy_reason}da band.
Quyidagi ma'lumotlar asosida qisqa, xushmuomala avtomatik javob yoz:
- Hozir band ekanligini bildir
- Xabar ko'rilganligini ayt
- Shoshilinch bo'lsa: {self.busy_urgent}
- 2-3 jumlа, O'zbek tilida, {OWNER_NAME} nomidan
"""
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150, temperature=0.5
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return (
                f"Salom! Men hozir {self.busy_reason}da bandman.\n"
                f"Keyinroq javob beraman. Shoshilinch bo'lsa: {self.busy_urgent}"
            )

    def get_reply_log(self, limit: int = 10) -> str:
        """So'nggi avtomatik javoblar logi"""
        if not self.auto_reply_log:
            return "📋 Avtomatik javoblar yo'q."

        lines = [f"📋 *So'nggi avtomatik javoblar:*\n"]
        for item in self.auto_reply_log[-limit:]:
            lines.append(
                f"⏰ {item['time']} | 👤 {item['from']}\n"
                f"   📨 _{item['msg']}..._\n"
                f"   📤 _{item['reply']}..._\n"
            )
        return "\n".join(lines)

    # ── Kechikish xabari ─────────────────────────────────────
    async def late_notification(self, minutes: int, reason: str = "",
                                 recipient: str = "") -> str:
        """
        Kechikish haqida professional xabar matni generatsiya qilish.
        TTS yoki matn xabar uchun ishlatiladi.
        """
        try:
            prompt = f"""
{OWNER_NAME} {minutes} daqiqa kechikmoqda.
{f'Sabab: {reason}' if reason else ''}
{'Xabar yuborilayotgan kishi: ' + recipient if recipient else ''}

Quyidagi formatda professional vositachi xabari yoz:
"Assalomu alaykum! Men {OWNER_NAME}ning sun'iy intellekt yordamchisiman.
{OWNER_NAME} texnik/shaxsiy sabablarga ko'ra [N] daqiqaga kechikmoqdalar.
[Kechirim so'z va kerak bo'lsa sabab].
Xavfsizlik va ish tartibiga rioya qilishlarini so'raydilar."

Faqat tayyor matnni yoz. O'zbek tilida. 3-5 jumla.
"""
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0.5
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return (
                f"Assalomu alaykum! Men {OWNER_NAME}ning AI yordamchisiman.\n"
                f"{OWNER_NAME} {minutes} daqiqaga kechikmoqdalar.\n"
                f"Tez orada yetib kelishlari kutilmoqda."
            )
