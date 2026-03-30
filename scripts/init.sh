#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# init.sh  --  One-time project initialisation
#
# Usage:  uv run poe init <project_name>
#
# Replaces the "app_name" placeholder throughout the repository with the
# supplied project name, renames directories, and runs uv sync.
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

if [[ $# -lt 1 ]]; then
    echo -e "${RED}Usage: uv run poe init <project_name>${NC}"
    echo "  project_name must be a valid Python identifier (lowercase, snake_case)."
    exit 1
fi

PROJECT_NAME="$1"

# Validate: must be a valid Python / shell-safe identifier (snake_case).
if [[ ! "$PROJECT_NAME" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo -e "${RED}Error: '${PROJECT_NAME}' is not a valid Python identifier.${NC}"
    echo "  Use lowercase letters, digits, and underscores. Must start with a letter."
    exit 1
fi

# Navigate to project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo -e "${CYAN}Initialising project as '${PROJECT_NAME}' ...${NC}"

# ---------------------------------------------------------------------------
# 1. Replace "app_name" in file contents (skip .git, node_modules, .venv)
# ---------------------------------------------------------------------------
echo "  Replacing 'app_name' in file contents ..."

export LC_ALL=C
find . \
    -not -path './.git/*' \
    -not -path './node_modules/*' \
    -not -path './.venv/*' \
    -not -path './src/frontend/node_modules/*' \
    -not -path './uv.lock' \
    -type f \
    \( -name '*.py' -o -name '*.toml' -o -name '*.yaml' -o -name '*.yml' \
       -o -name '*.md' -o -name '*.txt' -o -name '*.json' -o -name '*.ts' \
       -o -name '*.vue' -o -name '*.html' -o -name '*.css' -o -name '*.sh' \
       -o -name '*.cfg' -o -name '*.ini' -o -name '*.env*' -o -name '.gitignore' \
       -o -name '.pre-commit-config.yaml' -o -name '.python-version' \) \
    -exec grep -l 'app_name' {} + 2>/dev/null | while IFS= read -r file; do
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s/app_name/${PROJECT_NAME}/g" "$file"
    else
        sed -i "s/app_name/${PROJECT_NAME}/g" "$file"
    fi
done

# ---------------------------------------------------------------------------
# 2. Rename the source directory
# ---------------------------------------------------------------------------
if [[ -d "src/app_name" ]]; then
    echo "  Renaming src/app_name/ -> src/${PROJECT_NAME}/ ..."
    mv "src/app_name" "src/${PROJECT_NAME}"
fi

# ---------------------------------------------------------------------------
# 3. Re-sync dependencies (package name changed in pyproject.toml)
# ---------------------------------------------------------------------------
if command -v uv &>/dev/null; then
    echo "  Running uv sync ..."
    uv sync
else
    echo "  uv not found -- skipping dependency install. Run 'uv sync' manually."
fi

echo ""
echo -e "${GREEN}Done!  Project '${PROJECT_NAME}' is ready.${NC}"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env        # add your secrets"
echo "  2. uv run poe api              # start the backend"
echo "  3. cd src/frontend && npm install && cd ../.."
echo "  4. uv run poe frontend         # start the frontend"
