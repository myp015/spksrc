PKG_NAME = frpc
# Version defaults to the latest stable GitHub release (resolved at build
# time). Override on the command line with PKG_VERS=<version> to pin.
RESOLVE_VERSIONS := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../../spk/frpc/src/resolve-versions.sh
RESOLVED_VERSIONS := $(shell sh -c '$(RESOLVE_VERSIONS) 2>/dev/null')
LATEST_PKG_VERSION := $(patsubst PKG_VERSION=%,%,$(filter PKG_VERSION=%,$(RESOLVED_VERSIONS)))
PKG_VERS ?= $(LATEST_PKG_VERSION)
PKG_EXT = tar.gz

# Version resolves to the latest GitHub release at build time, so a fixed
# digests file can never match. Skip source checksum verification.
CHECKSUM_TARGET = checksum_skip
.PHONY: checksum_skip
checksum_skip:
	@$(create_target_dir)
	@touch -f $(CHECKSUM_COOKIE)

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
