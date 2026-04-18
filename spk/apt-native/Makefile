SPK_NAME = apt-native
SPK_VERS = 0.1.0
SPK_REV = 1
SPK_ICON = src/apt-native.png

# Experimental package: only x64 DSM 7.2+
UNSUPPORTED_ARCHS = $(ARMv5_ARCHS) $(ARMv7_ARCHS) $(ARMv8_ARCHS) $(PPC_ARCHS) $(i686_ARCHS)
REQUIRED_MIN_DSM = 7.2

MAINTAINER = ainas
MAINTAINER_URL = https://ainas.taobao.com
DESCRIPTION = Experimental system-layer apt bootstrap for DSM x64. HIGH RISK, FOR TESTING ONLY.
DISPLAY_NAME = APT Native (Experimental)
CHANGELOG = "Initial experimental release."

HOMEPAGE = https://ainas.taobao.com
LICENSE = MIT

STARTABLE = no
SERVICE_SETUP = src/service-setup.sh
SPK_COMMANDS = bin/apt bin/apt-get bin/dpkg bin/apt-native-bootstrap

COPY_TARGET = apt_native_copy_target

include ../../mk/spksrc.spk.mk

.PHONY: apt_native_copy_target
apt_native_copy_target:
	@$(MSG) Install apt-native payload
	@rm -rf $(STAGING_DIR)
	@install -d -m 755 $(STAGING_DIR)/bin
	@install -d -m 755 $(STAGING_DIR)/app
	@install -d -m 755 $(STAGING_DIR)/var
	@install -m 755 src/bin/apt $(STAGING_DIR)/bin/apt
	@install -m 755 src/bin/apt-get $(STAGING_DIR)/bin/apt-get
	@install -m 755 src/bin/dpkg $(STAGING_DIR)/bin/dpkg
	@install -m 755 src/bin/apt-native-bootstrap $(STAGING_DIR)/bin/apt-native-bootstrap
	@cp -rf src/app/* $(STAGING_DIR)/app/
