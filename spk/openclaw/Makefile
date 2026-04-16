SPK_NAME = openclaw
SPK_VERS = 2026.4.14
SPK_REV = 10
SPK_ICON = src/openclaw.png

DEPENDS =

# This package supports x64 and ARMv8 targets (DSM 7.2+).
UNSUPPORTED_ARCHS = $(i686_ARCHS) $(ARMv7_ARCHS) $(ARMv5_ARCHS) $(PPC_ARCHS)

# Bundled Node.js 22 binary requires newer glibc; keep DSM floor at 7.2.
REQUIRED_MIN_DSM = 7.2

MAINTAINER = myp015
DESCRIPTION = OpenClaw gateway packaged for Synology (native mode, no Docker).
DISPLAY_NAME = OpenClaw
CHANGELOG = "1. Keep bootstrap config at /volume1/docker/openclaw/.openclaw/openclaw.json, but move runtime config/state/home to the configured workspace path. 2. On startup, auto-recover workspace openclaw.json from bootstrap config when workspace is wiped. 3. Honor wizard workspace path consistently for skills/runtime files. 4. Auto-sync API providers model lists from upstream /models on each start/restart (non-blocking). 5. Refresh CN channel plugin defaults and stale-plugin cleanup behavior."

HOMEPAGE = https://github.com/openclaw/openclaw
LICENSE = MIT

STARTABLE = yes
SERVICE_USER = auto
SERVICE_SETUP = src/service-setup.sh
WIZARDS_TEMPLATES_DIR = src/wizard_templates

DSM_UI_DIR = app
SERVICE_PORT = 18789
SERVICE_PORT_TITLE = OpenClaw Gateway (HTTP)
SERVICE_URL = /
ADMIN_PORT = $(SERVICE_PORT)
ADMIN_URL = /

PRE_COPY_TARGET = openclaw_prepare_bundle
COPY_TARGET = openclaw_copy_target
POST_STRIP_TARGET = openclaw_extra_install

# Resolve node distro arch from target arch reliably (GH action passes ARCH like x64-7.2)
ARCH_PREFIX := $(word 1,$(subst -, ,$(ARCH)))
ifeq ($(ARCH_PREFIX),x64)
NODE_DIST_ARCH = x64
else ifeq ($(ARCH_PREFIX),aarch64)
NODE_DIST_ARCH = arm64
endif

include ../../mk/spksrc.spk.mk

.PHONY: openclaw_prepare_bundle
openclaw_prepare_bundle:
	@$(MSG) Prepare Node.js runtime and OpenClaw npm bundle
	@rm -rf $(WORK_DIR)/node-runtime $(WORK_DIR)/openclaw-bundle
	@install -d -m 755 $(WORK_DIR)/node-runtime $(WORK_DIR)/openclaw-bundle
	@cd $(WORK_DIR) && \
		curl -fsSL -o node-v22.22.0-linux-$(NODE_DIST_ARCH).tar.xz https://nodejs.org/dist/v22.22.0/node-v22.22.0-linux-$(NODE_DIST_ARCH).tar.xz
	@tar -xJf $(WORK_DIR)/node-v22.22.0-linux-$(NODE_DIST_ARCH).tar.xz -C $(WORK_DIR)/node-runtime --strip-components=1
	@cd $(WORK_DIR) && PATH="$(WORK_DIR)/node-runtime/bin:$$PATH" npm pack openclaw@2026.4.14 --silent
	@tar -xzf $(WORK_DIR)/openclaw-2026.4.14.tgz -C $(WORK_DIR)/openclaw-bundle --strip-components=1
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/node-runtime/bin:$$PATH" npm install --omit=dev --legacy-peer-deps --no-audit --no-fund
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/node-runtime/bin:$$PATH" npm install --omit=dev --legacy-peer-deps --no-audit --no-fund \
		@larksuiteoapi/feishu-openclaw-plugin@2026.3.8 \
		openclaw-channel-dingtalk@2.2.2 \
		@wecom/wecom-openclaw-plugin@2026.4.8 \
		@tencent-connect/openclaw-qqbot@1.7.1

.PHONY: openclaw_copy_target
openclaw_copy_target:
	@$(MSG) Create staging content for openclaw
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/bin
	@install -d -m 755 $(STAGING_DIR)/app/openclaw
	@install -d -m 755 $(STAGING_DIR)/var
	@cp -f $(WORK_DIR)/node-runtime/bin/node $(STAGING_DIR)/bin/node
	@cp -rf $(WORK_DIR)/openclaw-bundle/* $(STAGING_DIR)/app/openclaw/
	@cp -f src/openclaw.json $(STAGING_DIR)/var/openclaw.json
	@install -d -m 755 $(STAGING_DIR)/app
	@cp -rf src/app/* $(STAGING_DIR)/app/

.PHONY: openclaw_extra_install
openclaw_extra_install:
	@true
