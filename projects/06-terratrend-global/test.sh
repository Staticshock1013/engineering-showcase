#!/usr/bin/env bash
set -euo pipefail

DEPENDENCY_DIRECTORY="${TERRATREND_DEPS_DIR:-.terratrend-deps}"
if [[ ! -d "$DEPENDENCY_DIRECTORY/pytest" ]]; then
  pip install --upgrade --target "$DEPENDENCY_DIRECTORY" -r requirements.txt
fi
PYTHONPATH="$DEPENDENCY_DIRECTORY${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m pytest -q
