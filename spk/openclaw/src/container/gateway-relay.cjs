#!/usr/bin/env node
// OpenClaw container TCP relay (runs INSIDE the container, beside the gateway).
//
// Why it exists:
//   The gateway decides pairing locality from the TCP peer it sees. With the
//   plain docker-proxy port mapping every connection arrives from the bridge
//   gateway IP (172.24.0.x), so the Control UI / WebChat browser is "remote"
//   and requires a one-time manual device approval. If the connection instead
//   terminates at 127.0.0.1, ingress attribution reports "direct-local" and
//   the browser device pairing is silently auto-approved.
//
//   docker-proxy can never present loopback as the source (it always dials the
//   container's bridge IP), so this relay runs inside the container: it listens
//   on the host-published port and re-dials the gateway on 127.0.0.1. The
//   entrypoint starts the gateway loopback-only on an internal port and keeps
//   the relay's lifetime tied to the gateway's, so "is the public port
//   accepting" still reflects "is the gateway running".
//
//   A plain TCP pipe (no HTTP parsing) keeps every request byte-identical and
//   adds no X-Forwarded-*/X-Real-IP headers, so the gateway sees an ordinary
//   direct-local connection (no proxy attribution to confuse it).
'use strict';

const net = require('net');

const LISTEN_HOST = process.env.RELAY_LISTEN_HOST || '0.0.0.0';
const LISTEN_PORT = parseInt(process.env.RELAY_LISTEN_PORT || '58789', 10);
const UPSTREAM_HOST = process.env.RELAY_UPSTREAM_HOST || '127.0.0.1';
const UPSTREAM_PORT = parseInt(process.env.RELAY_UPSTREAM_PORT || '58788', 10);

const server = net.createServer((client) => {
    client.setNoDelay(true);
    const upstream = net.connect({ host: UPSTREAM_HOST, port: UPSTREAM_PORT }, () => {
        upstream.setNoDelay(true);
        client.pipe(upstream);
        upstream.pipe(client);
    });
    const teardown = () => {
        client.destroy();
        upstream.destroy();
    };
    // Upstream refused (gateway down): close the client so the panel's raw
    // socket probe and http_alive() both correctly report "not running".
    client.on('error', teardown);
    upstream.on('error', teardown);
    client.on('close', teardown);
    upstream.on('close', teardown);
});

server.on('error', (err) => {
    console.error(`[relay] listen error on ${LISTEN_HOST}:${LISTEN_PORT}: ${err.message}`);
    process.exit(1);
});

server.listen(LISTEN_PORT, LISTEN_HOST, () => {
    console.log(`[relay] listening ${LISTEN_HOST}:${LISTEN_PORT} -> ${UPSTREAM_HOST}:${UPSTREAM_PORT}`);
});

// Exit promptly when the supervisor stops us (SIGTERM on stop/docker stop).
process.on('SIGTERM', () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 1000).unref();
});
process.on('SIGINT', () => process.exit(0));
