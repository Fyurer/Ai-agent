"""
Digital Twin — Raqamli Egizak Moduli
O'tkirbekning barcha uskunalari holati real vaqtda kuzatish,
trend tahlili, prognoz va avtomatik ogohlantirishlar.
"""

import os
import json
import logging
import aiosqlite
from datetime import datetime, timedelta
from groq import Groq

log = logging.getLogger(__name__)
DB_PATH    = os.getenv("DB_PATH", "ai_agent.db")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ── MBF-3 Uskuna ro'yxati ─────────────────────────────────────
MBF3_EQUIPMENT_REGISTRY = {
    "nasos_1":  {"name": "Slurry nasos №1 (Warman 8/6 AH)", "group": "nasos",  "hall": "1"},
    "nasos_2":  {"name": "Slurry nasos №2 (Warman 10/8 AH)","group": "nasos",  "hall": "1"},
    "nasos_3":  {"name": "Alimentatsiya nasosi №3",          "group": "nasos",  "hall": "2"},
    "tegirmon_1":{"name": "SAG tegirmon №1 (GMD/ABB)",       "group": "tegirmon","hall": "3"},
    "tegirmon_2":{"name": "Shar tegirmon №2",                "group": "tegirmon","hall": "3"},
    "flotatsiya_1":{"name": "Flotatsiya №1 (Outotec 50m³)", "group": "flotatsiya","hall": "4"},
    "flotatsiya_2":{"name": "Flotatsiya №2",                 "group": "flotatsiya","hall": "4"},
    "kompressor_1":{"name": "Havo kompressor №1 (Atlas Copco)","group": "kompressor","hall": "5"},
    "konveyer_1":{"name": "Konveyer №1 (ruda transport)",   "group": "konveyer","hall": "0"},
    "konveyer_2":{"name": "Konveyer №2 (kontsentrat)",      "group": "konveyer","hall": "0"},
}

# ── Holat ranglari ────────────────────────────────────────────
STATUS_EMOJI = {
    "running":   "🟢",
    "warning":   "🟡",
    "critical":  "🔴",
    "stopped":   "⚫",
    "maintenance":"🔧",
    "unknown":   "⚪",
}


class DigitalTwin:
    """MBF-3 uskunalarining raqamli egizagi"""

    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def init(self, db_conn=None):
        """Jadvallarni yaratish"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS equipment_state (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_id TEXT NOT NULL,
                    status      TEXT DEFAULT 'unknown',
                    vibration   REAL,
                    temperature REAL,
                    pressure    REAL,
                    runtime_h   REAL DEFAULT 0,
                    notes       TEXT,
                    recorded_by TEXT DEFAULT 'manual',
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS equipment_events (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_id TEXT NOT NULL,
                    event_type   TEXT,
                    description  TEXT,
                    severity     TEXT DEFAULT 'info',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS maintenance_log (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_id TEXT NOT NULL,
                    work_type    TEXT,
                    description  TEXT,
                    parts_used   TEXT,
                    performed_by TEXT DEFAULT 'O'\''tkirbek',
                    duration_h   REAL,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()
        log.info("✅ DigitalTwin jadvallar tayyor")

    # ── Holat yangilash ───────────────────────────────────────
    async def update_state(self, equipment_id: str,
                            status: str = None,
                            vibration: float = None,
                            temperature: float = None,
                            pressure: float = None,
                            runtime_h: float = None,
                            notes: str = "") -> str:
        """Uskuna holatini yangilash va tekshirish"""
        eq_info = MBF3_EQUIPMENT_REGISTRY.get(
            equipment_id,
            {"name": equipment_id, "group": "unknown", "hall": "?"}
        )

        # Avtomatik status aniqlash (sensor qiymatlari bo'yicha)
        auto_status = self._auto_status(equipment_id, vibration, temperature, pressure)
        final_status = status or auto_status

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO equipment_state
                   (equipment_id, status, vibration, temperature, pressure, runtime_h, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (equipment_id, final_status, vibration, temperature,
                 pressure, runtime_h, notes)
            )

            # Kritik hodisani event log ga yozish
            if final_status == "critical":
                await db.execute(
                    """INSERT INTO equipment_events
                       (equipment_id, event_type, description, severity)
                       VALUES (?,?,?,?)""",
                    (equipment_id, "critical_state",
                     f"Vib:{vibration} T:{temperature} P:{pressure}", "critical")
                )
            await db.commit()

        emoji = STATUS_EMOJI.get(final_status, "⚪")
        result = [
            f"{emoji} *{eq_info['name']}* — Holat yangilandi",
            f"Status: *{final_status.upper()}*",
        ]
        if vibration is not None:
            result.append(f"📳 Vibratsiya: {vibration} mm/s")
        if temperature is not None:
            result.append(f"🌡 Harorat: {temperature}°C")
        if pressure is not None:
            result.append(f"📊 Bosim: {pressure} bar")
        if runtime_h is not None:
            result.append(f"⏱ Ishlash vaqti: {runtime_h} soat")
        if notes:
            result.append(f"📝 Izoh: {notes}")

        # Kritik bo'lsa ogohlantirish
        if final_status == "critical":
            result.append("\n🚨 *DARHOL DIQQAT! Kritik holat aniqlandi!*")
        elif final_status == "warning":
            result.append("\n⚠️ _Diqqat talab qiladigan parametrlar mavjud_")

        return "\n".join(result)

    def _auto_status(self, eq_id: str, vib=None, temp=None, press=None) -> str:
        """Sensor qiymatlari asosida avtomatik status"""
        eq_group = MBF3_EQUIPMENT_REGISTRY.get(eq_id, {}).get("group", "default")

        vib_limits  = {"nasos": (4.5, 7.1), "tegirmon": (7.1, 11.2)}.get(eq_group, (4.5, 7.1))
        temp_limits = {"tegirmon": (80, 100)}.get(eq_group, (75, 90))

        is_crit = (
            (vib  is not None and vib  >= vib_limits[1]) or
            (temp is not None and temp >= temp_limits[1])
        )
        is_warn = (
            (vib  is not None and vib  >= vib_limits[0]) or
            (temp is not None and temp >= temp_limits[0])
        )

        if is_crit: return "critical"
        if is_warn: return "warning"
        if any(x is not None for x in [vib, temp, press]):
            return "running"
        return "unknown"

    # ── Dashboard ─────────────────────────────────────────────
    async def get_dashboard(self) -> str:
        """Barcha uskunalar holati — bir ko'rinishda"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Har bir uskuna uchun oxirgi holat
            cursor = await db.execute(
                """SELECT equipment_id, status, vibration, temperature,
                          pressure, runtime_h, recorded_at
                   FROM equipment_state
                   WHERE id IN (
                       SELECT MAX(id) FROM equipment_state
                       GROUP BY equipment_id
                   )
                   ORDER BY equipment_id"""
            )
            rows = await cursor.fetchall()

        if not rows:
            return "📊 *MBF-3 Dashboard*\n\n_Hali hech qanday ma'lumot kiritilmagan_\n\nBiror uskunaning holatini yangilang."

        lines = [
            f"📊 *MBF-3 Digital Twin Dashboard*",
            f"_{datetime.now().strftime('%d.%m.%Y %H:%M')}_\n"
        ]

        by_hall = {}
        for row in rows:
            eq_id, status, vib, temp, press, runtime, rec_at = row
            eq_info = MBF3_EQUIPMENT_REGISTRY.get(eq_id, {"name": eq_id, "hall": "?"})
            hall = eq_info["hall"]
            if hall not in by_hall:
                by_hall[hall] = []
            by_hall[hall].append({
                "id": eq_id, "name": eq_info["name"],
                "status": status, "vib": vib, "temp": temp,
                "press": press, "runtime": runtime, "rec_at": rec_at
            })

        # Ro'yxatga kiritilmagan uskunalar
        registered_ids = {r[0] for r in rows}
        for eq_id, eq_info in MBF3_EQUIPMENT_REGISTRY.items():
            if eq_id not in registered_ids:
                hall = eq_info["hall"]
                if hall not in by_hall:
                    by_hall[hall] = []
                by_hall[hall].append({
                    "id": eq_id, "name": eq_info["name"],
                    "status": "unknown", "vib": None, "temp": None,
                    "press": None, "runtime": None, "rec_at": None
                })

        hall_names = {"0": "🏗 Konveyer", "1": "🏛 1-zal (Nasos)",
                       "2": "🏛 2-zal (Nasos)", "3": "🏭 3-zal (Tegirmon)",
                       "4": "⚗️ 4-zal (Flotatsiya)", "5": "💨 5-zal (Kompressor)"}

        criticals = []
        for hall, eqs in sorted(by_hall.items()):
            hall_label = hall_names.get(hall, f"Zal {hall}")
            lines.append(f"\n*{hall_label}:*")
            for e in sorted(eqs, key=lambda x: x["name"]):
                emoji = STATUS_EMOJI.get(e["status"], "⚪")
                params = []
                if e["vib"]  is not None: params.append(f"V:{e['vib']:.1f}")
                if e["temp"] is not None: params.append(f"T:{e['temp']:.0f}°C")
                if e["press"]is not None: params.append(f"P:{e['press']:.1f}bar")
                param_str = f" `{', '.join(params)}`" if params else ""
                lines.append(f"  {emoji} {e['name']}{param_str}")
                if e["status"] == "critical":
                    criticals.append(e["name"])

        # Umumiy statistika
        status_counts = {}
        for row in rows:
            s = row[1] or "unknown"
            status_counts[s] = status_counts.get(s, 0) + 1

        lines.append(f"\n{'─'*30}")
        lines.append(
            f"🟢 {status_counts.get('running',0)} | "
            f"🟡 {status_counts.get('warning',0)} | "
            f"🔴 {status_counts.get('critical',0)} | "
            f"🔧 {status_counts.get('maintenance',0)} | "
            f"⚫ {status_counts.get('stopped',0)}"
        )

        if criticals:
            lines.append(f"\n🚨 *KRITIK:* {', '.join(criticals)}")

        return "\n".join(lines)

    # ── Ta'mirlash logi ───────────────────────────────────────
    async def add_maintenance_log(self, equipment_id: str,
                                   work_type: str,
                                   description: str,
                                   parts_used: str = "",
                                   duration_h: float = None) -> str:
        """Ta'mirlash ishini qayd qilish"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO maintenance_log
                   (equipment_id, work_type, description, parts_used, duration_h)
                   VALUES (?,?,?,?,?)""",
                (equipment_id, work_type, description, parts_used, duration_h)
            )
            # Status ni "running" ga o'zgartirish (ta'mirdan keyin)
            await db.execute(
                """INSERT INTO equipment_state (equipment_id, status, notes)
                   VALUES (?,?,?)""",
                (equipment_id, "running", f"Ta'mirlash tugadi: {work_type}")
            )
            await db.commit()

        eq_name = MBF3_EQUIPMENT_REGISTRY.get(equipment_id, {}).get("name", equipment_id)
        return (
            f"✅ *Ta'mirlash qayd qilindi*\n\n"
            f"⚙️ {eq_name}\n"
            f"🔧 Turi: {work_type}\n"
            f"📝 {description}\n"
            f"{f'🔩 Ehtiyot qism: {parts_used}' if parts_used else ''}\n"
            f"{f'⏱ Davomiyligi: {duration_h} soat' if duration_h else ''}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    async def get_equipment_history(self, equipment_id: str, limit: int = 10) -> str:
        """Uskuna tarixi"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT status, vibration, temperature, pressure, notes, recorded_at
                   FROM equipment_state
                   WHERE equipment_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (equipment_id, limit)
            )
            rows = await cursor.fetchall()

        if not rows:
            return f"❓ '{equipment_id}' uchun ma'lumot topilmadi."

        eq_name = MBF3_EQUIPMENT_REGISTRY.get(equipment_id, {}).get("name", equipment_id)
        lines = [f"📈 *{eq_name} — Holat tarixi*\n"]
        for r in rows:
            status, vib, temp, press, notes, rec_at = r
            emoji = STATUS_EMOJI.get(status, "⚪")
            parts = []
            if vib:  parts.append(f"V:{vib:.1f}")
            if temp: parts.append(f"T:{temp:.0f}°C")
            if press:parts.append(f"P:{press:.1f}b")
            date_s = rec_at[:16] if rec_at else "?"
            param_s = f" [{', '.join(parts)}]" if parts else ""
            note_s  = f" — {notes[:40]}" if notes else ""
            lines.append(f"{emoji} {date_s}{param_s}{note_s}")

        return "\n".join(lines)

    async def get_ai_prediction(self, equipment_id: str) -> str:
        """AI orqali uskuna holatini prognoz qilish"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT status, vibration, temperature, pressure, runtime_h, recorded_at
                   FROM equipment_state
                   WHERE equipment_id = ?
                   ORDER BY id DESC LIMIT 20""",
                (equipment_id,)
            )
            rows = await cursor.fetchall()

        if not rows:
            return f"❓ '{equipment_id}' uchun etarli ma'lumot yo'q (kamida 3 ta o'lchash kerak)."

        eq_name = MBF3_EQUIPMENT_REGISTRY.get(equipment_id, {}).get("name", equipment_id)

        # Ma'lumotlarni formatlash
        data_str = "\n".join(
            f"{r[5][:16]}: status={r[0]}, vib={r[1]}, temp={r[2]}, press={r[3]}, runtime={r[4]}h"
            for r in rows
        )

        prompt = f"""Sen sanoat uskunalari diagnostic ekspertisan.
Uskuna: {eq_name}

Oxirgi {len(rows)} ta o'lchash natijasi:
{data_str}

O'zbek tilida qisqa prognoz ber:
1. Joriy holat bahosi
2. Trend (yaxshilanmoqda / barqaror / yomonlashmoqda)
3. Avariyagacha taxminiy vaqt (agar trend yomon bo'lsa)
4. Tavsiya etiladigan chora va muddat
5. Ta'mirlash turi: joriy (TO-1) / rejalashtirilgan (TO-2) / kapital"""

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3
            )
            answer = resp.choices[0].message.content
            return f"🤖 *AI Prognoz — {eq_name}*\n\n{answer}"
        except Exception as e:
            return f"❌ AI prognoz xatosi: {e}"

    def get_equipment_list(self) -> str:
        """Uskuna ID va nomlari ro'yxati"""
        lines = ["⚙️ *MBF-3 Uskunalar ro'yxati:*\n"]
        current_group = ""
        for eq_id, info in sorted(MBF3_EQUIPMENT_REGISTRY.items(),
                                   key=lambda x: (x[1]["group"], x[0])):
            if info["group"] != current_group:
                group_emoji = {"nasos":"🔩","tegirmon":"⚙️","flotatsiya":"⚗️",
                                "kompressor":"💨","konveyer":"🏗"}.get(info["group"],"•")
                lines.append(f"\n{group_emoji} *{info['group'].upper()}:*")
                current_group = info["group"]
            lines.append(f"  `{eq_id}` — {info['name']}")
        lines.append("\n_Yangilash: `Holat: nasos_1, vib=3.2, temp=65`_")
        return "\n".join(lines)
