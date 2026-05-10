"""
Incident Logger — Hodisalarni qayd qilish
"""

import os
import re
import logging
import aiosqlite
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")


class IncidentLogger:
    """Hodisalarni qayd qilish va tahlil qilish"""

    INCIDENT_TYPES = {
        "mechanical": "🔧 Mexanik nosozlik",
        "electrical": "⚡ Elektr nosozligi",
        "safety": "🦺 Xavfsizlik buzilishi",
        "injury": "🚑 Jarohat",
        "fire": "🔥 Yong'in",
        "other": "📋 Boshqa"
    }

    def __init__(self):
        self.db_path = DB_PATH

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_number TEXT,
                    incident_type TEXT,
                    description TEXT,
                    equipment TEXT,
                    location TEXT,
                    severity TEXT DEFAULT 'medium',
                    reported_by TEXT,
                    happened_at TIMESTAMP,
                    status TEXT DEFAULT 'open'
                );
                CREATE TABLE IF NOT EXISTS incident_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id INTEGER,
                    action_text TEXT,
                    performed_by TEXT,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

    async def log_incident(self, text: str, reported_by: str = "O'tkirbek") -> dict:
        text_lower = text.lower()
        incident_type = "other"
        type_mapping = {
            "nosozlik": "mechanical", "buzildi": "mechanical", "to'xtadi": "mechanical",
            "elektr": "electrical", "tok": "electrical",
            "xavfsizlik": "safety", "qoidabuzarlik": "safety",
            "jarohat": "injury", "qon": "injury",
            "yong'in": "fire", "olov": "fire"
        }
        for kw, itype in type_mapping.items():
            if kw in text_lower:
                incident_type = itype
                break

        equipment_match = re.search(r'([A-Za-z0-9_\-]+(?:nasos|kompressor|konveyer|tegirmon|PP-\d+))', text, re.I)
        equipment = equipment_match.group(1) if equipment_match else ""

        if any(w in text_lower for w in ['kritik', 'avaria', 'jarohat', 'yong\'in']):
            severity = "critical"
        else:
            severity = "medium"

        incident_number = f"INC-{datetime.now().strftime('%Y%m%d')}-{equipment[:3] if equipment else 'GEN'}"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO incidents (incident_number, incident_type, description, equipment, severity, reported_by, happened_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (incident_number, incident_type, text[:500], equipment, severity, reported_by, datetime.now().isoformat()))
            incident_id = cursor.lastrowid
            await db.commit()

        response = f"""📋 *HODISAV QAYD ETILDI*
🔢 Raqam: {incident_number}
📌 Turi: {self.INCIDENT_TYPES.get(incident_type, 'Boshqa')}
⚙️ Uskuna: {equipment or '—'}
🚨 Daraja: {'🔴 KRITIK' if severity == 'critical' else '🟡 O\'RTA'}
📅 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📝 *Tavsif:* {text[:300]}"""
        return {"incident_id": incident_id, "incident_number": incident_number, "message": response}

    async def add_action(self, incident_id: int, action_text: str, performed_by: str = "O'tkirbek") -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO incident_actions (incident_id, action_text, performed_by)
                VALUES (?, ?, ?)
            """, (incident_id, action_text, performed_by))
            await db.commit()
        return {"success": True, "message": f"✅ Hodisa #{incident_id} ga chora qo'shildi"}

    async def get_recent_incidents(self, limit: int = 10) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, incident_number, incident_type, description, severity, happened_at
                FROM incidents ORDER BY happened_at DESC LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
        if not rows:
            return "📋 Qayd etilgan hodisalar yo'q."
        lines = ["📋 *HODISALAR JURNALI*\n"]
        for row in rows:
            severity_emoji = "🔴" if row[4] == "critical" else "🟡"
            lines.append(f"{severity_emoji} *{row[1]}* — {row[2]}\n   {row[5][:16]} | {row[3][:60]}\n")
        return "\n".join(lines)

    async def get_incident_stats(self, days: int = 30) -> dict:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM incidents WHERE happened_at > ?", (cutoff,))
            total = (await cursor.fetchone())[0]
            cursor = await db.execute("""
                SELECT incident_type, COUNT(*) FROM incidents WHERE happened_at > ? GROUP BY incident_type
            """, (cutoff,))
            types = await cursor.fetchall()
        return {"total": total, "by_type": {self.INCIDENT_TYPES.get(t, t): c for t, c in types}}