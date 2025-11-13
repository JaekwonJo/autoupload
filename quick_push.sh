#!/usr/bin/env bash
set -euo pipefail

# 빠른 커밋 + 푸시 (WSL/리눅스/맥)
# 사용법: ./quick_push.sh [커밋메시지]

cd "$(dirname "$0")"

msg="${*:-}"
if [[ -z "$msg" ]]; then
  msg="auto commit $(date +'%Y-%m-%d %H:%M:%S')"
fi

echo "[git add]"
git add -A

echo "[git commit]"
if ! git commit -m "$msg"; then
  echo "변경 사항이 없어 커밋할 것이 없어요.^^"
fi

echo "[git push]"
git push

echo "완료!"

