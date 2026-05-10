"""
Analytics Service — Trend tahlili, prognozlar va metrikalar
MBF-3 uchun ilg'or analitika moduli
"""

import os
import logging
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
import aiosqlite

log = logging.getLogger(__name__)


class AnalyticsService:
    """Uskunalar trend tahlili, prognozlar va samaradorlik metrikalari"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("DB_PATH", "ai_agent.db")

    async def get_sensor_trend(self, equipment_id: str, sensor_type: str,
                                days: int = 30) -> dict:
        """
        Vibratsiya/harorat/bosim trendini tahlil qilish
        sensor_type: 'vibration', 'temperature', 'pressure'
        """
        async with aiosqlite.connect(self.db_path) as db:
            # equipment_state jadvalidan ma'lumot olish
            cursor = await db.execute("""
                SELECT recorded_at, vibration, temperature, pressure
                FROM equipment_state
                WHERE equipment_id = ?
                AND recorded_at > datetime('now', ?)
                ORDER BY recorded_at ASC
            """, (equipment_id, f'-{days} days'))
            
            rows = await cursor.fetchall()
            
            if not rows:
                return {"error": f"{equipment_id} uchun ma'lumot topilmadi", "trend": "unknown"}
            
            values = []
            for row in rows:
                if sensor_type == 'vibration' and row[1] is not None:
                    values.append(row[1])
                elif sensor_type == 'temperature' and row[2] is not None:
                    values.append(row[2])
                elif sensor_type == 'pressure' and row[3] is not None:
                    values.append(row[3])
            
            if len(values) < 3:
                return {"error": "Trend uchun ma'lumot yetarli emas", "trend": "unknown"}
            
            # Trendni hisoblash (oddiy regressiya)
            x = list(range(len(values)))
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(i * i for i in x)
            
            if n * sum_x2 - sum_x * sum_x != 0:
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            else:
                slope = 0
            
            # Trend yo'nalishi
            if slope > 0.05:
                trend = "yomonlashmoqda 📈"
                advice = "⚠️ Parametr yomonlashmoqda, tez orada tekshirish kerak!"
            elif slope < -0.05:
                trend = "yaxshilanmoqda 📉"
                advice = "✅ Yaxshi tendentsiya, monitoringni davom ettiring"
            else:
                trend = "barqaror ➡️"
                advice = "💚 Parametr barqaror, normal ishlash davom etmoqda"
            
            # Prognoz
            last_value = values[-1] if values else 0
            change_rate = slope / (max(values) if max(values) > 0 else 1) * 100
            
            return {
                "trend": trend,
                "slope": round(slope, 3),
                "last_value": round(last_value, 2),
                "change_rate": round(change_rate, 1),
                "data_points": len(values),
                "advice": advice
            }

    async def predict_failure_probability(self, equipment_id: str) -> dict:
        """
        Uskunaning ishdan chiqish ehtimolini prognoz qilish
        Vibratsiya va harorat ma'lumotlariga asoslangan
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT vibration, temperature, pressure, recorded_at
                FROM equipment_state
                WHERE equipment_id = ?
                ORDER BY recorded_at DESC
                LIMIT 20
            """, (equipment_id,))
            
            rows = await cursor.fetchall()
            
            if len(rows) < 5:
                return {
                    "probability": "unknown",
                    "estimated_days": None,
                    "critical_params": [],
                    "advice": "Etarli ma'lumot yo'q, kamida 5 ta o'lchash kerak"
                }
            
            # Chegaraviy qiymatlar (MBF-3 uchun)
            VIB_WARN = 4.5
            VIB_CRIT = 7.1
            TEMP_WARN = 75
            TEMP_CRIT = 90
            
            warnings = 0
            criticals = 0
            trends = []
            
            for row in rows[:10]:
                vib, temp, press, _ = row
                if vib is not None:
                    if vib >= VIB_CRIT:
                        criticals += 1
                    elif vib >= VIB_WARN:
                        warnings += 1
                if temp is not None:
                    if temp >= TEMP_CRIT:
                        criticals += 1
                    elif temp >= TEMP_WARN:
                        warnings += 1
            
            total_checks = len(rows[:10]) * 2  # vib + temp
            critical_ratio = criticals / total_checks if total_checks > 0 else 0
            warning_ratio = (warnings + criticals) / total_checks if total_checks > 0 else 0
            
            # Ehtimollik hisobi
            if critical_ratio > 0.3:
                probability = "YUQORI 🔴"
                estimated_days = 1
                advice = "🚨 DARHOL CHORA KO'RING! Uskuna istalgan vaqtda ishdan chiqishi mumkin!"
            elif critical_ratio > 0.1 or warning_ratio > 0.5:
                probability = "O'RTA 🟡"
                estimated_days = 7
                advice = "⚠️ Diqqat! 1 hafta ichida ta'mirlash rejalashtirilsin"
            elif warning_ratio > 0.2:
                probability = "PAST 🟢"
                estimated_days = 30
                advice = "🔧 Normal monitoring, PPR doirasida tekshirish yetarli"
            else:
                probability = "JUDA PAST ✅"
                estimated_days = 90
                advice = "💚 Uskuna yaxshi holatda, normal ishlash davom etmoqda"
            
            return {
                "probability": probability,
                "estimated_days": estimated_days,
                "critical_params": self._get_critical_params(rows),
                "advice": advice
            }

    def _get_critical_params(self, rows: list) -> list:
        """Kritik parametrlar ro'yxati"""
        critical = []
        for row in rows[:5]:
            vib, temp, press, _ = row
            if vib is not None and vib > 7.1:
                critical.append(f"Vibratsiya {vib} mm/s")
            if temp is not None and temp > 90:
                critical.append(f"Harorat {temp}°C")
            if press is not None and press < 0.5:
                critical.append(f"Bosim {press} bar (past)")
        return list(set(critical))

    async def get_performance_metrics(self, days: int = 7) -> dict:
        """
        Ish samaradorligi metrikalari:
        - Nechta muammo hal qilindi
        - O'rtacha reaktsiya vaqti
        - Eng ko'p takrorlanadigan nosozliklar
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Xabarlar soni
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor = await db.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE direction = 'in' AND created_at > ?
            """, (cutoff,))
            total_issues = (await cursor.fetchone())[0]
            
            # Bajarilgan vazifalar
            cursor = await db.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE status = 'done' AND updated_at > ?
            """, (cutoff,))
            solved = (await cursor.fetchone())[0]
            
            # Eng ko'p takrorlanadigan nosozliklar
            stats = await self._get_problem_frequency(days)
            
            return {
                "total_issues": total_issues,
                "solved": solved,
                "resolution_rate": round(solved / total_issues * 100, 1) if total_issues > 0 else 0,
                "top_problems": stats[:5] if stats else [],
                "days": days
            }

    async def _get_problem_frequency(self, days: int) -> list:
        """Eng ko'p uchraydigan nosozliklar"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT content FROM messages 
                WHERE direction = 'in' AND type = 'text' AND created_at > ?
            """, (cutoff,))
            
            rows = await cursor.fetchall()
            
            problem_keywords = {
                'nasos': ['nasos', 'pompa', 'slurry'],
                'kompressor': ['kompressor', 'havo'],
                'konveyer': ['konveyer', 'lenta', 'rolik'],
                'tegirmon': ['tegirmon', 'mill', 'sag'],
                'vibratsiya': ['vibratsiya', 'tebranish'],
                'harorat': ['harorat', 'qizib'],
                'oqish': ['oqish', 'sizib', 'muhr'],
                'elektr': ['elektr', 'motor', 'dvigatel']
            }
            
            freq = defaultdict(int)
            
            for row in rows:
                text = row[0].lower()
                for category, keywords in problem_keywords.items():
                    for kw in keywords:
                        if kw in text:
                            freq[category] += 1
                            break
            
            # Saralash
            sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            return [{"problem": k, "count": v} for k, v in sorted_freq]

    async def get_energy_anomaly(self, equipment_id: str, current_power: float) -> dict:
        """
        Energiya sarfi anomaliyasini aniqlash
        current_power: joriy quvvat (kW)
        """
        # Nominal quvvat ma'lumotlari
        nominal_power = {
            'nasos_1': 75, 'nasos_2': 110, 'nasos_3': 55,
            'tegirmon_1': 2800, 'tegirmon_2': 2200,
            'kompressor_1': 160,
            'konveyer_1': 45, 'konveyer_2': 30
        }
        
        nom = nominal_power.get(equipment_id, 50)
        
        if current_power > nom * 1.2:
            anomaly = "YUQORI 🔴"
            advice = f"Quvvat iste'moli {current_power} kW (norma: {nom} kW). Uskunada tiqilish yoki mexanik muammo bo'lishi mumkin!"
            status = "critical"
        elif current_power > nom * 1.1:
            anomaly = "O'RTA 🟡"
            advice = f"Quvvat iste'moli me'yordan {round((current_power/nom-1)*100)}% yuqori. Tekshirish tavsiya etiladi."
            status = "warning"
        elif current_power < nom * 0.7:
            anomaly = "PAST 🟡"
            advice = f"Quvvat iste'moli me'yordan past ({current_power} kW). Yuklama kam yoki uskuna to'liq ishlamayapti?"
            status = "warning"
        else:
            anomaly = "NORMAL ✅"
            advice = "Energiya sarfi me'yor doirasida"
            status = "normal"
        
        return {
            "anomaly": anomaly,
            "current_kw": round(current_power, 1),
            "nominal_kw": nom,
            "deviation_percent": round((current_power / nom - 1) * 100, 1),
            "advice": advice,
            "status": status
        }