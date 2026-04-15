PKG_NAME = cliproxy
PKG_VERS = 6.9.26
PKG_EXT = tar.gz
PKG_DIST_NAME = v$(PKG_VERS).$(PKG_EXT)
PKG_DIST_SITE = https://github.com/router-for-me/CLIProxyAPI/archive/refs/tags
PKG_DIST_FILE = CLIProxyAPI-$(PKG_VERS).$(PKG_EXT)
PKG_DIR = CLIProxyAPI-$(PKG_VERS)

BUILD_DEPENDS = native/go

# lacking support for atomics
UNSUPPORTED_ARCHS = $(ARMv5_ARCHS)
# not supported by go
UNSUPPORTED_ARCHS += $(PPC_ARCHS)

HOMEPAGE = https://github.com/router-for-me/CLIProxyAPI
COMMENT  = OpenAI/Gemini/Claude/Codex compatible proxy API server for CLI tools.
LICENSE = MIT

GO_SRC_DIR = $(WORK_DIR)/$(PKG_DIR)
COMPILE_TARGET = cliproxy_compile
INSTALL_TARGET = cliproxy_install

include ../../mk/spksrc.cross-go.mk

.PHONY: cliproxy_compile
cliproxy_compile:
	@$(MSG) "- Build cliproxy"
	@cd $(GO_SRC_DIR) && env $(ENV) go build -trimpath -ldflags "-s -w -X main.Version=v$(PKG_VERS)" -o cliproxy ./cmd/server

.PHONY: cliproxy_install
cliproxy_install:
	@install -m 755 -d $(STAGING_INSTALL_PREFIX)/bin
	@install -m 755 $(GO_SRC_DIR)/cliproxy $(STAGING_INSTALL_PREFIX)/bin/
