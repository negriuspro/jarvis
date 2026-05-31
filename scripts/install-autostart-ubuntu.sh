#!/bin/bash
# Daniel AI — Instalar servicio systemd en Ubuntu para autostart.
# Ejecutar UNA SOLA VEZ en el servidor Ubuntu:
#   chmod +x install-autostart-ubuntu.sh
#   sudo ./install-autostart-ubuntu.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="daniel-ai"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
CURRENT_USER="${SUDO_USER:-$(whoami)}"

echo ""
echo "=== Daniel AI — Instalando autostart en Ubuntu ==="
echo "Directorio del proyecto: $PROJECT_DIR"
echo "Usuario: $CURRENT_USER"
echo ""

# Verificar que docker compose existe
if ! docker compose version &>/dev/null; then
    echo "ERROR: 'docker compose' no encontrado. Instala Docker primero."
    exit 1
fi

# Crear el archivo de servicio systemd
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Daniel AI Voice Assistant
Documentation=https://github.com/negriuspro/daniel
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${PROJECT_DIR}
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300
TimeoutStopSec=60
User=${CURRENT_USER}
Group=docker
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Archivo de servicio creado en: $SERVICE_FILE"

# Habilitar Docker para que arranque con el sistema (si no lo está)
systemctl enable docker 2>/dev/null || true
echo "✓ Docker habilitado en el arranque."

# Recargar systemd y habilitar el servicio
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "✓ Servicio '$SERVICE_NAME' habilitado."

# Arrancar ahora mismo
systemctl start "$SERVICE_NAME"
echo "✓ Servicio iniciado."

echo ""
echo "=== Instalación completa ==="
echo ""
echo "Comandos útiles:"
echo "  Ver estado:    sudo systemctl status ${SERVICE_NAME}"
echo "  Ver logs:      sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Detener:       sudo systemctl stop ${SERVICE_NAME}"
echo "  Deshabilitar:  sudo systemctl disable ${SERVICE_NAME}"
echo ""
echo "Desde ahora Daniel AI arranca automáticamente cuando enciendas la PC."
