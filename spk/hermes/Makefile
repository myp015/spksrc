SPK_NAME = hermes
SPK_VERS := 0.16.0
SPK_REV = $(shell if [ -n "$$GITHUB_RUN_NUMBER" ]; then echo $$GITHUB_RUN_NUMBER; elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git rev-list --count HEAD; else date +%Y%m%d%H%M; fi)
SPK_ICON = src/hermes.png

DEPENDS =

# This package supports x64 and ARMv8 targets (DSM 7.2+).
UNSUPPORTED_ARCHS = $(i686_ARCHS) $(ARMv7_ARCHS) $(ARMv5_ARCHS) $(PPC_ARCHS)

# Bundled Node.js runtime requires newer glibc; keep DSM floor at 7.2.
REQUIRED_MIN_DSM = 7.2

MAINTAINER = openclaw
MAINTAINER_URL = https://github.com/NousResearch/hermes-agent
DESCRIPTION = Hermes Agent for Synology — self-improving AI agent framework by Nous Research
DISPLAY_NAME = Hermes Agent
CHANGELOG = "Hermes Agent v0.16.0 for DSM."

HOMEPAGE = https://hermes-agent.nousresearch.com
LICENSE = MIT

STARTABLE = yes
SERVICE_USER = auto
SERVICE_SETUP = src/service-setup.sh
WIZARDS_TEMPLATES_DIR = src/wizard_templates
NO_SERVICE_SHORTCUT = yes

DSM_UI_DIR = app
DSM_UI_CONFIG = src/app/config
DSM_APP_NAME = SYNOCOMMUNITY.HermesAgent.AppInstance
# DSM package metadata port (for conflict precheck) uses a fixed fallback.
# Runtime gateway port is dynamically assigned on fresh install in service-setup.sh.
SERVICE_PORT = 58790
SERVICE_PORT_TITLE = Hermes Agent Panel (HTTP)
SERVICE_URL = /app/hermes/

PRE_COPY_TARGET = hermes_prepare_bundle
COPY_TARGET = hermes_copy_target
POST_STRIP_TARGET = hermes_extra_install

# Resolve upstream binary arch from target arch reliably.
# ARCH can be generic (x64/aarch64) or platform-specific (apollolake/rtd1619b).
TARGET_ARCH_NAME = $(or $(ARCH),$(TC_ARCH),$(word 1,$(subst -, ,$(TC_NAME))))
NODE_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),arm64,))
BUN_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),aarch64,))
TTYD_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x86_64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),aarch64,))

include ../../mk/spksrc.spk.mk

# Runtime system user for Hermes Agent.
SPK_USER = hermes

.PHONY: hermes_prepare_bundle
hermes_prepare_bundle:
	@$(MSG) Prepare Hermes Agent bundle and Node.js runtime
	@rm -rf $(WORK_DIR)/hermes-bundle $(WORK_DIR)/hermes-runtime
	@install -d -m 755 $(WORK_DIR)/hermes-bundle $(WORK_DIR)/hermes-runtime
	@cd $(WORK_DIR) && \
		pip install hermes-agent==$(SPK_VERS) -t $(WORK_DIR)/hermes-bundle --quiet
	@# Verify the bundle
	@if [ ! -f "$(WORK_DIR)/hermes-bundle/hermes_cli/main.py" ]; then \
		echo "Hermes Agent bundle verification failed"; exit 1; \
	fi

.PHONY: hermes_copy_target
hermes_copy_target:
	@$(MSG) Create staging content for Hermes Agent
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/bin
	@install -d -m 755 $(STAGING_DIR)/app/hermes
	@install -d -m 755 $(STAGING_DIR)/var
	@cp -a $(WORK_DIR)/hermes-bundle/* $(STAGING_DIR)/app/hermes/
	@cp -f src/hermes-entry $(STAGING_DIR)/bin/hermes
	@chmod 755 $(STAGING_DIR)/bin/hermes
	@install -d -m 755 $(STAGING_DIR)/app
	@cp -rf src/app/* $(STAGING_DIR)/app/
	@rm -f $(STAGING_DIR)/app/index.cgi
	@ln -s ../ui/index.cgi $(STAGING_DIR)/app/index.cgi
	@install -d -m 755 $(STAGING_DIR)/ui
	@cp -rf src/ui/* $(STAGING_DIR)/ui/
	@chmod 755 $(STAGING_DIR)/ui/index.cgi
	@rm -f $(STAGING_DIR)/ui/config $(STAGING_DIR)/ui/hermes.sc
	# 强制覆盖最终安装脚本
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/service-setup.sh $(STAGING_DIR)/scripts/service-setup
	@chmod 755 $(STAGING_DIR)/scripts/service-setup
	# Copy template config
	@install -d -m 755 $(STAGING_DIR)/app/hermes/config
	@cp -f src/hermes.json $(STAGING_DIR)/app/hermes/config/hermes.template.json

.PHONY: hermes_extra_install
hermes_extra_install:
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/service-setup.sh $(STAGING_DIR)/scripts/service-setup
	@chmod 755 $(STAGING_DIR)/scripts/service-setup