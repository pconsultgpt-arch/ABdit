"""Consumption analysis engine.

Combines per-subscriber z-score against their own historical baseline with
peer comparison against subscribers that share similar household
characteristics. Subscribers that score high on either signal are flagged.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Bill,
    ConsumptionAnomaly,
    MeterReading,
    Notification,
    Subscriber,
)

HIGH_Z = 2.0
MEDIUM_Z = 1.0
PEER_HIGH = 1.6
PEER_MEDIUM = 1.25


@dataclass
class AnalysisResult:
    subscriber_id: int
    z_score: float
    peer_ratio: float
    severity: str
    description: str


def _peer_average(db: Session, subscriber: Subscriber) -> float:
    stmt = (
        select(MeterReading.cubic_meters, Subscriber.household_size)
        .join(Subscriber, Subscriber.id == MeterReading.subscriber_id)
        .where(Subscriber.id != subscriber.id)
        .where(Subscriber.household_size.between(
            max(1, subscriber.household_size - 1),
            subscriber.household_size + 1,
        ))
        .where(Subscriber.has_garden == subscriber.has_garden)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return 0.0
    values = [r[0] for r in rows]
    return statistics.mean(values)


def analyze_subscriber(db: Session, subscriber: Subscriber) -> AnalysisResult | None:
    readings = (
        db.execute(
            select(MeterReading)
            .where(MeterReading.subscriber_id == subscriber.id)
            .order_by(MeterReading.period_end.asc())
        )
        .scalars()
        .all()
    )
    if len(readings) < 4:
        return None

    history = [r.cubic_meters for r in readings[:-1]]
    latest = readings[-1].cubic_meters

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1.0
    z = (latest - mean) / stdev

    peer_avg = _peer_average(db, subscriber) or mean
    peer_ratio = latest / peer_avg if peer_avg else 1.0

    severity = None
    if z >= HIGH_Z or peer_ratio >= PEER_HIGH:
        severity = "high"
    elif z >= MEDIUM_Z or peer_ratio >= PEER_MEDIUM:
        severity = "medium"

    if not severity:
        return None

    description = (
        f"مصرف اخیر {latest:.1f} مترمکعب است؛ {z:+.1f}σ بالاتر از میانگین این "
        f"خانوار ({mean:.1f} مترمکعب) و {peer_ratio:.2f} برابر میانگین خانوارهای "
        f"مشابه ({peer_avg:.1f} مترمکعب)."
    )

    return AnalysisResult(
        subscriber_id=subscriber.id,
        z_score=z,
        peer_ratio=peer_ratio,
        severity=severity,
        description=description,
    )


def run_full_analysis(db: Session) -> list[AnalysisResult]:
    """Analyze every subscriber, persist anomalies + notifications, return results."""
    results: list[AnalysisResult] = []
    subscribers = db.execute(select(Subscriber)).scalars().all()
    for sub in subscribers:
        result = analyze_subscriber(db, sub)
        if not result:
            continue
        results.append(result)

        anomaly = ConsumptionAnomaly(
            subscriber_id=sub.id,
            severity=result.severity,
            z_score=result.z_score,
            peer_ratio=result.peer_ratio,
            description=result.description,
        )
        db.add(anomaly)
        db.flush()

        severity_fa = {"low": "کم", "medium": "متوسط", "high": "زیاد"}[result.severity]
        notification = Notification(
            subscriber_id=sub.id,
            anomaly_id=anomaly.id,
            title=f"مصرف بالای آب شناسایی شد (شدت: {severity_fa})",
            body=(
                result.description
                + " می‌توانید از یک ارزیابی رایگان بهینه‌مصرف آب توسط متخصص دارای "
                "گواهی آبدیت بهره‌مند شوید. مشارکت اختیاری است."
            ),
        )
        db.add(notification)
    db.commit()
    return results


def estimate_savings(bills: list[Bill], expected_pct: float) -> dict[str, float]:
    if not bills:
        return {"yearly_m3": 0.0, "yearly_amount": 0.0}
    last_year = bills[-12:] if len(bills) >= 12 else bills
    total_m3 = sum(b.cubic_meters for b in last_year)
    total_amount = sum(b.amount for b in last_year)
    factor = expected_pct / 100.0
    return {
        "yearly_m3": total_m3 * factor,
        "yearly_amount": total_amount * factor,
    }


def fmt_pct(x: float) -> str:
    return f"{x:.1f}%" if not math.isnan(x) else "—"
