"""
Spare Parts Service — Ehtiyot qismlar hisobi va resurs kalkulyatori
"""

import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)


class SparePartsService:
    """Ehtiyot qismlar resursini hisoblash va zayavka generatori"""

    # Standart ehtiyot qismlar ma'lumotlari
    STANDARD_PARTS = {
        "podshipnik_6310": {
            "name": "Podshipnik 6310 (sharsimon)",
            "life_hours": 12000,
            "equipment": ["nasos", "motor"],
            "code": "SKF 6310"
        },
        "podshipnik_6312": {
            "name": "Podshipnik 6312 (sharsimon)",
            "life_hours": 14000,
            "equipment": ["nasos", "kompressor"],
            "code": "SKF 6312"
        },
        "salnik_45x62x8": {
            "name": "Salnik 45x62x8",
            "life_hours": 4000,
            "equipment": ["nasos"],
            "code": "NBR 45-62-8"
        },
        "muhr_nasos": {
            "name": "Mexanik muhr (Warman)",
            "life_hours": 5000,
            "equipment": ["nasos", "slurry_pump"],
            "code": "WARM-MECH-01"
        },
        "lenta_konveyer": {
            "name": "Konveyer lentasi EP-800",
            "life_hours": 25000,
            "equipment": ["konveyer"],
            "code": "EP800-1000"
        },
        "rolik_konveyer": {
            "name": "Konveyer roligi D=108mm",
            "life_hours": 8000,
            "equipment": ["konveyer"],
            "code": "ROLL-108"
        },
        "filtr_hp": {
            "name": "Gidravlik filtr (HP)",
            "life_hours": 2000,
            "equipment": ["gidravlik", "nasos"],
            "code": "HP-FILTER-01"
        },
        "liner_tegirmon": {
            "name": "Tegirmon liner (Mn13Cr2)",
            "life_hours": 10000,
            "equipment": ["tegirmon", "mill"],
            "code": "ML-13Cr2"
        }
    }

    def calculate_remaining_life(self, part_name: str, daily_hours: float, current_hours: float = 0) -> dict:
        """
        Ehtiyot qism qolgan resursini hisoblash
        
        part_name: ehtiyot qism nomi
        daily_hours: sutkalik ishlash soati (masalan 16 soat)
        current_hours: hozirgi foydalanish soati
        """
        part_info = None
        for key, info in self.STANDARD_PARTS.items():
            if part_name.lower() in key.lower() or part_name.lower() in info["name"].lower():
                part_info = info
                break
        
        if not part_info:
            return {
                "found": False,
                "message": f"'{part_name}' ma'lumotlar bazasida topilmadi"
            }
        
        total_life = part_info["life_hours"]
        remaining = max(0, total_life - current_hours)
        
        if daily_hours > 0:
            remaining_days = remaining / daily_hours
        else:
            remaining_days = 0
        
        # Xulosa
        if remaining <= 0:
            status = "🔴 ACIlGAN"
            advice = "Darhol almashtirish kerak!"
        elif remaining < total_life * 0.2:
            status = "🟡 OXIRGI"
            advice = f"{remaining_days:.0f} kundan keyin almashtirish tavsiya etiladi"
        elif remaining < total_life * 0.5:
            status = "🟢 OK"
            advice = "Normal, monitoring davom etsin"
        else:
            status = "✅ YAXSHI"
            advice = "Resurs yetarli"
        
        return {
            "found": True,
            "part_name": part_info["name"],
            "part_code": part_info["code"],
            "total_life_hours": total_life,
            "current_hours": current_hours,
            "remaining_hours": round(remaining, 1),
            "remaining_days": round(remaining_days, 1) if daily_hours > 0 else None,
            "status": status,
            "advice": advice
        }

    def generate_request(self, equipment: str, part_name: str, quantity: int, reason: str = "") -> str:
        """
        Rasmiy zayavka (ariza) matnini tayyorlash
        """
        today = datetime.now().strftime("%d.%m.%Y")
        
        request_text = f"""📋 *ARIZA (ZAYAVKA)*
━━━━━━━━━━━━━━━━━━━━━━━
Sana: {today}
Ariza raqami: A-{datetime.now().strftime('%Y%m%d')}-{equipment[:3]}

Kimga: Ombor mudiri
Kimdan: O'tkirbek, 3-MBF mexanigi

🎯 *Mavzu:* {part_name} yetkazib berish

⚙️ *Uskuna:* {equipment}
🔩 *Ehtiyot qism:* {part_name}
📦 *Miqdor:* {quantity} dona

📝 *Sabab:*
{reason if reason else "Rejali ta'mirlash uchun kerak"}

📅 *Zaruriyat muddati:* {datetime.now().strftime("%d.%m.%Y")}

✍️ *Mexanik:* O'tkirbek
━━━━━━━━━━━━━━━━━━━━━━━
"""
        return request_text

    async def get_part_by_equipment(self, equipment_type: str) -> list:
        """Uskuna turiga mos ehtiyot qismlar ro'yxati"""
        matching_parts = []
        equipment_lower = equipment_type.lower()
        
        for key, info in self.STANDARD_PARTS.items():
            for eq in info["equipment"]:
                if eq in equipment_lower or equipment_lower in eq:
                    matching_parts.append({
                        "key": key,
                        "name": info["name"],
                        "code": info["code"],
                        "life_hours": info["life_hours"]
                    })
                    break
        
        return matching_parts