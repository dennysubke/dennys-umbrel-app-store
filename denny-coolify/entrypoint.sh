#!/bin/sh
set -eu
BRIDGE_IFACE="${DOCKER_ENSURE_BRIDGE%:*}"
BRIDGE_CIDR="${DOCKER_ENSURE_BRIDGE#*:}"
ip link show "$BRIDGE_IFACE" >/dev/null 2>&1 || {
  ip link add name "$BRIDGE_IFACE" type bridge
  ip addr add "$BRIDGE_CIDR" dev "$BRIDGE_IFACE"
  ip link set "$BRIDGE_IFACE" up
}
exec "$@"
