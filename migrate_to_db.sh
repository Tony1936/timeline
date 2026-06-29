#!/usr/bin/env bash
# One-time migration helper — run this on the Pi instead of a plain git pull.
# Backs up image folders, pulls latest code, restores images, migrates to DB.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP="/tmp/timeline_img_backup_$$"
APP_USER="${SUDO_USER:-pi}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}[migrate]${NC} $*"; }
warn() { echo -e "${YELLOW}[ warn  ]${NC} $*"; }
die()  { echo -e "${RED}[error  ]${NC} $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Please run with sudo:  sudo ./migrate_to_db.sh"

# ── 1. Back up image folders ──────────────────────────────────────────────────
info "Backing up image folders to $BACKUP ..."
mkdir -p "$BACKUP"
for _dir in static/timeline_images static/images static/timeline_maps; do
    if [[ -d "$INSTALL_DIR/$_dir" ]]; then
        cp -r "$INSTALL_DIR/$_dir" "$BACKUP/"
        COUNT=$(find "$INSTALL_DIR/$_dir" -type f | wc -l)
        info "  Backed up $_dir ($COUNT files)"
    else
        warn "  $_dir not found, skipping"
    fi
done

# ── 2. Back up database ───────────────────────────────────────────────────────
DB_FILE="$INSTALL_DIR/instance/sqlite3.db"
[[ -f "$DB_FILE" ]] && cp "$DB_FILE" "$BACKUP/sqlite3.db" && info "Backed up database"

# ── 3. Pull latest code ───────────────────────────────────────────────────────
info "Pulling latest code..."
sudo -u "$APP_USER" git -C "$INSTALL_DIR" fetch --prune origin
sudo -u "$APP_USER" git -C "$INSTALL_DIR" reset --hard origin/master
info "Code updated."

# ── 4. Restore database ───────────────────────────────────────────────────────
[[ -f "$BACKUP/sqlite3.db" ]] && cp "$BACKUP/sqlite3.db" "$DB_FILE" && info "Database restored."

# ── 5. Restore image folders ──────────────────────────────────────────────────
info "Restoring image folders..."
for _dir in timeline_images images timeline_maps; do
    SRC="$BACKUP/$_dir"
    DST="$INSTALL_DIR/static/$_dir"
    if [[ -d "$SRC" ]]; then
        mkdir -p "$DST"
        cp -r "$SRC/." "$DST/"
        COUNT=$(find "$DST" -type f | wc -l)
        info "  Restored static/$_dir ($COUNT files)"
    fi
done

# ── 6. Update Python dependencies ─────────────────────────────────────────────
info "Updating Python dependencies..."
sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# ── 7. Run migration — moves images into DB and deletes disk copies ───────────
info "Running migration (ingesting images into database)..."
sudo -u "$APP_USER" bash -c "
    set -e
    cd \"$INSTALL_DIR\"
    set -a; source .env; set +a
    venv/bin/python migrate_db.py
"
info "Migration complete."

# ── 8. Clean up backup ────────────────────────────────────────────────────────
rm -rf "$BACKUP"
info "Backup cleaned up."

# ── 9. Restart service ────────────────────────────────────────────────────────
info "Restarting service..."
systemctl restart timeline
sleep 2
if systemctl is-active --quiet timeline; then
    info "Service is running. All done!"
else
    die "Service failed to start. Check:  sudo journalctl -u timeline -n 50"
fi
