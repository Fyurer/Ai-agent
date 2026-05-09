"""
UserBot — Telethon orqali sizning profilingizdan xabar yuborish
Emoji, harflar aralash kontakt ismlarini ham topadi
"""

import os
import re
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import GetContactsRequest

log = logging.getLogger(__name__)


def clean_name(text: str) -> str:
    """Emoji va maxsus belgilarni olib tashlash"""
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002500-\U00002BEF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip().lower()


class UserBot:
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id   = api_id
        self.api_hash = api_hash
        self.phone    = phone
        self.session  = os.getenv("TG_SESSION_STRING", "")
        self.client   = None

    async def start(self):
        if not self.session:
            log.warning("⚠️ TG_SESSION_STRING yo'q — UserBot o'chirilgan")
            self.client = None
            return
        try:
            self.client = TelegramClient(
                StringSession(self.session), self.api_id, self.api_hash
            )
            await self.client.connect()
            if not await self.client.is_user_authorized():
                log.error("❌ Session muddati o'tgan")
                self.client = None
                return
            me = await self.client.get_me()
            log.info(f"✅ UserBot ulandi: {me.first_name} (@{me.username})")
        except Exception as e:
            log.error(f"UserBot xatosi: {e}")
            self.client = None

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    async def send_message(self, target: str, text: str) -> dict:
        if not self.client:
            return {"ok": False, "error": "UserBot ulanmagan"}
        try:
            # @username
            if target.startswith("@"):
                entity = await self.client.get_entity(target)
                await self.client.send_message(entity, text)
                return {"ok": True, "name": getattr(entity, 'first_name', target)}

            # +telefon
            if target.startswith("+") or target.isdigit():
                entity = await self.client.get_entity(target)
                await self.client.send_message(entity, text)
                return {"ok": True, "name": getattr(entity, 'first_name', target)}

            # Ism bo'yicha (emoji bilan ham)
            entity = await self._find_contact(target)
            if not entity:
                return {"ok": False, "error": f"'{target}' topilmadi"}
            await self.client.send_message(entity, text)
            name = f"{getattr(entity,'first_name','') or ''} {getattr(entity,'last_name','') or ''}".strip()
            return {"ok": True, "name": name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _find_contact(self, name: str):
        try:
            result = await self.client(GetContactsRequest(hash=0))
            search = clean_name(name)
            best, best_score = None, 0

            for user in result.users:
                first = getattr(user, 'first_name', '') or ''
                last  = getattr(user, 'last_name', '') or ''
                uname = getattr(user, 'username', '') or ''

                full_c  = clean_name(f"{first} {last}")
                first_c = clean_name(first)
                uname_c = clean_name(uname)

                if search == first_c or search == full_c:
                    return user

                score = 0
                if search in full_c:   score = 3
                elif search in first_c: score = 2
                elif search in uname_c: score = 2
                elif first_c in search: score = 1

                if score > best_score:
                    best_score = score
                    best = user

            return best if best_score > 0 else None
        except Exception as e:
            log.error(f"Kontakt qidirish xatosi: {e}")
            return None

    async def get_contacts_list(self) -> list:
        try:
            result = await self.client(GetContactsRequest(hash=0))
            return [
                {
                    "name": f"{getattr(u,'first_name','') or ''} {getattr(u,'last_name','') or ''}".strip(),
                    "username": getattr(u, 'username', '') or '',
                    "id": u.id
                }
                for u in result.users
            ]
        except Exception as e:
            log.error(f"Kontaktlar olishda xatolik: {e}")
            return []

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected()
