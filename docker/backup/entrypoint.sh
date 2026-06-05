#!/bin/sh
# Backup periódico de Redis RDB para Daniel.
# Copia /data/dump.rdb (redis-data volume, montado :ro) → /backups/redis_TS.rdb.gz
# Limpia archivos más antiguos de BACKUP_KEEP_DAYS días.
set -e

INTERVAL="${BACKUP_INTERVAL_SECONDS:-21600}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

mkdir -p "$BACKUP_DIR"
echo "[backup-daniel] Iniciando. Primer backup en 60s."
echo "[backup-daniel] Intervalo: ${INTERVAL}s | Retención: ${KEEP_DAYS} días | Destino: ${BACKUP_DIR}"

sleep 60

while true; do
  TS=$(date +%Y%m%d_%H%M%S)
  echo "[backup-daniel] ── ${TS} ────────────────────"

  if cp /data/dump.rdb "${BACKUP_DIR}/redis_${TS}.rdb" 2>/dev/null; then
    gzip -f "${BACKUP_DIR}/redis_${TS}.rdb"
    SIZE=$(du -sh "${BACKUP_DIR}/redis_${TS}.rdb.gz" 2>/dev/null | cut -f1 || echo "?")
    echo "[backup-daniel] OK → redis_${TS}.rdb.gz (${SIZE})"
  else
    echo "[backup-daniel] AVISO: /data/dump.rdb no disponible (Redis vacío o aún arrancando)"
  fi

  find "$BACKUP_DIR" -name "redis_*.rdb.gz" -mtime "+${KEEP_DAYS}" -delete
  TOTAL=$(find "$BACKUP_DIR" -name "redis_*.rdb.gz" 2>/dev/null | wc -l || echo 0)
  echo "[backup-daniel] ${TOTAL} backup(s) retenidos. Próximo en ${INTERVAL}s."
  sleep "$INTERVAL"
done
