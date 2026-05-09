"""
UserBot — Telethon orqali kontaktlarga xabar yuborish
+ AutoReply: AI suhbat rejimi
Railway uchun StringSession asosida ishlaydi
"""

import os
import re
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

log = logging.getLogger(__name__)

SESSION_STRING = os.getenv("TG_SESSION_STRING", "")


class UserBot:
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id       = api_id
        self.api_hash     = api_hash
        self.phone        = phone
        self.client: TelegramClient = None
        self.is_connected = False
        self.auto_reply   = None   # AutoReply instance

    async def start(self, bot_instance=None):
        """
        bot_instance — AutoReply xabarnomasi uchun aiogram Bot
        Railway da TG_SESSION_STRING bo'lishi SHART
        """
        try:
            if SESSION_STRING:
                self.client = TelegramClient(
                    StringSession(SESSION_STRING),
                    self.api_id,
                    self.api_hash
                )
                await self.client.start()
            else:
                # Lokal ishlatish uchun
                self.client = TelegramClient(
                    "userbot_session",
                    self.api_id,
                    self.api_hash
                )
                await self.client.start(phone=self.phone)

            self.is_connected = True
            me = await self.client.get_me()
            log.info(f"✅ UserBot: {me.first_name} (@{me.username})")

            # AutoReply ulash (ixtiyoriy modul)
            try:
                from auto_reply import AutoReply
                self.auto_reply = AutoReply(self.client, bot_instance)
                self.auto_reply.register_handlers()
                log.info(f"✅ AutoReply: {self.auto_reply.get_status()}")
            except ImportError:
                log.info("ℹ️ AutoReply moduli yo'q — o'tkazib yuborildi")

        except Exception as e:
            log.error(f"UserBot xatosi: {e}")
            self.is_connected = False

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    async def _resolve_target(self, target: str):
        target = target.strip()
        if target.startswith("@"):
            return await self.client.get_entity(target)
        if re.match(r'^\+?\d{7,15}$', target.replace(' ', '')):
            return await self.client.get_entity(target)
        contacts = await self.get_contacts_raw()
        tl = target.lower()
        for c in contacts:
            full = f"{c.get('first','')} {c.get('last','')}".strip().lower()
            if tl in full or full in tl:
                return await self.client.get_entity(c['user_id'])
        return await self.client.get_entity(target)

    async def send_message(self, target: str, content: str) -> dict:
        if not self.is_connected:
            return {"ok": False, "error": "UserBot ulanmagan"}
        try:
            entity = await self._resolve_target(target)
            await self.client.send_message(entity, content)
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', target)
            return {"ok": True, "name": name}
        except Exception as e:
            log.error(f"send_message xatosi: {e}")
            return {"ok": False, "error": str(e)}

    async def send_voice(self, target: str, audio_path: str) -> dict:
        if not self.is_connected:
            return {"ok": False, "error": "UserBot ulanmagan"}
        try:
            entity = await self._resolve_target(target)
            await self.client.send_file(entity, audio_path, voice_note=True)
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', target)
            return {"ok": True, "name": name}
        except Exception as e:
            log.error(f"send_voice xatosi: {e}")
            return {"ok": False, "error": str(e)}

    async def get_contacts_raw(self) -> list:
        if not self.is_connected:
            return []
        try:
            from telethon.tl.functions.contacts import GetContactsRequest
            result = await self.client(GetContactsRequest(hash=0))
            return [
                {"user_id": u.id, "first": u.first_name or "",
                 "last": u.last_name or "", "username": u.username}
                for u in result.users
            ]
        except Exception as e:
            log.error(f"get_contacts_raw xatosi: {e}")
            return []

    async def get_contacts_list(self) -> list:
        if not self.is_connected:
            return []
        try:
            from telethon.tl.functions.contacts import GetContactsRequest
            result = await self.client(GetContactsRequest(hash=0))
            contacts = []
            for u in result.users:
                name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Nomsiz"
                contacts.append({
                    "name": name, "username": u.username,
                    "phone": getattr(u, "phone", None),
                })
            return sorted(contacts, key=lambda x: x["name"])
        except Exception as e:
            log.error(f"get_contacts_list xatosi: {e}")
            return []
