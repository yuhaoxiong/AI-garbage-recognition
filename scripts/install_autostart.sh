#!/usr/bin/env bash
# -*- coding: utf-8 -*-

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err() { echo -e "${RED}[ERROR]${NC} $*" 1>&2; }
step() { echo -e "${BLUE}[STEP]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_ENTRY=""
if [[ -f "${PROJECT_DIR}/launcher.py" ]]; then
  DEFAULT_ENTRY="launcher.py"
elif [[ -f "${PROJECT_DIR}/main.py" ]]; then
  DEFAULT_ENTRY="main.py"
fi

SERVICE_NAME="waste-ai-guide"
SERVICE_USER="${SUDO_USER:-${USER}}"
PYTHON_BIN="python3"
ENTRY_FILE="${DEFAULT_ENTRY}"
WITH_GUI=1
LOG_FILE="${PROJECT_DIR}/logs/autostart.log"

usage() {
  cat <<EOF
用法:
  $(basename "$0") install [选项]    安装并启用systemd自启动
  $(basename "$0") uninstall [选项]  停用并卸载自启动
  $(basename "$0") status [选项]     查看服务状态

常用选项:
  --name NAME            服务名(默认: ${SERVICE_NAME})
  --user USER            运行用户(默认: 当前用户)
  --python /path/python  指定Python解释器(默认: ${PYTHON_BIN})
  --dir /path/project    项目目录(默认: ${PROJECT_DIR})
  --entry FILE.py        启动入口(默认: ${ENTRY_FILE})
  --log-file /path.log   日志文件(默认: ${LOG_FILE})
  --with-gui|--no-gui    是否在图形会话下运行(默认: --with-gui)

示例:
  sudo $(basename "$0") install --entry launcher.py --with-gui
  sudo $(basename "$0") uninstall
  $(basename "$0") status
EOF
}

parse_args() {
  local cmd="$1"; shift || true
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name) SERVICE_NAME="$2"; shift 2;;
      --user) SERVICE_USER="$2"; shift 2;;
      --python) PYTHON_BIN="$2"; shift 2;;
      --dir) PROJECT_DIR="$2"; shift 2;;
      --entry) ENTRY_FILE="$2"; shift 2;;
      --log-file) LOG_FILE="$2"; shift 2;;
      --with-gui) WITH_GUI=1; shift;;
      --no-gui) WITH_GUI=0; shift;;
      -h|--help) usage; exit 0;;
      *) warn "忽略未知参数: $1"; shift;;
    esac
  done

  if [[ -z "${ENTRY_FILE}" ]]; then
    err "未能确定入口文件，请通过 --entry 指定 launcher.py 或 main.py"
    exit 1
  fi
  if [[ ! -f "${PROJECT_DIR}/${ENTRY_FILE}" ]]; then
    err "入口文件不存在: ${PROJECT_DIR}/${ENTRY_FILE}"
    exit 1
  fi
}

ensure_root() {
  if [[ "$EUID" -ne 0 ]]; then
    err "需要root权限，请使用 sudo 运行"
    exit 1
  fi
}

install_service() {
  ensure_root
  step "创建systemd服务: ${SERVICE_NAME}.service"
  local unit="/etc/systemd/system/${SERVICE_NAME}.service"

  local USER_UID
  USER_UID="$(id -u "${SERVICE_USER}")"

  local AFTER_LINES="After=network-online.target"
  local WANTS_LINES="Wants=network-online.target"
  local WANTED_BY="multi-user.target"
  local ENV_GUI=""
  if [[ "${WITH_GUI}" -eq 1 ]]; then
    AFTER_LINES+="\nAfter=display-manager.service"
    WANTS_LINES+="\nWants=graphical.target"
    WANTED_BY="graphical.target"
    ENV_GUI=$(cat <<EOENV
Environment=QT_QPA_PLATFORM=xcb
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/${USER_UID}
EOENV
)
  fi

  mkdir -p "$(dirname "${LOG_FILE}")"

  cat > "${unit}" <<EOF
[Unit]
Description=Waste AI Guide Autostart Service
${AFTER_LINES}
${WANTS_LINES}

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
${ENV_GUI}
ExecStart=/bin/bash -lc 'cd ${PROJECT_DIR} && exec ${PYTHON_BIN} ${ENTRY_FILE} >> ${LOG_FILE} 2>&1'
Restart=on-failure
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=15

[Install]
WantedBy=${WANTED_BY}
EOF

  step "重载systemd"
  systemctl daemon-reload
  step "启用并启动服务"
  systemctl enable "${SERVICE_NAME}.service"
  systemctl restart "${SERVICE_NAME}.service"
  log "已启动。使用: journalctl -u ${SERVICE_NAME} -f 查看日志"
}

uninstall_service() {
  ensure_root
  local unit="/etc/systemd/system/${SERVICE_NAME}.service"
  if systemctl is-enabled --quiet "${SERVICE_NAME}.service" 2>/dev/null || \
     systemctl is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
    step "停止并禁用服务"
    systemctl stop "${SERVICE_NAME}.service" || true
    systemctl disable "${SERVICE_NAME}.service" || true
  fi
  if [[ -f "${unit}" ]]; then
    step "删除unit文件: ${unit}"
    rm -f "${unit}"
    systemctl daemon-reload
  fi
  log "卸载完成"
}

status_service() {
  if systemctl status "${SERVICE_NAME}.service" >/dev/null 2>&1; then
    systemctl --no-pager status "${SERVICE_NAME}.service"
  else
    warn "服务不存在: ${SERVICE_NAME}.service"
  fi
}

main() {
  local cmd="${1:-}" || true
  if [[ -z "${cmd}" ]]; then
    usage; exit 1
  fi
  shift || true

  case "${cmd}" in
    install)
      parse_args install "$@"
      install_service
      ;;
    uninstall)
      parse_args uninstall "$@"
      uninstall_service
      ;;
    status)
      parse_args status "$@"
      status_service
      ;;
    *)
      usage; exit 1;;
  esac
}

main "$@"


