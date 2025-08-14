"""Storm Audio ISP numbers."""

from __future__ import annotations

from decimal import Decimal

from stormaudio_isp_telnet.telnet_client import DeviceState, ProcessorState

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import helpers
from .const import DOMAIN
from .coordinator import StormAudioIspCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
) -> None:
    """Setup config entry."""
    coordinator: StormAudioIspCoordinator = hass.data[DOMAIN][config.entry_id][
        "coordinator"
    ]

    await helpers.async_wait_2_seconds_for_initial_device_state_or_raise_platform_not_ready(
        coordinator
    )

    device_info = coordinator.data["device_info"]
    device_unique_id = coordinator.data["device_unique_id"]
    device_name = coordinator.data["device_name"]

    add_entities(
        [
            StormAudioIspVolumeNumber(
                coordinator,
                f"{device_unique_id}_volume_level",
                f"{device_name} Volume Level",
                device_info,
            )
        ]
    )


class StormAudioIspVolumeNumber(CoordinatorEntity, NumberEntity):
    """Storm Audio ISP volume number/control."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self._attr_native_value = None

        self._attr_unique_id = unique_id
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:volume-high"
        self._attr_name = name

        self._attr_device_info = parent_device_info

        self._set_state_from_device()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._set_state_from_device()
        self.async_write_ha_state()

    def _set_state_from_device(self):
        device_state: DeviceState = self.coordinator.data["device_state"]
        self._attr_available = self.coordinator.connected

        if device_state is not None and device_state.volume_db is not None:
            self._attr_available = device_state.processor_state in [
                ProcessorState.ON,
                ProcessorState.INITIALIZING,
            ]

            decimal_volume_db: Decimal = device_state.volume_db
            fraction_value: float = float(
                helpers.decibels_to_volume_level(decimal_volume_db)
            )
            self._attr_native_value = round(fraction_value * 100.0, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        available: bool = self._attr_available
        if available:
            available = super().available
        return available

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if value < 0.0 or value > 100.0:
            return

        fraction_value: Decimal = round(Decimal(value / 100.0), 2)
        decimal_volume_db: Decimal = helpers.volume_level_to_decibels(fraction_value)

        await self.coordinator.async_set_volume(decimal_volume_db)
        self._attr_native_value = value
        self.async_write_ha_state()
