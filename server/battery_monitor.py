"""
battery_monitor.py — Automatización del enchufe inteligente.

Fuente de batería: Computadora Principal (vía system_monitor).
Lógica:
  batería <= LOW  → enciende enchufe
  batería >= HIGH → apaga enchufe
"""

import asyncio
import logging
import os

from .smarthome import control_device, get_device_status

log = logging.getLogger("daniel.battery")

_LOW = int(os.environ.get("BATTERY_LOW", "20"))
_HIGH = int(os.environ.get("BATTERY_HIGH", "80"))
_PLUG = os.environ.get("HA_PLUG_ENTITY_ID", "")

_plug_on: bool | None = None


async def monitor() -> None:
    global _plug_on

    if not _PLUG:
        log.warning(
            "[BATTERY_AUTOMATION] HA_PLUG_ENTITY_ID no configurado — desactivado."
        )
        return

    log.info(
        "[BATTERY_AUTOMATION] Iniciado — PC principal (LOW=%d%% → ON | HIGH=%d%% → OFF | PLUG=%s)",
        _LOW,
        _HIGH,
        _PLUG,
    )

    while True:
        try:
            from .system_monitor import get_main_pc_battery

            batt = get_main_pc_battery()

            if batt is None or batt.get("percent") is None:
                log.info(
                    "[BATTERY_AUTOMATION] Sin datos de PC principal — esperando agente..."
                )
                await asyncio.sleep(60)
                continue

            if not batt.get("online"):
                log.warning("[BATTERY_AUTOMATION] PC principal OFFLINE — pausado.")
                await asyncio.sleep(60)
                continue

            pct = batt["percent"]
            plugged = batt.get("plugged")

            log.info(
                "[BATTERY_AUTOMATION] BAT:%.0f%% PLUGGED:%s _plug_on:%s",
                pct,
                plugged,
                _plug_on,
            )

            # Leer estado real del enchufe
            actual = get_device_status(_PLUG)
            if actual is not None:
                _plug_on = actual
            log.info("[BATTERY_AUTOMATION] Estado real enchufe: %s", actual)

            if pct <= _LOW and _plug_on is not True:
                ok = control_device(_PLUG, True)
                if ok:
                    _plug_on = True
                    log.info(
                        "[BATTERY_AUTOMATION] Batería %.0f%% — enchufe ENCENDIDO", pct
                    )
                else:
                    log.warning(
                        "[BATTERY_AUTOMATION] Falló encender enchufe (bat=%.0f%%)", pct
                    )

            elif pct >= _HIGH and _plug_on is not False:
                ok = control_device(_PLUG, False)
                if ok:
                    _plug_on = False
                    log.info(
                        "[BATTERY_AUTOMATION] Batería %.0f%% — enchufe APAGADO", pct
                    )
                else:
                    log.warning(
                        "[BATTERY_AUTOMATION] Falló apagar enchufe (bat=%.0f%%)", pct
                    )

        except Exception as e:
            log.error("[BATTERY_AUTOMATION] Error: %s", e, exc_info=True)

        await asyncio.sleep(60)
