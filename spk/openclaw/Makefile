SPK_NAME = openclaw

# ---------------------------------------------------------------------------
# OpenClaw SPK (container mode) — FULL offline image bundle
#
# This package runs OpenClaw as a Docker container on DSM (requires the DSM
# "Docker" package / container manager). The COMPLETE container image
# (openclaw/openclaw:<tag>, including the Node runtime and the /app payload) is
# shipped INSIDE the SPK as a Docker *build context* (a Dockerfile + a flattened
# rootfs.tar.gz), so installation is fully OFFLINE — no download at install time.
#
# Why a build context and not a `docker save` tar: DSM refuses to run community
# package scripts as root (privilege `run-as: package` only), so postinst can
# never `docker load`. The one root context during install is Container
# Manager's docker-project postreplace, which runs `docker compose` and can
# *build* an image from a bundled context (same mechanism as the Baidu Netdisk
# package). `FROM scratch` => the build pulls no base image => zero online pull.
#
# The bundled image is FIXED. The OpenClaw app payload is copied into a
# persistent volume and updated IN-PLACE via npm, so the SPK does not need to
# be rebuilt for upstream OpenClaw releases.
# ---------------------------------------------------------------------------

# Fixed image tag. Do NOT bump this to update OpenClaw; the app self-updates
# inside the container. Change only when the base image layout/entrypoint
# changes materially.
OPENCLAW_IMAGE ?= openclaw/openclaw
OPENCLAW_IMAGE_TAG ?= 2026.8.2

# Path to a pre-built `docker save` tarball of the image for this arch.
# - CI provides this (runner saves the image with its Docker daemon).
# - Local builds may leave it empty; the SPK is then a "shell only" build
#   (no bundled image). Set OPENCLAW_PACK_IMAGE=1 to have the Makefile save
#   the image itself when a Docker daemon is available.
OPENCLAW_IMAGE_TAR ?=
OPENCLAW_PACK_IMAGE ?=

# App version shown in Package Center (can be bumped on packaging changes).
SPK_VERS = 2026.8.2
SPK_REV = 1

SPK_ICON = src/openclaw.png

DEPENDS =

# Require DSM Container Manager (handles the docker-project / container
# lifecycle as a root service, so the package scripts do not need docker).
# NOTE: no ">=version" — the ">" is eaten by the INFO echo (shell redirection).
SPK_DEPENDS = ContainerManager

UNSUPPORTED_ARCHS = $(i686_ARCHS) $(ARMv5_ARCHS) $(ARMv7_ARCHS) $(PPC_ARCHS)

REQUIRED_MIN_DSM = 7.2

MAINTAINER = ainas
MAINTAINER_URL = https://ainas.taobao.com
DESCRIPTION = OpenClaw for Synology（Docker 容器版，完整镜像打包，离线安装）。镜像固定，OpenClaw 本体容器内在线自更新。默认 Token: 335aba10f02647eb431a83e6e742589d4103c5681a4acb90。
DISPLAY_NAME = OpenClaw
CHANGELOG = "Full container image bundled; in-container self-update."

HOMEPAGE = https://ainas.taobao.com
LICENSE = MIT

STARTABLE = yes
SERVICE_USER = auto
SERVICE_SETUP = src/service-setup.sh
# Custom start/stop/status: this package drives a Docker container, so the
# generic PID-based service runner does not apply.
SSS_SCRIPT = src/start-stop-status
WIZARDS_TEMPLATES_DIR = src/wizard_templates
NO_SERVICE_SHORTCUT = yes

# Custom conf: overrides the generated privilege (run-as: root so postinst can
# docker load the bundled image + write sudoers) and resource (declares the
# docker-project so Container Manager manages the container lifecycle).
CONF_DIR = conf

DSM_UI_DIR = app
DSM_UI_CONFIG = src/app/config
DSM_APP_NAME = SYNOCOMMUNITY.OpenClaw.AppInstance
SERVICE_PORT = 58789
SERVICE_PORT_TITLE = OpenClaw Panel (HTTP)
SERVICE_URL = /app/openclaw/

# Resolve the upstream binary arch for docker --platform from the target arch.
TARGET_ARCH_NAME = $(or $(ARCH),$(TC_ARCH),$(word 1,$(subst -, ,$(TC_NAME))))
IMAGE_PLATFORM = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),linux/amd64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),linux/arm64,))
# ttyd (bundled terminal) prebuilt arch suffix.
TTYD_DIST_ARCH = $(if $(filter $(TARGET_ARCH_NAME),$(x64_ARCHS)),x86_64,$(if $(filter $(TARGET_ARCH_NAME),$(ARMv8_ARCHS)),aarch64,))

PRE_COPY_TARGET = openclaw_prepare_bundle
COPY_TARGET = openclaw_copy_target
POST_STRIP_TARGET = openclaw_extra_install

include ../../mk/spksrc.spk.mk

.PHONY: openclaw_prepare_bundle openclaw_gen_build_context
openclaw_prepare_bundle:
	@$(MSG) Prepare OpenClaw container image bundle - offline build context
	@if [ -n "$(OPENCLAW_IMAGE_TAR)" ]; then \
		echo "Using pre-built image tarball: $(OPENCLAW_IMAGE_TAR)"; \
		install -d -m 755 $(WORK_DIR); \
		cp -f "$(OPENCLAW_IMAGE_TAR)" $(WORK_DIR)/openclaw-image.tar; \
	elif [ "$(OPENCLAW_PACK_IMAGE)" = "1" ]; then \
		[ -n "$(IMAGE_PLATFORM)" ] || { echo "Unsupported arch for image platform: $(TARGET_ARCH_NAME)"; exit 1; }; \
		echo "Packing image openclaw/openclaw:$(OPENCLAW_IMAGE_TAG) ($(IMAGE_PLATFORM))"; \
		docker pull --platform $(IMAGE_PLATFORM) $(OPENCLAW_IMAGE):$(OPENCLAW_IMAGE_TAG); \
		docker save $(OPENCLAW_IMAGE):$(OPENCLAW_IMAGE_TAG) -o $(WORK_DIR)/openclaw-image.tar; \
	else \
		echo "WARN: no image bundle (OPENCLAW_IMAGE_TAR unset, OPENCLAW_PACK_IMAGE!=1) -> shell-only SPK"; \
	fi
	@if [ -f "$(WORK_DIR)/openclaw-image.tar" ]; then \
		$(MAKE) openclaw_gen_build_context; \
	else \
		echo "WARN: no image tar; skipping offline build context (shell-only SPK)"; \
	fi
	# Bundled terminal (ttyd) prebuilt binary.
	@[ -n "$(TTYD_DIST_ARCH)" ] || { echo "Unsupported target arch for ttyd bundle: $(TARGET_ARCH_NAME)"; exit 1; }
	@install -d -m 755 $(WORK_DIR)
	@if [ ! -f "$(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH)" ]; then \
		echo "Downloading ttyd 1.7.4 ($(TTYD_DIST_ARCH))"; \
		curl -fsSL -o "$(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH)" \
			https://github.com/tsl0922/ttyd/releases/download/1.7.4/ttyd.$(TTYD_DIST_ARCH); \
	fi
	@chmod +x "$(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH)"

# Generate the OFFLINE Docker build context (Dockerfile + flattened rootfs)
# from the bundled image tar. Container Manager builds the image from this
# context at install time (postreplace, runs as root); no base image, no
# registry access. The context is arch-neutral (no RUN steps), so it can be
# generated on any build host.
openclaw_gen_build_context:
	@$(MSG) Generate offline Docker build context from bundled image
	@install -d -m 755 $(WORK_DIR)/oc-context
	@echo "  loading image openclaw/openclaw:$(OPENCLAW_IMAGE_TAG)"
	@docker load -i $(WORK_DIR)/openclaw-image.tar >/dev/null
	@echo "  exporting flattened rootfs"
	@docker create --name openclaw-occtx-export $(OPENCLAW_IMAGE):$(OPENCLAW_IMAGE_TAG) >/dev/null
	@docker export openclaw-occtx-export | gzip -1 > $(WORK_DIR)/oc-context/rootfs.tar.gz
	@docker rm openclaw-occtx-export >/dev/null
	@docker image inspect $(OPENCLAW_IMAGE):$(OPENCLAW_IMAGE_TAG) > $(WORK_DIR)/oc-context/inspect.json
	@python3 src/container/gen-dockerfile.py $(WORK_DIR)/oc-context/inspect.json > $(WORK_DIR)/oc-context/Dockerfile
	@rm -f $(WORK_DIR)/oc-context/inspect.json
	@ls -lh $(WORK_DIR)/oc-context/Dockerfile $(WORK_DIR)/oc-context/rootfs.tar.gz

.PHONY: openclaw_copy_target
openclaw_copy_target:
	@$(MSG) Stage OpenClaw container-mode package content
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/bin
	@install -d -m 755 $(STAGING_DIR)/etc
	@install -d -m 755 $(STAGING_DIR)/app/openclaw
	@install -d -m 755 $(STAGING_DIR)/var
	@install -d -m 755 $(STAGING_DIR)/ui
	# Container-facing scripts (entrypoint + updater) live under target/etc
	@cp -f src/container/entrypoint.sh $(STAGING_DIR)/etc/entrypoint.sh
	@cp -f src/container/update-openclaw.sh $(STAGING_DIR)/etc/update-openclaw.sh
	@cp -f src/container/gateway-relay.cjs $(STAGING_DIR)/etc/gateway-relay.cjs
	@chmod 755 $(STAGING_DIR)/etc/entrypoint.sh $(STAGING_DIR)/etc/update-openclaw.sh $(STAGING_DIR)/etc/gateway-relay.cjs
	# Full offline image as a Docker build context (Dockerfile + flattened
	# rootfs). Container Manager builds the image from target/app/openclaw at
	# install time; the package scripts never touch docker.
	@if [ -d "$(WORK_DIR)/oc-context" ]; then \
		install -d -m 755 $(STAGING_DIR)/app/openclaw; \
		cp -f $(WORK_DIR)/oc-context/Dockerfile $(STAGING_DIR)/app/openclaw/Dockerfile; \
		cp -f $(WORK_DIR)/oc-context/rootfs.tar.gz $(STAGING_DIR)/app/openclaw/rootfs.tar.gz; \
		ls -lh $(STAGING_DIR)/app/openclaw/Dockerfile $(STAGING_DIR)/app/openclaw/rootfs.tar.gz; \
	else \
		echo "WARN: no offline build context; building shell-only SPK"; \
	fi
	# Host-side CLI wrapper `openclaw`
	@cp -f src/openclaw-spk $(STAGING_DIR)/bin/openclaw
	@chmod 755 $(STAGING_DIR)/bin/openclaw
	# Bundled terminal (ttyd)
	@if [ -f "$(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH)" ]; then \
		cp -f "$(WORK_DIR)/ttyd.$(TTYD_DIST_ARCH)" $(STAGING_DIR)/bin/ttyd; \
		chmod 755 $(STAGING_DIR)/bin/ttyd; \
		ls -lh $(STAGING_DIR)/bin/ttyd; \
	else \
		echo "WARN: ttyd binary not present"; \
	fi
	# Terminal entry script (host side)
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/scripts/openclaw-terminal-entry.sh $(STAGING_DIR)/scripts/openclaw-terminal-entry.sh
	@chmod 755 $(STAGING_DIR)/scripts/openclaw-terminal-entry.sh
	@cp -f src/scripts/terminal.sh $(STAGING_DIR)/scripts/terminal.sh
	@chmod 755 $(STAGING_DIR)/scripts/terminal.sh
	# Root helper executed by the panel's one-shot authorize scheduled task.
	@cp -f src/scripts/authorize-root.sh $(STAGING_DIR)/scripts/authorize-root.sh
	@chmod 755 $(STAGING_DIR)/scripts/authorize-root.sh
	# OpenClaw default config template
	@install -d -m 755 $(STAGING_DIR)/app/openclaw/config
	@cp -f src/openclaw.json $(STAGING_DIR)/app/openclaw/config/openclaw.template.json
	# DSM UI + app config
	@cp -rf src/app/* $(STAGING_DIR)/app/
	@rm -f $(STAGING_DIR)/app/index.cgi
	@ln -s ../ui/index.cgi $(STAGING_DIR)/app/index.cgi
	@cp -rf src/ui/* $(STAGING_DIR)/ui/
	@chmod 755 $(STAGING_DIR)/ui/index.cgi
	# Pre-render docker-compose files (default HOME dir + port) so Container
	# Manager always finds a valid compose at postinst. postinst re-renders if
	# the wizard supplies different values.
	@sed -e 's|{{OPENCLAW_HOME}}|/volume1/openclaw|g' -e 's|{{GATEWAY_PORT}}|58789|g' \
		src/app/docker-compose.yaml.tpl > $(STAGING_DIR)/app/docker-compose.yaml
	@sed -e 's|{{OPENCLAW_HOME}}|/volume1/openclaw|g' -e 's|{{GATEWAY_PORT}}|58789|g' \
		src/app/docker-compose.admin.yaml.tpl > $(STAGING_DIR)/app/docker-compose.admin.yaml
	@chmod 644 $(STAGING_DIR)/app/docker-compose.yaml $(STAGING_DIR)/app/docker-compose.admin.yaml
	@ls -l $(STAGING_DIR)/app/docker-compose*.yaml
	# Service lifecycle scripts
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/service-setup.sh $(STAGING_DIR)/scripts/service-setup
	@cp -f src/scripts/ui-run.sh $(STAGING_DIR)/scripts/ui-run.sh
	@chmod 755 $(STAGING_DIR)/scripts/service-setup $(STAGING_DIR)/scripts/ui-run.sh

.PHONY: openclaw_extra_install
openclaw_extra_install:
	@install -d -m 755 $(STAGING_DIR)/scripts
	@cp -f src/service-setup.sh $(STAGING_DIR)/scripts/service-setup
	@chmod 755 $(STAGING_DIR)/scripts/service-setup
	@cp -f src/scripts/ui-run.sh $(STAGING_DIR)/scripts/ui-run.sh
	@chmod 755 $(STAGING_DIR)/scripts/ui-run.sh
	@grep -q "docker" $(STAGING_DIR)/scripts/service-setup
