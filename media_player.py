"""Main integration"""

from __future__ import annotations
import asyncio
from decimal import Decimal
import logging
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
    DataUpdateCoordinator,
)

from stormaudio_isp_telnet.telnet_client import DeviceState, TelnetClient
from stormaudio_isp_telnet.constants import PowerCommand, ProcessorState

from .const import (
    ATTR_DETAILED_STATE,
    ATTR_SOURCE_ZONE2,
    DOMAIN,
)

_LOGGER = logging.getLogger("stormaudio_isp")

# Validation of user configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME): cv.string, vol.Required(CONF_HOST): cv.string}
)


ZERO = Decimal(0)
ONE = Decimal(1)
ONE_HUNDRED = Decimal(100)

volume_control_decibel_range: Decimal = Decimal(60)
log_a: Decimal = Decimal(1) / (
    Decimal(10) ** (volume_control_decibel_range / Decimal(20))
)
log_b: Decimal = (Decimal(1) / Decimal(log_a)).ln()


def volume_level_to_decibels(volume_level: Decimal) -> Decimal:
    """Convert volume level (0..1) to decibels (-60..0 dB)"""
    if volume_level <= ZERO:
        return ONE_HUNDRED
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


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
) -> None:
    """Setup config entry"""
    is_initial_device_state_set: bool = False
    wait_on_data: bool = True

    while True:
        coordinator: StormAudioIspCoordinator = hass.data[DOMAIN][config.entry_id][
            "coordinator"
        ]

        if coordinator.connected and coordinator.data is not None:
            device_state = coordinator.data["device_state"]
            if (
                device_state is not None
                and device_state.brand is not None
                and device_state.model is not None
            ):
                is_initial_device_state_set = True

        if not is_initial_device_state_set and wait_on_data:
            # Device state doesn't yet have all the initial data required.
            # Give it a couple more seconds.
            await asyncio.sleep(2)
            wait_on_data = False
        else:
            break

    if not is_initial_device_state_set:
        raise PlatformNotReady("Device state not yet fully loaded")

    add_entities([StormAudioIspDevice(coordinator)])


class StormAudioIspCoordinator(DataUpdateCoordinator):
    """Storm Audio ISP data update coordinator."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Storm Audio ISP",
        )
        self._host: str = host
        self._telnet_client: TelnetClient = TelnetClient(
            self._host,
            async_on_device_state_updated=self._async_on_device_state_updated,
            async_on_disconnected=self._async_on_disconnected,
        )
        self._connected: bool = False
        self._should_reconnect: bool = False
        self._connection_task: asyncio.Task = None

    @property
    def connected(self):
        """Gets a value indicating whether the underlying connection is established."""
        return self._connected

    def connect_and_stay_connected(self) -> None:
        """Connect to the ISP; if the connection is dropped, reconnect indefinitely."""
        self._should_reconnect = True
        self._connection_task = asyncio.create_task(self._async_connect())

    async def _async_connect(self):
        while True:
            try:
                await self._telnet_client.async_connect()
                self._connected = True
                await self._async_on_device_state_updated()
                break
            except ConnectionError:
                if not self._should_reconnect:
                    break
                await asyncio.sleep(2)

    async def _async_on_disconnected(self) -> None:
        self._connected = False
        await self._async_on_device_state_updated()
        if self._should_reconnect:
            self.connect_and_stay_connected()

    async def async_disconnect(self) -> None:
        """Disconnect from the ISP."""
        self._should_reconnect = False
        if self._connection_task is not None:
            await self._connection_task
        await self._telnet_client.async_disconnect()

    async def _async_on_device_state_updated(self) -> None:
        device_state: DeviceState = self._telnet_client.get_device_state()
        data = {"device_state": device_state}
        self.async_set_updated_data(data)

    async def async_set_power_state(self, power_command: PowerCommand):
        """Set power state (on/off)"""
        await self._telnet_client.async_set_power_command(power_command)

    async def async_set_input_id(self, input_id: int):
        """Set input ID"""
        await self._telnet_client.async_set_input_id(input_id)

    async def async_set_input_zone2_id(self, input_zone2_id: int):
        """Set input Zone2 ID"""
        await self._telnet_client.async_set_input_zone2_id(input_zone2_id)

    async def async_set_volume(self, volume_db: Decimal):
        """Set volume in dB (-100..0)"""
        await self._telnet_client.async_set_volume(volume_db)

    async def async_set_mute(self, mute: bool):
        """Set mute (True == muted, False == unmuted)"""
        await self._telnet_client.async_set_mute(mute)

    async def async_set_preset_id(self, preset_id: int):
        """Set preset ID"""
        await self._telnet_client.async_set_preset_id(preset_id)


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

    def __init__(self, coordinator: StormAudioIspCoordinator):
        """Initialize."""
        super().__init__(coordinator)

        device_state: DeviceState = coordinator.data["device_state"]

        self._attr_unique_id = coordinator.config_entry.unique_id
        self._attr_device_class = MediaPlayerDeviceClass.RECEIVER
        self._attr_icon = "mdi:audio-video"
        self._attr_name = coordinator.config_entry.title

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer=device_state.brand,
            model=device_state.model,
            name=self._attr_name,
        )

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
            decimal_volume_db: Decimal = device_state.volume_db
            self._attr_volume_level = float(decibels_to_volume_level(decimal_volume_db))

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
        self._attr_extra_state_attributes[ATTR_DETAILED_STATE] = 'initializing'
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.coordinator.async_set_power_state(PowerCommand.OFF)
        self._attr_state = MediaPlayerState.OFF
        self._attr_extra_state_attributes[ATTR_DETAILED_STATE] = 'shutting down'

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
        decimal_volume_db: Decimal = volume_level_to_decibels(rounded_volume)

        await self.coordinator.async_set_volume(decimal_volume_db)
        self._attr_volume_level = volume
        self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Volume step up."""
        await self.async_set_volume_level(min(1.0, self._attr_volume_level + 0.05))

    async def async_volume_down(self) -> None:
        """Volume step down."""
        await self.async_set_volume_level(max(0.0, self._attr_volume_level - 0.05))
