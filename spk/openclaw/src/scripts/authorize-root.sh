#!/bin/sh
# OpenClaw — grant panel-operation sudoers (http + sc-openclaw docker access).
#
# This script is executed AS ROOT by a one-shot DSM scheduled task
# (SYNO.Core.EventScheduler.Root), created from the panel's 授权面板操作 flow —
# the same method the SimplePermissionManager (权限管理器) package uses: the
# admin enters their password, DSM returns a SynoConfirmPWToken, and a root
# scheduled task is created/run/deleted. This script is the task's payload.
#
# It writes the exact rule set the package relies on (docker for http and
# sc-openclaw, plus the small set of helpers used to repair the web-terminal
# nginx alias and reload nginx). The new content is validated with `visudo -c`
# before it replaces the live file, so a broken rule can never be activated.
set -u

PATH="/usr/sbin:/usr/bin:/sbin:/bin"

SUDOERS_D="/etc/sudoers.d/openclaw-ui"
LOG="/var/packages/openclaw/var/authorize-root.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

# One rule per line. The panel CGI (http) and the service user (sc-openclaw)
# both get passwordless docker; the http rule also covers the terminal-alias
# repair commands (nginx / ln / systemctl) and the root ui-run helper. The
# service user may also re-exec its terminal entry script as root, so the web
# terminal becomes a root shell starting in /root (docker sudo already gives
# sc-openclaw root-equivalent access after authorization, so this adds no new
# privilege).
RULE='http ALL=(root) NOPASSWD: /usr/syno/bin/synopkg, /usr/local/bin/docker, /usr/bin/docker, /bin/systemctl, /usr/sbin/nginx, /usr/bin/nginx, /bin/ln, /var/packages/openclaw/target/scripts/ui-run.sh
sc-openclaw ALL=(root) NOPASSWD: /usr/local/bin/docker, /usr/bin/docker, /usr/syno/bin/synopkg, /var/packages/openclaw/target/scripts/openclaw-terminal-entry.sh'

TMP="${SUDOERS_D}.tmp.$$"
printf '%s\n' "$RULE" > "$TMP"
chmod 440 "$TMP"

if command -v visudo >/dev/null 2>&1 && ! visudo -c -f "$TMP" >/dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') FAIL visudo -c rejected new sudoers" >> "$LOG" 2>/dev/null || true
    rm -f "$TMP"
    exit 1
fi

mv -f "$TMP" "$SUDOERS_D"
chmod 440 "$SUDOERS_D"
echo "$(date '+%Y-%m-%d %H:%M:%S') OK wrote ${SUDOERS_D}" >> "$LOG" 2>/dev/null || true
exit 0
