SPK_NAME = ainasclaw
# Always resolve latest stable upstream tag (vX.Y.Z...) at build time.
# If resolution fails, stop immediately (workflow should fail fast).
LATEST_OPENCLAW_VERS := $(shell git ls-remote --tags --refs https://github.com/openclaw/openclaw.git 'v*' | awk -F/ '{print $$3}' | grep -E '^v[0-9]+(\.[0-9]+)*$$' | sed 's/^v//' | sort -V | tail -1)
ifeq ($(strip $(LATEST_OPENCLAW_VERS)),)
$(error Failed to resolve latest stable openclaw version from upstream tags)
endif
# Keep SPK_VERS strictly upstream-semver-like for DSM compatibility.
# Put custom build identity into numeric SPK_REV only.
# Prefer npm-published latest; gracefully fall back to upstream git tag if registry/network tooling is unavailable in CI.
OPENCLAW_NPM_VERS := $(shell sh -c 'set -e; \
	v=""; \
	if command -v curl >/dev/null 2>&1; then \
		v=$$(curl -fsSL --retry 3 --retry-delay 1 https://registry.npmjs.org/openclaw/latest 2>/dev/null | tr -d "\\n" | sed -n "s/.*\"version\":\"\([^\"]*\)\".*/\1/p"); \
	fi; \
	if [ -z "$$v" ] && command -v wget >/dev/null 2>&1; then \
		v=$$(wget -qO- https://registry.npmjs.org/openclaw/latest 2>/dev/null | tr -d "\\n" | sed -n "s/.*\"version\":\"\([^\"]*\)\".*/\1/p"); \
	fi; \
	echo "$$v"')
ifeq ($(strip $(OPENCLAW_NPM_VERS)),)
OPENCLAW_NPM_VERS := $(LATEST_OPENCLAW_VERS)
$(warning Failed to resolve npm latest from registry; fallback to upstream git tag v$(LATEST_OPENCLAW_VERS))
endif
ifneq ($(strip $(LATEST_OPENCLAW_VERS)),)
ifneq ($(OPENCLAW_NPM_VERS),$(LATEST_OPENCLAW_VERS))
$(warning Upstream git latest is v$(LATEST_OPENCLAW_VERS), npm latest is $(OPENCLAW_NPM_VERS); build pins npm latest)
endif
endif
SPK_VERS := $(OPENCLAW_NPM_VERS)
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
# Package Center details fallback metadata (runtime will sync to active gateway port).
ADMIN_PORT = 58789
ADMIN_URL = /default/chat

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
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm install --omit=dev --legacy-peer-deps --no-audit --no-fund \
		@larksuiteoapi/feishu-openclaw-plugin@2026.3.8 \
		@soimy/dingtalk@3.5.3 \
		@wecom/wecom-openclaw-plugin@2026.4.23 \
		@tencent-connect/openclaw-qqbot@1.7.1 \
		@tencent-weixin/openclaw-weixin@2.1.8 \
		acpx@0.5.3 \
		node-edge-tts@1.2.10
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node scripts/postinstall-bundled-plugins.mjs
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm install --omit=dev --legacy-peer-deps --no-audit --no-fund \
		@anthropic-ai/sdk@0.90.0 \
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
		dingtalk-stream@^2.1.4 \
		express@^5.2.1 \
		file-type@^21.3.0 \
		form-data@^4.0.0 \
		linkedom@^0.18.12 \
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
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm install --no-package-lock --no-save @aws-sdk/credential-provider-node@3.972.34
	@cd $(WORK_DIR)/openclaw-bundle/dist/extensions/amazon-bedrock && \
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm pack @aws-sdk/credential-provider-node@3.972.34 --silent && \
		install -d node_modules/@aws-sdk/credential-provider-node && \
		tar -xzf aws-sdk-credential-provider-node-3.972.34.tgz -C node_modules/@aws-sdk/credential-provider-node --strip-components=1 && \
		rm -f aws-sdk-credential-provider-node-3.972.34.tgz
	@cd $(WORK_DIR)/openclaw-bundle/node_modules/@soimy/dingtalk && \
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm pack axios@^1.13.6 --silent && \
		install -d node_modules/axios && \
		tar -xzf axios-*.tgz -C node_modules/axios --strip-components=1 && \
		rm -f axios-*.tgz
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
		PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" npm_config_platform=linux npm_config_arch=$(NODE_DIST_ARCH) npm install --omit=dev --legacy-peer-deps --no-audit --no-fund --no-save $$specs
	@cd $(WORK_DIR)/openclaw-bundle && PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node -e "const fs=require('fs');const path=require('path');const semver=require('semver');const root=process.cwd();const ext=path.join(root,'dist','extensions');const collect=(pkg)=>({...(pkg.dependencies||{}),...(pkg.optionalDependencies||{})});const byName=new Map();for(const e of fs.readdirSync(ext,{withFileTypes:true})){if(!e.isDirectory())continue;const pj=path.join(ext,e.name,'package.json');if(!fs.existsSync(pj))continue;let pkg;try{pkg=JSON.parse(fs.readFileSync(pj,'utf8'));}catch{continue;}for(const [n,v] of Object.entries(collect(pkg))){if(typeof v!=='string'||!v.trim())continue;const rec=byName.get(n)||{versions:new Set(),plugins:new Set()};rec.versions.add(v.trim());rec.plugins.add(e.name);byName.set(n,rec);}}const missing=[];for(const [n,rec] of byName){const sentinel=path.join(root,'node_modules',...n.split('/'),'package.json');if(!fs.existsSync(sentinel)){missing.push({name:n,version:[...rec.versions].join(' || '),plugins:[...rec.plugins].sort()});continue;}let installed='';try{installed=JSON.parse(fs.readFileSync(sentinel,'utf8')).version||'';}catch{}const specs=[...rec.versions];const ok=specs.some((spec)=>{const v=semver.valid(installed);const r=semver.validRange(spec);if(v&&r)return semver.satisfies(v,r,{includePrerelease:true});return installed===spec;});if(!ok)missing.push({name:n,version:[...rec.versions].join(' || '),installed:installed||'unknown',plugins:[...rec.plugins].sort()});}if(missing.length){console.error('Bundled plugin runtime deps missing/version-mismatch after build-stage install:');for(const m of missing){console.error('- '+m.name+' required('+m.version+') installed('+(m.installed||'none')+') (used by '+m.plugins.join(', ')+')');}process.exit(1);}console.log('Bundled runtime dependency verification passed ('+byName.size+' deps).');" | tee $(WORK_DIR)/doctor.log
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-pty-keys.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-bundled-runtime-deps.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-control-ui-update-banner.mjs $(WORK_DIR)/openclaw-bundle
	@PATH="$(WORK_DIR)/build-node-runtime/bin:$$PATH" node src/patch-startup-sidecars.mjs $(WORK_DIR)/openclaw-bundle
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
	@cp -f src/spk-integrity.pub.pem $(STAGING_DIR)/app/openclaw/config/spk-integrity.pub.pem
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
	@true
