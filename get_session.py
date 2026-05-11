#!/usr/bin/env python3
"""
Session String olish — BIR MARTA ishlatiladi!
Railway ga deploy qilishdan OLDIN bu faylni Termux da ishga tushiring.
Natijani Railway Environment Variables ga qo'shing: TG_SESSION_STRING
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

async def get_session():
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "telethon", "python-dotenv", "-q"])
        from telethon import TelegramClient
        from telethon.sessions import StringSession

    API_ID   = int(input("Telegram API ID: ") or os.getenv("TG_API_ID", "0"))
    API_HASH = input("Telegram API Hash: ") or os.getenv("TG_API_HASH", "")
    PHONE    = input("Telefon raqam (+998...): ") or os.getenv("TG_PHONE", "")

    print("\n📱 Telegramdan kod keladi...")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start(phone=PHONE)

    session_string = client.session.save()

    print("\n" + "="*60)
    print("✅ SESSION STRING (buni Railway ga qo'shing):")
    print("="*60)
    print(session_string)
    print("="*60)
    print("\nRailway → Variables → TG_SESSION_STRING = (yuqoridagi qiymat)")

    # Faylga ham saqlash
    with open("session_string.txt", "w") as f:
        f.write(session_string)
    print("\n📁 session_string.txt fayliga ham saqlandi.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(get_session())
