#!/usr/bin/env python3
"""Generate an offline Dockerfile for the bundled OpenClaw image.

The image is shipped as a Docker *build context* (this Dockerfile + a flattened
rootfs.tar.gz) instead of a `docker save` tar. Reason: DSM will not run a
community package's postinst as root (privilege run-as: package only), so the
package scripts can never touch docker.sock. The only root context during
install is Container Manager's postreplace, which runs `docker compose` for the
package's docker-project resource — i.e. it can *build* an image from a bundled
context (exactly how the Baidu Netdisk package works).

`FROM scratch` + `ADD rootfs.tar.gz /` means the build pulls NO base image and
never touches a registry: installation is fully offline. The Dockerfile has no
RUN steps, so the (arch-neutral) context builds on any host.

Input: `docker image inspect` JSON (path or stdin). Output: a Dockerfile.
"""

import json
import sys


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    else:
        raw = json.load(sys.stdin)
    # `docker image inspect` returns a list; a config.json object is a dict.
    if isinstance(raw, list):
        raw = raw[0]
    cfg = raw.get("Config", raw)

    lines = ["FROM scratch", "ADD rootfs.tar.gz /"]
    for entry in cfg.get("Env") or []:
        key, _, value = entry.partition("=")
        lines.append(f'ENV {key}="{value}"')
    if cfg.get("WorkingDir"):
        lines.append(f"WORKDIR {cfg['WorkingDir']}")
    if cfg.get("User"):
        lines.append(f"USER {cfg['User']}")
    for port in (cfg.get("ExposedPorts") or {}):
        lines.append(f"EXPOSE {port.split('/')[0]}")
    for vol in (cfg.get("Volumes") or {}):
        lines.append(f"VOLUME {json.dumps(vol)}")
    if cfg.get("Entrypoint"):
        lines.append(f"ENTRYPOINT {json.dumps(cfg['Entrypoint'])}")
    if cfg.get("Cmd"):
        lines.append(f"CMD {json.dumps(cfg['Cmd'])}")
    # Bundled first-start seeding material. The image carries its own copies of
    # the container-facing scripts (entrypoint/relay/updater) and the config
    # template so the entrypoint can self-seed a TRUE first install — when the
    # package's non-root postinst cannot create the HOME dir under /volume1.
    # The Makefile stages these into the build context next to rootfs.tar.gz.
    lines.append("ADD ocscripts/ /opt/ocscripts/")
    lines.append("ADD openclaw.template.json /opt/openclaw.template.json")
    sys.stdout.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
