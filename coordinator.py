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
