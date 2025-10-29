#!/bin/sh
set -e

# Default: BTC only
CHAINS="btc"
NBX_ARGS="--btcexplorerurl=${NBX_BTC_URL}"

if [ "${ENABLE_LIQUID}" = "true" ]; then
  CHAINS="btc,lbtc"
  NBX_ARGS="${NBX_ARGS} --lbtcexplorerurl=${NBX_LBTC_URL}"
  echo "[entrypoint] Liquid enabled: using NBX at ${NBX_LBTC_URL}"
else
  echo "[entrypoint] Liquid disabled: running BTC only"
fi

EXTRA_ARGS=""
if [ -n "${BTCPAY_ADDITIONAL_ARGS}" ]; then
  EXTRA_ARGS="${BTCPAY_ADDITIONAL_ARGS}"
fi

echo "[entrypoint] Starting BTCPay with --chains=${CHAINS}"
exec dotnet BTCPayServer.dll --chains=${CHAINS} ${NBX_ARGS} ${EXTRA_ARGS}
