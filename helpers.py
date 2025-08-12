"""Helper functions"""

import asyncio
from decimal import Decimal

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import DeviceInfo

from .coordinator import StormAudioIspCoordinator

ZERO = Decimal(0)
ONE = Decimal(1)

volume_control_decibel_range: Decimal = Decimal(60)
log_a: Decimal = Decimal(1) / (
    Decimal(10) ** (volume_control_decibel_range / Decimal(20))
)
log_b: Decimal = (Decimal(1) / Decimal(log_a)).ln()


def volume_level_to_decibels(volume_level: Decimal) -> Decimal:
    """Convert volume level (0..1) to decibels (-60..0 dB)"""
    if volume_level <= ZERO:
        return -volume_control_decibel_range
    if volume_level >= ONE:
        return ZERO
    x = log_a * (log_b * volume_level).exp()
    return Decimal(20) * x.log10()


def decibels_to_volume_level(decibels: Decimal) -> Decimal:
    """Convert decibels (-60..0 dB) to volume level (0..1)"""
    if decibels <= -volume_control_decibel_range:
        return ZERO
    if decibels >= ZERO:
        return ONE
    x = 10 ** (decibels / Decimal(20))
    return (x / log_a).ln() / log_b


async def async_wait_2_seconds_for_initial_device_state_or_raise_platform_not_ready(
    coordinator: StormAudioIspCoordinator,
) -> None:
    """Check for the initial device state in the coordinator's data; if it doesn't exist,
    wait for it up to 2 seconds; thereafter, raise PlatformNotReady exception"""
    wait_on_data: bool = True
    all_state_available: bool = False

    while True:
        if coordinator.connected and coordinator.data is not None:
            all_state_available = (
                coordinator.data["device_info"] is not None
                and coordinator.data["device_unique_id"] is not None
                and coordinator.data["device_name"] is not None
            )

        if not all_state_available and wait_on_data:
            # Device state doesn't yet have all the initial data required.
            # Give it a couple more seconds.
            await asyncio.sleep(2)
            wait_on_data = False
        else:
            break

    if not all_state_available:
        raise PlatformNotReady("Device state not yet fully loaded")
