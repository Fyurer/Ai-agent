"""
AutoLearner v1.0 — O'z-o'zini o'qitish moduli
GitHub repo + Web saytlardan avtomatik bilim yig'ish

Qo'llab-quvvatlanadigan manbalar:
  - GitHub repo (markdown, txt fayllar)
  - Ochiq web sahifalar (HTML → matn)
  - RSS/XML xabar oqimlari
"""

import os
import re
import json
import logging
import aiohttp
import aiosqlite
from datetime import datetime, timedelta
from groq import Groq

log        = logging.getLogger(__name__)
DB_PATH    = os.getenv("DB_PATH", "ai_agent.db")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Sozlamalar ────────────────────────────────────────────────
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "")   # ixtiyoriy, limit oshiradi
LEARN_INTERVAL_H = int(os.getenv("LEARN_INTERVAL_H", "24"))  # har necha soatda

# ── O'rganish manbalari ro'yxati ──────────────────────────────
# Bot avtomatik ravishda shu manbalardan o'qiydi
DEFAULT_SOURCES = [
    # GitHub repo misollari:
    # {"type":"github","repo":"owner/repo-name","path":"docs/","category":"custom"},

    # Web sahifa misollari:
    # {"type":"web","url":"https://example.com/page","category":"custom"},
]


class AutoLearner:
    """GitHub va Web manbalardan avtomatik bilim yig'uvchi"""

    def __init__(self, kb=None):
        self.kb      = kb       # KnowledgeBase obyekti
        self.groq    = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self._gh_hdr = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

    # ════════════════════════════════════════════════════════════
    #  DB — manbalarni saqlash
    # ════════════════════════════════════════════════════════════

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS learn_sources (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    type       TEXT NOT NULL,
                    url        TEXT NOT NULL UNIQUE,
                    category   TEXT DEFAULT 'auto',
                    label      TEXT,
                    enabled    INTEGER DEFAULT 1,
                    last_synced TIMESTAMP,
                    doc_count  INTEGER DEFAULT 0,
                    added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS learn_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id  INTEGER,
                    status     TEXT,
                    docs_added INTEGER DEFAULT 0,
                    error      TEXT,
                    ran_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()
        log.info("✅ AutoLearner DB tayyor")

    # ════════════════════════════════════════════════════════════
    #  MANBA BOSHQARUVI
    # ════════════════════════════════════════════════════════════

    async def add_source(self, source_type: str, url: str,
                         category: str = "auto", label: str = "") -> dict:
        """Yangi manba qo'shish"""
        source_type = source_type.lower().strip()
        if source_type not in ("github", "web", "rss"):
            return {"ok": False, "error": "Tur noto'g'ri. github | web | rss"}

        # URL ni normallashtirish
        url = url.strip().rstrip("/")
        label = label or url.split("/")[-1] or url

        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO learn_sources "
                    "(type, url, category, label) VALUES (?,?,?,?)",
                    (source_type, url, category, label)
                )
                await db.commit()
            return {"ok": True, "type": source_type, "url": url, "label": label}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def remove_source(self, source_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM learn_sources WHERE id=?", (source_id,))
            await db.commit()
        return True

    async def toggle_source(self, source_id: int, enabled: bool) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE learn_sources SET enabled=? WHERE id=?",
                (1 if enabled else 0, source_id)
            )
            await db.commit()
        return True

    async def list_sources(self) -> list:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT id, type, url, category, label, enabled, last_synced, doc_count "
                "FROM learn_sources ORDER BY id"
            )
            rows = await cur.fetchall()
        return [
            {"id": r[0], "type": r[1], "url": r[2], "category": r[3],
             "label": r[4], "enabled": bool(r[5]),
             "last_synced": r[6], "doc_count": r[7]}
            for r in rows
        ]

    # ════════════════════════════════════════════════════════════
    #  ASOSIY SINXRONIZATSIYA
    # ════════════════════════════════════════════════════════════

    async def sync_all(self, force: bool = False) -> dict:
        """Barcha faol manbalarni sinxronlashtirish"""
        sources = await self.list_sources()
        results = {"total": 0, "added": 0, "errors": 0, "details": []}

        for src in sources:
            if not src["enabled"]:
                continue

            # Interval tekshirish (force=True bo'lmasa)
            if not force and src["last_synced"]:
                try:
                    last = datetime.fromisoformat(src["last_synced"])
                    if datetime.now() - last < timedelta(hours=LEARN_INTERVAL_H):
                        continue
                except Exception:
                    pass

            results["total"] += 1
            try:
                if src["type"] == "github":
                    added = await self._sync_github(src)
                elif src["type"] == "web":
                    added = await self._sync_web(src)
                elif src["type"] == "rss":
                    added = await self._sync_rss(src)
                else:
                    added = 0

                results["added"] += added
                results["details"].append(
                    {"label": src["label"], "added": added, "ok": True}
                )
                await self._log(src["id"], "success", added)
                await self._update_synced(src["id"], added)

            except Exception as e:
                results["errors"] += 1
                results["details"].append(
                    {"label": src["label"], "added": 0, "ok": False, "error": str(e)}
                )
                await self._log(src["id"], "error", 0, str(e))
                log.error(f"AutoLearner sync xatosi [{src['label']}]: {e}")

        return results

    async def sync_one(self, source_id: int) -> dict:
        """Bitta manbani majburiy sinxronlash"""
        sources = await self.list_sources()
        src = next((s for s in sources if s["id"] == source_id), None)
        if not src:
            return {"ok": False, "error": "Manba topilmadi"}
        try:
            if src["type"] == "github":
                added = await self._sync_github(src)
            elif src["type"] == "web":
                added = await self._sync_web(src)
            elif src["type"] == "rss":
                added = await self._sync_rss(src)
            else:
                added = 0
            await self._update_synced(src["id"], added)
            return {"ok": True, "label": src["label"], "added": added}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ════════════════════════════════════════════════════════════
    #  GITHUB O'QISH
    # ════════════════════════════════════════════════════════════

    async def _sync_github(self, src: dict) -> int:
        """
        GitHub repo dan fayllarni o'qib KB ga qo'shish.
        URL formatlari:
          https://github.com/owner/repo                    → barcha .md fayllar
          https://github.com/owner/repo/tree/main/docs    → faqat docs/ papka
          https://github.com/owner/repo/blob/main/file.md → bitta fayl
        """
        url   = src["url"]
        added = 0

        # URL ni parse qilish
        # https://github.com/owner/repo[/tree/branch/path]
        m = re.match(
            r'https://github\.com/([^/]+)/([^/]+)'
            r'(?:/(?:tree|blob)/([^/]+)(?:/(.+))?)?',
            url
        )
        if not m:
            raise ValueError(f"GitHub URL noto'g'ri: {url}")

        owner, repo = m.group(1), m.group(2)
        branch      = m.group(3) or "main"
        path        = (m.group(4) or "").rstrip("/")

        # Contents API
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        if branch != "main":
            api_url += f"?ref={branch}"

        async with aiohttp.ClientSession() as session:
            files = await self._gh_list_files(session, api_url, owner, repo, branch)
            for finfo in files:
                try:
                    text = await self._gh_read_file(session, finfo["download_url"])
                    if not text or len(text.strip()) < 50:
                        continue
                    # AI bilan tozalash va kategoriya aniqlash
                    doc = await self._extract_knowledge(
                        text[:4000], finfo["name"], src["category"]
                    )
                    if doc and self.kb:
                        await self.kb.add_document(
                            title    = doc["title"],
                            content  = doc["content"],
                            category = src["category"],
                            tags     = doc.get("tags", ""),
                            source   = f"github:{owner}/{repo}"
                        )
                        added += 1
                        log.info(f"  ✅ GitHub: {finfo['name']} → KB")
                except Exception as fe:
                    log.warning(f"  ⚠️ {finfo['name']}: {fe}")

        return added

    async def _gh_list_files(self, session, api_url: str,
                              owner: str, repo: str, branch: str,
                              max_files: int = 30) -> list:
        """GitHub repo dan .md/.txt fayllar ro'yxatini olish (rekursiv)"""
        files = []
        async with session.get(api_url, headers=self._gh_hdr) as r:
            if r.status == 404:
                raise ValueError("GitHub repo/papka topilmadi")
            if r.status == 403:
                raise ValueError("GitHub API limit yetdi. GITHUB_TOKEN qo'shing")
            data = await r.json()

        if isinstance(data, dict) and data.get("type") == "file":
            # Bitta fayl
            if data["name"].endswith((".md", ".txt", ".rst")):
                files.append({"name": data["name"],
                               "download_url": data["download_url"]})
        elif isinstance(data, list):
            for item in data:
                if len(files) >= max_files:
                    break
                if item["type"] == "file" and item["name"].endswith((".md", ".txt", ".rst")):
                    files.append({"name": item["name"],
                                   "download_url": item["download_url"]})
                elif item["type"] == "dir":
                    # Rekursiv (faqat 1 daraja)
                    sub_url = (f"https://api.github.com/repos/{owner}/{repo}"
                               f"/contents/{item['path']}?ref={branch}")
                    sub = await self._gh_list_files(
                        session, sub_url, owner, repo, branch, max_files - len(files)
                    )
                    files.extend(sub)
        return files

    async def _gh_read_file(self, session, download_url: str) -> str:
        async with session.get(download_url, headers=self._gh_hdr,
                                timeout=aiohttp.ClientTimeout(total=15)) as r:
            return await r.text(encoding="utf-8", errors="replace")

    # ════════════════════════════════════════════════════════════
    #  WEB O'QISH
    # ════════════════════════════════════════════════════════════

    async def _sync_web(self, src: dict) -> int:
        """Web sahifadan matn o'qib KB ga qo'shish"""
        url   = src["url"]
        added = 0

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MBF3-Bot/1.0)"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    raise ValueError(f"HTTP {r.status}")
                html = await r.text(errors="replace")

        # HTML → toza matn
        text = self._html_to_text(html)
        if len(text.strip()) < 100:
            return 0

        doc = await self._extract_knowledge(
            text[:5000], src["label"] or url, src["category"]
        )
        if doc and self.kb:
            await self.kb.add_document(
                title    = doc["title"],
                content  = doc["content"],
                category = src["category"],
                tags     = doc.get("tags", ""),
                source   = f"web:{url}"
            )
            added = 1

        return added

    def _html_to_text(self, html: str) -> str:
        """Oddiy HTML → matn konvertatsiya (BeautifulSoup siz)"""
        # Script va style ni olib tashlash
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
        html = re.sub(r'<style[^>]*>.*?</style>',  '', html, flags=re.DOTALL | re.I)
        # HTML teglarini olib tashlash
        text = re.sub(r'<[^>]+>', ' ', html)
        # Ortiqcha bo'shliqlarni tozalash
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    # ════════════════════════════════════════════════════════════
    #  RSS O'QISH
    # ════════════════════════════════════════════════════════════

    async def _sync_rss(self, src: dict) -> int:
        """RSS/Atom xabar oqimidan yangi maqolalar olish"""
        added = 0
        async with aiohttp.ClientSession() as session:
            async with session.get(src["url"],
                                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                xml = await r.text(errors="replace")

        # Oddiy XML parse
        items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
        items += re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)

        for item in items[:10]:  # Oxirgi 10 ta
            title   = re.search(r'<title[^>]*>(.*?)</title>', item, re.DOTALL)
            desc    = re.search(r'<description[^>]*>(.*?)</description>', item, re.DOTALL)
            content = re.search(r'<content[^>]*>(.*?)</content>', item, re.DOTALL)

            title_t = self._html_to_text(title.group(1)) if title else "Sarlavhasiz"
            body_t  = self._html_to_text(
                (content or desc).group(1) if (content or desc) else ""
            )

            if len(body_t) < 50:
                continue

            if self.kb:
                await self.kb.add_document(
                    title    = title_t[:200],
                    content  = body_t[:2000],
                    category = src["category"],
                    tags     = src["label"],
                    source   = f"rss:{src['url']}"
                )
                added += 1

        return added

    # ════════════════════════════════════════════════════════════
    #  AI BILAN BILIM AJRATISH
    # ════════════════════════════════════════════════════════════

    async def _extract_knowledge(self, raw_text: str,
                                  filename: str, category: str) -> dict | None:
        """
        AI yordamida xom matndan strukturalangan bilim ajratish.
        Texnik emas matnlarni filtrlaydi.
        """
        prompt = (
            f"Quyidagi matnni tahlil qil va FAQAT JSON qaytар:\n\n"
            f"Fayl: {filename}\nMatn:\n{raw_text[:2000]}\n\n"
            "Agar matn texnik yoki foydali bo'lsa:\n"
            '{"useful":true,"title":"sarlavha","content":"asosiy texnik mazmun",'
            '"tags":"kalit so\'zlar"}\n\n'
            "Agar matn texnik emas, reklama, yoki foydasiz bo'lsa:\n"
            '{"useful":false}'
        )
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600, temperature=0.1
            )
            raw = resp.choices[0].message.content
            data = json.loads(re.sub(r'```json|```', '', raw).strip())
            if not data.get("useful", False):
                return None
            return data
        except Exception as e:
            log.warning(f"Extract xatosi: {e}")
            # Fallback: xom matnni to'g'ridan qo'sh
            return {
                "title":   filename.replace("-", " ").replace("_", " ")[:100],
                "content": raw_text[:2000],
                "tags":    category
            }

    # ════════════════════════════════════════════════════════════
    #  YORDAMCHI
    # ════════════════════════════════════════════════════════════

    async def _update_synced(self, source_id: int, added: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE learn_sources SET last_synced=?, doc_count=doc_count+? WHERE id=?",
                (datetime.now().isoformat(), added, source_id)
            )
            await db.commit()

    async def _log(self, source_id: int, status: str, docs: int, error: str = ""):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO learn_log (source_id, status, docs_added, error) VALUES (?,?,?,?)",
                (source_id, status, docs, error)
            )
            await db.commit()

    async def get_stats(self) -> str:
        """AutoLearner holati — Telegram uchun"""
        sources = await self.list_sources()
        if not sources:
            return (
                "🤖 *AutoLearner holati:*\n\n"
                "📭 Hech qanday manba yo'q.\n\n"
                "Qo'shish uchun:\n"
                "`Manba qo'sh: github https://github.com/owner/repo`\n"
                "`Manba qo'sh: web https://sayt.com/sahifa`"
            )

        lines = ["🤖 *AutoLearner manbalar:*\n"]
        for s in sources:
            st   = "✅" if s["enabled"] else "⏸"
            sync = s["last_synced"][:10] if s["last_synced"] else "hali yo'q"
            lines.append(
                f"{st} *#{s['id']}* `{s['type']}` — {s['label']}\n"
                f"   📂 {s['category']} | 📄 {s['doc_count']} ta | 🕐 {sync}"
            )

        lines.append(
            f"\n⏱ Interval: har *{LEARN_INTERVAL_H}* soatda avtomatik\n"
            "\n`/learn_sync` — hozir sinxronlash\n"
            "`/learn_sources` — ro'yxat"
        )
        return "\n".join(lines)
