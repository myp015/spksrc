version: !<tag:yaml.org,2002:str> 3.8
services:
  openclaw:
    # Fully-offline image: Container Manager builds it from the bundled build
    # context (target/app/openclaw — Dockerfile + rootfs.tar.gz, FROM scratch,
    # no base image, no online pull) at install time.
    build: /var/packages/openclaw/target/app/openclaw
    image: openclaw/openclaw:2026.8.2
    container_name: openclaw
    volumes:
      - {{OPENCLAW_HOME}}/.openclaw:/home/node/.openclaw
      - {{OPENCLAW_HOME}}/.openclaw/runtime:/data/runtime
      - {{OPENCLAW_HOME}}/.openclaw/scripts:/data/scripts
      - /etc/localtime:/etc/localtime:ro
    environment:
      - HOME=/home/node
      - TERM=xterm-256color
      - OPENCLAW_DISABLE_BONJOUR=1
      - OPENCLAW_RUNTIME_DIR=/data/runtime
      - OPENCLAW_CONF_DIR=/home/node/.openclaw
    user: "0:0"
    entrypoint: /data/scripts/entrypoint.sh
    restart: always
    ports:
      - "{{GATEWAY_PORT}}:{{GATEWAY_PORT}}/tcp"
    cap_add:
      - NET_BIND_SERVICE
networks:
  default:
    driver: bridge
