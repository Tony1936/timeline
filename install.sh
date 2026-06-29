#!/usr/bin/env bash
# =============================================================================
# install.sh — Fresh installation of Historical Timelines on a Raspberry Pi
#
# Prerequisites
#   • Raspberry Pi OS (Debian/Raspbian) with internet access
#   • The project files already present in the same directory as this script
#     (copy them to the Pi via USB, scp, or any other method)
#
# Usage
#   chmod +x install.sh
#   sudo ./install.sh
#
# What it does
#   1. Installs system packages (python3, pip, venv, git, sqlite3)
#   2. Pulls the latest code from GitHub (if this directory is a git repo)
#   3. Creates a Python virtual environment and installs all dependencies
#   4. Generates a random SECRET_KEY and writes it to .env
#   5. Initialises (or migrates) the SQLite database
#   6. Creates and enables a systemd service (gunicorn on port 5000)
# =============================================================================

set -euo pipefail

# Install dir is wherever this script lives
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="timeline"
PORT=5010

# The service runs as the user who called sudo; fall back to "pi"
APP_USER="${SUDO_USER:-pi}"

# ── colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[install]${NC} $*"; }
warn()  { echo -e "${YELLOW}[ warn  ]${NC} $*"; }
die()   { echo -e "${RED}[ error ]${NC} $*" >&2; exit 1; }

# ── must run as root ──────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "Please run with sudo:  sudo ./install.sh"

info "Installing from : $INSTALL_DIR"
info "Service user    : $APP_USER"

# ── system packages ───────────────────────────────────────────────────────────
info "Updating package list..."
apt-get update -qq

info "Installing system packages (python3, pip, venv, git, sqlite3)..."
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git sqlite3

# ── pull latest code (if this is a git repository) ───────────────────────────
if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Git repository detected — pulling latest code from GitHub..."
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" pull --ff-only origin master \
        && info "Code is up to date." \
        || warn "git pull failed — continuing with existing files."
else
    info "No git repository found — using files as-is."
fi

chown -R "$APP_USER":"$APP_USER" "$INSTALL_DIR"

# ── Python virtual environment ────────────────────────────────────────────────
VENV="$INSTALL_DIR/venv"

if [[ -d "$VENV" ]]; then
    warn "Virtual environment already exists — skipping creation."
else
    info "Creating Python virtual environment..."
    sudo -u "$APP_USER" python3 -m venv "$VENV"
fi

info "Installing Python dependencies..."
sudo -u "$APP_USER" "$VENV/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$VENV/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
info "Python dependencies installed."

# ── .env / secret key ────────────────────────────────────────────────────────
ENV_FILE="$INSTALL_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists — keeping existing SECRET_KEY."
else
    info "Generating a random SECRET_KEY..."
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    printf "SECRET_KEY=%s\n" "$SECRET" > "$ENV_FILE"
    chown "$APP_USER":"$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    info "SECRET_KEY written to $ENV_FILE"
fi

# ── instance & static directories ────────────────────────────────────────────
info "Creating required directories..."
sudo -u "$APP_USER" mkdir -p \
    "$INSTALL_DIR/instance" \
    "$INSTALL_DIR/static/timeline_images" \
    "$INSTALL_DIR/static/timeline_maps"

# ── initialise / migrate database ────────────────────────────────────────────
info "Initialising database..."
sudo -u "$APP_USER" bash -c "
    set -e
    cd \"$INSTALL_DIR\"
    set -a; source .env; set +a
    venv/bin/python migrate_db.py
"
info "Database ready."

# ── systemd service ───────────────────────────────────────────────────────────
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
info "Writing systemd service to $SERVICE_FILE..."

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Historical Timelines Web App
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:$PORT app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    info "Service '$SERVICE_NAME' is running."
else
    die "Service failed to start. Check logs:  sudo journalctl -u $SERVICE_NAME -n 50"
fi

# ── summary ───────────────────────────────────────────────────────────────────
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
info "Installation complete!"
info "  App URL     :  http://${PI_IP}:${PORT}"
info "  First run   :  visit /setup to create the admin account"
info "  Logs        :  sudo journalctl -u $SERVICE_NAME -f"
info "  To update   :  sudo $INSTALL_DIR/update.sh"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
