"""
bhm_service.py - O'zbekiston Respublikasi Bazaviy hisoblash miqdori (BHM) va
jarimalarni real vaqt rejimida aniq hisoblash xizmati.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

# Tashkent vaqt mintaqasi (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))

# Ma'lumotlar papkasi
DATA_DIR = Path(__file__).parent / "data"
CONFIG_FILE = DATA_DIR / "bhm_config.json"

# Standart zaxira jadval (agar konfiguratsiya fayli topilmasa)
FALLBACK_SCHEDULE = [
    {
        "start_date": "2026-09-01",
        "amount": 440000,
        "label": "2026-yil 1-sentabrdan",
        "decree": "Prezident Farmoni"
    },
    {
        "start_date": "2025-08-01",
        "amount": 412000,
        "label": "2025-yil 1-avgustdan",
        "decree": "Prezident Farmoni"
    },
    {
        "start_date": "2024-10-01",
        "amount": 375000,
        "label": "2024-yil 1-oktabrdan",
        "decree": "PF-108-son Farmon"
    },
    {
        "start_date": "2023-12-01",
        "amount": 340000,
        "label": "2023-yil 1-dekabrdan",
        "decree": "PF-196-son Farmon"
    },
    {
        "start_date": "2023-05-01",
        "amount": 330000,
        "label": "2023-yil 1-maydan",
        "decree": "Prezident Farmoni"
    },
    {
        "start_date": "2022-06-01",
        "amount": 300000,
        "label": "2022-yil 1-iyundan",
        "decree": "Prezident Farmoni"
    }
]

_config_cache: Optional[Dict[str, Any]] = None


def load_bhm_config() -> Dict[str, Any]:
    """Konfiguratsiya faylini o'qish (keshlash bilan)"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                _config_cache = json.load(f)
                return _config_cache
        except Exception as e:
            print(f"[BHMService warning]: {e}")

    _config_cache = {
        "currency": "so'm",
        "discounts": {
            "day_15_percent": 50,
            "day_30_percent": 30,
            "day_30_pay_percent": 70
        },
        "schedule": FALLBACK_SCHEDULE
    }
    return _config_cache


def format_sum(amount: int) -> str:
    """Raqamni bo'shliqlar bilan chiroyli formatlash: masalan 440000 -> '440 000 so'm'"""
    s = f"{int(amount):,}".replace(",", " ")
    return f"{s} so'm"


def get_current_bhm(at_date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Hozirgi real vaqt sanasi bo'yicha amaldagi BHM miqdorini aniqlash.
    Agar .env yoki muhitda BHM_AMOUNT / CURRENT_BHM o'rnatilgan bo'lsa, u ustuvor bo'ladi.
    """
    env_override = os.getenv("BHM_AMOUNT") or os.getenv("CURRENT_BHM")
    if env_override:
        try:
            val = int(env_override.replace(" ", "").replace(",", ""))
            return {
                "amount": val,
                "formatted": format_sum(val),
                "label": "Qo'lda belgilangan miqdor (Environment)",
                "decree": "Maxsus sozlama",
                "start_date": "Joriy",
                "is_override": True
            }
        except ValueError:
            pass

    config = load_bhm_config()
    schedule = config.get("schedule", FALLBACK_SCHEDULE)

    if at_date is None:
        current_dt = datetime.now(TASHKENT_TZ)
    else:
        current_dt = at_date

    today_str = current_dt.strftime("%Y-%m-%d")

    # Sanalar bo'yicha kamayish tartibida saralash
    sorted_schedule = sorted(schedule, key=lambda x: x.get("start_date", ""), reverse=True)

    for item in sorted_schedule:
        if today_str >= item.get("start_date", ""):
            amount = item.get("amount", 440000)
            return {
                "amount": amount,
                "formatted": format_sum(amount),
                "label": item.get("label", ""),
                "decree": item.get("decree", ""),
                "start_date": item.get("start_date", ""),
                "is_override": False
            }

    # Jadvaldagi eng kichik qiymat
    oldest = sorted_schedule[-1]
    return {
        "amount": oldest.get("amount", 340000),
        "formatted": format_sum(oldest.get("amount", 340000)),
        "label": oldest.get("label", ""),
        "decree": oldest.get("decree", ""),
        "start_date": oldest.get("start_date", ""),
        "is_override": False
    }


def calculate_fine(multiplier: float, custom_bhm: Optional[int] = None) -> Dict[str, Any]:
    """
    BHM baravari bo'yicha to'liq summani va muddatli chegirmalarni hisoblaydi.
    15 kun ichida: 50% to'lov (50% chegirma)
    30 kun ichida: 70% to'lov (30% chegirma)
    """
    bhm_info = get_current_bhm()
    bhm_amount = custom_bhm if custom_bhm is not None else bhm_info["amount"]

    multiplier_float = float(multiplier)
    total_uzs = int(round(multiplier_float * bhm_amount))
    discount_50_uzs = int(round(total_uzs * 0.5))
    discount_70_uzs = int(round(total_uzs * 0.7))

    # BHM ko'rinishini qulay qilish (1.0 -> '1', 0.5 -> '0.5')
    mult_str = f"{multiplier_float:g}"

    return {
        "multiplier": multiplier_float,
        "multiplier_str": mult_str,
        "bhm_amount": bhm_amount,
        "bhm_formatted": format_sum(bhm_amount),
        "total_uzs": total_uzs,
        "total_formatted": format_sum(total_uzs),
        "discount_50_uzs": discount_50_uzs,
        "discount_50_formatted": format_sum(discount_50_uzs),
        "discount_70_uzs": discount_70_uzs,
        "discount_70_formatted": format_sum(discount_70_uzs),
        "label": bhm_info.get("label", ""),
        "decree": bhm_info.get("decree", "")
    }


def format_fine_card(article: str, violation: str, multiplier: float) -> str:
    """Jarima ma'lumotlarini to'liq so'm, chegirma va qoidalar bilan chiroyli markdown formatga aylantirish"""
    calc = calculate_fine(multiplier)

    if multiplier <= 0:
        return f"""📌 **{article}:** {violation}
* ⚠️ **Jarima:** Jarima solinmaydi (ma'muriy ogohlantirish yoki haydovchilik huquqidan mahrum etish jazosi qo'llaniladi)."""

    return f"""📌 **{article}:** {violation}
* 💰 **Jarima miqdori:** **{calc['multiplier_str']} BHM — {calc['total_formatted']}** *(1 BHM = {calc['bhm_formatted']})*
* ⚡ **15 kun ichida (50% chegirma):** **{calc['discount_50_formatted']}**
* ⏱ **30 kun ichida (70% to'lov):** **{calc['discount_70_formatted']}**"""


def get_bhm_overview_markdown() -> str:
    """BHM haqidagi rasmiy va to'liq ma'lumotnoma (dinamika jadvali va chegirmalar bilan)"""
    bhm_info = get_current_bhm()
    config = load_bhm_config()
    schedule = config.get("schedule", FALLBACK_SCHEDULE)

    schedule_lines = []
    for item in schedule:
        active_mark = " *(amalda)*" if item.get("start_date") == bhm_info.get("start_date") else ""
        schedule_lines.append(f"* **{item.get('label')}:** **{format_sum(item.get('amount'))}**{active_mark} — _{item.get('decree')}_")

    return f"""### 📊 O'zbekiston Respublikasida Bazaviy hisoblash miqdori (BHM)

Ayni vaqtda O'zbekistonda amaldagi Bazaviy hisoblash miqdori:
👉 **1 BHM = {bhm_info['formatted']}**  
📌 *Asos:* {bhm_info.get('decree', 'Prezident Farmoni')} ({bhm_info.get('label', '')})

---

### 📅 BHM o'zgarishlar dinamikasi (xronologiya):

{chr(10).join(schedule_lines)}

---

### ⚖️ Yo'l harakati jarimalarini to'lashda imtiyozli chegirmalar:

O'zbekiston Respublikasi Ma'muriy javobgarlik to'g'risidagi kodeksiga binoan:
* 🟢 **15 kun ichida:** Jarima miqdorining **50 foizi** to'lansa, qolgan qismidan to'liq ozod qilinadi.
* 🟡 **30 kun ichida:** Jarima miqdorining **70 foizi** to'lansa (30% chegirma), jarima to'langan hisoblanadi.
* 🔴 **30 kundan keyin:** Jarima **100% to'liq** miqdorda va qo'shimcha penya/ijro xarajatlari bilan undirilishi mumkin.

*(Eslatma: Mast holda boshqarish, takroriy qoidabuzarliklar yoki qaror ustidan shikoyat qilingan hollarda chegirmalar tatbiq etilmaydi).*"""
