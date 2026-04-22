SPK_NAME = ainasclaw
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

MAINTAINER = ainas
MAINTAINER_URL = https://ainas.taobao.com
DESCRIPTION = AiNasClaw for Synology (ported from sc-openclaw_v0.0.10.fpk with fn monitor assets + DSM runtime integration). 默认 Token: 123456（安装后可修改）。
DISPLAY_NAME = AiNasClaw
CHANGELOG = "Initial AiNasClaw package: migrated fn.sc-openclaw monitor/ui assets from sc-openclaw_v0.0.10.fpk and integrated with DSM OpenClaw runtime bundle."

HOMEPAGE = https://ainas.taobao.com
LICENSE = MIT

STARTABLE = yes
SERVICE_USER = auto
SERVICE_SETUP = src/service-setup.sh
NO_SERVICE_SHORTCUT = yes

DSM_UI_DIR = app
DSM_UI_CONFIG = src/app/config
DSM_APP_NAME = SYNOCOMMUNITY.AiNasClaw.AppInstance
SERVICE_PORT = 18700
SERVICE_PORT_TITLE = AiNasClaw Panel (HTTP)
SERVICE_URL = /app/openclaw/
# Package Center "Open" should use DSM webman entry (same-origin with session).
ADMIN_PORT = $(SERVICE_PORT)
ADMIN_URL = /webman/3rdparty/ainasclaw/index.cgi

PRE_COPY_TARGET = openclaw_prepare_bundle
COPY_TARGET = openclaw_copy_target
POST_STRIP_TARGET = openclaw_extra_install

# Resolve node distro arch from target arch reliably (GH action passes ARCH like x64-7.2)
ARCH_PREFIX := $(word 1,$(subst -, ,$(ARCH)))
ifeq ($(ARCH_PREFIX),x64)
NODE_DIST_ARCH = x64
BUN_DIST_ARCH = x64
TTYD_DIST_ARCH = x86_64
else ifeq ($(ARCH_PREFIX),aarch64)
NODE_DIST_ARCH = arm64
BUN_DIST_ARCH = aarch64
TTYD_DIST_ARCH = aarch64
endif

include ../../mk/spksrc.spk.mk

# Keep package id as `ainasclaw`, but force runtime account to `sc-openclaw`.
# spksrc defaults SPK_USER to SPK_NAME on DSM7; override here intentionally.
SPK_USER = openclaw

.PHONY: openclaw_prepare_bundle
openclaw_prepare_bundle:
	@$(MSG) Prepare Node.js runtime and OpenClaw npm bundle
	@rm -rf $(WORK_DIR)/node-runtime $(WORK_DIR)/build-node-runtime $(WORK_DIR)/openclaw-bundle $(WORK_DIR)/bun-runtime
	@install -d -m 755 $(WORK_DIR)/node-runtime $(WORK_DIR)/build-node-runtime $(WORK_DIR)/openclaw-bundle $(WORK_DIR)/bun-runtime
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
		@tencent-connect/openclaw-qqbot@1.7.1 \
		@tencent-weixin/openclaw-weixin@2.1.8
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node scripts/postinstall-bundled-plugins.mjs
	@cd $(WORK_DIR) && \
		curl -fsSL -o bun-linux-$(BUN_DIST_ARCH).zip https://github.com/oven-sh/bun/releases/latest/download/bun-linux-$(BUN_DIST_ARCH).zip
	@cd $(WORK_DIR)/bun-runtime && unzip -q $(WORK_DIR)/bun-linux-$(BUN_DIST_ARCH).zip
	@cd $(WORK_DIR)/bun-runtime && mv bun-linux-$(BUN_DIST_ARCH)/bun bun && rm -rf bun-linux-$(BUN_DIST_ARCH)
	@cd $(WORK_DIR) && \
		curl -fsSL -o ttyd.$(TTYD_DIST_ARCH) https://github.com/tsl0922/ttyd/releases/download/1.7.4/ttyd.$(TTYD_DIST_ARCH)
	@chmod +x $(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH)

.PHONY: openclaw_copy_target
openclaw_copy_target:
	@$(MSG) Create staging content for openclaw
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/bin
	@install -d -m 755 $(STAGING_DIR)/app/openclaw
	@install -d -m 755 $(STAGING_DIR)/var
	@cp -f $(WORK_DIR)/node-runtime/bin/node $(STAGING_DIR)/bin/node
	@cp -f $(WORK_DIR)/bun-runtime/bun $(STAGING_DIR)/bin/bun
	@chmod 755 $(STAGING_DIR)/bin/bun
	@cp -f $(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH) $(STAGING_DIR)/bin/ttyd
	@chmod 755 $(STAGING_DIR)/bin/ttyd
	@cp -rf $(WORK_DIR)/openclaw-bundle/* $(STAGING_DIR)/app/openclaw/
	@install -d -m 755 $(STAGING_DIR)/app/openclaw/config
	@cp -f src/openclaw.json $(STAGING_DIR)/app/openclaw/config/openclaw.template.json
	@install -d -m 755 $(STAGING_DIR)/app
	@cp -rf src/app/* $(STAGING_DIR)/app/
	@rm -f $(STAGING_DIR)/app/index.cgi
	@ln -s ../ui/index.cgi $(STAGING_DIR)/app/index.cgi
	@install -d -m 755 $(STAGING_DIR)/ui
	@cp -rf src/ui/* $(STAGING_DIR)/ui/
	@chmod 755 $(STAGING_DIR)/ui/index.cgi
	@rm -f $(STAGING_DIR)/ui/config $(STAGING_DIR)/ui/ainasclaw.sc
	@cp -f src/openclaw-spk $(STAGING_DIR)/bin/openclaw
	@chmod 755 $(STAGING_DIR)/bin/openclaw
	@cp -f src/SPK-README-openclaw-spk.md $(STAGING_DIR)/app/openclaw/SPK-README-openclaw-spk.md

.PHONY: openclaw_extra_install
openclaw_extra_install:
	@true
