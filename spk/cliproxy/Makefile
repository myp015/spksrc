SPK_NAME = cliproxy
SPK_VERS = 6.9.26
SPK_REV = 1
SPK_ICON = src/cliproxy.png

DEPENDS = cross/cliproxy

UNSUPPORTED_ARCHS = $(ARMv5_ARCHS)
# not supported by go:
UNSUPPORTED_ARCHS += $(PPC_ARCHS)

MAINTAINER = myp015
DESCRIPTION = OpenAI/Gemini/Claude/Codex compatible proxy API server for CLI tools.
DISPLAY_NAME = CLIProxyAPI
CHANGELOG = "1. Initial package for CLIProxyAPI v6.9.26."

HOMEPAGE = https://github.com/router-for-me/CLIProxyAPI
LICENSE = MIT

SERVICE_SETUP = src/service-setup.sh

STARTABLE = yes
SERVICE_USER = auto
SERVICE_PORT = 8317
ADMIN_PORT = $(SERVICE_PORT)
NO_SERVICE_SHORTCUT = yes
DSM_UI_DIR = ui

POST_STRIP_TARGET = cliproxy_extra_install

include ../../mk/spksrc.spk.mk

.PHONY: cliproxy_extra_install
cliproxy_extra_install:
	@install -d -m 755 $(STAGING_DIR)/var
	@install -m 644 src/config.yaml $(STAGING_DIR)/var/
	@install -d -m 755 $(STAGING_DIR)/ui
	@cp -rf src/ui/* $(STAGING_DIR)/ui/
	@chmod 755 $(STAGING_DIR)/ui/index.cgi
