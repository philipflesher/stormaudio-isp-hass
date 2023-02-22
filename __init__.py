"""Storm Audio ISP Integration"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.reload import async_setup_reload_service

from .coordinator import StormAudioIspCoordinator

from .const import DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup config entry"""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    host: str = entry.data["host"]
    coordinator = StormAudioIspCoordinator(hass, host)
    coordinator.connect_and_stay_connected()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "host": host,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry"""
    coordinator: StormAudioIspCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    await coordinator.async_disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
