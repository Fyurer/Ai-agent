# ── Yangi importlar ───────────────────────────────────────────
from analytics_service import AnalyticsService
from briefing_service import BriefingService
from spare_parts_service import SparePartsService

# ── Servislarni ishga tushirish ───────────────────────────────
analytics = AnalyticsService()
briefing = BriefingService()
spare_parts = SparePartsService()

# ════════════════════════════════════════════════════════════
#  YANGI BUYRUQLAR
# ════════════════════════════════════════════════════════════

@dp.message(Command("briefing"))
async def cmd_briefing(msg: Message):
    """Kunlik briefing — matnli yoki ovozli"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    as_voice = "-v" in args or "--voice" in args
    
    wait = await msg.answer("📊 _Briefing tayyorlanmoqda..._")
    
    if as_voice:
        audio = await briefing.generate_audio_briefing()
        if audio:
            await wait.delete()
            await msg.answer_voice(BufferedInputFile(audio, filename="briefing.mp3"))
        else:
            text = await briefing.generate_daily_briefing()
            await wait.edit_text(text)
    else:
        text = await briefing.generate_daily_briefing()
        await wait.edit_text(text)

@dp.message(Command("trend"))
async def cmd_trend(msg: Message):
    """Trend tahlili: /trend nasos_1 vibration"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer(
            "📈 *Trend tahlili*\n\n"
            "Ishlatish:\n"
            "`/trend nasos_1 vibration`\n"
            "`/trend tegirmon_1 temperature`\n"
            "`/trend kompressor_1 pressure`"
        )
        return
    
    equipment = args[1]
    sensor_type = args[2]
    
    wait = await msg.answer(f"📊 _Trend tahlili: {equipment} - {sensor_type}_")
    
    result = await analytics.get_sensor_trend(equipment, sensor_type)
    if "error" in result:
        await wait.edit_text(f"❌ {result['error']}")
    else:
        response = (
            f"📈 *Trend Tahlili*\n"
            f"⚙️ {equipment}\n"
            f"📊 Parametr: {sensor_type}\n\n"
            f"📉 Trend: {result['trend']}\n"
            f"📐 Nishablik: {result['slope']}\n"
            f"💎 Oxirgi qiymat: {result['last_value']}\n"
            f"🔄 O'zgarish: {result['change_rate']}%\n\n"
            f"💡 {result['advice']}"
        )
        await wait.edit_text(response)

@dp.message(Command("predict"))
async def cmd_predict(msg: Message):
    """Uskuna ishdan chiqish ehtimoli: /predict nasos_1"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("Ishlatish: `/predict nasos_1`")
        return
    
    equipment = args[1]
    wait = await msg.answer(f"🔮 _Prognoz: {equipment}_")
    
    result = await analytics.predict_failure_probability(equipment)
    
    response = f"🔮 *Ishdan chiqish ehtimoli — {equipment}*\n\n"
    response += f"🎲 Ehtimol: {result['probability']}\n"
    if result['estimated_days']:
        response += f"⏱ Taxminiy muddat: {result['estimated_days']} kun\n"
    response += f"\n💡 {result['advice']}"
    
    if result['critical_params']:
        response += f"\n\n⚠️ *Kritik parametrlar:*\n"
        for p in result['critical_params']:
            response += f"  • {p}\n"
    
    await wait.edit_text(response)

@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    """Ish samaradorligi statistikasi"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
    
    wait = await msg.answer(f"📊 _Statistika yig'ilmoqda ({days} kun)..._")
    
    metrics = await analytics.get_performance_metrics(days)
    
    response = (
        f"📊 *Ish Samaradorligi — {days} kun*\n\n"
        f"📨 Jami muammolar: {metrics['total_issues']}\n"
        f"✅ Hal qilingan: {metrics['solved']}\n"
        f"📈 Yechim darajasi: {metrics['resolution_rate']}%\n\n"
        f"🔝 *Eng ko'p uchraydigan:*\n"
    )
    
    for p in metrics['top_problems'][:5]:
        response += f"  • {p['problem']}: {p['count']} marta\n"
    
    await wait.edit_text(response)

@dp.message(Command("part"))
async def cmd_part(msg: Message):
    """Ehtiyot qism resursi: /part podshipnik_6310 16"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer(
            "🔧 *Ehtiyot qismlar kalkulyatori*\n\n"
            "Ishlatish:\n"
            "`/part podshipnik_6310 16` — 16 soat/sutka bilan hisoblash\n"
            "`/part muhr_nasos` — faqat ma'lumot\n\n"
            "Mavjud qismlar:\n"
            "• podshipnik_6310, podshipnik_6312\n"
            "• salnik_45x62x8, muhr_nasos\n"
            "• lenta_konveyer, rolik_konveyer\n"
            "• filtr_hp, liner_tegirmon"
        )
        return
    
    part_name = args[1]
    daily_hours = float(args[2]) if len(args) > 2 and args[2].replace('.', '').isdigit() else 0
    
    result = spare_parts.calculate_remaining_life(part_name, daily_hours, 0)
    
    if not result["found"]:
        await msg.answer(f"❌ {result['message']}")
        return
    
    response = (
        f"🔧 *Ehtiyot qism resursi*\n\n"
        f"📦 Nomi: {result['part_name']}\n"
        f"🔢 Kodi: {result['part_code']}\n"
        f"⏱ Umumiy resurs: {result['total_life_hours']} soat\n"
        f"📊 Qolgan: {result['remaining_hours']} soat\n"
    )
    if result['remaining_days']:
        response += f"📅 Kunlarda: ~{result['remaining_days']} kun\n"
    response += f"\n⚡ Holat: {result['status']}\n"
    response += f"💡 {result['advice']}"
    
    await msg.answer(response)

@dp.message(Command("request"))
async def cmd_request(msg: Message):
    """Ariza (zayavka) yaratish: /request nasos salnik 3"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    if len(args) < 4:
        await msg.answer(
            "📋 *Ariza generatori*\n\n"
            "Ishlatish:\n"
            "`/request nasos_1 podshipnik_6310 2`\n"
            "Ariza avtomatik tayyorlanadi"
        )
        return
    
    equipment = args[1]
    part_name = args[2]
    quantity = int(args[3])
    reason = " ".join(args[4:]) if len(args) > 4 else ""
    
    request_text = spare_parts.generate_request(equipment, part_name, quantity, reason)
    await msg.answer(request_text)

@dp.message(Command("energy"))
async def cmd_energy(msg: Message):
    """Energiya sarfi anomaliyasi: /energy nasos_1 85"""
    if not is_owner(msg): return
    
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer("Ishlatish: `/energy nasos_1 85` (85 kW joriy quvvat)")
        return
    
    equipment = args[1]
    current_power = float(args[2])
    
    result = await analytics.get_energy_anomaly(equipment, current_power)
    
    response = (
        f"⚡ *Energiya sarfi tahlili*\n"
        f"⚙️ {equipment}\n\n"
        f"📊 Joriy quvvat: {result['current_kw']} kW\n"
        f"📋 Nominal: {result['nominal_kw']} kW\n"
        f"📉 Normadan: {result['deviation_percent']}%\n"
        f"🚦 Holat: {result['anomaly']}\n\n"
        f"💡 {result['advice']}"
    )
    
    await msg.answer(response)

@dp.message(Command("remember"))
async def cmd_remember(msg: Message):
    """Avvalgi suhbatlarni eslab qolish: /remember nasos muammosi"""
    if not is_owner(msg): return
    
    query = msg.text.replace("/remember", "").strip()
    if not query:
        await msg.answer("Nimani eslash kerak? Masalan: `/remember nasos`")
        return
    
    wait = await msg.answer(f"📚 _Xotira qidiruvi: '{query}'_")
    
    context = await db.get_conversation_memory_context(query)
    if context:
        await wait.edit_text(context)
    else:
        await wait.edit_text(f"📚 '{query}' haqida xotirada ma'lumot topilmadi.")