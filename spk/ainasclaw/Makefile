SPK_NAME = ainasclaw
# Version resolution: automatically fetch the latest STABLE versions of the
# OpenClaw core package and its bundled channel plugins from the npm registry
# (dist-tags.latest) at build time. This keeps the build tracking upstream
# releases without manual pins. resolve-versions.sh is also run by CI (and can
# be invoked with --json for tooling).
#
# Keep SPK_VERS strictly upstream-semver-like for DSM compatibility:
# DSM package INFO versions do not accept npm build suffixes like `-2`, so we
# derive SPK_VERS from the clean base semver and carry the exact npm version
# (with suffix, e.g. 2026.7.1-2) in OPENCLAW_NPM_VERS for packaging.
# Make is invoked with -C spk/ainasclaw, so CURDIR is already the package root.
RESOLVE_VERSIONS := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/src/resolve-versions.sh
RESOLVED_VERSIONS := $(shell sh -c '$(RESOLVE_VERSIONS)')
OPENCLAW_NPM_VERSION := $(patsubst OPENCLAW_NPM_VERSION=%,%,$(filter OPENCLAW_NPM_VERSION=%,$(RESOLVED_VERSIONS)))
OPENCLAW_SPK_VERSION_TMP := $(patsubst OPENCLAW_SPK_VERSION=%,%,$(filter OPENCLAW_SPK_VERSION=%,$(RESOLVED_VERSIONS)))
FEISHU_VERSION := $(patsubst FEISHU_VERSION=%,%,$(filter FEISHU_VERSION=%,$(RESOLVED_VERSIONS)))
WECOM_VERSION := $(patsubst WECOM_VERSION=%,%,$(filter WECOM_VERSION=%,$(RESOLVED_VERSIONS)))
QQ_BOT_VERSION := $(patsubst QQ_BOT_VERSION=%,%,$(filter QQ_BOT_VERSION=%,$(RESOLVED_VERSIONS)))
ifeq ($(strip $(OPENCLAW_NPM_VERSION)),)
OPENCLAW_NPM_VERSION := 2026.8.1
OPENCLAW_SPK_VERSION_TMP := 2026.8.1
endif
# Safety: pin FEISHU_VERSION to the core version if resolve-versions failed or
# returned an incompatible version (e.g. feishu 2026.8.x with core 2026.7.x).
OPENCLAW_BASE_VER = $(firstword $(subst -, ,$(OPENCLAW_NPM_VERSION)))
ifeq ($(strip $(FEISHU_VERSION)),)
FEISHU_VERSION := $(OPENCLAW_BASE_VER)
endif
# If feishu major.minor doesn't match core major.minor, override to core version.
ifneq ($(word 1,$(subst ., ,$(FEISHU_VERSION))).$(word 2,$(subst ., ,$(FEISHU_VERSION))),$(word 1,$(subst ., ,$(OPENCLAW_BASE_VER))).$(word 2,$(subst ., ,$(OPENCLAW_BASE_VER))))
FEISHU_VERSION := $(OPENCLAW_BASE_VER)
endif
OPENCLAW_NPM_VERS := $(OPENCLAW_NPM_VERSION)
MIN_NODEJS_RUNTIME_VERS := 24.11.1
NODEJS_RUNTIME_VERS := $(shell sh -c 'set -e; \
	v=""; \
	if command -v curl >/dev/null 2>&1; then \
		v=$$(curl -fsSL --retry 3 --retry-delay 1 https://nodejs.org/dist/index.json 2>/dev/null | \
			grep -oE "\"version\":\"v24\\.[0-9]+\\.[0-9]+\"" | sed -E "s/.*\"v([0-9]+\\.[0-9]+\\.[0-9]+)\".*/\\1/" | sort -V | tail -n 1); \
	fi; \
	if [ -z "$$v" ] && command -v wget >/dev/null 2>&1; then \
		v=$$(wget -qO- https://nodejs.org/dist/index.json 2>/dev/null | \
			grep -oE "\"version\":\"v24\\.[0-9]+\\.[0-9]+\"" | sed -E "s/.*\"v([0-9]+\\.[0-9]+\\.[0-9]+)\".*/\\1/" | sort -V | tail -n 1); \
	fi; \
	echo "$$v"')
ifeq ($(strip $(NODEJS_RUNTIME_VERS)),)
NODEJS_RUNTIME_VERS := 24.11.1
$(warning Failed to resolve latest Node.js v24.x; fallback to v$(NODEJS_RUNTIME_VERS))
endif
ifneq ($(shell printf '%s\n%s\n' $(MIN_NODEJS_RUNTIME_VERS) $(NODEJS_RUNTIME_VERS) | sort -V | head -n1),$(MIN_NODEJS_RUNTIME_VERS))
$(warning Resolved Node.js runtime v$(NODEJS_RUNTIME_VERS) is below minimum v$(MIN_NODEJS_RUNTIME_VERS); force minimum)
NODEJS_RUNTIME_VERS := $(MIN_NODEJS_RUNTIME_VERS)
endif
SPK_VERS := $(OPENCLAW_SPK_VERSION_TMP)
# SPK_REV must be a plain integer: DSM package INFO only accepts
# `SPK_VERS-SPK_REV` where the revision is a non-negative integer (spksrc
# writes version="$(SPK_VERS)-$(SPK_REV)"). Putting a '.' or long hash here
# makes DSM reject the package as '套件格式不正确'. Upstream version changes
# are surfaced through SPK_VERS itself (e.g. 2026.7.1 -> 2026.7.2).
SPK_REV = $(shell if [ -n "$$GITHUB_RUN_NUMBER" ]; then echo $$GITHUB_RUN_NUMBER; elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git rev-list --count HEAD; else date +%Y%m%d%H%M; fi)
SPK_ICON = src/openclaw.png

DEPENDS =

# This package supports x64 and ARMv8 targets (DSM 7.2+).
UNSUPPORTED_ARCHS = $(i686_ARCHS) $(ARMv7_ARCHS) $(ARMv5_ARCHS) $(PPC_ARCHS)

# Bundled Node.js 22 binary requires newer glibc; keep DSM floor at 7.2.
REQUIRED_MIN_DSM = 7.2

MAINTAINER = ainas
MAINTAINER_URL = https://ainas.taobao.com
DESCRIPTION = AiNasClaw for Synology，淘宝店铺：https://ainas.taobao.com  默认 Token: 123456。
DISPLAY_NAME = AiNasClaw
CHANGELOG = "integrated with DSM OpenClaw runtime bundle."

HOMEPAGE = https://ainas.taobao.com
LICENSE = MIT

STARTABLE = yes
SERVICE_USER = auto
SERVICE_SETUP = src/service-setup.sh
WIZARDS_TEMPLATES_DIR = src/wizard_templates
NO_SERVICE_SHORTCUT = yes

DSM_UI_DIR = app
DSM_UI_CONFIG = src/app/config
DSM_APP_NAME = SYNOCOMMUNITY.AiNasClaw.AppInstance
# DSM package metadata port (for conflict precheck) uses a fixed fallback.
# Runtime gateway port is dynamically assigned on fresh install in service-setup.sh.
SERVICE_PORT = 58789
SERVICE_PORT_TITLE = AiNasClaw Panel (HTTP)
SERVICE_URL = /app/openclaw/

PRE_COPY_TARGET = openclaw_prepare_bundle
COPY_TARGET = openclaw_copy_target
POST_STRIP_TARGET = openclaw_extra_install

# Resolve upstream binary arch from target arch reliably.
# ARCH can be generic (x64/aarch64) or platform-specific (apollolake/rtd1619b).
TARGET_ARCH_NAME = $(or $(ARCH),$(TC_ARCH),$(word 1,$(subst -, ,$(TC_NAME))))
NODE_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),arm64,))
BUN_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),aarch64,))
TTYD_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x86_64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),aarch64,))

include ../../mk/spksrc.spk.mk

# Include signed outer INFO checksum metadata in final SPK root.
SPK_CONTENT += spk-info.sha256 spk-info.sig

# Keep package id as `ainasclaw`, but force runtime account to `sc-openclaw`.
# spksrc defaults SPK_USER to SPK_NAME on DSM7; override here intentionally.
SPK_USER = openclaw

.PHONY: openclaw_prepare_bundle
openclaw_prepare_bundle:
	@$(MSG) Prepare Node.js runtime and OpenClaw npm bundle
	@[ -n "$(NODE_DIST_ARCH)" ] || { echo "Unsupported target arch for node bundle: $(TARGET_ARCH_NAME)"; exit 1; }
	@[ -n "$(BUN_DIST_ARCH)" ] || { echo "Unsupported target arch for bun bundle: $(TARGET_ARCH_NAME)"; exit 1; }
	@[ -n "$(TTYD_DIST_ARCH)" ] || { echo "Unsupported target arch for ttyd bundle: $(TARGET_ARCH_NAME)"; exit 1; }
	@rm -rf $(WORK_DIR)/node-runtime $(WORK_DIR)/build-node-runtime $(WORK_DIR)/openclaw-bundle $(WORK_DIR)/bun-runtime
	@install -d -m 755 $(WORK_DIR)/node-runtime $(WORK_DIR)/build-node-runtime $(WORK_DIR)/openclaw-bundle $(WORK_DIR)/bun-runtime
	@cd $(WORK_DIR) && \
		curl -fsSL -o node-v$(NODEJS_RUNTIME_VERS)-linux-$(NODE_DIST_ARCH).tar.xz https://nodejs.org/dist/v$(NODEJS_RUNTIME_VERS)/node-v$(NODEJS_RUNTIME_VERS)-linux-$(NODE_DIST_ARCH).tar.xz
	@tar -xJf $(WORK_DIR)/node-v$(NODEJS_RUNTIME_VERS)-linux-$(NODE_DIST_ARCH).tar.xz -C $(WORK_DIR)/node-runtime --strip-components=1
	@HOST_ARCH=$$(uname -m); \
		case "$$HOST_ARCH" in \
			x86_64|amd64) HOST_NODE_DIST_ARCH=x64 ;; \
			aarch64|arm64) HOST_NODE_DIST_ARCH=arm64 ;; \
			*) echo "Unsupported host arch for build-node-runtime: $$HOST_ARCH"; exit 1 ;; \
		esac; \
		cd $(WORK_DIR) && \
		curl -fsSL -o node-v$(NODEJS_RUNTIME_VERS)-linux-$$HOST_NODE_DIST_ARCH.tar.xz https://nodejs.org/dist/v$(NODEJS_RUNTIME_VERS)/node-v$(NODEJS_RUNTIME_VERS)-linux-$$HOST_NODE_DIST_ARCH.tar.xz && \
		tar -xJf node-v$(NODEJS_RUNTIME_VERS)-linux-$$HOST_NODE_DIST_ARCH.tar.xz -C $(WORK_DIR)/build-node-runtime --strip-components=1
	@cd $(WORK_DIR) && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm pack openclaw@$(OPENCLAW_NPM_VERS) --silent
	@tar -xzf $(WORK_DIR)/openclaw-$(OPENCLAW_NPM_VERS).tgz -C $(WORK_DIR)/openclaw-bundle --strip-components=1
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm_config_ignore_scripts=true npm_config_legacy_peer_deps=true npm install --omit=dev --legacy-peer-deps --save-exact --no-audit --no-fund \
		@openclaw/feishu@$(FEISHU_VERSION) \
		@sunnoy/wecom@$(WECOM_VERSION) \
		@tencent-connect/openclaw-qqbot@$(QQ_BOT_VERSION) \
		acpx@0.5.3 \
		node-edge-tts@1.2.10
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node scripts/postinstall-bundled-plugins.mjs
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm_config_ignore_scripts=true npm_config_legacy_peer_deps=true npm install --omit=dev --legacy-peer-deps --force --no-audit --no-fund \
		@anthropic-ai/sdk@0.93.0 \
		@anthropic-ai/claude-agent-sdk@0.3.239 \
		@anthropic-ai/vertex-sdk@^0.16.0 \
		@aws-sdk/client-bedrock@3.1034.0 \
		@aws-sdk/client-bedrock-runtime@3.1034.0 \
		@aws-sdk/credential-provider-node@3.972.34 \
		@aws/bedrock-token-generator@^1.1.0 \
		@clack/prompts@^1.2.0 \
		@google/genai@^1.50.1 \
		@homebridge/ciao@^1.3.6 \
		@larksuiteoapi/node-sdk@^1.61.1 \
		@mariozechner/pi-agent-core@0.70.2 \
		@mariozechner/pi-ai@0.70.2 \
		@modelcontextprotocol/sdk@1.29.0 \
		@mozilla/readability@^0.6.0 \
		@tencent-connect/qqbot-connector@^1.1.0 \
		@wecom/aibot-node-sdk@^1.0.3 \
		acpx@0.5.3 \
		commander@^14.0.3 \
		express@^5.2.1 \
		file-type@^21.3.0 \
		form-data@^4.0.0 \
		linkedom@^0.18.12 \
		lit@3.3.3 \
		markdown-it@15.0.0 \
		mammoth@^1.12.0 \
		mpg123-decoder@^1.0.3 \
		node-edge-tts@^1.2.10 \
		pdf-parse@^2.4.5 \
		pdfjs-dist@^5.6.205 \
		pinyin-pro@^3.28.0 \
		playwright-core@1.59.1 \
		qrcode-terminal@0.12.0 \
		silk-wasm@^3.7.1 \
		typebox@1.1.31 \
		undici@8.1.0 \
		ws@^8.20.0 \
		zod@4.3.6
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm dedupe --prefer-dedupe --legacy-peer-deps --no-audit --no-fund || true
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm_config_legacy_peer_deps=true npm install --legacy-peer-deps --no-package-lock --no-save @aws-sdk/credential-provider-node@3.972.34
	@if [ -d "$(WORK_DIR)/openclaw-bundle/dist/extensions/amazon-bedrock" ]; then \
		cd $(WORK_DIR)/openclaw-bundle/dist/extensions/amazon-bedrock && \
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm pack @aws-sdk/credential-provider-node@3.972.34 --silent && \
		install -d node_modules/@aws-sdk/credential-provider-node && \
		tar -xzf aws-sdk-credential-provider-node-3.972.34.tgz -C node_modules/@aws-sdk/credential-provider-node --strip-components=1 && \
		rm -f aws-sdk-credential-provider-node-3.972.34.tgz; \
	else \
		echo "[ainasclaw] skip amazon-bedrock runtime patch: dist/extensions/amazon-bedrock not found"; \
	fi
	@cd $(WORK_DIR)/openclaw-bundle && \
		if [ "$(NODE_DIST_ARCH)" = "x64" ]; then \
			find node_modules -type d \( -name '*linux-arm64*' -o -name '*arm64-musl*' -o -name '*arm64-gnu*' -o -name '*-arm64' -o -name '*aarch64*' \) -prune -exec rm -rf {} + 2>/dev/null || true; \
		else \
			find node_modules -type d \( -name '*linux-x64*' -o -name '*x64-musl*' -o -name '*x64-gnu*' -o -name '*-x64' -o -name '*x86_64*' \) -prune -exec rm -rf {} + 2>/dev/null || true; \
		fi
	@cd $(WORK_DIR)/openclaw-bundle && \
		find dist/extensions -type l -lname '*\.openclaw-install-stage/*' -delete 2>/dev/null || true
	@cd $(WORK_DIR)/openclaw-bundle && \
		find dist/extensions -type d -path '*/node_modules/.bin' -prune -exec rm -rf {} + 2>/dev/null || true
	@cd $(WORK_DIR)/openclaw-bundle && \
		mkdir -p .spk-build-state && \
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node -e "const fs=require('fs');const path=require('path');const root=process.cwd();const ext=path.join(root,'dist','extensions');const collect=(pkg)=>({...(pkg.dependencies||{}),...(pkg.optionalDependencies||{})});const byName=new Map();for(const e of fs.readdirSync(ext,{withFileTypes:true})){if(!e.isDirectory())continue;const pj=path.join(ext,e.name,'package.json');if(!fs.existsSync(pj))continue;let pkg;try{pkg=JSON.parse(fs.readFileSync(pj,'utf8'));}catch{continue;}for(const [n,v] of Object.entries(collect(pkg))){if(typeof v!=='string'||!v.trim())continue;if(!byName.has(n))byName.set(n,v.trim());}}const out=[...byName.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([n,v])=>n+'@'+v).join('\n')+'\n';fs.writeFileSync(path.join(root,'.spk-build-state','bundled-runtime-specs.txt'),out,'utf8');console.log('Prepared bundled runtime spec count: '+byName.size);" && \
		specs="$$(tr '\n' ' ' < .spk-build-state/bundled-runtime-specs.txt)" && \
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm_config_ignore_scripts=true npm_config_legacy_peer_deps=true npm install --omit=dev --legacy-peer-deps --force --no-audit --no-fund --no-save $$specs
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node -e "const fs=require('fs');const path=require('path');const semver=require('semver');const root=process.cwd();const ext=path.join(root,'dist','extensions');const collect=(pkg)=>({...(pkg.dependencies||{}),...(pkg.optionalDependencies||{})});const byName=new Map();for(const e of fs.readdirSync(ext,{withFileTypes:true})){if(!e.isDirectory())continue;const pj=path.join(ext,e.name,'package.json');if(!fs.existsSync(pj))continue;let pkg;try{pkg=JSON.parse(fs.readFileSync(pj,'utf8'));}catch{continue;}for(const [n,v] of Object.entries(collect(pkg))){if(typeof v!=='string'||!v.trim())continue;const rec=byName.get(n)||{versions:new Set(),plugins:new Set()};rec.versions.add(v.trim());rec.plugins.add(e.name);byName.set(n,rec);}}const missing=[];for(const [n,rec] of byName){const sentinel=path.join(root,'node_modules',...n.split('/'),'package.json');if(!fs.existsSync(sentinel)){missing.push({name:n,version:[...rec.versions].join(' || '),plugins:[...rec.plugins].sort()});continue;}let installed='';try{installed=JSON.parse(fs.readFileSync(sentinel,'utf8')).version||'';}catch{}const specs=[...rec.versions];const ok=specs.some((spec)=>{const v=semver.valid(installed);const r=semver.validRange(spec);if(v&&r)return semver.satisfies(v,r,{includePrerelease:true});return installed===spec;});if(!ok)missing.push({name:n,version:[...rec.versions].join(' || '),installed:installed||'unknown',plugins:[...rec.plugins].sort()});}if(missing.length){console.error('Bundled plugin runtime deps missing/version-mismatch after build-stage install:');for(const m of missing){console.error('- '+m.name+' required('+m.version+') installed('+(m.installed||'none')+') (used by '+m.plugins.join(', ')+')');}process.exit(1);}console.log('Bundled runtime dependency verification passed ('+byName.size+' deps).');" | tee $(WORK_DIR)/doctor.log
	@cd $(WORK_DIR)/openclaw-bundle && \
		mkdir -p .spk-build-state/doctor-state/agents/main/sessions .spk-build-state/doctor-state/credentials .spk-build-state/doctor-home .spk-build-state/doctor-ws && \
		chmod 700 .spk-build-state/doctor-state .spk-build-state/doctor-home && \
		printf '{"gateway":{"mode":"local","bind":"lan","port":58789,"controlUi":{"allowedOrigins":["*"]},"auth":{"mode":"token","token":"123456"}},"commands":{"ownerAllowFrom":["build:owner"]},"agents":{"defaults":{"workspace":"%s","model":{"primary":"anthropic/claude-sonnet-4-6"}}},"skills":{"enabled":false,"entries":{}}, "plugins":{"enabled":true,"allow":["browser","device-pair","memory-core"],"deny":["codex"],"entries":{"browser":{"enabled":true},"device-pair":{"enabled":true},"memory-core":{"enabled":true}}},"browser":{"extensionRelay":{"allowLegacyAuth":false}},"memory":{"search":{"enabled":false,"rememberAcrossConversations":false}}}\n' "$(WORK_DIR)/openclaw-bundle/.spk-build-state/doctor-ws" > .spk-build-state/doctor-config.json && \
		printf '# Memory\n\nMemory search is disabled in the package build environment.\n' > .spk-build-state/doctor-ws/MEMORY.md && \
		chmod 600 .spk-build-state/doctor-config.json && \
		OPENCLAW_STATE_DIR="$(WORK_DIR)/openclaw-bundle/.spk-build-state/doctor-state" \
		OPENCLAW_WORKSPACE_DIR="$(WORK_DIR)/openclaw-bundle/.spk-build-state/doctor-ws" \
		OPENCLAW_CONFIG_PATH="$(WORK_DIR)/openclaw-bundle/.spk-build-state/doctor-config.json" \
		HOME="$(WORK_DIR)/openclaw-bundle/.spk-build-state/doctor-home" \
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" \
		node dist/index.js doctor --fix --non-interactive | tee -a $(WORK_DIR)/doctor.log
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-pty-keys.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-bundled-runtime-deps.mjs $(WORK_DIR)/openclaw-bundle
	# Keep official OpenClaw Feishu extension as-is (no local compatibility rewrites).
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-jiti-loader-try-native.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-bundled-allowlist-discovery.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-control-ui-update-banner.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-startup-sidecars.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-wecom-bundled-entry.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-control-ui-preload.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-gateway-warmup-cache.mjs $(WORK_DIR)/openclaw-bundle
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
	@install -d -m 755 $(STAGING_DIR)/lib/node_modules
	@install -d -m 755 $(STAGING_DIR)/app/openclaw
	@install -d -m 755 $(STAGING_DIR)/var
	@cp -f $(WORK_DIR)/node-runtime/bin/node $(STAGING_DIR)/bin/node
	@cp -a $(WORK_DIR)/build-node-runtime/lib/node_modules/npm $(STAGING_DIR)/lib/node_modules/npm
	@cp -a $(WORK_DIR)/build-node-runtime/lib/node_modules/corepack $(STAGING_DIR)/lib/node_modules/corepack
	@cp -f $(WORK_DIR)/build-node-runtime/lib/node_modules/npm/bin/npm $(STAGING_DIR)/bin/npm || true
	@cp -f $(WORK_DIR)/build-node-runtime/lib/node_modules/npm/bin/npx $(STAGING_DIR)/bin/npx || true
	@chmod 755 $(STAGING_DIR)/bin/npm $(STAGING_DIR)/bin/npx 2>/dev/null || true
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
	@cp -f src/spk-integrity.pub.pem $(STAGING_DIR)/app/openclaw/config/spk-integrity.pub.pem
	# 强制覆盖最终安装脚本，避免 work 缓存导致旧版 service-setup 混入 SPK。
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/service-setup.sh $(STAGING_DIR)/scripts/service-setup
	@cp -f src/auto-approve-pairing.sh $(STAGING_DIR)/scripts/auto-approve-pairing.sh
	@chmod 755 $(STAGING_DIR)/scripts/service-setup $(STAGING_DIR)/scripts/auto-approve-pairing.sh
	@cd $(STAGING_DIR) && sha256sum \
		bin/openclaw \
		ui/index.cgi \
		app/openclaw/dist/index.js \
		app/openclaw/config/openclaw.template.json \
		> app/openclaw/config/spk-integrity.sha256
	@SPK_SIGN_KEY_PATH=$${SPK_SIGN_KEY_PATH:-/root/.openclaw/keys/ainasclaw/spk-signing-private.pem}; \
	if [ -f "$$SPK_SIGN_KEY_PATH" ]; then \
		openssl dgst -sha256 -sign "$$SPK_SIGN_KEY_PATH" \
			-out $(STAGING_DIR)/app/openclaw/config/spk-integrity.sig \
			$(STAGING_DIR)/app/openclaw/config/spk-integrity.sha256; \
	else \
		echo "Missing signing key: $$SPK_SIGN_KEY_PATH"; \
		exit 1; \
	fi

$(WORK_DIR)/spk-info.sha256: $(WORK_DIR)/INFO info-checksum
	@info_sum=$$(sha256sum "$(WORK_DIR)/INFO" | awk '{print $$1}'); \
	if [ -z "$$info_sum" ]; then \
		echo "Empty INFO checksum, aborting"; \
		exit 1; \
	fi; \
	printf '%s  INFO\n' "$$info_sum" > "$@"

$(WORK_DIR)/spk-info.sig: $(WORK_DIR)/spk-info.sha256
	@SPK_SIGN_KEY_PATH=$${SPK_SIGN_KEY_PATH:-/root/.openclaw/keys/ainasclaw/spk-signing-private.pem}; \
	if [ ! -f "$$SPK_SIGN_KEY_PATH" ]; then \
		echo "Missing signing key: $$SPK_SIGN_KEY_PATH"; \
		exit 1; \
	fi; \
	openssl dgst -sha256 -sign "$$SPK_SIGN_KEY_PATH" -out "$@" "$<"

$(SPK_FILE_NAME): $(WORK_DIR)/spk-info.sha256 $(WORK_DIR)/spk-info.sig

.PHONY: openclaw_extra_install
openclaw_extra_install:
	# Final guard: ensure packaged lifecycle script always comes from src,
	# preventing stale work/scripts/service-setup from being reintroduced later
	# by intermediate spksrc build steps.
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/service-setup.sh $(STAGING_DIR)/scripts/service-setup
	@cp -f src/auto-approve-pairing.sh $(STAGING_DIR)/scripts/auto-approve-pairing.sh
	@chmod 755 $(STAGING_DIR)/scripts/service-setup $(STAGING_DIR)/scripts/auto-approve-pairing.sh
	@grep -q "cleanup_duplicate_default_config" $(STAGING_DIR)/scripts/service-setup
	@grep -q "Upgrade flow must not change the existing workspace directory or gateway" $(STAGING_DIR)/scripts/service-setup
	@grep -q "resolve_effective_service_group" $(STAGING_DIR)/scripts/service-setup
