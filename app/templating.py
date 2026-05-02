"""Shared Jinja2 templates instance with Persian translation lookup tables.

All routers import the same `templates` object so globals (translation dicts,
date helpers, ...) are defined in one place.
"""

from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=BASE_DIR / "templates")

templates.env.globals["now"] = datetime.utcnow

templates.env.globals["t_status"] = {
    "requested": "ثبت درخواست",
    "assigned": "اختصاص متخصص",
    "report_submitted": "گزارش ارسال شد",
    "proposal_sent": "پیش‌فاکتور ارسال شد",
    "accepted": "پذیرفته شد",
    "declined": "رد شد",
    "installed": "نصب شد",
    "completed": "تکمیل شد",
    "cancelled": "لغو شد",
}

templates.env.globals["t_severity"] = {
    "low": "کم",
    "medium": "متوسط",
    "high": "زیاد",
}

templates.env.globals["t_category"] = {
    "smart_irrigation": "آبیاری هوشمند",
    "efficient_faucet": "شیرآلات کم‌مصرف",
    "efficient_showerhead": "دوش کم‌مصرف",
    "leak_detection": "نشت‌یاب",
    "water_recycling": "بازچرخانی آب",
    "smart_meter": "کنتور هوشمند",
}

templates.env.globals["t_role"] = {
    "subscriber": "مشترک",
    "specialist": "متخصص",
    "water_company": "شرکت آب",
    "provider": "تأمین‌کننده",
    "admin": "اپراتور آبدیت",
}

templates.env.globals["t_proposal_status"] = {
    "draft": "پیش‌نویس",
    "sent": "ارسال شده",
    "accepted": "پذیرفته شده",
    "declined": "رد شده",
}

templates.env.globals["t_install_status"] = {
    "scheduled": "زمان‌بندی شده",
    "installed": "نصب شده",
    "verified": "تأیید شده",
}

templates.env.globals["t_paid"] = {True: "پرداخت‌شده", False: "پرداخت‌نشده"}
