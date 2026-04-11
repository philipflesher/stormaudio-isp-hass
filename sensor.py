"""Storm Audio ISP sensors."""

from __future__ import annotations

from stormaudio_isp_telnet.telnet_client import DeviceState, ProcessorState

from homeassistant.components.sensor import SensorEntity
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
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_sample_rate",
                f"{device_name} Sample Rate",
                device_info,
                icon="mdi:sine-wave",
                get_value_fn=lambda ds: ds.sample_rate,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_stream_type",
                f"{device_name} Stream Type",
                device_info,
                icon="mdi:surround-sound",
                get_value_fn=lambda ds: ds.stream_type,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_channel_format",
                f"{device_name} Channel Format",
                device_info,
                icon="mdi:speaker-multiple",
                get_value_fn=lambda ds: ds.channel_format,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_firmware_version",
                f"{device_name} Firmware Version",
                device_info,
                icon="mdi:chip",
                get_value_fn=lambda ds: ds.firmware_version,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_hdmi1_timing",
                f"{device_name} HDMI 1 Timing",
                device_info,
                icon="mdi:hdmi-port",
                get_value_fn=lambda ds: ds.hdmi1_timing,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_hdmi1_hdr",
                f"{device_name} HDMI 1 HDR",
                device_info,
                icon="mdi:hdmi-port",
                get_value_fn=lambda ds: ds.hdmi1_hdr,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_hdmi2_timing",
                f"{device_name} HDMI 2 Timing",
                device_info,
                icon="mdi:hdmi-port",
                get_value_fn=lambda ds: ds.hdmi2_timing,
            ),
            StormAudioIspSensor(
                coordinator,
                f"{device_unique_id}_hdmi2_hdr",
                f"{device_name} HDMI 2 HDR",
                device_info,
                icon="mdi:hdmi-port",
                get_value_fn=lambda ds: ds.hdmi2_hdr,
            ),
        ]
    )


class StormAudioIspSensor(CoordinatorEntity, SensorEntity):
    """Generic Storm Audio ISP sensor entity."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
        icon: str,
        get_value_fn,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_native_value = None
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self._attr_name = name
        self._attr_device_info = parent_device_info
        self._get_value_fn = get_value_fn

        self._set_state_from_device()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._set_state_from_device()
        self.async_write_ha_state()

    def _set_state_from_device(self):
        device_state: DeviceState = self.coordinator.data["device_state"]
        self._attr_available = self.coordinator.connected

        if device_state is not None:
            self._attr_available = device_state.processor_state in [
                ProcessorState.ON,
                ProcessorState.INITIALIZING,
            ]
            self._attr_native_value = self._get_value_fn(device_state)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        available: bool = self._attr_available
        if available:
            available = super().available
        return available
