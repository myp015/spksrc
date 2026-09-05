version: '3.8'
services:
  openclaw:
    # Fully-offline image: Container Manager builds it from the bundled build
    # context (target/app/openclaw — Dockerfile + rootfs.tar.gz, FROM scratch,
    # no base image, no online pull) at install time. OpenClaw app self-updates
    # inside the persistent volume.
    build: /var/packages/openclaw/target/app/openclaw
    image: openclaw/openclaw:latest
    container_name: openclaw
    volumes:
      # Mount the whole HOME volume (always exists) instead of the individual
      # $HOME subdirs: DSM docker does not auto-create bind-mount source dirs,
      # and the non-root postinst cannot create dirs under the root-owned
      # /volume1 root. The entrypoint (root) creates $HOME/.openclaw on the
      # volume on first boot and symlinks /home/node/.openclaw, /data/runtime,
      # /data/scripts into it. workspace 固定为 $HOME/.openclaw。
      - {{OPENCLAW_VOLUME}}:/ocvol
      - /etc/localtime:/etc/localtime:ro
    environment:
      - HOME=/home/node
      - TERM=xterm-256color
      - OPENCLAW_DISABLE_BONJOUR=1
      - OPENCLAW_RUNTIME_DIR=/data/runtime
      - OPENCLAW_CONF_DIR=/home/node/.openclaw
      - OPENCLAW_HOST_HOME={{OPENCLAW_HOME}}
    user: "0:0"
    # In-image bootstrap: on a TRUE first install the host-side dirs don't exist
    # yet (non-root postinst could not create $HOME), so the entrypoint must
    # come from the image itself (/opt/ocscripts, see gen-dockerfile.py). It
    # creates $HOME/.openclaw on /ocvol, symlinks the app paths, seeds
    # /data/scripts + the config template, then runs the supervisor.
    entrypoint: /opt/ocscripts/entrypoint.sh
    restart: always
    ports:
      - "{{GATEWAY_PORT}}:{{GATEWAY_PORT}}/tcp"
networks:
  default:
    driver: bridge
