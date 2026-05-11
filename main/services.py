"""Business logic: load balancing across the ESP32-controlled devices.

The algorithm runs on every telemetry packet:

1. Refresh the device's `last_power_watts` and `last_seen_at` so the snapshot
   of "what is the network drawing right now" stays up to date.
2. Sum the current draw over all `is_on` devices.
3. If the sum exceeds the operator-configured limit, shed the lowest-priority
   (highest `priority` value) devices one by one until the system is back
   below the limit or no more devices can be shed.
4. Otherwise, if there is enough slack, try to restore the highest-priority
   (lowest `priority` value) previously-shed device — but only if doing so
   would not push the total back over the limit.

All mutations happen inside a single DB transaction so a concurrent telemetry
post cannot observe a half-rebalanced state.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from .models import Device, SystemSettings, Telemetry


logger = logging.getLogger(__name__)


@dataclass
class BalancingReport:
    """Summary of what the algorithm changed during a single rebalance pass."""

    total_power_watts: float = 0.0
    power_limit_watts: int = 0
    is_overloaded: bool = False
    shed_devices: list[str] = field(default_factory=list)
    restored_devices: list[str] = field(default_factory=list)


def _current_total_load(devices: Iterable[Device]) -> float:
    """Sum the last known power draw across the devices that are ON."""
    return float(sum(d.last_power_watts for d in devices if d.is_on))


def _shed_one(devices: list[Device]) -> Device | None:
    """Turn off the on-device with the lowest priority (highest priority number).

    Returns the device that was switched off, or None if nothing could be shed.
    """
    candidates = [d for d in devices if d.is_on]
    if not candidates:
        return None
    victim = max(candidates, key=lambda d: (d.priority, d.last_power_watts))
    victim.is_on = False
    victim.save(update_fields=['is_on', 'updated_at'])
    return victim


def _restore_one(devices: list[Device], headroom_watts: float) -> Device | None:
    """Turn back on the highest-priority off-device that fits within headroom.

    `headroom_watts` is `limit - current_total`. We only flip a device on if
    its estimated draw (its last known reading) leaves the system below the
    limit, so we do not immediately trigger a new shedding pass.
    """
    if headroom_watts <= 0:
        return None

    off_devices = [d for d in devices if not d.is_on and d.last_power_watts > 0]
    if not off_devices:
        return None

    off_devices.sort(key=lambda d: (d.priority, -d.last_power_watts))
    for device in off_devices:
        if device.last_power_watts <= headroom_watts:
            device.is_on = True
            device.save(update_fields=['is_on', 'updated_at'])
            return device
    return None


@transaction.atomic
def record_telemetry(device: Device, power_watts: float) -> Telemetry:
    """Persist a telemetry sample and refresh the device's live-state fields.

    Wrapped in `select_for_update` so two concurrent posts for the same device
    cannot interleave their writes to `last_power_watts`.
    """
    locked = Device.objects.select_for_update().get(pk=device.pk)
    locked.last_power_watts = float(power_watts)
    locked.last_seen_at = timezone.now()
    locked.save(update_fields=['last_power_watts', 'last_seen_at', 'updated_at'])

    sample = Telemetry.objects.create(device=locked, power_watts=power_watts)
    return sample


@transaction.atomic
def rebalance_load() -> BalancingReport:
    """Run the shed/restore loop and return what changed.

    Designed to be called immediately after :func:`record_telemetry`. Safe to
    call standalone (e.g. from a management command or admin action).
    """
    settings_row = SystemSettings.load()
    report = BalancingReport(
        power_limit_watts=settings_row.power_limit_watts,
    )

    if not settings_row.is_active:
        logger.info('Balancing skipped: SystemSettings.is_active=False')
        devices = list(Device.objects.select_for_update().all())
        report.total_power_watts = _current_total_load(devices)
        report.is_overloaded = report.total_power_watts > settings_row.power_limit_watts
        return report

    devices = list(Device.objects.select_for_update().all())
    total = _current_total_load(devices)

    # Shed phase: keep dropping the lowest-priority device until we are within
    # the limit or there is nothing left to drop.
    while total > settings_row.power_limit_watts:
        victim = _shed_one(devices)
        if victim is None:
            break
        report.shed_devices.append(victim.device_id)
        total -= victim.last_power_watts
        logger.warning(
            'Shed device %s (priority=%d, draw=%.1fW); new total=%.1fW',
            victim.device_id, victim.priority, victim.last_power_watts, total,
        )

    # Restore phase: only when there is comfortable headroom. Repeat as long
    # as the algorithm can fit another previously-shed device.
    while True:
        headroom = settings_row.power_limit_watts - total
        restored = _restore_one(devices, headroom)
        if restored is None:
            break
        report.restored_devices.append(restored.device_id)
        total += restored.last_power_watts
        logger.info(
            'Restored device %s (priority=%d, draw=%.1fW); new total=%.1fW',
            restored.device_id, restored.priority, restored.last_power_watts, total,
        )

    report.total_power_watts = total
    report.is_overloaded = total > settings_row.power_limit_watts
    return report


def ingest_and_rebalance(device: Device, power_watts: float) -> tuple[Telemetry, BalancingReport]:
    """High-level entry point used by the telemetry endpoint."""
    sample = record_telemetry(device, power_watts)
    report = rebalance_load()
    return sample, report
