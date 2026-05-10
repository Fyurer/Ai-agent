def quick_intent(text: str) -> tuple:
    # ... mavjud kodlar ...
    
    # Yangi funksiyalar
    if any(w in tl for w in ['briefing', 'ertalabki hisobot', 'kunlik hisobot']):
        return ("daily_briefing", {"voice": "-v" in tl or "ovoz" in tl})
    
    if any(w in tl for w in ['trend', 'tendentsiya']):
        m = re.search(r'trend\s+(\w+)\s+(\w+)', tl)
        if m:
            return ("trend_analysis", {"equipment": m.group(1), "sensor": m.group(2)})
    
    if any(w in tl for w in ['prognoz', 'predict', 'ehtimol']):
        m = re.search(r'prognoz\s+(\w+)', tl)
        if m:
            return ("failure_prediction", {"equipment": m.group(1)})
    
    if any(w in tl for w in ['statistika', 'performance']):
        return ("performance_stats", {"days": 7})
    
    if any(w in tl for w in ['zayavka', 'ariza', 'request']):
        m = re.search(r'zayavka\s+(\w+)\s+(\w+)\s+(\d+)', tl)
        if m:
            return ("generate_request", {"equipment": m.group(1), "part": m.group(2), "qty": m.group(3)})
    
    if any(w in tl for w in ['resurs', 'qolgan vaqt', 'part']):
        m = re.search(r'resurs\s+(\w+)', tl)
        if m:
            return ("part_life", {"part": m.group(1)})
    
    if any(w in tl for w in ['energiya', 'quvvat']):
        m = re.search(r'energiya\s+(\w+)\s+(\d+)', tl)
        if m:
            return ("energy_check", {"equipment": m.group(1), "power": m.group(2)})
    
    if any(w in tl for w in ['eslab qol', 'remember', 'xotira']):
        return ("memory_recall", {"query": text.replace("/remember", "").strip()})
    
    # ... davomi ...