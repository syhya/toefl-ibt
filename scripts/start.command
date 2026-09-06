#!/bin/zsh
# Finder entry point. First installation uses scripts/install.sh.
set -eu
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd -- "$PROJECT_DIR"
stop_with_message() {
  printf '\n%s\n' "$1"
  printf 'Press Return to close / 按回车关闭此窗口。'
  IFS= read -r response || true
  exit 1
}
NODE_BIN=''
PATH_NODE="$(command -v node || true)"
for candidate in "$PATH_NODE" /opt/homebrew/bin/node /usr/local/bin/node /opt/homebrew/opt/node@22/bin/node /usr/local/opt/node@22/bin/node; do
  if [[ -n "$candidate" && -x "$candidate" ]] && "$candidate" -e 'const [m,n]=process.versions.node.split(".").map(Number);process.exit(m>22||(m===22&&n>=12)?0:1)'; then
    NODE_BIN="$candidate"
    break
  fi
done
if [[ -z "$NODE_BIN" ]]; then stop_with_message 'Node.js 22.12+ required. Run ./scripts/install.sh / 需要 Node.js 22.12+，然后执行安装脚本。'; fi
export PATH="$(dirname -- "$NODE_BIN"):$PATH"
if [[ ! -x .venv/bin/python ]]; then stop_with_message 'Run ./scripts/install.sh first, then double-click again / 请先执行安装脚本后再双击。'; fi
export TOEFL_OPEN_BROWSER=1
if ! "$NODE_BIN" server.mjs; then stop_with_message 'Startup failed. Check the dependency, build, or port error above / 启动失败，请检查上方依赖、构建或端口提示。'; fi
