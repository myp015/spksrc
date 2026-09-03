PKG_NAME = ddns-go
# Version defaults to the latest stable GitHub release (resolved at build
# time). Override on the command line with PKG_VERS=<version> to pin.
RESOLVE_VERSIONS := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../../spk/ddns-go/src/resolve-versions.sh
RESOLVED_VERSIONS := $(shell sh -c '$(RESOLVE_VERSIONS) 2>/dev/null')
LATEST_PKG_VERSION := $(patsubst PKG_VERSION=%,%,$(filter PKG_VERSION=%,$(RESOLVED_VERSIONS)))
PKG_VERS ?= $(LATEST_PKG_VERSION)
WEB_VERSION = $(PKG_VERS)
PKG_EXT = tar.gz
PKG_DIST_NAME = v$(PKG_VERS).$(PKG_EXT)
PKG_DIST_SITE = https://github.com/jeessy2/ddns-go/archive
PKG_DIST_FILE = $(PKG_NAME)-$(PKG_VERS).$(PKG_EXT)
PKG_DIR = $(PKG_NAME)-$(PKG_VERS)

BUILD_DEPENDS = native/go

# lacking support for atomics
UNSUPPORTED_ARCHS = $(ARMv5_ARCHS)
# not supported by go
UNSUPPORTED_ARCHS += $(PPC_ARCHS)

HOMEPAGE = https://github.com/jeessy2/ddns-go
COMMENT  = Automatically obtain your public IPv4 or IPv6 address and resolve it to the corresponding domain name service.
LICENSE = MIT

COMPILE_TARGET = ddns-go_compile_target
INSTALL_TARGET = ddns-go_install

include ../../mk/spksrc.cross-go.mk

.PHONY: ddns-go_compile_target
ddns-go_compile_target:
	@$(RUN) $(MAKE) VERSION=v$(PKG_VERS) BUILD_TIME="$$(date -u +'%Y-%m-%dT%H:%M:%SZ')" build

.PHONY: ddns-go_install
ddns-go_install:
	@mkdir -p $(STAGING_INSTALL_PREFIX)/bin
	@install -m 755 $(WORK_DIR)/$(PKG_DIR)/ddns-go $(STAGING_INSTALL_PREFIX)/bin/
