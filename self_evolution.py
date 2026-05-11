"""
Self-Evolution Engine v1.0
Bot o'zini-o'zi kuchaytiradi:
 1. AI yangi modul yozadi → modules/ ga saqlaydi
 2. Dinamik yuklaydi → xato bo'lsa AI tuzatadi
 3. Muvaffaqiyatli bo'lsa → GitHub ga commit qiladi
"""

import os
import re
import sys
import logging
import importlib
import importlib.util
import subprocess
import traceback
from datetime import datetime
from pathlib import Path

from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MODULES_DIR = Path(os.getenv("MODULES_DIR", "modules"))
LOGS_DIR    = Path(os.getenv("LOGS_DIR", "logs"))
GIT_ENABLED = os.getenv("GIT_AUTO_COMMIT", "false").lower() == "true"

MODULES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── Muhandis tizim prompti ────────────────────────────────────
ENGINEER_SYSTEM = """Sen Avtonom Python Muhandisisan. Vazifang — ishlaydigan Python modullari yozish.

QOIDALAR (qat'iy):
1. Faqat Python kodi yoz, hech qanday izoh yoki markdown blok yo'q
2. Har doim try-except bloklari ishlatish (xato butun botni to'xtatmasin)
3. Modul asosiy funksiyasini `run(**kwargs) -> str` ko'rinishida eksport qil
4. Imports faylning tepasida bo'lsin
5. Logging: `log = logging.getLogger(__name__)` ishlatish
6. Kod importlib orqali dinamik yuklanishga mos bo'lsin
7. Agar tashqi API kerak bo'lsa → os.getenv() orqali olish

TUZILISH NAMUNASI:
```python
import os, logging
log = logging.getLogger(__name__)

async def run(**kwargs) -> str:
    try:
        # ... kod ...
        return "✅ Natija"
    except Exception as e:
        log.error(f"Xato: {e}")
        return f"❌ Xato: {e}"
```

Faqat funksional kodni qaytар. Ortiqcha gapirma."""


class SelfEvolutionEngine:
    """Botning o'z-o'zini kuchaytirish mexanizmi"""

    def __init__(self):
        self.groq    = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self._loaded: dict[str, object] = {}   # modul_nomi → modul ob'ekti

    # ════════════════════════════════════════════════════════
    #  1. AI YORDAMIDA MODUL YOZISH
    # ════════════════════════════════════════════════════════

    async def create_module(self, description: str,
                             module_name: str = None,
                             extra_context: str = "") -> dict:
        """
        Tavsifga ko'ra yangi modul yaratadi.
        Qaytaradi: {ok, name, path, code, error}
        """
        # Modul nomini aniqlash
        if not module_name:
            module_name = await self._name_module(description)

        module_path = MODULES_DIR / f"{module_name}.py"

        # AI yordamida kod yozish
        code = await self._write_code(description, module_name, extra_context)
        if not code:
            return {"ok": False, "error": "Kod yozilmadi", "name": module_name}

        # Faylga saqlash
        module_path.write_text(code, encoding="utf-8")
        log.info(f"📝 Modul yozildi: {module_path}")

        # Yuklash va test
        result = await self._load_and_test(module_name, module_path)
        if result["ok"]:
            log.info(f"✅ Modul muvaffaqiyatli yuklandi: {module_name}")
            if GIT_ENABLED:
                await self._git_commit(f"Self-update: added {module_name} module")
        else:
            # Xatoni tuzatish
            fixed = await self._fix_module(module_name, module_path, result["error"])
            if fixed:
                result = await self._load_and_test(module_name, module_path)
                if result["ok"] and GIT_ENABLED:
                    await self._git_commit(f"Self-fix: repaired {module_name} module")

        return {
            "ok":   result["ok"],
            "name": module_name,
            "path": str(module_path),
            "code": code,
            "error": result.get("error", ""),
        }

    # ════════════════════════════════════════════════════════
    #  2. XATO TUZATISH
    # ════════════════════════════════════════════════════════

    async def _fix_module(self, name: str, path: Path, error_text: str,
                           max_attempts: int = 3) -> bool:
        """Xatoli modulni AI yordamida tuzatadi"""
        for attempt in range(1, max_attempts + 1):
            log.info(f"🔧 {name} tuzatilmoqda (urinish {attempt}/{max_attempts})...")

            old_code = path.read_text(encoding="utf-8")
            prompt   = (
                f"Bu Python modul quyidagi xatoni berdi:\n\n"
                f"XATO:\n{error_text}\n\n"
                f"KOD:\n{old_code}\n\n"
                f"Kodni to'g'irla. FAQAT tuzatilgan Python kodi qaytар, "
                f"hech qanday izoh yoki markdown yo'q."
            )

            fixed_code = await self._call_ai(prompt, system=ENGINEER_SYSTEM, max_tokens=1500)
            if not fixed_code:
                continue

            fixed_code = self._clean_code(fixed_code)
            path.write_text(fixed_code, encoding="utf-8")
            self._log_error(name, f"Tuzatish urinish {attempt}: {error_text[:200]}")

            result = await self._load_and_test(name, path)
            if result["ok"]:
                log.info(f"✅ {name} tuzatildi ({attempt}-urinishda)")
                return True

            error_text = result["error"]

        log.error(f"❌ {name} {max_attempts} urinishda ham tuzatilmadi")
        return False

    # ════════════════════════════════════════════════════════
    #  3. DINAMIK YUKLASH
    # ════════════════════════════════════════════════════════

    async def _load_and_test(self, name: str, path: Path) -> dict:
        """Modulni yuklab, sintaksis va import xatolarini tekshiradi"""
        try:
            spec   = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded[name] = module
            return {"ok": True}
        except Exception as e:
            error = traceback.format_exc()
            self._log_error(name, error)
            return {"ok": False, "error": error}

    def load_all_modules(self) -> dict:
        """modules/ papkasidagi barcha modullarni yuklash"""
        results = {}
        for py_file in MODULES_DIR.glob("*.py"):
            name = py_file.stem
            if name.startswith("_"):
                continue
            result = self._load_sync(name, py_file)
            results[name] = result
        return results

    def _load_sync(self, name: str, path: Path) -> dict:
        """Sinxron modul yuklash"""
        try:
            spec   = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded[name] = module
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def run_module(self, name: str, **kwargs) -> str:
        """Yuklangan modulning run() funksiyasini chaqirish"""
        module = self._loaded.get(name)
        if not module:
            # Avval yuklashga urinish
            path = MODULES_DIR / f"{name}.py"
            if path.exists():
                res = await self._load_and_test(name, path)
                if not res["ok"]:
                    return f"❌ Modul yuklanmadi: {res['error']}"
                module = self._loaded[name]
            else:
                return f"❌ Modul topilmadi: {name}"

        run_fn = getattr(module, "run", None)
        if not run_fn:
            return f"❌ {name} modulida run() funksiyasi yo'q"

        try:
            import inspect
            if inspect.iscoroutinefunction(run_fn):
                return await run_fn(**kwargs)
            else:
                return run_fn(**kwargs)
        except Exception as e:
            error = traceback.format_exc()
            self._log_error(name, error)
            return f"❌ {name} xatosi: {e}"

    # ════════════════════════════════════════════════════════
    #  4. MODULLAR RO'YXATI
    # ════════════════════════════════════════════════════════

    def list_modules(self) -> list:
        """Mavjud modullar ro'yxati"""
        modules = []
        for py_file in sorted(MODULES_DIR.glob("*.py")):
            name    = py_file.stem
            loaded  = name in self._loaded
            size    = py_file.stat().st_size
            mtime   = datetime.fromtimestamp(py_file.stat().st_mtime)
            modules.append({
                "name":    name,
                "loaded":  loaded,
                "size":    size,
                "created": mtime.strftime("%d.%m.%Y %H:%M"),
                "path":    str(py_file),
            })
        return modules

    def delete_module(self, name: str) -> bool:
        """Modulni o'chirish"""
        path = MODULES_DIR / f"{name}.py"
        if path.exists():
            path.unlink()
            self._loaded.pop(name, None)
            return True
        return False

    def get_module_code(self, name: str) -> str:
        """Modul kodini ko'rish"""
        path = MODULES_DIR / f"{name}.py"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    # ════════════════════════════════════════════════════════
    #  5. GIT INTEGRATSIYA
    # ════════════════════════════════════════════════════════

    async def _git_commit(self, message: str) -> bool:
        """modules/ papkasidagi o'zgarishlarni Git ga commit qilish"""
        try:
            cmds = [
                ["git", "add", str(MODULES_DIR)],
                ["git", "commit", "-m", message, "--allow-empty"],
            ]
            for cmd in cmds:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )
                if proc.returncode != 0:
                    log.warning(f"Git {cmd[1]} xato: {proc.stderr}")
                    return False
            log.info(f"✅ Git commit: {message}")
            return True
        except Exception as e:
            log.warning(f"Git xato: {e}")
            return False

    async def git_push(self) -> str:
        """Remote ga push qilish"""
        try:
            proc = subprocess.run(
                ["git", "push"], capture_output=True, text=True, timeout=60
            )
            if proc.returncode == 0:
                return "✅ Git push muvaffaqiyatli"
            return f"❌ Git push xato: {proc.stderr}"
        except Exception as e:
            return f"❌ Git push xatosi: {e}"

    # ════════════════════════════════════════════════════════
    #  YORDAMCHI METODLAR
    # ════════════════════════════════════════════════════════

    async def _name_module(self, description: str) -> str:
        """Tavsifdan modul nomi yaratish"""
        prompt = (
            f"Python modul nomini tavsifdan chiqar. "
            f"FAQAT snake_case nom qaytар (masalan: weather_checker, currency_rates). "
            f"Tavsif: {description}"
        )
        name = await self._call_ai(prompt, max_tokens=30)
        name = re.sub(r'[^a-z0-9_]', '_', name.lower().strip())
        name = re.sub(r'_+', '_', name).strip('_')
        return name or "custom_module"

    async def _write_code(self, description: str, module_name: str,
                           context: str = "") -> str:
        """AI yordamida modul kodi yozish"""
        prompt = (
            f"Quyidagi funksiyani Python modulida yoz:\n\n"
            f"Modul nomi: {module_name}\n"
            f"Vazifa: {description}\n"
            f"{'Qoshimcha kontekst: ' + context if context else ''}\n\n"
            f"run(**kwargs) -> str funksiyasi eksport qilinsin."
        )
        code = await self._call_ai(prompt, system=ENGINEER_SYSTEM, max_tokens=2000)
        return self._clean_code(code)

    async def _call_ai(self, prompt: str, system: str = "",
                        max_tokens: int = 1000) -> str:
        """Groq API ga so'rov"""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"AI call xatosi: {e}")
            return ""

    @staticmethod
    def _clean_code(code: str) -> str:
        """Markdown bloklari va ortiqcha bo'shliqlarni olib tashlash"""
        code = re.sub(r'```python\s*', '', code)
        code = re.sub(r'```\s*', '', code)
        return code.strip()

    def _log_error(self, module_name: str, error_text: str):
        """Xato logini faylga yozish"""
        log_file = LOGS_DIR / "error.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f"\n[{datetime.now().isoformat()}] [{module_name}]\n"
                f"{error_text}\n{'─'*60}\n"
            )
