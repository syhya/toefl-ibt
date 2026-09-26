#!/bin/sh
# One-time setup. Python/media packages stay in the project environment.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
cd "$PROJECT_DIR"
command -v python3 >/dev/null 2>&1 || { printf '%s\n' 'Python 3.10+ required / 需要 Python 3.10 或更高版本。'; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ is required"'
command -v node >/dev/null 2>&1 || { printf '%s\n' 'Node.js 22.12+ required / 需要 Node.js 22.12 或更高版本。'; exit 1; }
node -e 'const [m,n]=process.versions.node.split(".").map(Number);if(m<22||(m===22&&n<12))process.exit(1)' || { printf '%s\n' 'Upgrade Node.js to 22.12+ / 请升级到 Node.js 22.12+。'; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt -r requirements-import.txt
if [ -f package-lock.json ]; then npm ci; else npm install; fi
npm run build
if [ ! -f generated/catalog.json ]; then
  printf '%s\n' 'No library yet. Start the app and choose Try Practice Test 1, or run npm run demo. / 尚无题库，启动后可点击“体验官方样题第1套”，或运行 npm run demo。'
fi
printf '%s\n' 'Ready: npm start, then http://127.0.0.1:4173 / 安装完成：运行 npm start 后打开上述网址。'
