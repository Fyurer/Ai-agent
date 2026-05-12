"""
Mechanic Service v2.0 — Mis boyitish fabrikasi mexanigi uchun
AGMK 3-MBF | Yangi funksiyalar:
  - Ehtiyot qismlar kalkulyatori
  - Ariza/Zayavka generatori
  - QR-kod integratsiyasi
  - Avariya ssenariysi simulyatori
  - Til tarjimoni (ABB/Metso hujjatlari)
  - Trend tahlili va prognoz
  - Energiya sarfi monitoringi
  - Ish samaradorligi metrikalari
"""

import os
import re
import logging
from datetime import datetime
from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

MECHANIC_SYSTEM_PROMPT = """Sen Olmaliq kon-metallurgiya kombinati 3-mis boyitish fabrikasidagi
mexanik O'tkirbekning AI yordamchisisan.
Sening vazifang:
- Sanoat uskunalari (nasoslar, kompressorlar, konveyerlar, tegirmonlar, flotatsiya mashinalar,
  separatorlar, kranlar, reduktorlar) haqida texnik ma'lumot berish
- Gidravlik va pnevmatik tizimlar hisobi
- Ta'mirlash va PPR (profilaktik ta'mirlash) bo'yicha maslahat
- Xavfsizlik talablari (OHSAS, GOST standartlari)
- Chertyo'j va sxemalar tahlili
- Defekt aktlari, xizmat xatlari, hisobotlar tuzish
- O'zbek va rus tillarida texnik terminologiya

Javoblarda:
- Aniq va qisqa bo'l
- Formulalar kerak bo'lsa ko'rsat
- GOST raqamlarini qo'sh (agar bilsang)
- Xavfsizlik ogohlantirishlarini unutma ⚠️
- Telegram Markdown (*bold*, _italic_) ishlatishingiz mumkin
"""

# ── Qurilma bazasi ─────────────────────────────────────────────
EQUIPMENT_DB = {
    "nasos": {
        "muammolar": [
            "1️⃣ Kaviatsiya — suv ta'minoti yetarli emas, kirish bosimi past",
            "2️⃣ Muhrlar yeyilgan — eje oqmoqda, almashtirish kerak",
            "3️⃣ Podshipniklar ishdan chiqqan — g'alati shovqin, harorat yuqori",
            "4️⃣ Impeller tiqilib qolgan — qattiq zarrachalar",
            "5️⃣ Motor elektr nosozligi — tok o'lchang",
            "6️⃣ Ventil yopiq — truboprovod tekshiring",
            "7️⃣ Havo kamerasi — sistemani purgatsiya qiling",
        ],
        "tekshirish": [
            "☑️ Kirish/chiqish bosimi (manometr)",
            "☑️ Harorat (termometr yoki IQ)",
            "☑️ Tebranish darajasi (vibrometr ≤4.5 mm/s)",
            "☑️ Elektr tok (ampermeter)",
            "☑️ Muhrlash holati (oqish yo'qmi)",
            "☑️ Moy sathi (yog' ko'rsatgichi)",
        ],
        "ppr": "Har 2000 soatda: moy almashtirish, podshipnik tekshirish\nHar 8000 soatda: to'liq demontaj va kapital ta'mirlash",
        "ehtiyot_qismlar": {
            "muhr (salnk)": {"resurs_soat": 4000, "birlik": "dona", "taxminiy_narx": "50-150 USD"},
            "podshipnik": {"resurs_soat": 8000, "birlik": "dona", "taxminiy_narx": "100-500 USD"},
            "impeller": {"resurs_soat": 6000, "birlik": "dona", "taxminiy_narx": "200-1000 USD"},
            "liner (voluta)": {"resurs_soat": 10000, "birlik": "dona", "taxminiy_narx": "500-2000 USD"},
            "hidravlik moy": {"resurs_soat": 2000, "birlik": "litr", "taxminiy_narx": "3-8 USD/l"},
        },
        "quvvat_kw": 75,   # o'rtacha quvvat
    },
    "kompressor": {
        "muammolar": [
            "1️⃣ Havo bosimi yetmayapti — filtr tiqilgan yoki klapan yeyilgan",
            "2️⃣ Haddan tashqari qizish — sovutish tizimi nosoz",
            "3️⃣ Moy iste'moli ko'p — muhrlar yeyilgan",
            "4️⃣ Shovqin kuchaygan — moy yetarli emas yoki podshipnik",
            "5️⃣ Kompressor ishga tushmayapti — bosim reglatori tekshiring",
        ],
        "tekshirish": [
            "☑️ Havo bosimi (raqam manometri)",
            "☑️ Moy sathi va rangi",
            "☑️ Havo filtri holati",
            "☑️ Harorat (maks 120°C)",
            "☑️ Quvur va shlanglar oqishi",
        ],
        "ppr": "Har 500 soatda: havo filtri\nHar 2000 soatda: moy + klapanlar\nHar 8000 soatda: kapital ta'mirlash",
        "ehtiyot_qismlar": {
            "havo filtri": {"resurs_soat": 500, "birlik": "dona", "taxminiy_narx": "20-80 USD"},
            "klapan": {"resurs_soat": 2000, "birlik": "dona", "taxminiy_narx": "50-200 USD"},
            "kompressor moyi": {"resurs_soat": 2000, "birlik": "litr", "taxminiy_narx": "5-15 USD/l"},
            "muhr to'plami": {"resurs_soat": 4000, "birlik": "to'plam", "taxminiy_narx": "100-400 USD"},
        },
        "quvvat_kw": 55,
    },
    "konveyer": {
        "muammolar": [
            "1️⃣ Lenta sirpanmoqda — tarang qilish kerak",
            "2️⃣ Lenta chetga chiqmoqda — roliki tekislang",
            "3️⃣ Rolik ishlamayapti — yog'lash yoki almashtirish",
            "4️⃣ Haydovchi baraban yeyilgan — rezina qoplama tekshiring",
            "5️⃣ Motor qizib ketmoqda — yukni kamaytiring yoki yog'lang",
        ],
        "tekshirish": [
            "☑️ Lenta tarangligi (GOST 22645)",
            "☑️ Roliklar aylanishi (qo'lda tekshirish)",
            "☑️ Tayanch konstruktsiya (bo'shashgan vintlar)",
            "☑️ Avariya to'xtatgich ishlashi",
            "☑️ Lenta yuzasi (yirtiq, tirqish)",
        ],
        "ppr": "Kundalik: roliklar va taranglik\nHar oy: podshipniklar yog'lash\nHar yil: lenta tekshirish, kapital",
        "ehtiyot_qismlar": {
            "rolik": {"resurs_soat": 3000, "birlik": "dona", "taxminiy_narx": "15-50 USD"},
            "konveyer lentasi": {"resurs_soat": 15000, "birlik": "metr", "taxminiy_narx": "20-100 USD/m"},
            "reduktor moyi": {"resurs_soat": 4000, "birlik": "litr", "taxminiy_narx": "5-12 USD/l"},
            "podshipnik (rolik)": {"resurs_soat": 8000, "birlik": "dona", "taxminiy_narx": "30-120 USD"},
        },
        "quvvat_kw": 30,
    },
    "tegirmon": {
        "muammolar": [
            "1️⃣ Haddan tashqari tebranish — murvat bo'shashgan yoki muvozanat buzilgan",
            "2️⃣ Ishlab chiqarish kamaydi — liner yeyilgan",
            "3️⃣ Shovqin — maydalovchi element yetarli emas",
            "4️⃣ Moy bosimi past — nasos yoki filtr",
            "5️⃣ Harorat ko'tarildi — sovutish tekshiring",
        ],
        "tekshirish": [
            "☑️ Tebranish ≤ 7.1 mm/s (ISO 10816)",
            "☑️ Moy bosimi (0.1–0.3 MPa)",
            "☑️ Kirish/chiqish material granulometri",
            "☑️ Liner qalinligi (ultrasonik o'lchash)",
        ],
        "ppr": "Har oy: liner tekshirish\nHar 6 oy: to'liq tekshirish\nHar yil: kapital ta'mirlash + liner almashtirish",
        "ehtiyot_qismlar": {
            "liner (bron plita)": {"resurs_soat": 8000, "birlik": "dona", "taxminiy_narx": "200-800 USD"},
            "maydalovchi sharlar": {"resurs_soat": 2000, "birlik": "tonna", "taxminiy_narx": "800-1200 USD/t"},
            "trunnion podshipnik": {"resurs_soat": 20000, "birlik": "dona", "taxminiy_narx": "2000-8000 USD"},
            "moy filtri": {"resurs_soat": 500, "birlik": "dona", "taxminiy_narx": "30-100 USD"},
        },
        "quvvat_kw": 500,
    },
    "flotatsiya": {
        "muammolar": [
            "1️⃣ Ko'pik kam — reagentlar yetarli emas yoki havo",
            "2️⃣ Turbina to'xtadi — motor yoki val tekshiring",
            "3️⃣ Havo etkazib berilmayapti — kompressor, truba",
            "4️⃣ Drenaj tiqilgan — texnologik truba tozalang",
        ],
        "tekshirish": [
            "☑️ Havo sarfi (rotametr)",
            "☑️ Reagent dozalash",
            "☑️ Turbina aylanish tezligi (RPM)",
            "☑️ Pulpa sathi",
        ],
        "ppr": "Har hafta: turbina va havo tizimi\nHar oy: to'liq texnik ko'rik",
        "ehtiyot_qismlar": {
            "turbina (rotor)": {"resurs_soat": 6000, "birlik": "dona", "taxminiy_narx": "300-1200 USD"},
            "havo quvuri": {"resurs_soat": 10000, "birlik": "metr", "taxminiy_narx": "5-20 USD/m"},
            "reagent dozator": {"resurs_soat": 4000, "birlik": "dona", "taxminiy_narx": "200-600 USD"},
        },
        "quvvat_kw": 15,
    },
}

# ── Xavfsizlik checklari ───────────────────────────────────────
SAFETY_CHECKLISTS = {
    "elektr": [
        "⚡ 1. Energiyani o'chirish va QULFLASH (Lockout/Tagout - LOTO)",
        "⚡ 2. Voltmetr bilan kuchlanish yo'qligini tekshirish",
        "⚡ 3. Yerga ulash (zazemlenie) tekshirish",
        "⚡ 4. Dielektrik qo'lqop va poyabzal kiyish",
        "⚡ 5. Ogohlantiruvchi yorliq osish: 'YOQMANG — odam ishlayapti'",
        "⚡ 6. Yonib turgan joyda ishlashda yong'in o'chiruvchi hozir tursin",
    ],
    "balandlik": [
        "🪜 1. Balandlik harnessini kiyish (3 m dan yuqori)",
        "🪜 2. Narvon mustahkamligini tekshirish",
        "🪜 3. Pastda xavfsizlik maydoni ajratish",
        "🪜 4. 2 kishidan kam bo'lmagan holda ishlash",
        "🪜 5. Qurol-asboblarni belkilash (tushib ketmasin)",
        "🪜 6. Shamol kuchli bo'lsa ishlamaslik (>10 m/s)",
    ],
    "bosimli_tizim": [
        "🔴 1. Bosimni nolga tushirish va bloklash",
        "🔴 2. Manometr ko'rsatuvini tekshirish",
        "🔴 3. Havoni purgatsiya qilish",
        "🔴 4. Himoya ko'zoynak va yuz qalqoni kiyish",
        "🔴 5. Razgruzka ventili holatini tekshirish",
        "🔴 6. Truba va fitinglar holati vizual tekshirish",
    ],
    "kimyoviy": [
        "☣️ 1. Material xavfsizlik pasportini (MSDS) o'qish",
        "☣️ 2. Himoya kiyimi, qo'lqop, ko'zoynak, respirator",
        "☣️ 3. Shamollatish ishlamayotgan bo'lsa kirmang",
        "☣️ 4. Birinchi yordam vositalari hozir bo'lsin",
        "☣️ 5. Dush va ko'z yuvish stansiyasi joylashuvini bilish",
        "☣️ 6. Reaktivlarni aralashtirish jadvalini bilish",
    ],
    "yeyuvchi": [
        "🔧 1. Rotatsiyalanayotgan qismlarni BLOKLA (LOTO)",
        "🔧 2. Kaftali qo'lqop va himoya kiyim",
        "🔧 3. Ko'z qalqoni",
        "🔧 4. Qurilma to'liq to'xtaganini tekshirish",
        "🔧 5. Hech kim yaqin turmasligini ta'minlash",
    ],
    "umumiy": [
        "✅ 1. Ish ruxsatnomasini (наряд-допуск) olish",
        "✅ 2. Xavfli zona chegarasini belgilash",
        "✅ 3. Nazoratchi tayinlash",
        "✅ 4. Aloqa vositalari (ratsiya/telefon) ishlashini tekshirish",
        "✅ 5. Birinchi yordam vositalarini hozir qilish",
        "✅ 6. Ob-havo sharoitini tekshirish",
        "✅ 7. Avval instruktaj o'tkazish",
    ],
}

INCIDENT_GUIDE = {
    "jarohat": [
        "🚨 1. XAVFSIZLIKNI TA'MINLA — boshqalarni jarohat xavfidan muhofaza et",
        "📞 2. 103 (tez yordam) yoki kombinat tibbiy punkti",
        "🛑 3. Ish joyini saqla — biror narsani surmang (tekshiruv uchun)",
        "🔴 4. Birinchi yordam ber (agar mutaxassis bo'lsang)",
        "📝 5. Darhol ustingizga xabar ber",
        "📋 6. Hodisa haqida dalolatnoma tuz (F-H-1 shakli)",
        "📸 7. Rasm oling (imkon bo'lsa)",
    ],
    "yongin": [
        "🔥 1. Xodimlarni evakuatsiya qil — DARHOL",
        "📞 2. 101 (yong'in xizmati) va smenaning boshliqiga xabar ber",
        "🧯 3. Kichik yong'inda: OP-5 yoki CO2 o'chiruvchi ishlatish",
        "🚪 4. Eshik va derazalarni yop (havo kirmasin)",
        "🚫 5. Liftdan foydalanma",
        "🔌 6. Elektr qurilmalar yonayotgan bo'lsa — suv ISHLATMA",
    ],
    "kimyoviy_tokilish": [
        "☣️ 1. Ajralish joyini izolyatsiya qil",
        "💧 2. Teriga tushgan bo'lsa — 15 daqiqa suv bilan yuv",
        "👁️ 3. Ko'zga tushgan bo'lsa — 20 daqiqa ko'z yuvish stansiyasida yuo",
        "📞 4. 103 va kimyoviy xizmat boshlig'iga xabar ber",
        "💨 5. Shamollatishni yoq, binoni bo'shat",
        "📋 6. Qaysi modda ekanini aniqlash (MSDS topish)",
    ],
}


# ═══════════════════════════════════════════════════════════════
#  HISOB-KITOB FUNKSIYALARI
# ═══════════════════════════════════════════════════════════════

def hydraulic_calc(flow_m3h: float, pipe_dia_mm: float, length_m: float,
                   viscosity_cst: float = 46.0, density: float = 870.0) -> str:
    dia_m = pipe_dia_mm / 1000
    area  = 3.14159 * (dia_m / 2) ** 2
    v     = (flow_m3h / 3600) / area
    nu    = viscosity_cst * 1e-6
    Re    = v * dia_m / nu
    if Re < 2300:
        f, rejim = 64 / Re, "Laminar"
    elif Re > 4000:
        f, rejim = 0.316 / (Re ** 0.25), "Turbulent"
    else:
        f, rejim = 0.04, "O'tish zonasi"
    dp     = f * (length_m / dia_m) * density * v ** 2 / 2
    dp_bar = dp / 1e5
    dp_mwc = dp / (density * 9.81)
    return (
        f"📐 *Gidravlik Hisob-Kitob*\n\n"
        f"📊 *Kirish:* sarif={flow_m3h} m³/soat | diametr={pipe_dia_mm} mm | uzunlik={length_m} m\n\n"
        f"📈 *Natijalar:*\n"
        f"  Tezlik: *{v:.2f} m/s*\n"
        f"  Reynolds: Re = {Re:.0f} ({rejim})\n"
        f"  Bosim yo'qotish: *{dp_bar:.3f} bar* ({dp_mwc:.2f} m.s.u.)\n\n"
        f"⚠️ _Mahalliy qarshiliklar (+10–30%) hisobga olinmagan_\n"
        f"📌 _GOST 8734 / ISO 4200_"
    )


def pneumatic_calc(volume_m3: float, pressure_bar: float, fill_time_min: float) -> str:
    q_free  = volume_m3 * pressure_bar / fill_time_min
    power_kw = q_free * pressure_bar * 0.1 / 0.7
    return (
        f"💨 *Pnevmatik Hisob-Kitob*\n\n"
        f"  Hajm: {volume_m3} m³ | Bosim: {pressure_bar} bar | Vaqt: {fill_time_min} min\n\n"
        f"  Havo sarfi: *{q_free:.2f} Nm³/min*\n"
        f"  Zaruriy kompressor quvvati: *≥ {power_kw:.1f} kW*\n\n"
        f"📌 _GOST 24484 — pnevmatik tizimlar_"
    )


def bearing_life_calc(C_kN: float, P_kN: float, n_rpm: float,
                      bearing_type: str = "shar") -> str:
    p    = 3.0 if bearing_type == "shar" else 10 / 3
    L10  = (C_kN / P_kN) ** p * 1e6
    L10h = L10 / (60 * n_rpm)
    return (
        f"⚙️ *Podshipnik Resursi (ISO 281)*\n\n"
        f"  C = {C_kN} kN | P = {P_kN} kN | n = {n_rpm} min⁻¹\n"
        f"  Tip: {'sharsimon' if bearing_type == 'shar' else 'rolikli'}\n\n"
        f"  L₁₀ = *{L10/1e6:.1f}·10⁶ aylanish*\n"
        f"  L₁₀h = *{L10h:.0f} soat* (~{L10h/8760:.1f} yil)\n\n"
        f"⚠️ _a₁=1 qabul qilindi (GOST 18855 / ISO 281)_"
    )


# ═══════════════════════════════════════════════════════════════
#  MechanicService KLASSI
# ═══════════════════════════════════════════════════════════════

class MechanicService:
    """Mexanik uchun barcha maxsus funksiyalar"""

    def __init__(self):
        api_key  = os.getenv("GROQ_API_KEY", "")
        self.groq = Groq(api_key=api_key) if api_key else None

    def _ai(self, prompt: str, system: str = MECHANIC_SYSTEM_PROMPT,
            max_tokens: int = 1200) -> str:
        """Sinxron Groq chaqiruvi"""
        if not self.groq:
            return "❌ GROQ_API_KEY sozlanmagan."
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system},
                           {"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"❌ AI xatosi: {e}"

    async def _ai_async(self, prompt: str, system: str = MECHANIC_SYSTEM_PROMPT,
                        max_tokens: int = 1200) -> str:
        """Asinxron — threadda ishlatiladi"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ai, prompt, system, max_tokens)

    # ── 1. Ehtiyot qismlar kalkulyatori ──────────────────────
    def spare_parts_calc(self, equip_type: str, runtime_h: float,
                          intensity: str = "o'rtacha") -> str:
        """
        Ishlatish intensivligi va joriy ish soatiga qarab
        ehtiyot qism almashtirish jadvalini hisoblaydi.

        intensity: "yumshoq" | "o'rtacha" | "og'ir"
        """
        key = None
        for k in EQUIPMENT_DB:
            if k in equip_type.lower():
                key = k
                break
        if not key:
            return f"❓ '{equip_type}' topilmadi. Mavjud: {', '.join(EQUIPMENT_DB.keys())}"

        koef = {"yumshoq": 1.3, "o'rtacha": 1.0, "og'ir": 0.7}.get(intensity, 1.0)
        parts = EQUIPMENT_DB[key].get("ehtiyot_qismlar", {})
        if not parts:
            return f"❌ {key} uchun ehtiyot qism ma'lumoti yo'q."

        lines = [
            f"🔩 *Ehtiyot Qismlar Kalkulyatori — {key.upper()}*\n",
            f"⏱ Joriy ish vaqti: {runtime_h:,.0f} soat",
            f"🏭 Intensivlik: {intensity} (koef: {koef})\n",
        ]

        need_soon = []
        for name, info in parts.items():
            resurs = info["resurs_soat"] * koef
            qolgan = resurs - (runtime_h % resurs)
            foiz   = (runtime_h % resurs) / resurs * 100

            if foiz >= 80:
                status = "🔴 DARHOL almashtiring"
                need_soon.append(name)
            elif foiz >= 60:
                status = "🟠 Tez orada almashtiring"
                need_soon.append(name)
            elif foiz >= 40:
                status = "🟡 Kuzatuvda turing"
            else:
                status = "🟢 Yaxshi holat"

            lines.append(
                f"*{name}:*\n"
                f"  Resurs: {resurs:,.0f} soat | Yeyilish: {foiz:.0f}%\n"
                f"  {status}\n"
                f"  _(≈{qolgan:,.0f} soat qoldi | {info['taxminiy_narx']})_"
            )

        if need_soon:
            lines.append(f"\n⚠️ *Zudlik bilan kerakli qismlar:*\n" +
                         "\n".join(f"  • {p}" for p in need_soon))
        lines.append(f"\n📌 _GOST 27.002 — ishonchlilik standartlari_")
        return "\n".join(lines)

    # ── 2. Ariza/Zayavka generatori ───────────────────────────
    def generate_zayavka(self, description: str, equip_name: str = "",
                          qty_str: str = "") -> str:
        """
        Tavsifdan rasmiy ta'minot arizasi (zayavka) shakllantiradi.
        Misol: "nasosga 3 ta salnk kerak" → to'liq ariza
        """
        now = datetime.now()

        # Miqdor va qism nomini ajratib olish
        # "3 ta salnk", "2 dona podshipnik", "10 litr moy"
        qty_match = re.search(r'(\d+)\s*(?:ta|dona|litr|metr|kg|to\'plam)?\s*(.+)', description, re.I)
        if qty_match:
            qty  = qty_match.group(1)
            part = qty_match.group(2).strip()
        else:
            qty  = qty_str or "1"
            part = description

        # Birlikni aniqlash
        birlik = "dona"
        for b in ["litr", "metr", "kg", "to'plam", "m", "l"]:
            if b in description.lower():
                birlik = b
                break

        return (
            f"📋 *EHTIYOT QISM ARIZASI (ZAYAVKA)*\n"
            f"_{now.strftime('%d.%m.%Y')}_\n\n"
            f"🏭 *Korxona:* AGMK, 3-mis boyitish fabrika\n"
            f"👤 *Ariza beruvchi:* Mexanik O'tkirbek\n"
            f"📍 *Bo'lim:* MBF-3 Mexanik xizmat\n\n"
            f"{'─'*32}\n\n"
            f"| # | Nomenklatura | Miqdor | Birlik | Izoh |\n"
            f"|---|---|---|---|---|\n"
            f"| 1 | {part} | {qty} | {birlik} | {equip_name or 'Texnik xizmat'} |\n\n"
            f"{'─'*32}\n\n"
            f"📌 *Kerak bo'lish sababi:*\n"
            f"_{description}_\n\n"
            f"⚙️ *Uskuna:* {equip_name or '—'}\n"
            f"📅 *Kerakli muddat:* {now.strftime('%d.%m.%Y')} dan boshlab\n\n"
            f"✍️ Mexanik: O'tkirbek ________\n"
            f"✍️ Sex boshlig'i: ________\n"
            f"✍️ Ta'minot bo'limi: ________\n\n"
            f"📌 _Ariza AGMK ta'minot qoidalariga muvofiq tuzilgan_"
        )

    # ── 3. QR-kod integratsiyasi ──────────────────────────────
    def lookup_equipment_by_qr(self, qr_data: str, db_records: list = None) -> str:
        """
        QR kod ma'lumotlaridan uskuna tarixini ko'rsatadi.
        qr_data: QR skaner qaytargan matn (ID, nomer, yoki JSON)
        db_records: ma'lumotlar bazasidan olingan uskuna yozuvlari
        """
        lines = [f"📱 *QR-Kod Skanerlandi*\n", f"🔍 Ma'lumot: `{qr_data[:100]}`\n"]

        # QR dan ID yoki nomer ajratish
        equip_id = None
        m = re.search(r'(?:id|nomer|no)[=:\s]+(\w+)', qr_data, re.I)
        if m:
            equip_id = m.group(1)
        else:
            equip_id = qr_data.strip()

        lines.append(f"🔢 *Uskuna ID:* `{equip_id}`\n")

        if db_records:
            # Ma'lumotlar bazasidan topilgan yozuvlar
            lines.append("📋 *Ta'mirlash tarixi:*")
            for r in db_records[:5]:
                date = r.get("date", r.get("created_at", "—"))[:10]
                work = r.get("work_type", r.get("description", "—"))[:60]
                lines.append(f"  📅 {date} — {work}")

            if not db_records:
                lines.append("  _Tarix topilmadi_")
        else:
            # Standart uskuna ma'lumotlari bazasidan qidirish
            found = False
            for key, info in EQUIPMENT_DB.items():
                if key in equip_id.lower() or equip_id.lower() in key:
                    lines.append(f"⚙️ *Tur:* {key.upper()}")
                    lines.append(f"📅 *PPR jadvali:*\n_{info['ppr']}_")
                    found = True
                    break

            if not found:
                lines.append("⚠️ _Uskuna bazada topilmadi_")
                lines.append("_Digital Twin ga qo'shish: `Holat: " + equip_id + ", status=ishlamoqda`_")

        lines.append(f"\n_QR: {qr_data[:50]}..._" if len(qr_data) > 50 else "")
        return "\n".join(lines)

    # ── 4. Avariya ssenariysi simulyatori ─────────────────────
    async def simulate_accident(self, scenario: str) -> str:
        """
        Avariya stsenariysi bo'yicha step-by-step oqibatlar va choralar.
        Misol: "tegirmonning moylanish tizimi ishdan chiqsa"
        """
        prompt = f"""
AGMK 3-mis boyitish fabrikasidagi quyidagi avariya ssenariysini tahlil qil:

STSENARIY: {scenario}

Quyidagi strukturada javob ber (O'zbek tilida, qisqa va aniq):

1️⃣ DARHOL OQIBATLAR (0-5 daqiqa ichida nima bo'ladi)
2️⃣ QISQA MUDDATLI OQIBATLAR (5-60 daqiqa)
3️⃣ UZOK MUDDATLI OQIBATLAR (ishlab chiqarishga ta'sir)
4️⃣ DARHOL CHORALAR (nima qilish kerak, tartib bo'yicha)
5️⃣ OLDINI OLISH CHORALARI (kelajakda bunday bo'lmasligi uchun)
6️⃣ ZARUR EHTIYOT QISMLAR (bu holat uchun)

Har bo'lim 2-3 ta qisqa nuqta bilan.
"""
        result = await self._ai_async(prompt, max_tokens=1500)
        return f"🚨 *Avariya Ssenariysi Tahlili*\n\n_{scenario}_\n\n{'─'*30}\n\n{result}"

    # ── 5. Til tarjimoni ──────────────────────────────────────
    async def translate_technical(self, text: str,
                                   target_lang: str = "uzbek",
                                   manufacturer: str = "") -> str:
        """
        ABB, Metso, Warman, Sulzer va boshqa xorijiy texnik hujjatlarni tarjima qiladi.
        target_lang: "uzbek" | "russian"
        """
        lang_name = "O'zbek" if target_lang == "uzbek" else "Rus"
        mfr_context = f"Bu {manufacturer} qurilmasining texnik hujjati." if manufacturer else ""

        prompt = f"""
{mfr_context}
Quyidagi texnik matnni {lang_name} tiliga tarjima qil.
Sanoat/mexanik terminlarni to'g'ri tarjima qil.
Agar texnik termin o'zbek/ruscha ekvivalenti yo'q bo'lsa, inglizcha qoldir va qavs ichida tushuntir.
Formatni saqlа (ro'yxat, raqamlar, birliklar).

MATN:
{text[:2000]}
"""
        result = await self._ai_async(prompt, max_tokens=1500)
        return (
            f"🌐 *Texnik Tarjima — {lang_name} tili*\n"
            f"{f'📦 Ishlab chiqaruvchi: {manufacturer}' if manufacturer else ''}\n\n"
            f"{'─'*30}\n\n{result}"
        )

    # ── 6. Trend tahlili va prognoz ───────────────────────────
    def analyze_trend(self, equip_id: str, param_name: str,
                       data_points: list) -> str:
        """
        Sensor ma'lumotlari trendini tahlil qiladi va ishdan chiqish ehtimolini hisoblaydi.
        data_points: [(timestamp, value), ...] — oxirgi o'lchovlar
        param_name: "vibration" | "temperature" | "pressure" | "current"
        """
        if len(data_points) < 2:
            return "❌ Trend tahlili uchun kamida 2 ta o'lchov kerak."

        values  = [v for _, v in data_points]
        n       = len(values)
        avg     = sum(values) / n
        mx      = max(values)
        mn      = min(values)

        # Chiziqli trend (oddiy regressiya)
        x_mean  = (n - 1) / 2
        slope_n = sum((i - x_mean) * (v - avg) for i, v in enumerate(values))
        slope_d = sum((i - x_mean) ** 2 for i in range(n))
        slope   = slope_n / slope_d if slope_d else 0

        # Kritik chegaralar
        limits = {
            "vibration":   {"warn": 4.5, "crit": 7.1, "birlik": "mm/s"},
            "temperature": {"warn": 80,  "crit": 95,  "birlik": "°C"},
            "pressure":    {"warn": 8.0, "crit": 10.0, "birlik": "bar"},
            "current":     {"warn": 90,  "crit": 110, "birlik": "A"},
        }
        lim = limits.get(param_name, {"warn": avg*1.2, "crit": avg*1.5, "birlik": ""})

        # Prognoz: qachon kritik chegara yetib kelinadi?
        cur_val = values[-1]
        prognoz_str = "—"
        ehtimol = 0

        if slope > 0 and cur_val < lim["crit"]:
            steps_to_crit = (lim["crit"] - cur_val) / slope if slope > 0 else float("inf")
            ehtimol = min(int((cur_val - lim["warn"]) / (lim["crit"] - lim["warn"]) * 100), 95)
            ehtimol = max(ehtimol, 0)
            if steps_to_crit < 24:
                prognoz_str = f"⚠️ {steps_to_crit:.0f} soat ichida kritik chegara!"
            elif steps_to_crit < 168:
                prognoz_str = f"🟡 ~{steps_to_crit/24:.1f} kun ichida kritik chegara"
            else:
                prognoz_str = f"🟢 ~{steps_to_crit/168:.1f} hafta zaxira bor"
        elif slope <= 0:
            prognoz_str = "🟢 Barqaror yoki yaxshilanmoqda"
            ehtimol = 5

        # Status
        if cur_val >= lim["crit"]:
            status = "🔴 KRİTİK — darhol to'xtatish kerak!"
        elif cur_val >= lim["warn"]:
            status = "🟠 OGOHLANTIRISH — kuzatuvni kuchaytiring"
        else:
            status = "🟢 Normal"

        trend_arrow = "📈" if slope > 0.01 else ("📉" if slope < -0.01 else "➡️")

        return (
            f"📊 *Trend Tahlili — {equip_id}*\n"
            f"📡 Parametr: *{param_name}* ({lim['birlik']})\n\n"
            f"📈 *Statistika ({n} ta o'lchov):*\n"
            f"  Joriy: *{cur_val:.2f}*\n"
            f"  O'rtacha: {avg:.2f} | Min: {mn:.2f} | Max: {mx:.2f}\n"
            f"  Trend: {trend_arrow} {'+' if slope>0 else ''}{slope:.4f}/soat\n\n"
            f"🚨 *Chegaralar:* ogohlantirish={lim['warn']} | kritik={lim['crit']}\n"
            f"🎯 *Joriy holat:* {status}\n\n"
            f"🔮 *Prognoz:* {prognoz_str}\n"
            f"📉 *Ishdan chiqish ehtimoli (bu oy):* *{ehtimol}%*\n\n"
            f"📌 _ISO 10816 / GOST R 55263 tebranish standartlari_"
        )

    # ── 7. Energiya sarfi monitoringi ─────────────────────────
    def energy_monitor(self, equip_id: str, equip_type: str,
                        current_kw: float, runtime_h: float = 24) -> str:
        """
        Uskunaning quvvat iste'molini tahlil qiladi va anomaliya aniqlaydi.
        """
        key = None
        for k in EQUIPMENT_DB:
            if k in equip_type.lower():
                key = k
                break

        nominal_kw   = EQUIPMENT_DB[key]["quvvat_kw"] if key else current_kw
        tariff_uzs   = float(os.getenv("ELECTRICITY_TARIFF", "600"))  # so'm/kWh

        # Hisob
        deviation    = ((current_kw - nominal_kw) / nominal_kw * 100) if nominal_kw else 0
        energy_kwh   = current_kw * runtime_h
        cost_uzs     = energy_kwh * tariff_uzs

        # Anomaliya
        if abs(deviation) > 20:
            anomaly = f"🔴 *ANOMALIYA:* nominal dan {deviation:+.0f}%"
            if deviation > 0:
                anomaly += "\n_Sabab: ortiqcha yuk, mexanik ishqalanish, motor nosozligi_"
            else:
                anomaly += "\n_Sabab: yuk kamayganligi, hisoblash xatosi_"
        elif abs(deviation) > 10:
            anomaly = f"🟡 Nominal dan {deviation:+.0f}% — kuzatuvda turing"
        else:
            anomaly = f"🟢 Normal ({deviation:+.0f}%)"

        return (
            f"⚡ *Energiya Sarfi Monitoringi — {equip_id}*\n\n"
            f"🔌 *Joriy quvvat:* {current_kw:.1f} kW\n"
            f"📊 *Nominal quvvat:* {nominal_kw:.1f} kW\n"
            f"📏 *Og'ish:* {deviation:+.1f}%\n\n"
            f"{anomaly}\n\n"
            f"💡 *{runtime_h}h sarfi:* {energy_kwh:.1f} kWh\n"
            f"💰 *Xarajat:* {cost_uzs:,.0f} so'm\n"
            f"📅 *Oylik (720h):* {current_kw*720:.0f} kWh ≈ "
            f"{current_kw*720*tariff_uzs/1_000_000:.2f} mln so'm\n\n"
            f"📌 _Tarif: {tariff_uzs:.0f} so'm/kWh_"
        )

    # ── 8. Ish samaradorligi metrikalari ─────────────────────
    def performance_metrics(self, stats: dict) -> str:
        """
        Mexanik ish samaradorligini hisoblaydi.
        stats: {solved, total, avg_response_min, failures: {type: count}}
        """
        solved       = stats.get("solved", 0)
        total        = stats.get("total", 0)
        avg_resp     = stats.get("avg_response_min", 0)
        failures     = stats.get("failures", {})
        uptime_pct   = stats.get("uptime_pct", 0)

        resolution_rate = (solved / total * 100) if total else 0

        # Top nosozliklar
        top_failures = sorted(failures.items(), key=lambda x: x[1], reverse=True)[:3]

        lines = [
            f"📈 *Ish Samaradorligi Metrikalari*\n"
            f"_{datetime.now().strftime('%B %Y')}_\n",
            f"✅ *Hal qilish darajasi:* {resolution_rate:.0f}% ({solved}/{total})",
            f"⏱ *O'rtacha javob vaqti:* {avg_resp:.0f} daqiqa",
            f"🏭 *Uskuna ishlash vaqti:* {uptime_pct:.1f}%\n",
        ]

        if top_failures:
            lines.append("🔧 *Eng ko'p takrorlanadigan nosozliklar:*")
            for i, (ftype, cnt) in enumerate(top_failures, 1):
                lines.append(f"  {i}. {ftype}: *{cnt}* ta")

        # Baholash
        if resolution_rate >= 90:
            grade = "⭐⭐⭐ A'lo"
        elif resolution_rate >= 75:
            grade = "⭐⭐ Yaxshi"
        elif resolution_rate >= 60:
            grade = "⭐ Qoniqarli"
        else:
            grade = "⚠️ Yaxshilash kerak"

        lines.append(f"\n🎯 *Umumiy baho:* {grade}")
        return "\n".join(lines)

    # ── Mavjud funksiyalar (o'zgarmagan) ──────────────────────

    async def analyze_technical(self, query: str) -> str:
        return await self._ai_async(query)

    def get_equipment_info(self, equip_type: str) -> str:
        key = None
        for k in EQUIPMENT_DB:
            if k in equip_type.lower() or equip_type.lower() in k:
                key = k
                break
        synonyms = {
            "pump": "nasos", "pompa": "nasos",
            "kompr": "kompressor",
            "lenta": "konveyer",
            "mill": "tegirmon", "maydalag": "tegirmon",
            "flot": "flotatsiya",
        }
        if not key:
            for syn, real in synonyms.items():
                if syn in equip_type.lower():
                    key = real
                    break
        if not key:
            return f"❓ '{equip_type}' uchun ma'lumot topilmadi. Mavjud: {', '.join(EQUIPMENT_DB.keys())}"
        info  = EQUIPMENT_DB[key]
        lines = [f"🔧 *{key.upper()} — Muammo tahlili*\n", "*Mumkin bo'lgan sabablar:*"]
        lines.extend(info["muammolar"])
        lines.append("\n*Tekshirish tartibi:*")
        lines.extend(info["tekshirish"])
        lines.append(f"\n📅 *PPR jadvali:*\n_{info['ppr']}_")
        return "\n".join(lines)

    def get_safety_checklist(self, work_type: str) -> str:
        key     = None
        mapping = {
            "elektr": "elektr", "tok": "elektr", "kabel": "elektr",
            "balandlik": "balandlik", "narvon": "balandlik",
            "bosim": "bosimli_tizim", "gidravlik": "bosimli_tizim",
            "kimyo": "kimyoviy", "kislota": "kimyoviy", "reagent": "kimyoviy",
            "rotor": "yeyuvchi", "aylan": "yeyuvchi", "tegirmon": "yeyuvchi",
        }
        for kw, cat in mapping.items():
            if kw in work_type.lower():
                key = cat
                break
        if not key:
            key = "umumiy"
        checklist = SAFETY_CHECKLISTS[key]
        lines     = [f"🦺 *Xavfsizlik Checklisti — {work_type}*\n_GOST 12.0.004 / OHSAS 18001_\n"]
        lines.extend(checklist)
        lines.append("\n⚠️ _Nazoratchi imzosisiz ish boshlanmaydi!_")
        return "\n".join(lines)

    def get_incident_guide(self, incident_type: str) -> str:
        key = None
        if any(w in incident_type.lower() for w in ["jarohat", "baxtsiz", "qon"]):
            key = "jarohat"
        elif any(w in incident_type.lower() for w in ["yong'in", "olov"]):
            key = "yongin"
        elif any(w in incident_type.lower() for w in ["kimyo", "kislota", "tokildi"]):
            key = "kimyoviy_tokilish"
        else:
            key = "jarohat"
        guide = INCIDENT_GUIDE[key]
        lines = ["🚨 *HODISA KO'RSATMASI*\n"]
        lines.extend(guide)
        lines.append("\n📞 _Kombinat dispatcher: (0379) 7-55-00_")
        lines.append("📞 _Tez yordam: 103 | Yong'in: 101_")
        return "\n".join(lines)

    def build_defect_act(self, params: dict) -> str:
        now = datetime.now()
        return (
            f"📋 *DEFEKT AKTI*\n_{now.strftime('%d.%m.%Y')}_\n\n"
            f"🏭 Korxona: AGMK, 3-mis boyitish fabrika\n"
            f"👤 Mexanik: O'tkirbek | 📍 Joy: {params.get('joy', '___')}\n"
            f"⚙️ Qurilma: {params.get('qurilma', '___')} | №: {params.get('nomer', '___')}\n\n"
            f"❌ *Nuqson:*\n{params.get('nuqson', '___')}\n\n"
            f"🔧 *Ta'mirlash:*\n{params.get('tamirlash', '___')}\n\n"
            f"🔩 *Ehtiyot qismlar:*\n{params.get('ehtiyot', '___')}\n\n"
            f"📅 *Muddat:* {params.get('muddat', '___')}\n\n"
            f"✍️ Mexanik: O'tkirbek ________ | Sex boshlig'i: ________\n"
            f"📌 _GOST 2.602-2013_"
        )

    def build_work_report(self, params: dict) -> str:
        now = datetime.now()
        return (
            f"📊 *KUNLIK ISH HISOBOTI*\n"
            f"_{now.strftime('%d.%m.%Y')} | Smena: {params.get('smena', '1')}_\n\n"
            f"🏭 AGMK 3-MB | Mexanik: O'tkirbek\n\n"
            f"✅ *Bajarildi:*\n{params.get('bajarildi', '—')}\n\n"
            f"⏳ *Davom etmoqda:*\n{params.get('davom', '—')}\n\n"
            f"❌ *Muammolar:*\n{params.get('muammo', '—')}\n\n"
            f"📦 *Sarflangan:*\n{params.get('sarf', '—')}\n\n"
            f"📋 *Keyingi smena:*\n{params.get('keyingi', '—')}\n\n"
            f"✍️ Mexanik: O'tkirbek ________"
        )

    def build_service_letter(self, params: dict) -> str:
        now = datetime.now()
        return (
            f"📝 *XIZMAT XATI*\n\n"
            f"*Kimga:* {params.get('kimga', '___')}\n"
            f"*Kimdan:* 3-MB mexanigi O'tkirbek\n"
            f"*Sana:* {now.strftime('%d.%m.%Y')}\n"
            f"*Mavzu:* {params.get('mavzu', '___')}\n\n"
            f"{'─'*30}\n\n{params.get('matn', '___')}\n\n{'─'*30}\n"
            f"Iltimos, ko'rib chiqib tegishli choralar ko'rishingizni so'rayman.\n\n"
            f"Hurmat bilan, O'tkirbek\nAGMK 3-MB mexanigi\nTel: {params.get('tel', '___')}"
        )

    def hydraulic_calc(self, flow, dia, length, visc=46.0, rho=870.0):
        return hydraulic_calc(flow, dia, length, visc, rho)

    def pneumatic_calc(self, vol, pressure, time):
        return pneumatic_calc(vol, pressure, time)

    def bearing_calc(self, C, P, n, btype="shar"):
        return bearing_life_calc(C, P, n, btype)

    async def generate_ppr_schedule(self, equipment_list: list) -> str:
        equip_str = ", ".join(equipment_list)
        result    = await self._ai_async(
            f"Quyidagi uskunalar uchun oylik PPR jadvali tuz: {equip_str}\n"
            f"Har uskuna uchun: TO-1 (kundalik), TO-2 (haftalik), TO-3 (oylik), kapital (yillik). O'zbek tilida.",
            max_tokens=1500
        )
        return "📅 *PPR JADVALI*\n\n" + result
