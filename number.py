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
    device_state: DeviceState = coordinator.data["device_state"]

    entities = [
        StormAudioIspVolumeNumber(
            coordinator,
            f"{device_unique_id}_volume_level",
            f"{device_name} Volume Level",
            device_info,
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_bass",
            f"{device_name} Bass",
            device_info,
            icon="mdi:music-clef-bass",
            min_value=-6,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.bass,
            is_available_fn=lambda ds: ds.bass is not None,
            async_set_fn=lambda coord, val: coord.async_set_bass(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_treble",
            f"{device_name} Treble",
            device_info,
            icon="mdi:music-clef-treble",
            min_value=-6,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.treble,
            is_available_fn=lambda ds: ds.treble is not None,
            async_set_fn=lambda coord, val: coord.async_set_treble(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_brightness",
            f"{device_name} Brightness",
            device_info,
            icon="mdi:brightness-6",
            min_value=-6,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.brightness,
            is_available_fn=lambda ds: ds.brightness is not None,
            async_set_fn=lambda coord, val: coord.async_set_brightness(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_center_enhance",
            f"{device_name} Center Enhance",
            device_info,
            icon="mdi:surround-sound",
            min_value=-6,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.center_enhance,
            is_available_fn=lambda ds: ds.center_enhance is not None,
            async_set_fn=lambda coord, val: coord.async_set_center_enhance(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_surround_enhance",
            f"{device_name} Surround Enhance",
            device_info,
            icon="mdi:surround-sound",
            min_value=-6,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.surround_enhance,
            is_available_fn=lambda ds: ds.surround_enhance is not None,
            async_set_fn=lambda coord, val: coord.async_set_surround_enhance(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_lfe_enhance",
            f"{device_name} LFE Enhance",
            device_info,
            icon="mdi:speaker",
            min_value=-6,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.lfe_enhance,
            is_available_fn=lambda ds: ds.lfe_enhance is not None,
            async_set_fn=lambda coord, val: coord.async_set_lfe_enhance(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_lipsync",
            f"{device_name} Lipsync",
            device_info,
            icon="mdi:timer-outline",
            min_value=0,
            max_value=500,
            step=1,
            unit="ms",
            get_value_fn=lambda ds: ds.lipsync,
            is_available_fn=lambda ds: ds.lipsync is not None,
            async_set_fn=lambda coord, val: coord.async_set_lipsync(int(val)),
        ),
        StormAudioIspNumber(
            coordinator,
            f"{device_unique_id}_dialog_control",
            f"{device_name} Dialog Control",
            device_info,
            icon="mdi:account-voice",
            min_value=0,
            max_value=6,
            step=1,
            get_value_fn=lambda ds: ds.dialog_control,
            is_available_fn=lambda ds: ds.dialog_control is not None,
            async_set_fn=lambda coord, val: coord.async_set_dialog_control(int(val)),
        ),
    ]

    # Per-zone number entities
    if device_state is not None and device_state.zones is not None:
        for zone in device_state.zones:
            zone_id = zone.id
            zone_name = zone.name

            entities.extend(
                [
                    StormAudioIspZoneVolumeNumber(
                        coordinator,
                        f"{device_unique_id}_zone{zone_id}_volume",
                        f"{device_name} {zone_name} Volume",
                        device_info,
                        zone_id,
                    ),
                    StormAudioIspNumber(
                        coordinator,
                        f"{device_unique_id}_zone{zone_id}_bass",
                        f"{device_name} {zone_name} Bass",
                        device_info,
                        icon="mdi:music-clef-bass",
                        min_value=-6,
                        max_value=6,
                        step=1,
                        get_value_fn=lambda ds, zid=zone_id: _get_zone_attr(
                            ds, zid, "bass"
                        ),
                        is_available_fn=lambda ds, zid=zone_id: _get_zone(ds, zid)
                        is not None,
                        async_set_fn=lambda coord, val, zid=zone_id: coord.async_set_zone_bass(
                            zid, int(val)
                        ),
                    ),
                    StormAudioIspNumber(
                        coordinator,
                        f"{device_unique_id}_zone{zone_id}_treble",
                        f"{device_name} {zone_name} Treble",
                        device_info,
                        icon="mdi:music-clef-treble",
                        min_value=-6,
                        max_value=6,
                        step=1,
                        get_value_fn=lambda ds, zid=zone_id: _get_zone_attr(
                            ds, zid, "treble"
                        ),
                        is_available_fn=lambda ds, zid=zone_id: _get_zone(ds, zid)
                        is not None,
                        async_set_fn=lambda coord, val, zid=zone_id: coord.async_set_zone_treble(
                            zid, int(val)
                        ),
                    ),
                    StormAudioIspNumber(
                        coordinator,
                        f"{device_unique_id}_zone{zone_id}_lipsync",
                        f"{device_name} {zone_name} Lipsync",
                        device_info,
                        icon="mdi:timer-outline",
                        min_value=0,
                        max_value=500,
                        step=1,
                        unit="ms",
                        get_value_fn=lambda ds, zid=zone_id: _get_zone_attr(
                            ds, zid, "lipsync_ms"
                        ),
                        is_available_fn=lambda ds, zid=zone_id: _get_zone(ds, zid)
                        is not None,
                        async_set_fn=lambda coord, val, zid=zone_id: coord.async_set_zone_lipsync(
                            zid, int(val)
                        ),
                    ),
                ]
            )

    add_entities(entities)


def _get_zone(device_state: DeviceState, zone_id: int):
    """Get a zone by ID from device state."""
    if device_state is None or device_state.zones is None:
        return None
    for zone in device_state.zones:
        if zone.id == zone_id:
            return zone
    return None


def _get_zone_attr(device_state: DeviceState, zone_id: int, attr: str):
    """Get a zone attribute by zone ID."""
    zone = _get_zone(device_state, zone_id)
    if zone is None:
        return None
    return getattr(zone, attr, None)


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


class StormAudioIspZoneVolumeNumber(CoordinatorEntity, NumberEntity):
    """Storm Audio ISP zone volume number/control."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
        zone_id: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._zone_id = zone_id
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

        zone = _get_zone(device_state, self._zone_id)
        if zone is not None and zone.volume_db is not None:
            self._attr_available = device_state.processor_state in [
                ProcessorState.ON,
                ProcessorState.INITIALIZING,
            ]

            decimal_volume_db: Decimal = zone.volume_db
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

        await self.coordinator.async_set_zone_volume(self._zone_id, decimal_volume_db)
        self._attr_native_value = value
        self.async_write_ha_state()


class StormAudioIspNumber(CoordinatorEntity, NumberEntity):
    """Generic Storm Audio ISP number entity."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        get_value_fn,
        is_available_fn,
        async_set_fn,
        unit: str = None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = unit

        self._attr_unique_id = unique_id
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = icon
        self._attr_name = name

        self._attr_device_info = parent_device_info
        self._get_value_fn = get_value_fn
        self._is_available_fn = is_available_fn
        self._async_set_fn = async_set_fn

        self._set_state_from_device()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._set_state_from_device()
        self.async_write_ha_state()

    def _set_state_from_device(self):
        device_state: DeviceState = self.coordinator.data["device_state"]
        self._attr_available = self.coordinator.connected

        if device_state is not None and self._is_available_fn(device_state):
            self._attr_available = device_state.processor_state in [
                ProcessorState.ON,
                ProcessorState.INITIALIZING,
            ]
            value = self._get_value_fn(device_state)
            if value is not None:
                self._attr_native_value = float(value)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        available: bool = self._attr_available
        if available:
            available = super().available
        return available

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_fn(self.coordinator, value)
        self._attr_native_value = value
        self.async_write_ha_state()
