#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where this repo lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Global target
TARGET_DIR="$HOME/.claude/skills"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  --uninstall)
    printf "${BLUE}Uninstalling RUBATO skills...${NC}\n"
    REMOVED=0
    for link in "$TARGET_DIR"/rubato-*; do
      if [[ -L "$link" ]]; then
        rm "$link"
        printf "${GREEN}  ✓ Removed $(basename "$link")${NC}\n"
        REMOVED=$((REMOVED + 1))
      fi
    done
    if [[ $REMOVED -eq 0 ]]; then
      printf "${YELLOW}No RUBATO skills found in $TARGET_DIR${NC}\n"
    else
      printf "${GREEN}✓ Removed $REMOVED skills${NC}\n"
    fi
    exit 0
    ;;
  --help)
    echo "Usage: ./install.sh [--uninstall]"
    echo ""
    echo "Installs RUBATO skills globally to ~/.claude/skills/"
    echo "Skills are symlinked, so 'git pull' updates them in place."
    echo ""
    echo "Options:"
    echo "  --uninstall  Remove all rubato-* symlinks from ~/.claude/skills/"
    echo "  --help       Show this help"
    exit 0
    ;;
  *)
    echo "Unknown option: $1"
    echo "Use --help for usage information"
    exit 1
    ;;
  esac
done

printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${BLUE}RUBATO Installation${NC}\n"
printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
echo ""

# Step 1: Check Python version
printf "${YELLOW}[1/4] Checking Python version...${NC}\n"
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
  PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
  PYTHON_CMD="python"
else
  printf "${RED}✗ Python not found${NC}\n"
  echo "Please install Python >= 3.10"
  exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $MAJOR_VERSION -lt 3 ]] || [[ $MAJOR_VERSION -eq 3 && $MINOR_VERSION -lt 10 ]]; then
  printf "${RED}✗ Python $PYTHON_VERSION found, but >= 3.10 required${NC}\n"
  exit 1
fi
printf "${GREEN}✓ Python $PYTHON_VERSION${NC}\n"
echo ""

# Step 2: Check and install PyYAML
printf "${YELLOW}[2/4] Checking PyYAML dependency...${NC}\n"
if $PYTHON_CMD -c "import yaml" 2>/dev/null; then
  printf "${GREEN}✓ PyYAML already installed${NC}\n"
else
  printf "${YELLOW}Installing PyYAML...${NC}\n"
  if command -v pip3 &>/dev/null; then
    pip3 install pyyaml
  elif command -v pip &>/dev/null; then
    pip install pyyaml
  else
    printf "${RED}✗ pip not found. Please install PyYAML manually:${NC}\n"
    echo "  pip install pyyaml"
    exit 1
  fi
  printf "${GREEN}✓ PyYAML installed${NC}\n"
fi
echo ""

# Step 3: Set target directory
printf "${YELLOW}[3/4] Setting up global installation target...${NC}\n"
mkdir -p "$TARGET_DIR"
printf "${GREEN}✓ Target: $TARGET_DIR${NC}\n"
echo ""

# Step 4: Clean up old psi-* symlinks and install rubato-* skills
printf "${YELLOW}[4/4] Installing skills (symlinks)...${NC}\n"

# Remove stale psi-* symlinks that point into this repo
for link in "$TARGET_DIR"/psi-*; do
  if [[ -L "$link" ]]; then
    LINK_TARGET="$(readlink "$link" 2>/dev/null || true)"
    if [[ "$LINK_TARGET" == "$SCRIPT_DIR"* ]]; then
      rm "$link"
      printf "${YELLOW}  ✗ Removed old symlink: $(basename "$link")${NC}\n"
    fi
  fi
done

# Auto-discover all rubato-* skill directories
INSTALLED_COUNT=0
for SOURCE in "$SCRIPT_DIR"/skills/rubato-*; do
  [[ -d "$SOURCE" ]] || continue

  SKILL_NAME="$(basename "$SOURCE")"
  LINK_PATH="$TARGET_DIR/$SKILL_NAME"

  # Remove existing (symlink or directory) before linking
  if [[ -L "$LINK_PATH" ]] || [[ -d "$LINK_PATH" ]]; then
    rm -rf "$LINK_PATH"
  fi

  ln -sfn "$SOURCE" "$LINK_PATH"
  printf "${GREEN}  ✓ $SKILL_NAME${NC}\n"
  INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
done

printf "${GREEN}✓ Installed $INSTALLED_COUNT skills${NC}\n"
echo ""

# Final message
printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${GREEN}Installation complete!${NC}\n"
printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
echo ""
printf "Skills are symlinked from:\n"
printf "  ${BLUE}$SCRIPT_DIR/skills/${NC}\n"
printf "To update, just run ${YELLOW}git pull${NC} in this repo.\n"
printf "To uninstall, run ${YELLOW}./install.sh --uninstall${NC}\n"
echo ""
printf "${BLUE}Documentation:${NC}\n"
echo ""
echo "  README.md          - Overview and quick reference"
echo "  skills/*/SKILL.md  - Individual skill documentation"
echo ""
