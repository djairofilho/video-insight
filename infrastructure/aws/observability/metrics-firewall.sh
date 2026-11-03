#!/usr/bin/env bash
# Regras exclusivas das portas de métricas; não alteram as demais portas da máquina.
set -euo pipefail
: "${MONITORING_PRIVATE_HOST:?Configure o coletor autorizado}"
[[ "$MONITORING_PRIVATE_HOST" =~ ^[0-9.]+$ ]]
iptables-restore --noflush <<EOF
*filter
:VI_METRICS_INPUT - [0:0]
:VI_METRICS_FORWARD - [0:0]
-A VI_METRICS_INPUT -i lo -j ACCEPT
-A VI_METRICS_INPUT -i docker+ -j ACCEPT
-A VI_METRICS_INPUT -i br+ -j ACCEPT
-A VI_METRICS_INPUT -s ${MONITORING_PRIVATE_HOST} -j ACCEPT
-A VI_METRICS_INPUT -j DROP
-A VI_METRICS_FORWARD -i docker+ -j ACCEPT
-A VI_METRICS_FORWARD -i br+ -j ACCEPT
-A VI_METRICS_FORWARD -s ${MONITORING_PRIVATE_HOST} -j ACCEPT
-A VI_METRICS_FORWARD -j DROP
COMMIT
EOF
for port in 9100 9091 9090; do
  iptables -C INPUT -p tcp --dport "$port" -j VI_METRICS_INPUT 2>/dev/null ||
    iptables -I INPUT 1 -p tcp --dport "$port" -j VI_METRICS_INPUT
done
if iptables -nL DOCKER-USER >/dev/null 2>&1; then
  for port in 9090 9091; do
    iptables -C DOCKER-USER -p tcp --dport "$port" -j VI_METRICS_FORWARD 2>/dev/null ||
      iptables -I DOCKER-USER 1 -p tcp --dport "$port" -j VI_METRICS_FORWARD
  done
fi
