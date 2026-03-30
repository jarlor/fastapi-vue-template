#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# init.sh  --  One-time project initialisation
#
# Usage:  uv run poe init [project_name]
#
# If project_name is omitted, derives it from the directory name:
#   my-project → my_project
#   MyProject  → myproject
#
# Replaces the "app_name" placeholder, renames directories, syncs deps,
# and installs pre-commit hooks.
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

# Navigate to project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# ---------------------------------------------------------------------------
# Resolve project name
# ---------------------------------------------------------------------------
if [[ $# -ge 1 ]]; then
    PROJECT_NAME="$1"
else
    # Derive from directory name: kebab-case → snake_case, lowercase
    DIR_NAME="$(basename "$(pwd)")"
    PROJECT_NAME="$(echo "$DIR_NAME" | tr '[:upper:]' '[:lower:]' | tr '-' '_' | tr -cd 'a-z0-9_')"
    echo -e "${CYAN}No project name given, derived '${PROJECT_NAME}' from directory '${DIR_NAME}'${NC}"
fi

# Validate: must be a valid Python / shell-safe identifier (snake_case).
if [[ ! "$PROJECT_NAME" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo -e "${RED}Error: '${PROJECT_NAME}' is not a valid Python identifier.${NC}"
    echo "  Use lowercase letters, digits, and underscores. Must start with a letter."
    echo "  You can pass the name explicitly: uv run poe init my_project"
    exit 1
fi

echo -e "${CYAN}Initialising project as '${PROJECT_NAME}' ...${NC}"

# ---------------------------------------------------------------------------
# 1. Replace "app_name" in file contents (skip .git, node_modules, .venv)
# ---------------------------------------------------------------------------
echo "  [1/5] Replacing 'app_name' in file contents ..."

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
    echo "  [2/5] Renaming src/app_name/ -> src/${PROJECT_NAME}/ ..."
    mv "src/app_name" "src/${PROJECT_NAME}"
else
    echo "  [2/5] Source directory already renamed, skipping ..."
fi

# Restore reserved field names that should stay stable across generated projects.
# These are semantic config keys, not package/module placeholders.
if [[ -f "src/${PROJECT_NAME}/config.py" ]]; then
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' -E "s/^([[:space:]]*)${PROJECT_NAME}: str = \"${PROJECT_NAME}\"$/\\1app_name: str = \"${PROJECT_NAME}\"/" "src/${PROJECT_NAME}/config.py"
    else
        sed -i -E "s/^([[:space:]]*)${PROJECT_NAME}: str = \"${PROJECT_NAME}\"$/\\1app_name: str = \"${PROJECT_NAME}\"/" "src/${PROJECT_NAME}/config.py"
    fi
fi

if [[ -f "tests/conftest.py" ]]; then
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' -E "s/^([[:space:]]*)${PROJECT_NAME}=\"${PROJECT_NAME}_test\"/\\1app_name=\"${PROJECT_NAME}_test\"/" "tests/conftest.py"
    else
        sed -i -E "s/^([[:space:]]*)${PROJECT_NAME}=\"${PROJECT_NAME}_test\"/\\1app_name=\"${PROJECT_NAME}_test\"/" "tests/conftest.py"
    fi
fi

# ---------------------------------------------------------------------------
# 3. Re-sync dependencies (package name changed in pyproject.toml)
# ---------------------------------------------------------------------------
if command -v uv &>/dev/null; then
    echo "  [3/5] Running uv sync ..."
    uv sync
else
    echo "  [3/5] uv not found -- skipping. Run 'uv sync' manually."
fi

# ---------------------------------------------------------------------------
# 4. Install frontend dependencies
# ---------------------------------------------------------------------------
if [[ -f "src/frontend/package.json" ]]; then
    echo "  [4/5] Installing frontend dependencies ..."
    (cd src/frontend && npm install --silent 2>/dev/null) || echo "  npm install skipped (Node.js not found)"
else
    echo "  [4/5] No frontend package.json found, skipping ..."
fi

# ---------------------------------------------------------------------------
# 5. Install pre-commit hooks
# ---------------------------------------------------------------------------
if command -v pre-commit &>/dev/null || (command -v uv &>/dev/null && uv run pre-commit --version &>/dev/null 2>&1); then
    echo "  [5/5] Installing pre-commit hooks ..."
    uv run pre-commit install 2>/dev/null || true
else
    echo "  [5/5] pre-commit not available, skipping hooks ..."
fi

echo ""
echo -e "${GREEN}Done!  Project '${PROJECT_NAME}' is ready.${NC}"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env        # add your secrets"
echo "  2. uv run poe api              # start the backend"
echo "  3. uv run poe frontend         # start the frontend"
