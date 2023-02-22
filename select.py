"""Storm Audio ISP selects"""

from __future__ import annotations
import itertools

from homeassistant.components.select import (
    SelectEntity,
)

from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import helpers
from .const import DOMAIN
from .coordinator import StormAudioIspCoordinator

from stormaudio_isp_telnet.telnet_client import (
    DeviceState,
    ProcessorState,
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

    device_info = coordinator.data["device_info"]
    device_unique_id = coordinator.data["device_unique_id"]
    device_name = coordinator.data["device_name"]

    add_entities(
        [
            StormAudioIspSelect(
                coordinator,
                f"{device_unique_id}_source",
                f"{device_name} Source",
                device_info,
                lambda device_state: map(
                    lambda i: (i.id, i.name),
                    device_state.inputs,
                ),
                lambda device_state: device_state.input_id,
                lambda coordinator, selected_id: coordinator.async_set_input_id(
                    selected_id
                ),
            ),
            StormAudioIspSelect(
                coordinator,
                f"{device_unique_id}_source_zone2",
                f"{device_name} Source (Zone 2)",
                device_info,
                lambda device_state: itertools.chain(
                    map(
                        lambda i: (i.id, i.name),
                        device_state.inputs,
                    ),
                    # add an entry to allow for selection of no-value; maps to ID 0
                    [(0, "")],
                ),
                lambda device_state: device_state.input_zone2_id,
                lambda coordinator, selected_id: coordinator.async_set_input_zone2_id(
                    selected_id
                ),
            ),
            StormAudioIspSelect(
                coordinator,
                f"{device_unique_id}_preset",
                f"{device_name} Preset",
                device_info,
                lambda device_state: map(
                    lambda i: (i.id, i.name),
                    device_state.presets,
                ),
                lambda device_state: device_state.preset_id,
                lambda coordinator, selected_id: coordinator.async_set_preset_id(
                    selected_id
                ),
            ),
        ]
    )


class StormAudioIspSelect(CoordinatorEntity, SelectEntity):
    """Storm Audio ISP select."""

    def __init__(
        self,
        coordinator: StormAudioIspCoordinator,
        unique_id: str,
        name: str,
        parent_device_info: DeviceInfo,
        get_id_name_map_fn,
        get_current_id_fn,
        async_set_current_id_fn,
    ):
        """Initialize."""
        super().__init__(coordinator)

        self._attr_options = None
        self._attr_current_option = None

        self._attr_unique_id = unique_id
        self._attr_icon = "mdi:audio-video"
        self._attr_name = name

        self._attr_device_info = parent_device_info
        self._get_id_name_map_fn = get_id_name_map_fn
        self._get_current_id_fn = get_current_id_fn
        self._async_set_current_id_fn = async_set_current_id_fn

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

            id_name_map = self._get_id_name_map_fn(device_state)
            self._id_to_name = dict(id_name_map)
            self._name_to_id = {v: k for k, v in self._id_to_name.items()}
            self._attr_options = list(self._name_to_id.keys())

            self._attr_current_option = None
            current_id = self._get_current_id_fn(device_state)
            if self._id_to_name is not None and current_id in self._id_to_name:
                self._attr_current_option = self._id_to_name[current_id]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        available: bool = self._attr_available
        if available:
            available = super().available
        return available

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if self._name_to_id is None:
            return

        option_id: int
        if option not in self._name_to_id:
            option_id = 0
        else:
            option_id = self._name_to_id[option]

        await self._async_set_current_id_fn(self.coordinator, option_id)
        self._attr_current_option = option
        self.async_write_ha_state()
