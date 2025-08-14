"""Storm Audio ISP switches."""

from __future__ import annotations

from stormaudio_isp_telnet.telnet_client import DeviceState, ProcessorState

from homeassistant.components.switch import SwitchEntity
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
            StormAudioIspMuteSwitch(
                coordinator,
                f"{device_unique_id}_mute",
                f"{device_name} Mute",
                device_info,
            )
        ]
    )


class StormAudioIspMuteSwitch(CoordinatorEntity, SwitchEntity):
    """Storm Audio ISP mute switch."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_native_value = None

        self._attr_unique_id = unique_id
        self._attr_icon = "mdi:volume-mute"
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

            self._attr_native_value = device_state.mute

    @property
    def is_on(self) -> bool:
        """Return the state of the switch (muted == True/"on")."""
        return self._attr_native_value

    async def async_turn_on(self) -> None:
        """Turn the switch on (mute)."""
        await self.coordinator.async_set_mute(True)

    async def async_turn_off(self) -> None:
        """Turn the switch off (unmute)."""
        await self.coordinator.async_set_mute(False)
