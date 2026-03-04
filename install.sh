#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  --help)
    echo "Usage: ./install.sh"
    echo ""
    echo "Installs psi-skills to the project's .claude/skills/ directory"
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
printf "${BLUE}psi-skills Installation${NC}\n"
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
printf "${YELLOW}[3/4] Setting up installation target...${NC}\n"
TARGET_DIR=".claude/skills"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"
printf "${GREEN}✓ Target: $TARGET_DIR${NC}\n"
echo ""

# Step 4: Copy skills
printf "${YELLOW}[4/4] Installing skills...${NC}\n"
SKILLS_TO_INSTALL=(
  "psi-init"
  "psi-new-calc"
  "psi-update-calc"
  "psi-new-report"
  "psi-update-report"
  "psi-status"
  "psi-graph"
  "psi-rebuild-index"
  "psi-add-computer"
  "psi-list-computers"
  "psi-remove-computer"
  "psi-update-computer"
  "psi-run-calc"
)

INSTALLED_COUNT=0
for skill in "${SKILLS_TO_INSTALL[@]}"; do
  SOURCE="$SCRIPT_DIR/skills/$skill"
  if [[ ! -d "$SOURCE" ]]; then
    printf "${RED}✗ Skill directory not found: $SOURCE${NC}\n"
    exit 1
  fi

  cp -r "$SOURCE" "$TARGET_DIR/"
  printf "${GREEN}  ✓ $skill${NC}\n"
  ((INSTALLED_COUNT++))
done
printf "${GREEN}✓ Installed $INSTALLED_COUNT skills${NC}\n"
echo ""

# Final message
printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${GREEN}Installation complete!${NC}\n"
printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
echo ""
printf "${BLUE}Documentation:${NC}\n"
echo ""
echo "  README.md          - Overview and quick reference"
echo "  PSI.md          - Project configuration guide"
echo "  skills/*/SKILL.md  - Individual skill documentation"
echo ""
