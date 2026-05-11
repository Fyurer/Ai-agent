"""
Evolution Handlers — Self-Evolution tizimi uchun Telegram buyruqlari
handlers.py ga qo'shiladi yoki alohida ishlatiladi.

Buyruqlar:
  /modules         — yuklangan modullar ro'yxati
  /module_run      — modulni ishga tushirish
  /module_del      — modulni o'chirish
  /module_code     — modul kodini ko'rish
  /git_push        — GitHub ga push

Matnli buyruqlar:
  "Yangi modul qo'sh: <tavsif>"   → modul yaratadi
  "Modul ishgat tushir: <nom>"    → run() chaqiradi
"""

import logging
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from self_evolution import SelfEvolutionEngine

log       = logging.getLogger(__name__)
evolution = SelfEvolutionEngine()

# Ishga tushganda mavjud modullarni yuklash
_boot_results = evolution.load_all_modules()
if _boot_results:
    ok  = sum(1 for v in _boot_results.values() if v["ok"])
    bad = len(_boot_results) - ok
    log.info(f"✅ EvolutionEngine: {ok} modul yuklandi, {bad} ta xato")


def register_evolution_handlers(dp: Dispatcher, owner_id: int):
    """Evolution handlerlarini Dispatcher ga ro'yxatdan o'tkazish"""

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ── /modules ──────────────────────────────────────────────
    @dp.message(Command("modules"))
    async def cmd_modules(msg: Message):
        if not is_owner(msg):
            return
        mods = evolution.list_modules()
        if not mods:
            await msg.answer(
                "📦 *Modullar yo'q*\n\n"
                "Yangi modul qo'shish:\n"
                "`Yangi modul qo'sh: ob-havoni ko'rsatadigan funksiya`"
            )
            return

        lines = ["📦 *Dinamik Modullar:*\n"]
        for m in mods:
            st = "🟢" if m["loaded"] else "⚫"
            lines.append(
                f"{st} `{m['name']}` — {m['size']} bayt\n"
                f"   📅 {m['created']}"
            )
        lines.append(
            "\n_Ishlatish:_ `/module_run <nom>`\n"
            "_O'chirish:_ `/module_del <nom>`\n"
            "_Kodni ko'rish:_ `/module_code <nom>`"
        )
        await msg.answer("\n".join(lines))

    # ── /module_run ───────────────────────────────────────────
    @dp.message(Command("module_run"))
    async def cmd_module_run(msg: Message):
        if not is_owner(msg):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer("❓ Format: `/module_run <modul_nomi>`")
            return
        name = parts[1].strip()
        wait = await msg.answer(f"⚙️ _`{name}` ishga tushirilmoqda..._")
        result = await evolution.run_module(name)
        await wait.edit_text(f"📦 *{name}* natijasi:\n\n{result[:3000]}")

    # ── /module_del ───────────────────────────────────────────
    @dp.message(Command("module_del"))
    async def cmd_module_del(msg: Message):
        if not is_owner(msg):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer("❓ Format: `/module_del <modul_nomi>`")
            return
        name = parts[1].strip()
        if evolution.delete_module(name):
            await msg.answer(f"🗑 `{name}` moduli o'chirildi.")
        else:
            await msg.answer(f"❌ `{name}` topilmadi.")

    # ── /module_code ──────────────────────────────────────────
    @dp.message(Command("module_code"))
    async def cmd_module_code(msg: Message):
        if not is_owner(msg):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer("❓ Format: `/module_code <modul_nomi>`")
            return
        name = parts[1].strip()
        code = evolution.get_module_code(name)
        if not code:
            await msg.answer(f"❌ `{name}` kodi topilmadi.")
            return
        await msg.answer(
            f"```python\n{code[:3500]}\n```",
            parse_mode="Markdown"
        )

    # ── /git_push ─────────────────────────────────────────────
    @dp.message(Command("git_push"))
    async def cmd_git_push(msg: Message):
        if not is_owner(msg):
            return
        wait = await msg.answer("📤 _GitHub ga push qilinmoqda..._")
        result = await evolution.git_push()
        await wait.edit_text(result)

    # ── "Yangi modul qo'sh: ..." ──────────────────────────────
    @dp.message(F.text.lower().startswith("yangi modul qo'sh:"))
    @dp.message(F.text.lower().startswith("yangi modul:"))
    @dp.message(F.text.lower().startswith("modul qo'sh:"))
    async def handle_create_module(msg: Message):
        if not is_owner(msg):
            return

        # Tavsifni ajratib olish
        for prefix in ["yangi modul qo'sh:", "yangi modul:", "modul qo'sh:"]:
            if msg.text.lower().startswith(prefix):
                description = msg.text[len(prefix):].strip()
                break
        else:
            description = msg.text

        if not description:
            await msg.answer("❓ Modul tavsifini yozing:\n`Yangi modul qo'sh: <funksiya tavsifi>`")
            return

        wait = await msg.answer(
            f"🤖 _AI modul yozmoqda..._\n\n"
            f"📝 Tavsif: _{description}_"
        )

        result = await evolution.create_module(description)

        if result["ok"]:
            await wait.edit_text(
                f"✅ *Yangi modul tayyor!*\n\n"
                f"📦 Nom: `{result['name']}`\n"
                f"📁 Yo'l: `{result['path']}`\n\n"
                f"_Ishlatish:_ `/module_run {result['name']}`\n"
                f"_Kodni ko'rish:_ `/module_code {result['name']}`"
            )
        else:
            await wait.edit_text(
                f"❌ *Modul yaratishda xato:*\n\n"
                f"```\n{result['error'][:500]}\n```\n\n"
                f"_Bot qayta urinib ko'radi..._"
            )

    # ── "Modul ishga tushir: ..." ─────────────────────────────
    @dp.message(F.text.lower().startswith("modul ishga tushir:"))
    @dp.message(F.text.lower().startswith("modul chaqir:"))
    async def handle_run_module(msg: Message):
        if not is_owner(msg):
            return
        for prefix in ["modul ishga tushir:", "modul chaqir:"]:
            if msg.text.lower().startswith(prefix):
                name = msg.text[len(prefix):].strip()
                break
        else:
            name = ""

        if not name:
            await msg.answer("❓ Modul nomini yozing.")
            return

        wait   = await msg.answer(f"⚙️ _`{name}` ishga tushirilmoqda..._")
        result = await evolution.run_module(name)
        await wait.edit_text(f"📦 *{name}* natijasi:\n\n{result[:3000]}")

    log.info("✅ Evolution handlers ro'yxatdan o'tdi")
