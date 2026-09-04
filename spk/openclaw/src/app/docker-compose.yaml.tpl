version: '3.8'
services:
  openclaw:
    # Fixed bundled image; OpenClaw app self-updates inside the persistent volume.
    image: openclaw/openclaw:2026.8.2
    container_name: openclaw
    volumes:
      - {{DATA_DIR}}/runtime:/data/runtime
      - {{DATA_DIR}}/conf:/home/node/.openclaw
      - {{DATA_DIR}}/workspace:/home/node/.openclaw/workspace
      - {{DATA_DIR}}/scripts:/data/scripts
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
networks:
  default:
    driver: bridge
