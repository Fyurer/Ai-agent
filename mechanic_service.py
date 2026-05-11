"""
Mechanic Service — Mis boyitish fabrikasi mexanigi uchun
Olmaliq kon-metallurgiya kombinati, 3-fabrika
"""

import os
import re
import logging
from datetime import datetime
from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

MECHANIC_SYSTEM_PROMPT = """Sen Olmaliq kon-metallurgiya kombinati 3-mis boyitish fabrikasidagi
mexanik O'tkirbek ning AI yordamchisisan. 
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

# ── Qurilma bazasi ────────────────────────────────────────────
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
        "ppr": "Har 2000 soatda: moy almashtirish, podshipnik tekshirish\nHar 8000 soatda: to'liq demontaj va kapital ta'mirlash"
    },
    "kompressor": {
        "muammolar": [
            "1️⃣ Havo bosimi yetmayapti — filtr tiqilgan yoki klapan yeyilgan",
            "2️⃣ Haddan tashqari qizish — sovutish tizimi nosoz",
            "3️⃣ Moy iste'moli ko'p — muhrlar yeyilgan",
            "4️⃣ Shovqin kuchaygan — moy yetarli emas yoki podshipnik",
            "5️⃣ Kompressor ishga tushmaяпti — bosim reglatori tekshiring",
        ],
        "tekshirish": [
            "☑️ Havo bosimi (raqam manometri)",
            "☑️ Moy sathi va rangi",
            "☑️ Havo filtri holati",
            "☑️ Harorat (maks 120°C)",
            "☑️ Quvur va shlanglar oqishi",
        ],
        "ppr": "Har 500 soatda: havo filtri\nHar 2000 soatda: moy + klapanlar\nHar 8000 soatda: kapital ta'mirlash"
    },
    "konveyер": {
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
        "ppr": "Kundalik: roliklar va taranglik\nHar oy: podshipniklar yog'lash\nHar yil: lenta tekshirish, kapital"
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
            "☑️ Vkhodnoy/выходной material granulometri",
            "☑️ Liner qalinligi (ultrasonik o'lchash)",
        ],
        "ppr": "Har oy: liner tekshirish\nHar 6 oy: to'liq tekshirish\nHar yil: kapital ta'mirlash + liner almashtirish"
    },
    "flotatsiya": {
        "muammolar": [
            "1️⃣ Ko'pik kam — reagentlar yetarli emas yoki havo",
            "2️⃣ Turbina to'xtadi — motor yoki val tekshiring",
            "3️⃣ Havo etkazib berilmayapti — kompressor, truba",
            "4️⃣ Drenaj tiqilgan — texnologik truba tozalang",
        ],
        "tekshirish": [
            "☑️ Havo sarfi (ротametр)",
            "☑️ Reagent dozalash",
            "☑️ Turbina aylanish tezligi (RPM)",
            "☑️ Pulpa sathi",
        ],
        "ppr": "Har hafta: turbina va havo tizimi\nHar oy: to'liq texnik ko'rik"
    }
}

# ── Xavfsizlik checklari ──────────────────────────────────────
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
    ]
}

# ── Hodisa ko'rsatmasi ────────────────────────────────────────
INCIDENT_GUIDE = {
    "jarohat": [
        "🚨 1. XAVFSIZLIKNI TA'MINLA — boshqalarni jarohat xavfidan muhofaza et",
        "📞 2. 103 (tez yordam) yoki kombinat tibbiy punkti: ko'rsatmadan foydalaning",
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
    ]
}

# ── Gidravlik hisob ───────────────────────────────────────────
def hydraulic_calc(flow_m3h: float, pipe_dia_mm: float, length_m: float,
                   viscosity_cst: float = 46.0, density: float = 870.0) -> str:
    """Gidravlik hisob-kitob (nasos/truboprovod)"""
    # Tezlik
    dia_m = pipe_dia_mm / 1000
    area = 3.14159 * (dia_m / 2) ** 2
    flow_m3s = flow_m3h / 3600
    v = flow_m3s / area

    # Reynolds soni
    nu = viscosity_cst * 1e-6  # m²/s
    Re = v * dia_m / nu

    # Ishqalanish koeffitsienti (Darcy-Weisbach)
    if Re < 2300:  # Laminar
        f = 64 / Re
        rejim = "Laminar"
    elif Re > 4000:  # Turbulent (Blasius)
        f = 0.316 / (Re ** 0.25)
        rejim = "Turbulent"
    else:
        f = 0.04
        rejim = "O'tish zonasi"

    # Bosim yo'qotish
    delta_p = f * (length_m / dia_m) * density * v ** 2 / 2  # Pa
    delta_p_bar = delta_p / 1e5
    delta_p_mwc = delta_p / (density * 9.81)  # metр suv ustuni

    return (
        f"📐 *Gidravlik Hisob-Kitob*\n\n"
        f"📊 *Kirish ma'lumotlari:*\n"
        f"  Sarif: {flow_m3h} m³/soat\n"
        f"  Quvur diametri: {pipe_dia_mm} mm\n"
        f"  Uzunlik: {length_m} m\n"
        f"  Viskozitet: {viscosity_cst} cSt\n"
        f"  Zichlik: {density} kg/m³\n\n"
        f"📈 *Natijalar:*\n"
        f"  Tezlik: *{v:.2f} m/s*\n"
        f"  Reynolds: Re = {Re:.0f} ({rejim})\n"
        f"  Ishqalanish koef.: λ = {f:.4f}\n\n"
        f"  Bosim yo'qotish:\n"
        f"  ΔP = *{delta_p_bar:.3f} bar*\n"
        f"  ΔP = *{delta_p_mwc:.2f} m.s.u.*\n\n"
        f"⚠️ _Mahalliy qarshiliklar (+10–30%) hisobga olinmagan_\n"
        f"📌 _GOST 8734 / ISO 4200 quvur standarti_"
    )


def pneumatic_calc(volume_m3: float, pressure_bar: float,
                   fill_time_min: float) -> str:
    """Pnevmatik tizim: kompressor quvvati hisoblash"""
    # Havo sarfi (Nm³/min)
    q_free = volume_m3 * pressure_bar / fill_time_min
    # Kompressor quvvati (taxminiy)
    power_kw = q_free * pressure_bar * 0.1 / 0.7  # η=0.7

    return (
        f"💨 *Pnevmatik Hisob-Kitob*\n\n"
        f"  Hajm: {volume_m3} m³\n"
        f"  Bosim: {pressure_bar} bar\n"
        f"  To'ldirilish vaqti: {fill_time_min} min\n\n"
        f"  Havo sarfi: *{q_free:.2f} Nm³/min*\n"
        f"  Zaruriy kompressor quvvati: *≥ {power_kw:.1f} kW*\n\n"
        f"📌 _GOST 24484 — pnevmatik tizimlar_"
    )


def bearing_life_calc(C_kN: float, P_kN: float, n_rpm: float,
                      bearing_type: str = "shar") -> str:
    """Podshipnik resurs hisoblash (ISO 281)"""
    p = 3.0 if bearing_type == "shar" else 10/3
    L10 = (C_kN / P_kN) ** p * 1e6  # aylanish
    L10h = L10 / (60 * n_rpm)  # soat

    return (
        f"⚙️ *Podshipnik Resursi (ISO 281)*\n\n"
        f"  Dinamik yuk qobiliyati C: {C_kN} kN\n"
        f"  Ekvivalent yuk P: {P_kN} kN\n"
        f"  Aylanish tezligi: {n_rpm} min⁻¹\n"
        f"  Tip: {'sharsimon' if bearing_type == 'shar' else 'rolikli'}\n\n"
        f"  L₁₀ = (C/P)^p = *{L10/1e6:.1f}·10⁶ aylanish*\n"
        f"  L₁₀h = *{L10h:.0f} soat* (~{L10h/8760:.1f} yil)\n\n"
        f"⚠️ _Chiniqtirish koeffitsienti a₁=1 qabul qilindi_\n"
        f"📌 _GOST 18855 / ISO 281_"
    )


class MechanicService:
    """Mexanik uchun barcha maxsus funksiyalar"""

    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def analyze_technical(self, query: str, image_bytes: bytes = None) -> str:
        """Texnik savol — Groq orqali mexanik kontekstda javob"""
        try:
            messages = [
                {"role": "system", "content": MECHANIC_SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ]
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=messages,
                max_tokens=1500, temperature=0.3
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ Texnik tahlil xatosi: {e}"

    async def analyze_drawing(self, image_query: str) -> str:
        """Chertyo'j tahlili uchun prompt"""
        prompt = f"""
        Bu sanoat chertyo'ji/sxemasi. O'zbek tilida qisqacha:
        1. Nima tasvirlangan (qurilma, tizim, element nomi)
        2. Asosiy o'lchamlar (agar ko'rinsa)
        3. Texnik belgilar izohi
        4. GOST/ISO standarti (agar aniqlansa)
        
        Qo'shimcha savol: {image_query if image_query else 'Umumiy tahlil'}
        """
        return prompt  # Bu Gemini'ga uzatiladi handlers.py da

    def get_equipment_info(self, equip_type: str) -> str:
        """Qurilma muammolari va PPR jadvalini qaytaradi"""
        key = None
        for k in EQUIPMENT_DB:
            if k in equip_type.lower() or equip_type.lower() in k:
                key = k
                break

        if not key:
            # Taxminiy qidirish
            synonyms = {
                "pump": "nasos", "pompa": "nasos",
                "kompr": "kompressor",
                "lenta": "konveyer", "транспортёр": "konveyer",
                "mill": "tegirmon", "maydalag": "tegirmon",
                "flot": "flotatsiya",
            }
            for syn, real in synonyms.items():
                if syn in equip_type.lower():
                    key = real
                    break

        if not key:
            return f"❓ '{equip_type}' uchun ma'lumot topilmadi. Mavjud: nasos, kompressor, konveyер, tegirmon, flotatsiya"

        info = EQUIPMENT_DB[key]
        lines = [f"🔧 *{key.upper()} — Muammo tahlili*\n"]
        lines.append("*Mumkin bo'lgan sabablar:*")
        lines.extend(info["muammolar"])
        lines.append("\n*Tekshirish tartibi:*")
        lines.extend(info["tekshirish"])
        lines.append(f"\n📅 *PPR jadvali:*\n_{info['ppr']}_")
        return "\n".join(lines)

    def get_safety_checklist(self, work_type: str) -> str:
        """Xavfli ish uchun xavfsizlik checklisti"""
        key = None
        mapping = {
            "elektr": "elektr", "tok": "elektr", "kabel": "elektr",
            "balandlik": "balandlik", "krovat": "balandlik", "narvon": "balandlik",
            "bosim": "bosimli_tizim", "gidravlik": "bosimli_tizim", "pnevmat": "bosimli_tizim",
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
        lines = [f"🦺 *Xavfsizlik Checklisti — {work_type}*\n",
                 f"_GOST 12.0.004 / OHSAS 18001_\n"]
        lines.extend(checklist)
        lines.append("\n⚠️ _Nazoratchi imzosisiz ish boshlanmaydi!_")
        return "\n".join(lines)

    def get_incident_guide(self, incident_type: str) -> str:
        """Hodisa bo'lganda nima qilish"""
        key = None
        if any(w in incident_type.lower() for w in ["jarohat", "baxtsiz", "qon", "kasalx"]):
            key = "jarohat"
        elif any(w in incident_type.lower() for w in ["yong'in", "olov", "yonmoq"]):
            key = "yongin"
        elif any(w in incident_type.lower() for w in ["kimyo", "kislota", "tokildi", "oqdi"]):
            key = "kimyoviy_tokilish"
        else:
            key = "jarohat"  # default

        guide = INCIDENT_GUIDE[key]
        lines = [f"🚨 *HODISA KO'RSATMASI*\n"]
        lines.extend(guide)
        lines.append("\n📞 _Kombinat dispatcher: (0379) 7-55-00_")
        lines.append("📞 _Tez yordam: 103 | Yong'in: 101_")
        return "\n".join(lines)

    def build_defect_act(self, params: dict) -> str:
        """Defekt akti shablon"""
        now = datetime.now()
        return (
            f"📋 *DEFEKT AKTI*\n"
            f"_{now.strftime('%d.%m.%Y')}_\n\n"
            f"🏭 Korxona: AGMK, 3-mis boyitish fabrika\n"
            f"👤 Mexanik: O'tkirbek\n"
            f"📍 Ish joyi: {params.get('joy', '___')}\n"
            f"⚙️ Qurilma: {params.get('qurilma', '___')}\n"
            f"🔢 Inventar №: {params.get('nomer', '___')}\n\n"
            f"❌ *Aniqlangan nuqson:*\n"
            f"{params.get('nuqson', '___')}\n\n"
            f"🔧 *Ta'mirlash ishlari:*\n"
            f"{params.get('tamirlash', '___')}\n\n"
            f"🔩 *Ehtiyot qismlar:*\n"
            f"{params.get('ehtiyot', '___')}\n\n"
            f"📅 *Rejalashtirilgan muddat:* {params.get('muddat', '___')}\n\n"
            f"✍️ Mexanik: O'tkirbek ________\n"
            f"✍️ Sex boshlig'i: ________\n"
            f"✍️ Moddiy mas'ul: ________\n\n"
            f"📌 _GOST 2.602-2013 — Ta'mirlash hujjatlari_"
        )

    def build_work_report(self, params: dict) -> str:
        """Kunlik ish hisoboti"""
        now = datetime.now()
        smena = params.get("smena", "1")
        return (
            f"📊 *KUNLIK ISH HISOBOTI*\n"
            f"_{now.strftime('%d.%m.%Y')} | Smena: {smena}_\n\n"
            f"🏭 AGMK, 3-mis boyitish fabrika | Mexanik: O'tkirbek\n\n"
            f"✅ *Bajarilgan ishlar:*\n"
            f"{params.get('bajarildi', '—')}\n\n"
            f"⏳ *Davom etayotgan ishlar:*\n"
            f"{params.get('davom', '—')}\n\n"
            f"❌ *Muammolar / Nosozliklar:*\n"
            f"{params.get('muammo', '—')}\n\n"
            f"📦 *Sarflangan ehtiyot qismlar:*\n"
            f"{params.get('sarf', '—')}\n\n"
            f"📋 *Keyingi smena uchun:*\n"
            f"{params.get('keyingi', '—')}\n\n"
            f"✍️ Mexanik: O'tkirbek ________"
        )

    def build_service_letter(self, params: dict) -> str:
        """Xizmat xati shablon"""
        now = datetime.now()
        return (
            f"📝 *XIZMAT XATI*\n\n"
            f"*Kimga:* {params.get('kimga', '___')}\n"
            f"*Kimdan:* 3-MB mexanigi O'tkirbek\n"
            f"*Sana:* {now.strftime('%d.%m.%Y')}\n"
            f"*Mavzu:* {params.get('mavzu', '___')}\n\n"
            f"{'─'*30}\n\n"
            f"{params.get('matn', '___')}\n\n"
            f"{'─'*30}\n"
            f"Iltimos, ko'rib chiqib, tegishli choralar ko'rishingizni so'rab qolaman.\n\n"
            f"Hurmat bilan,\n"
            f"O'tkirbek\n"
            f"3-mis boyitish fabrika mexanigi\n"
            f"AGMK\n"
            f"Tel: {params.get('tel', '___')}"
        )

    def hydraulic_calc(self, flow: float, dia: float, length: float,
                       visc: float = 46.0, rho: float = 870.0) -> str:
        return hydraulic_calc(flow, dia, length, visc, rho)

    def pneumatic_calc(self, vol: float, pressure: float, time: float) -> str:
        return pneumatic_calc(vol, pressure, time)

    def bearing_calc(self, C: float, P: float, n: float, btype: str = "shar") -> str:
        return bearing_life_calc(C, P, n, btype)

    async def generate_ppr_schedule(self, equipment_list: list) -> str:
        """PPR jadvali — AI yordamida"""
        equip_str = ", ".join(equipment_list)
        prompt = f"""
        Quyidagi uskunalar uchun oylik PPR (profilaktik ta'mirlash) jadvali tuz:
        {equip_str}
        
        AGMK 3-mis boyitish fabrika uchun. Har bir ushkuna uchun:
        - Kundalik tekshirish (TO-1)
        - Haftalik (TO-2)
        - Oylik (TO-3)
        - Yillik (kapital)
        
        Qisqa va aniq format. O'zbek tilida.
        """
        try:
            messages = [
                {"role": "system", "content": MECHANIC_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=messages,
                max_tokens=1500, temperature=0.3
            )
            return "📅 *PPR JADVALI*\n\n" + resp.choices[0].message.content
        except Exception as e:
            return f"❌ PPR jadval xatosi: {e}"
