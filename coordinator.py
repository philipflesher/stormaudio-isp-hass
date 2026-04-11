"""Storm Audio ISP data update coordinator."""

from __future__ import annotations

import asyncio
from decimal import Decimal
import logging

from stormaudio_isp_telnet.constants import PowerCommand
from stormaudio_isp_telnet.telnet_client import DeviceState, TelnetClient
import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger("stormaudio_isp")

# Validation of user configuration
MEDIA_PLAYER_PLATFORM_SCHEMA = MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME): cv.string, vol.Required(CONF_HOST): cv.string}
)


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
    def connected(self) -> bool:
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
        device_unique_id: str = self.config_entry.unique_id
        device_name: str = self.config_entry.title
        device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, device_unique_id)},
            manufacturer=device_state.brand,
            model=device_state.model,
            name=device_name,
        )
        data = {
            "device_state": device_state,
            "device_unique_id": device_unique_id,
            "device_name": device_name,
            "device_info": device_info,
        }
        self.async_set_updated_data(data)

    async def async_set_power_state(self, power_command: PowerCommand):
        """Set power state (on/off)."""
        await self._telnet_client.async_set_power_command(power_command)

    async def async_set_input_id(self, input_id: int):
        """Set input ID."""
        await self._telnet_client.async_set_input_id(input_id)

    async def async_set_input_zone2_id(self, input_zone2_id: int):
        """Set input Zone2 ID."""
        await self._telnet_client.async_set_input_zone2_id(input_zone2_id)

    async def async_set_volume(self, volume_db: Decimal):
        """Set volume in dB (-100..0)."""
        await self._telnet_client.async_set_volume(volume_db)

    async def async_set_mute(self, mute: bool):
        """Set mute (True == muted, False == unmuted)."""
        await self._telnet_client.async_set_mute(mute)

    async def async_toggle_mute(self):
        """Toggle mute."""
        await self._telnet_client.async_toggle_mute()

    async def async_set_preset_id(self, preset_id: int):
        """Set preset ID."""
        await self._telnet_client.async_set_preset_id(preset_id)

    # ---- Zone commands ----

    async def async_set_zone_volume(self, zone_id: int, volume_db):
        """Set zone volume in dB."""
        await self._telnet_client.async_set_zone_volume(zone_id, volume_db)

    async def async_set_zone_mute(self, zone_id: int, mute: bool):
        """Set zone mute."""
        await self._telnet_client.async_set_zone_mute(zone_id, mute)

    async def async_set_zone_eq(self, zone_id: int, enabled: bool):
        """Set zone EQ on/off."""
        await self._telnet_client.async_set_zone_eq(zone_id, enabled)

    async def async_set_zone_bass(self, zone_id: int, value: int):
        """Set zone bass."""
        await self._telnet_client.async_set_zone_bass(zone_id, value)

    async def async_set_zone_treble(self, zone_id: int, value: int):
        """Set zone treble."""
        await self._telnet_client.async_set_zone_treble(zone_id, value)

    async def async_set_zone_loudness(self, zone_id: int, value: int):
        """Set zone loudness."""
        await self._telnet_client.async_set_zone_loudness(zone_id, value)

    async def async_set_zone_lipsync(self, zone_id: int, ms: int):
        """Set zone lipsync delay."""
        await self._telnet_client.async_set_zone_lipsync(zone_id, ms)

    # ---- Theater audio controls ----

    async def async_set_dim(self, enabled: bool):
        """Set dim on/off."""
        await self._telnet_client.async_set_dim(enabled)

    async def async_set_bass(self, value: int):
        """Set main bass."""
        await self._telnet_client.async_set_bass(value)

    async def async_set_treble(self, value: int):
        """Set main treble."""
        await self._telnet_client.async_set_treble(value)

    async def async_set_brightness(self, value: int):
        """Set main brightness."""
        await self._telnet_client.async_set_brightness(value)

    async def async_set_center_enhance(self, value: int):
        """Set center enhance."""
        await self._telnet_client.async_set_center_enhance(value)

    async def async_set_surround_enhance(self, value: int):
        """Set surround enhance."""
        await self._telnet_client.async_set_surround_enhance(value)

    async def async_set_lfe_enhance(self, value: int):
        """Set LFE enhance."""
        await self._telnet_client.async_set_lfe_enhance(value)

    async def async_set_loudness(self, value: int):
        """Set main loudness."""
        await self._telnet_client.async_set_loudness(value)

    async def async_set_lipsync(self, value: int):
        """Set main lipsync."""
        await self._telnet_client.async_set_lipsync(value)

    async def async_set_surround_mode(self, mode_id: int):
        """Set surround mode."""
        await self._telnet_client.async_set_surround_mode(mode_id)

    async def async_set_drc(self, mode: str):
        """Set DRC mode."""
        await self._telnet_client.async_set_drc(mode)

    async def async_set_dialog_control(self, value: int):
        """Set dialog control level."""
        await self._telnet_client.async_set_dialog_control(value)

    async def async_set_dialog_norm(self, enabled: bool):
        """Set dialog norm on/off."""
        await self._telnet_client.async_set_dialog_norm(enabled)

    async def async_set_dolby_mode(self, mode_id: int):
        """Set Dolby mode."""
        await self._telnet_client.async_set_dolby_mode(mode_id)

    async def async_set_storm_xt(self, enabled: bool):
        """Set Storm XT on/off."""
        await self._telnet_client.async_set_storm_xt(enabled)

    async def async_set_lfe_dim(self, enabled: bool):
        """Set LFE dim on/off."""
        await self._telnet_client.async_set_lfe_dim(enabled)

    async def async_set_trigger(self, trigger_id: int, enabled: bool):
        """Set trigger on/off."""
        await self._telnet_client.async_set_trigger(trigger_id, enabled)
