#!/bin/bash

# =============================================================================
# 🚀 A3Data Incident Extractor - Quick Setup Script
# =============================================================================

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Emojis for better UX
ROCKET="🚀"
CHECK="✅"
WARNING="⚠️"
INFO="ℹ️"
GEAR="⚙️"
PACKAGE="📦"

echo -e "${BOLD}${BLUE}${ROCKET} A3Data Incident Extractor Setup${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

# Check if Make is available
if ! command -v make &> /dev/null; then
    echo -e "${RED}${WARNING} Make is not installed. Please install it first.${NC}"
    exit 1
fi

echo -e "${CYAN}${INFO} This script will set up the development environment${NC}"
echo -e "${CYAN}    It's equivalent to running 'make setup'${NC}"
echo ""

# Ask for confirmation
read -p "$(echo -e ${YELLOW}Continue with setup? [Y/n]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}Setup cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BOLD}${BLUE}${GEAR} Running setup...${NC}"

# Run the make setup command
if make setup; then
    echo ""
    echo -e "${BOLD}${GREEN}${CHECK} Setup completed successfully!${NC}"
    echo ""
    echo -e "${BOLD}${CYAN}🎯 Next steps:${NC}"
    echo -e "  ${GREEN}make run${NC}     - Start the development server"
    echo -e "  ${GREEN}make demo${NC}    - Try the API with sample data"
    echo -e "  ${GREEN}make help${NC}    - See all available commands"
    echo ""
    echo -e "${BOLD}${BLUE}${ROCKET} Happy coding!${NC}"
else
    echo ""
    echo -e "${BOLD}${RED}${WARNING} Setup failed. Please check the errors above.${NC}"
    exit 1
fi
