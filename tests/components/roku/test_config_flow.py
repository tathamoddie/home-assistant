"""Test the Roku config flow."""

import dataclasses
from unittest.mock import AsyncMock, MagicMock

import pytest
from rokuecp import Device as RokuDevice, RokuConnectionError

from homeassistant.components.roku.const import CONF_PLAY_MEDIA_APP_ID, DOMAIN
from homeassistant.config_entries import (
    SOURCE_HOMEKIT,
    SOURCE_SSDP,
    SOURCE_USER,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import (
    HOMEKIT_HOST,
    HOST,
    MOCK_HOMEKIT_DISCOVERY_INFO,
    MOCK_SSDP_DISCOVERY_INFO,
    NAME_ROKUTV,
    UPNP_FRIENDLY_NAME,
)

from tests.common import MockConfigEntry

RECONFIGURE_HOST = "192.168.1.190"


async def test_duplicate_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_roku_config_flow: MagicMock,
) -> None:
    """Test that errors are shown when duplicates are added."""
    mock_config_entry.add_to_hass(hass)

    user_input = {CONF_HOST: mock_config_entry.data[CONF_HOST]}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=user_input
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    user_input = {CONF_HOST: mock_config_entry.data[CONF_HOST]}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=user_input
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    discovery_info = dataclasses.replace(MOCK_SSDP_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_SSDP}, data=discovery_info
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_form(
    hass: HomeAssistant,
    mock_roku_config_flow: MagicMock,
    mock_setup_entry: None,
) -> None:
    """Test the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    user_input = {CONF_HOST: HOST}
    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input=user_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Roku 3"

    assert "data" in result
    assert result["data"][CONF_HOST] == HOST

    assert "result" in result
    assert result["result"].unique_id == "1GU48T017973"


async def test_form_cannot_connect(
    hass: HomeAssistant, mock_roku_config_flow: MagicMock
) -> None:
    """Test we handle cannot connect roku error."""
    mock_roku_config_flow.update.side_effect = RokuConnectionError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input={CONF_HOST: HOST}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(
    hass: HomeAssistant, mock_roku_config_flow: MagicMock
) -> None:
    """Test we handle unknown error."""
    mock_roku_config_flow.update.side_effect = Exception

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    user_input = {CONF_HOST: HOST}
    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input=user_input
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_homekit_cannot_connect(
    hass: HomeAssistant, mock_roku_config_flow: MagicMock
) -> None:
    """Test we abort homekit flow on connection error."""
    mock_roku_config_flow.update.side_effect = RokuConnectionError

    discovery_info = dataclasses.replace(MOCK_HOMEKIT_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_HOMEKIT},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_homekit_unknown_error(
    hass: HomeAssistant, mock_roku_config_flow: MagicMock
) -> None:
    """Test we abort homekit flow on unknown error."""
    mock_roku_config_flow.update.side_effect = Exception

    discovery_info = dataclasses.replace(MOCK_HOMEKIT_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_HOMEKIT},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


@pytest.mark.parametrize("mock_device", ["roku/rokutv-7820x.json"], indirect=True)
async def test_homekit_discovery(
    hass: HomeAssistant,
    mock_roku_config_flow: MagicMock,
    mock_setup_entry: None,
) -> None:
    """Test the homekit discovery flow."""
    discovery_info = dataclasses.replace(MOCK_HOMEKIT_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_HOMEKIT}, data=discovery_info
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"] == {CONF_NAME: NAME_ROKUTV}

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME_ROKUTV

    assert "data" in result
    assert result["data"][CONF_HOST] == HOMEKIT_HOST
    assert result["data"][CONF_NAME] == NAME_ROKUTV

    # test abort on existing host
    discovery_info = dataclasses.replace(MOCK_HOMEKIT_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_HOMEKIT}, data=discovery_info
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_ssdp_cannot_connect(
    hass: HomeAssistant, mock_roku_config_flow: MagicMock
) -> None:
    """Test we abort SSDP flow on connection error."""
    mock_roku_config_flow.update.side_effect = RokuConnectionError

    discovery_info = dataclasses.replace(MOCK_SSDP_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_ssdp_unknown_error(
    hass: HomeAssistant, mock_roku_config_flow: MagicMock
) -> None:
    """Test we abort SSDP flow on unknown error."""
    mock_roku_config_flow.update.side_effect = Exception

    discovery_info = dataclasses.replace(MOCK_SSDP_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_ssdp_discovery(
    hass: HomeAssistant,
    mock_roku_config_flow: MagicMock,
    mock_setup_entry: None,
) -> None:
    """Test the SSDP discovery flow."""
    discovery_info = dataclasses.replace(MOCK_SSDP_DISCOVERY_INFO)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_SSDP}, data=discovery_info
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"] == {CONF_NAME: UPNP_FRIENDLY_NAME}

    result = await hass.config_entries.flow.async_configure(
        flow_id=result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == UPNP_FRIENDLY_NAME

    assert result["data"]
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_NAME] == UPNP_FRIENDLY_NAME


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test options config flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_PLAY_MEDIA_APP_ID: "782875"},
    )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("data") == {
        CONF_PLAY_MEDIA_APP_ID: "782875",
    }


async def _start_reconfigure_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> ConfigFlowResult:
    """Initialize a reconfigure flow."""
    mock_config_entry.add_to_hass(hass)

    reconfigure_result = await mock_config_entry.start_reconfigure_flow(hass)

    assert reconfigure_result["type"] is FlowResultType.FORM
    assert reconfigure_result["step_id"] == "user"

    return await hass.config_entries.flow.async_configure(
        reconfigure_result["flow_id"],
        {CONF_HOST: RECONFIGURE_HOST},
    )


async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mock_roku_config_flow: MagicMock,
) -> None:
    """Test reconfigure flow."""
    result = await _start_reconfigure_flow(hass, mock_config_entry)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry
    assert entry.data == {
        CONF_HOST: RECONFIGURE_HOST,
    }


async def test_reconfigure_unique_id_mismatch(
    hass: HomeAssistant,
    mock_device: RokuDevice,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mock_roku_config_flow: MagicMock,
) -> None:
    """Ensure reconfigure flow aborts when the device changes."""
    mock_device.info.serial_number = "RECONFIG"

    result = await _start_reconfigure_flow(hass, mock_config_entry)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
