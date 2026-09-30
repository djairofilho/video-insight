#!/usr/bin/env bash
set -euo pipefail

cache_dir="$HOME/.vscode-server/cli/servers"
minimum_free_kib=1048576

if [[ ! -d "$cache_dir" ]]; then
  df -h /
  exit 0
fi

cache_dir=$(realpath -e "$cache_dir")
mapfile -t installs < <(
  find "$cache_dir" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' |
    sort -nr |
    cut -d' ' -f2-
)

free_kib=$(df -Pk / | awk 'NR == 2 {print $4}')
for ((i = ${#installs[@]} - 1; i >= 2 && free_kib < minimum_free_kib; i--)); do
  install=$(realpath -e "${installs[$i]}")
  [[ "$install" == "$cache_dir"/* ]] || continue

  if ps -eo args= | grep -F -- "$install" | grep -v -F 'grep -F' >/dev/null; then
    echo "Preservando instalação em uso: $install"
    continue
  fi

  echo "Removendo instalação antiga do VS Code: $install"
  rm -rf -- "$install"
  free_kib=$(df -Pk / | awk 'NR == 2 {print $4}')
done

df -h /
