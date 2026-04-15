SPK_NAME = frpc
SPK_VERS = 0.68.1
SPK_REV = 1
SPK_ICON = src/frpc.png

DEPENDS = cross/frpc

UNSUPPORTED_ARCHS = $(ARMv5_ARCHS)
# not supported by go:
UNSUPPORTED_ARCHS += $(PPC_ARCHS)

MAINTAINER = myp015
DESCRIPTION = frp client for exposing local services to the Internet through a remote frp server.
DISPLAY_NAME = frpc
CHANGELOG = "1. Update frpc to 0.68.1."

HOMEPAGE = https://github.com/fatedier/frp
LICENSE = Apache-2.0

SERVICE_SETUP = src/service-setup.sh

STARTABLE = yes
SERVICE_USER = auto
NO_SERVICE_SHORTCUT = yes
DSM_UI_DIR = ui

POST_STRIP_TARGET = frpc_extra_install

include ../../mk/spksrc.spk.mk

.PHONY: frpc_extra_install
frpc_extra_install:
	@install -d -m 755 $(STAGING_DIR)/var
	@install -m 644 src/frpc.toml $(STAGING_DIR)/var/
	@install -d -m 755 $(STAGING_DIR)/ui
	@cp -rf src/ui/* $(STAGING_DIR)/ui/
	@chmod 755 $(STAGING_DIR)/ui/index.cgi
