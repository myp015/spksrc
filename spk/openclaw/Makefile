SPK_NAME = openclaw
# Always resolve latest stable upstream tag (vX.Y.Z...) at build time.
# If resolution fails, stop immediately (workflow should fail fast).
LATEST_OPENCLAW_VERS := $(shell git ls-remote --tags --refs https://github.com/openclaw/openclaw.git 'v*' | awk -F/ '{print $$3}' | grep -E '^v[0-9]+(\.[0-9]+)*$$' | sed 's/^v//' | sort -V | tail -1)
ifeq ($(strip $(LATEST_OPENCLAW_VERS)),)
$(error Failed to resolve latest stable openclaw version from upstream tags)
endif
# Keep SPK_VERS strictly upstream-semver-like for DSM compatibility.
# Put custom build identity into numeric SPK_REV only.
OPENCLAW_NPM_VERS := $(LATEST_OPENCLAW_VERS)
SPK_VERS := $(LATEST_OPENCLAW_VERS)
SPK_REV = $(shell if [ -n "$$GITHUB_RUN_NUMBER" ]; then echo $$GITHUB_RUN_NUMBER; elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git rev-list --count HEAD; else date +%Y%m%d%H%M; fi)
SPK_ICON = src/openclaw.png

DEPENDS =

# This package supports x64 and ARMv8 targets (DSM 7.2+).
UNSUPPORTED_ARCHS = $(i686_ARCHS) $(ARMv7_ARCHS) $(ARMv5_ARCHS) $(PPC_ARCHS)

# Bundled Node.js 22 binary requires newer glibc; keep DSM floor at 7.2.
REQUIRED_MIN_DSM = 7.2

MAINTAINER = myp015
DESCRIPTION = OpenClaw gateway packaged for Synology (native mode, no Docker).
DISPLAY_NAME = OpenClaw
CHANGELOG = "1. Build-time auto-resolve latest stable upstream OpenClaw tag; fail fast if fetch fails. 2. Follow upstream bundled-plugin runtime dependency postinstall at build time. 3. Keep extra preinstall plugins for Feishu/DingTalk/WeCom/QQBot. 4. Normalize Feishu allowFrom for open policy and migrate legacy ~/.openclaw/extensions into state/extensions to reduce state-split warnings. 5. Default memory backend to builtin in SPK template and auto-fallback to builtin when qmd binary is unavailable. 6. Tighten runtime config permission to 600. 7. Provide /usr/local/bin/openclaw alias (keep openclaw-spk for compatibility). 8. Keep SPK_VERS clean and use numeric SPK_REV as build identity for DSM/SPK format compatibility."

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
	@rm -rf $(WORK_DIR)/node-runtime $(WORK_DIR)/build-node-runtime $(WORK_DIR)/openclaw-bundle
	@install -d -m 755 $(WORK_DIR)/node-runtime $(WORK_DIR)/build-node-runtime $(WORK_DIR)/openclaw-bundle
	@cd $(WORK_DIR) && \
		curl -fsSL -o node-v22.22.0-linux-$(NODE_DIST_ARCH).tar.xz https://nodejs.org/dist/v22.22.0/node-v22.22.0-linux-$(NODE_DIST_ARCH).tar.xz
	@tar -xJf $(WORK_DIR)/node-v22.22.0-linux-$(NODE_DIST_ARCH).tar.xz -C $(WORK_DIR)/node-runtime --strip-components=1
	@HOST_ARCH=$$(uname -m); \
		case "$$HOST_ARCH" in \
			x86_64|amd64) HOST_NODE_DIST_ARCH=x64 ;; \
			aarch64|arm64) HOST_NODE_DIST_ARCH=arm64 ;; \
			*) echo "Unsupported host arch for build-node-runtime: $$HOST_ARCH"; exit 1 ;; \
		esac; \
		cd $(WORK_DIR) && \
		curl -fsSL -o node-v22.22.0-linux-$$HOST_NODE_DIST_ARCH.tar.xz https://nodejs.org/dist/v22.22.0/node-v22.22.0-linux-$$HOST_NODE_DIST_ARCH.tar.xz && \
		tar -xJf node-v22.22.0-linux-$$HOST_NODE_DIST_ARCH.tar.xz -C $(WORK_DIR)/build-node-runtime --strip-components=1
	@cd $(WORK_DIR) && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm pack openclaw@$(OPENCLAW_NPM_VERS) --silent
	@tar -xzf $(WORK_DIR)/openclaw-$(OPENCLAW_NPM_VERS).tgz -C $(WORK_DIR)/openclaw-bundle --strip-components=1
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm install --omit=dev --legacy-peer-deps --no-audit --no-fund \
		@larksuiteoapi/feishu-openclaw-plugin@2026.3.8 \
		@soimy/dingtalk@3.5.3 \
		@sunnoy/wecom@3.0.0 \
		@tencent-connect/openclaw-qqbot@1.7.1
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node scripts/postinstall-bundled-plugins.mjs

.PHONY: openclaw_copy_target
openclaw_copy_target:
	@$(MSG) Create staging content for openclaw
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/bin
	@install -d -m 755 $(STAGING_DIR)/app/openclaw
	@install -d -m 755 $(STAGING_DIR)/var
	@cp -f $(WORK_DIR)/node-runtime/bin/node $(STAGING_DIR)/bin/node
	@cp -rf $(WORK_DIR)/openclaw-bundle/* $(STAGING_DIR)/app/openclaw/
	@install -d -m 755 $(STAGING_DIR)/app/openclaw/config
	@cp -f src/openclaw.json $(STAGING_DIR)/app/openclaw/config/openclaw.template.json
	@install -d -m 755 $(STAGING_DIR)/app
	@cp -rf src/app/* $(STAGING_DIR)/app/
	@cp -f src/openclaw-spk $(STAGING_DIR)/bin/openclaw-spk
	@cp -f src/openclaw-spk $(STAGING_DIR)/bin/openclaw
	@chmod 755 $(STAGING_DIR)/bin/openclaw-spk
	@chmod 755 $(STAGING_DIR)/bin/openclaw
	@cp -f src/SPK-README-openclaw-spk.md $(STAGING_DIR)/app/openclaw/SPK-README-openclaw-spk.md

.PHONY: openclaw_extra_install
openclaw_extra_install:
	@true
