"""
AutoReply — AutoPilot moduli v3.0
- PersonalTwin bilan integratsiya (xo'jayin uslubida javob)
- Suhbat tarixi DB ga yoziladi (kim, nima so'radi, qanday javob berdim)
- Owner ga bildirishnomada: savol + berilgan javob ko'rsatiladi
- 5 daqiqa cheklovi yo'q — har bir xabarga javob beradi
- Autopilot yoqish/o'chirish/pause buyruqlari saqlanib qoldi
"""

import os
import logging
import aiosqlite
from datetime import datetime, timedelta
from groq import Groq

log = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OWNER_NAME   = os.getenv("OWNER_NAME", "O'tkirbek")
OWNER_ID     = int(os.getenv("OWNER_CHAT_ID", "0"))
DB_PATH      = os.getenv("DB_PATH", "ai_agent.db")

WHITELIST_ENV = os.getenv("AUTO_REPLY_WHITELIST", "")


class AutoReply:
    """
    Rejimlar:
    - off       : o'chirilgan
    - on        : hammaga javob beradi
    - whitelist : faqat ruxsatli kontaktlarga
    """

    def __init__(self, client, bot_instance=None, personal_twin=None):
        self.client        = client
        self.bot           = bot_instance
        self.mode          = "off"
        self.enabled       = False
        self.paused_until  = None
        self.personal_twin = personal_twin
        self.groq          = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

        self.whitelist = [
            w.strip() for w in WHITELIST_ENV.split(",") if w.strip()
        ]

    # ── DB: suhbat tarixi ─────────────────────────────────────
    async def _ensure_table(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autopilot_chats (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id   INTEGER,
                    sender_name TEXT,
                    username    TEXT,
                    question    TEXT,
                    ai_reply    TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def _save_chat(self, sender_id, sender_name, username, question, ai_reply):
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO autopilot_chats
                       (sender_id, sender_name, username, question, ai_reply)
                       VALUES (?, ?, ?, ?, ?)""",
                    (sender_id, sender_name, username, question, ai_reply)
                )
                await db.commit()
        except Exception as e:
            log.error(f"Suhbat saqlash xatosi: {e}")

    async def get_chat_history(self, limit: int = 20) -> list:
        """Oxirgi suhbatlar ro'yxati"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    """SELECT sender_name, username, question, ai_reply, created_at
                       FROM autopilot_chats ORDER BY id DESC LIMIT ?""",
                    (limit,)
                )
                return await cur.fetchall()
        except Exception:
            return []

    async def get_chat_stats(self) -> str:
        """AutoPilot statistikasi"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                c1 = await db.execute("SELECT COUNT(*) FROM autopilot_chats")
                total = (await c1.fetchone())[0]

                c2 = await db.execute(
                    "SELECT COUNT(*) FROM autopilot_chats WHERE DATE(created_at)=DATE('now')"
                )
                today = (await c2.fetchone())[0]

                c3 = await db.execute(
                    """SELECT sender_name, username, COUNT(*) as cnt
                       FROM autopilot_chats GROUP BY sender_id
                       ORDER BY cnt DESC LIMIT 5"""
                )
                top = await c3.fetchall()

            lines = [
                "📊 *AutoPilot statistikasi:*",
                f"📨 Jami suhbatlar: *{total}*",
                f"📅 Bugun: *{today}*",
            ]
            if top:
                lines.append("\n👥 *Eng faol odamlar:*")
                for i, (name, uname, cnt) in enumerate(top, 1):
                    ustr = f" (@{uname})" if uname else ""
                    lines.append(f"  {i}. {name}{ustr} — {cnt} ta xabar")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Statistika xatosi: {e}"

    # ── Handler ────────────────────────────────────────────────
    def register_handlers(self):
        from telethon import events

        @self.client.on(events.NewMessage(incoming=True))
        async def handle_incoming(event):
            await self._process_incoming(event)

        log.info("✅ AutoReply handlers ro'yxatdan o'tdi")

    async def _process_incoming(self, event):
        try:
            if not self.enabled or self.mode == "off":
                return
            if self.paused_until and datetime.now() < self.paused_until:
                return
            if event.is_group or event.is_channel:
                return

            sender = await event.get_sender()
            if not sender:
                return
            if getattr(sender, 'id', None) == OWNER_ID:
                return
            if getattr(sender, 'bot', False):
                return
            if self.mode == "whitelist" and not self._is_whitelisted(sender):
                return

            text = event.message.text or event.message.message or ""
            if not text.strip():
                return

            # AI javob
            reply = await self._generate_reply(text, sender)
            if not reply:
                return

            await event.respond(reply)

            sender_id   = getattr(sender, 'id', 0)
            sender_name = getattr(sender, 'first_name', '') or "Noma'lum"
            username    = getattr(sender, 'username', '') or ''

            log.info(f"AutoPilot → {sender_name}: {reply[:60]}...")

            # DB ga saqlash
            await self._ensure_table()
            await self._save_chat(sender_id, sender_name, username, text, reply)

            # PersonalTwin — javobdan o'rganadi (uslub takomillashadi)
            if self.personal_twin:
                try:
                    await self.personal_twin.learn_from_message(
                        reply,
                        situation=f"{sender_name} so'radi: {text[:80]}"
                    )
                except Exception as e:
                    log.warning(f"Twin o'rganish xatosi: {e}")

            # Owner ga bildirishnoma: savol + javob birga
            if self.bot and OWNER_ID:
                uname_str = f" (@{username})" if username else ""
                notif = (
                    f"🤖 *AutoPilot suhbat*\n\n"
                    f"👤 *Kim:* {sender_name}{uname_str}\n"
                    f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"❓ *Savol:*\n_{text[:300]}_\n\n"
                    f"✅ *Bergan javobim:*\n_{reply[:300]}_"
                )
                try:
                    await self.bot.send_message(OWNER_ID, notif)
                except Exception as e:
                    log.warning(f"Bildirishnoma xatosi: {e}")

        except Exception as e:
            log.error(f"AutoReply process xatosi: {e}")

    # ── AI javob ──────────────────────────────────────────────
    async def _generate_reply(self, text: str, sender) -> str:
        sender_name = getattr(sender, 'first_name', "Do'st") or "Do'st"

        # 1️⃣ PersonalTwin — xo'jayin uslubida
        if self.personal_twin:
            try:
                reply = await self.personal_twin.generate_reply(text, sender_name)
                if reply:
                    return reply
            except Exception as e:
                log.error(f"PersonalTwin xatosi: {e}")

        # 2️⃣ Groq zaxira
        if not self.groq:
            return f"Assalomu alaykum! {OWNER_NAME} hozir band, tez orada javob beradi."

        system = (
            f"Sen {OWNER_NAME}. Bu sening Telegram profilingdan kelayotgan xabar. "
            f"Aynan o'zing kabi — qisqa, aniq, inson kabi javob ber. "
            f"Xabar tiliga qarab o'zbek yoki ruscha yoz. "
            f"Hech qachon AI yoki bot ekanligingni aytma."
        )
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"{sender_name}: {text}"}
                ],
                max_tokens=200, temperature=0.8
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"Groq xatosi: {e}")
            return "Salom! Hozir bandman, tez orada javob beraman."

    # ── Whitelist ──────────────────────────────────────────────
    def _is_whitelisted(self, sender) -> bool:
        username = getattr(sender, 'username', '') or ''
        user_id  = str(getattr(sender, 'id', ''))
        phone    = getattr(sender, 'phone', '') or ''
        for entry in self.whitelist:
            entry = entry.lstrip('@').lower()
            if entry in (username.lower(), user_id, phone):
                return True
        return False

    # ── Boshqaruv metodlari ───────────────────────────────────
    def enable(self):
        self.enabled = True
        self.paused_until = None
        log.info(f"AutoReply YONDIRILDI — rejim: {self.mode}")

    def disable(self):
        self.enabled = False
        log.info("AutoReply O'CHIRILDI")

    def set_mode(self, mode: str):
        if mode in ("on", "whitelist", "off"):
            self.mode = mode
            log.info(f"AutoReply rejim: {mode}")

    def pause(self, minutes: int = 60):
        self.paused_until = datetime.now() + timedelta(minutes=minutes)
        log.info(f"AutoReply {minutes} daqiqa to'xtatildi")

    def resume(self):
        self.paused_until = None
        log.info("AutoReply davom ettirildi")

    def add_to_whitelist(self, username: str):
        username = username.lstrip('@').lower()
        if username not in self.whitelist:
            self.whitelist.append(username)

    def remove_from_whitelist(self, username: str):
        username = username.lstrip('@').lower()
        if username in self.whitelist:
            self.whitelist.remove(username)

    def get_status(self) -> str:
        if not self.enabled:
            return "⚫ O'chirilgan"
        if self.paused_until and datetime.now() < self.paused_until:
            left = int((self.paused_until - datetime.now()).total_seconds() / 60)
            return f"⏸ To'xtatilgan ({left} daqiqa qoldi)"
        return {
            "on":        "🟢 Hammaga javob beradi",
            "whitelist": f"🟡 Faqat ruxsatlilarga ({len(self.whitelist)} ta)",
            "off":       "⚫ O'chirilgan"
        }.get(self.mode, "❓ Noma'lum")
