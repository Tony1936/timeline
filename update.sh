#!/usr/bin/env bash
# =============================================================================
# update.sh — Update an existing Historical Timelines installation
#
# Prerequisites
#   • install.sh has been run from this directory
#   • The app user's SSH key is authorised on GitHub
#
# Usage
#   cd /path/to/timeline && sudo ./update.sh
#
# What it does
#   1. Pulls the latest code from GitHub via SSH (git fetch + reset)
#   2. Updates Python dependencies from requirements.txt
#   3. Applies any new database schema changes (new tables or columns)
#   4. Restarts the systemd service
# =============================================================================

set -euo pipefail

# Run from wherever this script lives
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="timeline"
APP_USER="${SUDO_USER:-pi}"

# ── colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[update]${NC} $*"; }
warn()  { echo -e "${YELLOW}[ warn  ]${NC} $*"; }
die()   { echo -e "${RED}[error  ]${NC} $*" >&2; exit 1; }

# ── guards ────────────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "Please run with sudo:  sudo ./update.sh"
[[ -d "$INSTALL_DIR/.git" ]] || \
    die "$INSTALL_DIR does not contain a git repository. Run install.sh first."

VENV="$INSTALL_DIR/venv"
[[ -d "$VENV" ]] || \
    die "Virtual environment not found at $VENV. Run install.sh first."

# ── stop service before update (avoids locked db during migration) ────────────
info "Stopping $SERVICE_NAME service..."
systemctl stop "$SERVICE_NAME" || warn "Service was not running."

# ── pull latest code ──────────────────────────────────────────────────────────
info "Fetching latest code from GitHub (SSH)..."
sudo -u "$APP_USER" git -C "$INSTALL_DIR" fetch --prune origin

CURRENT=$(sudo -u "$APP_USER" git -C "$INSTALL_DIR" rev-parse HEAD)
UPSTREAM=$(sudo -u "$APP_USER" git -C "$INSTALL_DIR" rev-parse origin/master)

if [[ "$CURRENT" == "$UPSTREAM" ]]; then
    warn "Already up to date ($(git -C "$INSTALL_DIR" rev-parse --short HEAD))."
else
    info "Updating from $(git -C "$INSTALL_DIR" rev-parse --short HEAD) \
→ $(git -C "$INSTALL_DIR" rev-parse --short origin/master)..."

    # Back up live db before reset --hard (git overwrites tracked files).
    DB_FILE="$INSTALL_DIR/instance/sqlite3.db"
    DB_BACKUP="$DB_FILE.bak"
    [[ -f "$DB_FILE" ]] && cp "$DB_FILE" "$DB_BACKUP"

    # Back up image/map folders — migrate_db.py needs them after the reset.
    IMG_BACKUP="$INSTALL_DIR/.img_backup_$$"
    mkdir -p "$IMG_BACKUP"
    for _dir in static/timeline_images static/images static/timeline_maps; do
        [[ -d "$INSTALL_DIR/$_dir" ]] && cp -r "$INSTALL_DIR/$_dir" "$IMG_BACKUP/"
    done

    sudo -u "$APP_USER" git -C "$INSTALL_DIR" reset --hard origin/master

    # Restore the live db immediately after — never let the committed dev
    # copy replace production data.
    if [[ -f "$DB_BACKUP" ]]; then
        mv "$DB_BACKUP" "$DB_FILE"
        chown "$APP_USER:$APP_USER" "$DB_FILE"
        chmod 664 "$DB_FILE"
    fi

    # Restore image/map folders so migrate_db.py can ingest them.
    for _dir in static/timeline_images static/images static/timeline_maps; do
        _src="$IMG_BACKUP/$(basename "$_dir")"
        [[ -d "$_src" ]] && cp -r "$_src" "$INSTALL_DIR/$_dir"
    done
    rm -rf "$IMG_BACKUP"

    info "Code updated."
fi

# ── update Python dependencies ────────────────────────────────────────────────
info "Updating Python dependencies..."
sudo -u "$APP_USER" "$VENV/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$VENV/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
info "Dependencies up to date."

# ── ensure core directories still exist ──────────────────────────────────────
# NOTE: images and maps are now stored as blobs in the SQLite database.
# The static/timeline_images and static/timeline_maps folders are legacy
# and only needed if running migrate_db.py to ingest old on-disk files.
sudo -u "$APP_USER" mkdir -p "$INSTALL_DIR/instance"

# ── ensure db file is writable by the app user ───────────────────────────────
DB_FILE="$INSTALL_DIR/instance/sqlite3.db"
if [[ -f "$DB_FILE" ]]; then
    chown "$APP_USER:$APP_USER" "$DB_FILE"
    chmod 664 "$DB_FILE"
fi

# ── apply database migrations ─────────────────────────────────────────────────
info "Running database migration..."
sudo -u "$APP_USER" bash -c "
    set -e
    cd \"$INSTALL_DIR\"
    set -a; source .env; set +a
    venv/bin/python migrate_db.py
"
info "Database migration complete."

# ── restart service ───────────────────────────────────────────────────────────
info "Starting $SERVICE_NAME service..."
systemctl start "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    info "Service is running."
else
    die "Service failed to start. Check logs:  sudo journalctl -u $SERVICE_NAME -n 50"
fi

# ── summary ───────────────────────────────────────────────────────────────────
PI_IP=$(hostname -I | awk '{print $1}')
COMMIT=$(sudo -u "$APP_USER" git -C "$INSTALL_DIR" rev-parse --short HEAD)
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
info "Update complete!  (commit $COMMIT)"
info "  App URL  :  http://${PI_IP}:5010"
info "  Logs     :  sudo journalctl -u $SERVICE_NAME -f"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
