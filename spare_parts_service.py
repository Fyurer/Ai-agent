"""
Spare Parts Service — Ehtiyot qismlar hisobi
"""

import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)


class SparePartsService:
    """Ehtiyot qismlar resursini hisoblash"""

    STANDARD_PARTS = {
        "podshipnik_6310": {"name": "Podshipnik 6310 (sharsimon)", "life_hours": 12000, "code": "SKF 6310"},
        "podshipnik_6312": {"name": "Podshipnik 6312 (sharsimon)", "life_hours": 14000, "code": "SKF 6312"},
        "salnik_45x62x8": {"name": "Salnik 45x62x8", "life_hours": 4000, "code": "NBR 45-62-8"},
        "muhr_nasos": {"name": "Mexanik muhr (Warman)", "life_hours": 5000, "code": "WARM-MECH-01"}
    }

    def calculate_remaining_life(self, part_name: str, daily_hours: float, current_hours: float = 0) -> dict:
        part_info = None
        for key, info in self.STANDARD_PARTS.items():
            if part_name.lower() in key.lower() or part_name.lower() in info["name"].lower():
                part_info = info
                break
        if not part_info:
            return {"found": False, "message": f"'{part_name}' topilmadi"}

        total_life = part_info["life_hours"]
        remaining = max(0, total_life - current_hours)
        remaining_days = remaining / daily_hours if daily_hours > 0 else 0

        if remaining <= 0:
            status, advice = "🔴 ACIlGAN", "Darhol almashtirish kerak!"
        elif remaining < total_life * 0.2:
            status, advice = "🟡 OXIRGI", f"{remaining_days:.0f} kundan keyin almashtirish tavsiya etiladi"
        else:
            status, advice = "✅ YAXSHI", "Resurs yetarli"

        return {
            "found": True, "part_name": part_info["name"], "part_code": part_info["code"],
            "total_life_hours": total_life, "current_hours": current_hours,
            "remaining_hours": round(remaining, 1), "remaining_days": round(remaining_days, 1) if daily_hours > 0 else None,
            "status": status, "advice": advice
        }

    def generate_request(self, equipment: str, part_name: str, quantity: int, reason: str = "") -> str:
        today = datetime.now().strftime("%d.%m.%Y")
        return f"""📋 *ARIZA (ZAYAVKA)*
Sana: {today}
Kimga: Ombor mudiri
Kimdan: O'tkirbek, 3-MBF mexanigi

🎯 *Mavzu:* {part_name} yetkazib berish
⚙️ *Uskuna:* {equipment}
🔩 *Ehtiyot qism:* {part_name}
📦 *Miqdor:* {quantity} dona

📝 *Sabab:* {reason if reason else "Rejali ta'mirlash uchun kerak"}
✍️ *Mexanik:* O'tkirbek"""