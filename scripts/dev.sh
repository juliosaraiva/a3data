#!/bin/bash

# =============================================================================
# 🛠️ Development Helper Script
# =============================================================================

# This script provides quick access to common development tasks

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

show_help() {
    echo -e "${BOLD}${BLUE}🛠️ Development Helper${NC}"
    echo ""
    echo "Usage: ./scripts/dev.sh <command>"
    echo ""
    echo -e "${BOLD}Available commands:${NC}"
    echo -e "  ${GREEN}test${NC}      - Run tests and show results"
    echo -e "  ${GREEN}format${NC}    - Format and lint code"
    echo -e "  ${GREEN}check${NC}     - Run type checking"
    echo -e "  ${GREEN}fix${NC}       - Auto-fix all issues (format + lint-fix + type-check)"
    echo -e "  ${GREEN}serve${NC}     - Start development server"
    echo -e "  ${GREEN}health${NC}    - Check system health"
    echo -e "  ${GREEN}clean${NC}     - Clean cache files"
    echo -e "  ${GREEN}reset${NC}     - Reset development environment"
    echo ""
}

case "${1:-help}" in
    "test")
        echo -e "${BOLD}${BLUE}🧪 Running tests...${NC}"
        make test
        ;;
    "format")
        echo -e "${BOLD}${BLUE}✨ Formatting code...${NC}"
        make format
        ;;
    "check")
        echo -e "${BOLD}${BLUE}🔬 Running type checks...${NC}"
        make type-check
        ;;
    "fix")
        echo -e "${BOLD}${BLUE}🔧 Auto-fixing all issues...${NC}"
        make quality
        ;;
    "serve"|"start"|"run")
        echo -e "${BOLD}${BLUE}🚀 Starting server...${NC}"
        make run
        ;;
    "health")
        echo -e "${BOLD}${BLUE}🏥 Checking system health...${NC}"
        make health
        ;;
    "clean")
        echo -e "${BOLD}${BLUE}🧹 Cleaning cache...${NC}"
        make clean
        ;;
    "reset")
        echo -e "${BOLD}${BLUE}🔄 Resetting environment...${NC}"
        make reset
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
