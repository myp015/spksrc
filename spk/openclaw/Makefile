SPK_NAME = openclaw
SPK_VERS = 2026.4.14
SPK_REV = 1
SPK_ICON = src/openclaw.png

DEPENDS =


MAINTAINER = myp015
DESCRIPTION = OpenClaw gateway packaged for Synology. Requires Container Manager / Docker.
DISPLAY_NAME = OpenClaw
CHANGELOG = "1. Initial OpenClaw package using official Docker image ghcr.io/openclaw/openclaw:v2026.4.14."

HOMEPAGE = https://github.com/openclaw/openclaw
LICENSE = MIT

STARTABLE = yes
SERVICE_USER = auto
SERVICE_SETUP = src/service-setup.sh
SSS_SCRIPT = src/start-stop-status.sh

DSM_UI_DIR = app
SERVICE_PORT = 18789
SERVICE_PORT_TITLE = OpenClaw Gateway (HTTP)
SERVICE_URL = /
ADMIN_PORT = $(SERVICE_PORT)
ADMIN_URL = /

COPY_TARGET = openclaw_copy_target
POST_STRIP_TARGET = openclaw_extra_install

UNSUPPORTED_ARCHS = $(OLD_PPC_ARCHS) $(ARMv5_ARCHS)

include ../../mk/spksrc.spk.mk

.PHONY: openclaw_copy_target
openclaw_copy_target:
	@$(MSG) Create staging content for openclaw
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/var
	@install -m 644 src/openclaw.json $(STAGING_DIR)/var/openclaw.json
	@install -d -m 755 $(STAGING_DIR)/app
	@cp -rf src/app/* $(STAGING_DIR)/app/

.PHONY: openclaw_extra_install
openclaw_extra_install:
	@true
