SPK_NAME = cliproxy
SPK_VERS = 6.9.26
SPK_REV = 9
SPK_ICON = src/cliproxy.png

DEPENDS = cross/cliproxy

UNSUPPORTED_ARCHS = $(ARMv5_ARCHS)
# not supported by go:
UNSUPPORTED_ARCHS += $(PPC_ARCHS)

MAINTAINER = myp015
DESCRIPTION = OpenAI/Gemini/Claude/Codex compatible proxy API server for CLI tools. 管理后台默认密码: 123456.
DISPLAY_NAME = CLIProxyAPI
CHANGELOG = "1. Keep DSM .url shortcut opening /management.html. 2. Add ADMIN_URL=/management.html so Package Center detail URL includes path."

HOMEPAGE = https://github.com/router-for-me/CLIProxyAPI
LICENSE = MIT

SERVICE_SETUP = src/service-setup.sh

STARTABLE = yes
SERVICE_USER = auto
SERVICE_PORT = 8317
SERVICE_URL = /management.html
ADMIN_PORT = $(SERVICE_PORT)
ADMIN_URL = /management.html
NO_SERVICE_SHORTCUT = no
DSM_UI_DIR = app

POST_STRIP_TARGET = cliproxy_extra_install

include ../../mk/spksrc.spk.mk

.PHONY: cliproxy_extra_install
cliproxy_extra_install:
	@install -d -m 755 $(STAGING_DIR)/var
	@install -m 644 src/config.yaml $(STAGING_DIR)/var/
	@install -d -m 755 $(STAGING_DIR)/app
	@cp -rf src/app/* $(STAGING_DIR)/app/
