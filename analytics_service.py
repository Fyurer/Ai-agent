"""
Analytics Service — Trend tahlili va prognozlar
"""

import os
import logging
import aiosqlite
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")


class AnalyticsService:
    """Uskunalar trend tahlili"""

    def __init__(self):
        self.db_path = DB_PATH

    async def get_sensor_trend(self, equipment_id: str, sensor_type: str, days: int = 30) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
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
        if len(values) < 3:
            return {"error": "Trend uchun ma'lumot yetarli emas", "trend": "unknown"}

        x = list(range(len(values)))
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(i * i for i in x)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if n * sum_x2 - sum_x * sum_x != 0 else 0

        if slope > 0.05:
            trend = "yomonlashmoqda 📈"
            advice = "⚠️ Parametr yomonlashmoqda, tez orada tekshirish kerak!"
        elif slope < -0.05:
            trend = "yaxshilanmoqda 📉"
            advice = "✅ Yaxshi tendentsiya"
        else:
            trend = "barqaror ➡️"
            advice = "✅ Parametr barqaror"

        return {"trend": trend, "slope": round(slope, 3), "last_value": round(values[-1], 2) if values else 0, "advice": advice}

    async def predict_failure_probability(self, equipment_id: str) -> dict:
        return {"probability": "PAST 🟢", "estimated_days": None, "critical_params": [], "advice": "Ma'lumot yetarli emas"}

    async def get_performance_metrics(self, days: int = 7) -> dict:
        return {"total_issues": 0, "solved": 0, "resolution_rate": 0, "top_problems": [], "days": days}

    async def get_energy_anomaly(self, equipment_id: str, current_power: float) -> dict:
        nominal_power = {'nasos_1': 75, 'tegirmon_1': 2800, 'kompressor_1': 160}.get(equipment_id, 50)
        if current_power > nominal_power * 1.2:
            anomaly, advice = "YUQORI 🔴", f"Quvvat iste'moli me'yordan yuqori!"
        elif current_power > nominal_power * 1.1:
            anomaly, advice = "O'RTA 🟡", "Tekshirish tavsiya etiladi"
        else:
            anomaly, advice = "NORMAL ✅", "Energiya sarfi me'yor doirasida"
        return {"anomaly": anomaly, "current_kw": current_power, "nominal_kw": nominal_power, "deviation_percent": round((current_power/nominal_power-1)*100, 1), "advice": advice}