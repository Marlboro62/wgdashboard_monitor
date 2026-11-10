"""Configuration, entités des peers (ajoutés en cours de route), clé API refusée, diagnostics."""
from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.wgdashboard_monitor.const import DOMAIN
from custom_components.wgdashboard_monitor.diagnostics import async_get_config_entry_diagnostics

HOST = "http://wg.test:10086"
INFO = f"{HOST}/api/getWireguardConfigurationInfo?configurationName=wg0"
DATA = {"host": HOST, "api_key": "secret", "config_name": "wg0", "verify_ssl": True}


def _peer(pid: str, name: str, status: str = "running", hs: str = "0:00:42") -> dict:
    return {"id": pid, "name": name, "status": status, "latest_handshake": hs, "endpoint": "203.0.113.7:51820",
            "allowed_ip": "10.0.0.2/32", "cumu_receive": 1.5, "cumu_sent": 0.25}


def _info(*peers: dict) -> dict:
    return {"status": True, "data": {"configurationPeers": list(peers)}}


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=f"{HOST}_wg0", title="WGDashboard (wg0)", data=DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{HOST}/api/getWireguardConfigurations", json={"status": True, "data": []})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**DATA, "host": f" {HOST}/ "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == HOST


async def test_config_flow_errors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**DATA, "host": "wg.test"})
    assert result["errors"] == {"host": "invalid_host"}
    aioclient_mock.get(f"{HOST}/api/getWireguardConfigurations", status=401)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
    assert result["errors"] == {"base": "invalid_auth"}


async def test_peers_and_new_peer(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(INFO, json=_info(_peer("AAA=", "Phone")))
    entry = await _setup(hass)
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_AAA=_connected")
    count = hass.states.get(reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_connected_peers"))
    assert count.state == "1" and count.attributes["total_peers"] == 1

    # un peer ajouté dans WGDashboard après le démarrage reçoit ses entités
    aioclient_mock.clear_requests()
    aioclient_mock.get(INFO, json=_info(_peer("AAA=", "Phone"), _peer("BBB=", "Laptop", "stopped", "No Handshake")))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    new = reg.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_BBB=_connected")
    assert new and hass.states.get(new).state == "off"


async def test_rejected_api_key_starts_reauth(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(INFO, status=401)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=f"{HOST}_wg0", data=DATA)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress())


async def test_diagnostics_redacted(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(INFO, json=_info(_peer("AAA=", "Phone")))
    entry = await _setup(hass)
    text = str(await async_get_config_entry_diagnostics(hass, entry))
    for secret in ("secret", "wg.test", "AAA=", "203.0.113.7", "10.0.0.2", "Phone"):
        assert secret not in text


async def test_debug_log_has_no_secrets(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog) -> None:
    peer = {**_peer("AAA=", "Phone"), "private_key": "PRIVATEKEYSECRET=", "preshared_key": "PSKSECRET="}
    aioclient_mock.get(INFO, json=_info(peer))
    caplog.set_level("DEBUG", logger="custom_components.wgdashboard_monitor")
    await _setup(hass)
    for secret in ("PRIVATEKEYSECRET", "PSKSECRET", "203.0.113.7", "10.0.0.2", "Phone", "secret"):
        assert secret not in caplog.text
    assert "1 peers, 1 connected" in caplog.text


async def test_entity_names_follow_language(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Noms des entités dans la langue de Home Assistant, avec le nom du peer (renommage suivi)."""
    hass.config.language = "fr"
    aioclient_mock.get(INFO, json=_info(_peer("AAA=", "Phone")))
    entry = await _setup(hass)
    reg = er.async_get(hass)

    def name(domain: str, suffix: str) -> str:
        return hass.states.get(reg.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{suffix}")).attributes["friendly_name"]

    assert name("binary_sensor", "AAA=_connected") == "WGDashboard (wg0) Phone connecté"
    assert name("sensor", "AAA=_receive") == "WGDashboard (wg0) Phone données reçues"
    assert name("sensor", "AAA=_sent") == "WGDashboard (wg0) Phone données envoyées"
    assert name("sensor", "AAA=_last_handshake") == "WGDashboard (wg0) Phone dernière connexion"
    assert name("sensor", "connected_peers") == "WGDashboard (wg0) Pairs connectés"
    # identifiants d'entité toujours en anglais (automatisations existantes inchangées)
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_AAA=_connected") == "binary_sensor.wgdashboard_wg0_phone_connected"

    aioclient_mock.clear_requests()
    aioclient_mock.get(INFO, json=_info(_peer("AAA=", "Téléphone")))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert name("binary_sensor", "AAA=_connected") == "WGDashboard (wg0) Téléphone connecté"
