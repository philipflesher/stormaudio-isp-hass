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
    device_state: DeviceState = coordinator.data["device_state"]

    entities = [
        StormAudioIspMuteSwitch(
            coordinator,
            f"{device_unique_id}_mute",
            f"{device_name} Mute",
            device_info,
        ),
        StormAudioIspSwitch(
            coordinator,
            f"{device_unique_id}_dim",
            f"{device_name} Dim",
            device_info,
            icon="mdi:brightness-4",
            get_value_fn=lambda ds: ds.dim,
            is_available_fn=lambda ds: ds.dim is not None,
            async_turn_on_fn=lambda coord: coord.async_set_dim(True),
            async_turn_off_fn=lambda coord: coord.async_set_dim(False),
        ),
        StormAudioIspSwitch(
            coordinator,
            f"{device_unique_id}_dialog_norm",
            f"{device_name} Dialog Norm",
            device_info,
            icon="mdi:account-voice",
            get_value_fn=lambda ds: ds.dialog_norm,
            is_available_fn=lambda ds: ds.dialog_norm is not None,
            async_turn_on_fn=lambda coord: coord.async_set_dialog_norm(True),
            async_turn_off_fn=lambda coord: coord.async_set_dialog_norm(False),
        ),
        StormAudioIspSwitch(
            coordinator,
            f"{device_unique_id}_storm_xt",
            f"{device_name} Storm XT",
            device_info,
            icon="mdi:surround-sound",
            get_value_fn=lambda ds: ds.storm_xt,
            is_available_fn=lambda ds: ds.storm_xt is not None,
            async_turn_on_fn=lambda coord: coord.async_set_storm_xt(True),
            async_turn_off_fn=lambda coord: coord.async_set_storm_xt(False),
        ),
        StormAudioIspSwitch(
            coordinator,
            f"{device_unique_id}_lfe_dim",
            f"{device_name} LFE Dim",
            device_info,
            icon="mdi:speaker",
            get_value_fn=lambda ds: ds.lfe_dim,
            is_available_fn=lambda ds: ds.lfe_dim is not None,
            async_turn_on_fn=lambda coord: coord.async_set_lfe_dim(True),
            async_turn_off_fn=lambda coord: coord.async_set_lfe_dim(False),
        ),
    ]

    # Per-zone switches
    if device_state is not None and device_state.zones is not None:
        for zone in device_state.zones:
            zone_id = zone.id
            zone_name = zone.name

            entities.extend(
                [
                    StormAudioIspSwitch(
                        coordinator,
                        f"{device_unique_id}_zone{zone_id}_mute",
                        f"{device_name} {zone_name} Mute",
                        device_info,
                        icon="mdi:volume-mute",
                        get_value_fn=lambda ds, zid=zone_id: _get_zone_attr(
                            ds, zid, "mute"
                        ),
                        is_available_fn=lambda ds, zid=zone_id: _get_zone(ds, zid)
                        is not None,
                        async_turn_on_fn=lambda coord, zid=zone_id: coord.async_set_zone_mute(
                            zid, True
                        ),
                        async_turn_off_fn=lambda coord, zid=zone_id: coord.async_set_zone_mute(
                            zid, False
                        ),
                    ),
                    StormAudioIspSwitch(
                        coordinator,
                        f"{device_unique_id}_zone{zone_id}_eq",
                        f"{device_name} {zone_name} EQ",
                        device_info,
                        icon="mdi:equalizer",
                        get_value_fn=lambda ds, zid=zone_id: _get_zone_attr(
                            ds, zid, "eq_enabled"
                        ),
                        is_available_fn=lambda ds, zid=zone_id: _get_zone(ds, zid)
                        is not None,
                        async_turn_on_fn=lambda coord, zid=zone_id: coord.async_set_zone_eq(
                            zid, True
                        ),
                        async_turn_off_fn=lambda coord, zid=zone_id: coord.async_set_zone_eq(
                            zid, False
                        ),
                    ),
                ]
            )

    # Trigger switches
    if device_state is not None and device_state.triggers:
        for trigger_id in sorted(device_state.triggers.keys()):
            trigger_name = f"Trigger {trigger_id}"
            if (
                device_state.trigger_names
                and trigger_id <= len(device_state.trigger_names)
            ):
                name_from_list = device_state.trigger_names[trigger_id - 1]
                if name_from_list:
                    trigger_name = name_from_list

            entities.append(
                StormAudioIspSwitch(
                    coordinator,
                    f"{device_unique_id}_trigger{trigger_id}",
                    f"{device_name} {trigger_name}",
                    device_info,
                    icon="mdi:electric-switch",
                    get_value_fn=lambda ds, tid=trigger_id: ds.triggers.get(tid),
                    is_available_fn=lambda ds, tid=trigger_id: tid in ds.triggers,
                    async_turn_on_fn=lambda coord, tid=trigger_id: coord.async_set_trigger(
                        tid, True
                    ),
                    async_turn_off_fn=lambda coord, tid=trigger_id: coord.async_set_trigger(
                        tid, False
                    ),
                ),
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


class StormAudioIspSwitch(CoordinatorEntity, SwitchEntity):
    """Generic Storm Audio ISP switch entity."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
        icon: str,
        get_value_fn,
        is_available_fn,
        async_turn_on_fn,
        async_turn_off_fn,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_is_on = None
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self._attr_name = name

        self._attr_device_info = parent_device_info
        self._get_value_fn = get_value_fn
        self._is_available_fn = is_available_fn
        self._async_turn_on_fn = async_turn_on_fn
        self._async_turn_off_fn = async_turn_off_fn

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
            self._attr_is_on = self._get_value_fn(device_state)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        available: bool = self._attr_available
        if available:
            available = super().available
        return available

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        await self._async_turn_on_fn(self.coordinator)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        await self._async_turn_off_fn(self.coordinator)
        self._attr_is_on = False
        self.async_write_ha_state()
