import json
import logging
import os
from pathlib import Path

import requests

log = logging.getLogger("daniel.smarthome")

_HA_URL = os.environ.get("HA_URL", "http://homeassistant:8123").rstrip("/")
_HA_TOKEN = os.environ.get("HA_TOKEN", "")

_CONFIG_JSON = Path(os.environ.get("DATA_DIR", "/app/data")) / "ha_devices.json"
# Fallback a la raíz del proyecto (desarrollo local)
if not _CONFIG_JSON.exists():
    _CONFIG_JSON = Path(__file__).parent.parent / "ha_devices.json"
_config_cache: dict | None = None

# Modo de aire → escena HA
_AC_MODES = {
    "frio": "frio",
    "frío": "frio",
    "cool": "frio",
    "viento": "viento",
    "ventilacion": "viento",
    "ventilación": "viento",
    "fan": "viento",
    "dormir": "dormir",
    "sleep": "dormir",
}

_ON_WORDS = {"on", "encender", "encendido", "prender", "activar"}
_OFF_WORDS = {"off", "apagar", "apagado", "desactivar"}


# ── Config (mapeo de dispositivos/escenas de Home Assistant) ─────


def _load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    try:
        _config_cache = json.loads(_CONFIG_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Error leyendo ha_devices.json: %s", e)
        _config_cache = {}
    return _config_cache


def list_devices() -> list[dict]:
    devices = _load_config().get("devices", [])
    return [
        {
            "id": d["id"],
            "name": d.get("name", d["id"]),
            "online": True,
            "product_name": "Home Assistant",
        }
        for d in devices
    ]


# ── Cliente REST de Home Assistant ────────────────────────────────


def _headers() -> dict:
    return {"Authorization": f"Bearer {_HA_TOKEN}", "Content-Type": "application/json"}


def _ha_get(path: str):
    try:
        r = requests.get(f"{_HA_URL}{path}", headers=_headers(), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error("HA GET %s: %s", path, e)
        return None


def _ha_post(path: str, payload: dict) -> bool:
    try:
        r = requests.post(
            f"{_HA_URL}{path}", headers=_headers(), json=payload, timeout=5
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.error("HA POST %s: %s", path, e)
        return False


# ── Public API ───────────────────────────────────────────────────


def get_device_status(entity_id: str) -> bool | None:
    state = _ha_get(f"/api/states/{entity_id}")
    if not state:
        return None
    return state.get("state") == "on"


def control_device(entity_id: str, turn_on: bool) -> bool:
    domain = entity_id.split(".", 1)[0]
    service = "turn_on" if turn_on else "turn_off"
    ok = _ha_post(f"/api/services/{domain}/{service}", {"entity_id": entity_id})
    if ok:
        log.info("%s → %s (HA)", entity_id, "ON" if turn_on else "OFF")
    return ok


def ac_control(device_name: str, power: str = "", mode: str = "") -> str:
    """Control de aire acondicionado vía escenas de Home Assistant."""
    cfg = _load_config()
    ac_scenes = cfg.get("ac_scenes", {})

    power_lower = power.lower()
    mode_key = _AC_MODES.get(mode.lower())

    if power_lower in _OFF_WORDS:
        scene = ac_scenes.get("off")
        label = "apagado"
    elif mode_key:
        scene = ac_scenes.get(mode_key)
        label = f"modo {mode_key}"
    elif power_lower in _ON_WORDS:
        scene = ac_scenes.get("frio")
        label = "encendido (modo frío)"
    else:
        return "No entendí qué hacer con el aire. Especifica encender/apagar o un modo: frío, viento o dormir."

    if not scene:
        return "Esa escena de aire no está configurada en ha_devices.json."

    ok = _ha_post("/api/services/scene/turn_on", {"entity_id": scene})
    return f"Aire: {label}." if ok else "No pude controlar el aire."


def find_device_by_name(name: str) -> str | None:
    name_lower = name.lower()
    for dev in _load_config().get("devices", []):
        if name_lower in dev.get("name", "").lower():
            return dev["id"]
    return None


def smart_control(device_name: str, action: str) -> str:
    turn_on = action.lower() in _ON_WORDS
    name_lower = device_name.lower()

    if "led" in name_lower or "luz" in name_lower:
        led_scenes = _load_config().get("led_scenes", {})
        scene = led_scenes.get("on" if turn_on else "off")
        if not scene:
            return "Esa escena de LED no está configurada en ha_devices.json."
        ok = _ha_post("/api/services/scene/turn_on", {"entity_id": scene})
        estado = "encendido" if turn_on else "apagado"
        return f"LED {estado}." if ok else "No pude controlar el LED."

    if "aire" in name_lower or "clima" in name_lower or name_lower.strip() == "ac":
        return ac_control(device_name, power="on" if turn_on else "off")

    entity_id = find_device_by_name(device_name)
    if not entity_id:
        names = ", ".join(d.get("name", "?") for d in _load_config().get("devices", []))
        return (
            f"No encontré '{device_name}'. Dispositivos: {names}"
            if names
            else f"No encontré '{device_name}'."
        )
    ok = control_device(entity_id, turn_on)
    estado = "encendido" if turn_on else "apagado"
    return f"{device_name} {estado}." if ok else f"No pude controlar {device_name}."
