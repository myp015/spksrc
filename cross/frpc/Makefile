PKG_NAME = frpc
PKG_VERS = 0.68.1
PKG_EXT = tar.gz
PKG_DIST_NAME = v$(PKG_VERS).$(PKG_EXT)
PKG_DIST_SITE = https://github.com/fatedier/frp/archive
PKG_DIST_FILE = frp-$(PKG_VERS).$(PKG_EXT)
PKG_DIR = frp-$(PKG_VERS)

BUILD_DEPENDS = native/go

# lacking support for atomics
UNSUPPORTED_ARCHS = $(ARMv5_ARCHS)
# not supported by go
UNSUPPORTED_ARCHS += $(PPC_ARCHS)

HOMEPAGE = https://github.com/fatedier/frp
COMMENT  = A fast reverse proxy helping expose a local server behind NAT or firewall to the internet.
LICENSE = Apache-2.0

GO_SRC_DIR = $(WORK_DIR)/$(PKG_DIR)
COMPILE_TARGET = frpc_compile
INSTALL_TARGET = frpc_install

include ../../mk/spksrc.cross-go.mk

.PHONY: frpc_compile
frpc_compile:
	@$(MSG) "- Build frpc"
	@cd $(GO_SRC_DIR) && env $(ENV) go build -trimpath -tags noweb -ldflags "-s -w" -o frpc ./cmd/frpc

.PHONY: frpc_install
frpc_install:
	@install -m 755 -d $(STAGING_INSTALL_PREFIX)/bin
	@install -m 755 $(GO_SRC_DIR)/frpc $(STAGING_INSTALL_PREFIX)/bin/
