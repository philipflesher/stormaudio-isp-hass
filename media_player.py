"""Storm Audio ISP media players"""

from __future__ import annotations
from decimal import Decimal
import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)

from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback, HomeAssistant
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from . import helpers
from .const import (
    ATTR_DETAILED_STATE,
    ATTR_SOURCE_ZONE2,
    DOMAIN,
)
from .coordinator import StormAudioIspCoordinator

from stormaudio_isp_telnet.telnet_client import DeviceState
from stormaudio_isp_telnet.constants import PowerCommand, ProcessorState


# Validation of user configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME): cv.string, vol.Required(CONF_HOST): cv.string}
)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
) -> None:
    """Setup config entry"""
    coordinator: StormAudioIspCoordinator = hass.data[DOMAIN][config.entry_id][
        "coordinator"
    ]

    await helpers.async_wait_2_seconds_for_initial_device_state_or_raise_platform_not_ready(
        coordinator
    )

    isp_device: StormAudioIspDevice = StormAudioIspDevice(coordinator)
    add_entities([isp_device])

    coordinator.data["device"] = isp_device


class StormAudioIspDevice(CoordinatorEntity, MediaPlayerEntity):
    """Storm Audio ISP device."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    _attr_extra_state_attributes = {
        ATTR_DETAILED_STATE: None,
        ATTR_SOURCE_ZONE2: None,
    }

    @property
    def detailed_state(self) -> str | None:
        """Return detailed state of the processor: 'on', 'off', 'initializing', or 'shutting down'."""
        return self._attr_extra_state_attributes[ATTR_DETAILED_STATE]

    @property
    def source_zone2(self) -> str | None:
        """Name of the current input source for Zone2."""
        return self._attr_extra_state_attributes[ATTR_SOURCE_ZONE2]

    def __init__(self, coordinator: StormAudioIspCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)

        device_info: DeviceInfo = coordinator.data["device_info"]
        device_unique_id: str = coordinator.data["device_unique_id"]
        device_name: str = coordinator.data["device_name"]

        self._attr_unique_id = device_unique_id
        self._attr_device_class = MediaPlayerDeviceClass.RECEIVER
        self._attr_icon = "mdi:audio-video"
        self._attr_name = device_name

        self._attr_device_info = device_info

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
            # on/off state
            self._attr_state = (
                MediaPlayerState.ON
                if device_state.processor_state
                in [ProcessorState.ON, ProcessorState.INITIALIZING]
                else MediaPlayerState.OFF
            )

            # detailed processor state
            self._attr_extra_state_attributes[ATTR_DETAILED_STATE] = (
                "on"
                if device_state.processor_state == ProcessorState.ON
                else "off"
                if device_state.processor_state == ProcessorState.OFF
                else "initializing"
                if device_state.processor_state == ProcessorState.INITIALIZING
                else "shutting down"
                if device_state.processor_state == ProcessorState.SHUTTING_DOWN
                else None
            )

            # inputs
            self._inputs = device_state.inputs
            self._input_id_to_input_name = None
            self._input_name_to_input_id = None
            self._attr_source_list = None
            if self._inputs is not None:
                self._input_id_to_input_name = dict(
                    map(lambda i: (i.id, i.name), self._inputs)
                )
                self._input_name_to_input_id = {
                    v: k for k, v in self._input_id_to_input_name.items()
                }
                self._attr_source_list = list(self._input_name_to_input_id.keys())

            # selected input
            self._attr_source = None
            if (
                self._input_id_to_input_name is not None
                and device_state.input_id in self._input_id_to_input_name
            ):
                self._attr_source = self._input_id_to_input_name[device_state.input_id]

            # selected Zone2 input
            self._attr_extra_state_attributes[ATTR_SOURCE_ZONE2] = None
            if (
                self._input_id_to_input_name is not None
                and device_state.input_zone2_id in self._input_id_to_input_name
            ):
                self._attr_extra_state_attributes[
                    ATTR_SOURCE_ZONE2
                ] = self._input_id_to_input_name[device_state.input_zone2_id]

            # presets
            self._presets = device_state.presets
            self._preset_id_to_preset_name = None
            self._preset_name_to_preset_id = None
            self._attr_sound_mode_list = None
            if self._presets is not None:
                self._preset_id_to_preset_name = dict(
                    map(lambda i: (i.id, i.name), self._presets)
                )
                self._preset_name_to_preset_id = {
                    v: k for k, v in self._preset_id_to_preset_name.items()
                }
                self._attr_sound_mode_list = list(self._preset_name_to_preset_id.keys())

            # selected preset
            self._attr_sound_mode = None
            if (
                self._preset_id_to_preset_name is not None
                and device_state.preset_id in self._preset_id_to_preset_name
            ):
                self._attr_sound_mode = self._preset_id_to_preset_name[
                    device_state.preset_id
                ]

            # volume level
            self._attr_volume_level = None
            decimal_volume_db: Decimal = device_state.volume_db
            if decimal_volume_db is not None:
                self._attr_volume_level = float(
                    helpers.decibels_to_volume_level(decimal_volume_db)
                )

            self._attr_is_volume_muted = device_state.mute

    async def async_select_source(self, source: str) -> None:
        """Set input source."""
        if (
            self._input_name_to_input_id is None
            or source not in self._input_name_to_input_id
        ):
            return

        await self.coordinator.async_set_input_id(self._input_name_to_input_id[source])
        self._attr_source = source
        self.async_write_ha_state()

    async def async_select_source_zone2(self, source: str) -> None:
        """Set input source for Zone2."""
        if self._input_name_to_input_id is None:
            return

        source_id: int | None = (
            self._input_name_to_input_id[source]
            if source in self._input_name_to_input_id
            else 0
        )

        await self.coordinator.async_set_input_zone2_id(source_id)
        self._attr_extra_state_attributes[ATTR_SOURCE_ZONE2] = source
        self.async_write_ha_state()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Set sound mode."""
        if (
            self._preset_name_to_preset_id is None
            or sound_mode not in self._preset_name_to_preset_id
        ):
            return

        await self.coordinator.async_set_preset_id(
            self._preset_name_to_preset_id[sound_mode]
        )
        self._attr_sound_mode = sound_mode
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.coordinator.async_set_power_state(PowerCommand.ON)
        self._attr_state = MediaPlayerState.ON
        self._attr_extra_state_attributes[ATTR_DETAILED_STATE] = "initializing"
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.coordinator.async_set_power_state(PowerCommand.OFF)
        self._attr_state = MediaPlayerState.OFF
        self._attr_extra_state_attributes[ATTR_DETAILED_STATE] = "shutting down"
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false)."""
        await self.coordinator.async_set_mute(mute)
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        if volume < 0.0 or volume > 1.0:
            return

        rounded_volume: Decimal = round(Decimal(volume), 2)
        decimal_volume_db: Decimal = helpers.volume_level_to_decibels(rounded_volume)

        await self.coordinator.async_set_volume(decimal_volume_db)
        self._attr_volume_level = volume
        self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Volume step up."""
        await self.async_set_volume_level(min(1.0, self._attr_volume_level + 0.05))

    async def async_volume_down(self) -> None:
        """Volume step down."""
        await self.async_set_volume_level(max(0.0, self._attr_volume_level - 0.05))
