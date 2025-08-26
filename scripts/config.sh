#!/bin/bash

# =============================================================================
# ⚙️ Environment Configuration Manager
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ENV_FILE=".env"
EXAMPLE_FILE=".env.example"

show_help() {
    echo -e "${BOLD}${BLUE}⚙️ Environment Configuration Manager${NC}"
    echo ""
    echo "Usage: ./scripts/config.sh <command>"
    echo ""
    echo -e "${BOLD}Available commands:${NC}"
    echo -e "  ${GREEN}init${NC}           - Create .env from .env.example"
    echo -e "  ${GREEN}show${NC}           - Show current configuration"
    echo -e "  ${GREEN}validate${NC}       - Validate configuration"
    echo -e "  ${GREEN}ollama${NC}         - Switch to Ollama provider"
    echo -e "  ${GREEN}openai${NC}         - Switch to OpenAI provider (interactive)"
    echo -e "  ${GREEN}backup${NC}         - Create backup of current .env"
    echo -e "  ${GREEN}restore${NC}        - Restore .env from backup"
    echo ""
}

init_env() {
    if [ ! -f "$EXAMPLE_FILE" ]; then
        echo -e "${RED}Error: $EXAMPLE_FILE not found${NC}"
        exit 1
    fi

    if [ -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}⚠️  .env file already exists${NC}"
        read -p "$(echo -e ${YELLOW}Overwrite? [y/N]: ${NC})" -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Keeping existing .env file${NC}"
            return 0
        fi
    fi

    cp "$EXAMPLE_FILE" "$ENV_FILE"
    echo -e "${GREEN}✓ Created .env from $EXAMPLE_FILE${NC}"
}

show_config() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found. Run 'init' first.${NC}"
        exit 1
    fi

    echo -e "${BOLD}${BLUE}📋 Current Configuration${NC}"
    echo ""
    echo -e "${BOLD}Application:${NC}"
    grep -E "^(APP_NAME|APP_VERSION|ENVIRONMENT|DEBUG)=" "$ENV_FILE" | sed 's/^/  /'
    echo ""
    echo -e "${BOLD}LLM Provider:${NC}"
    grep -E "^(LLM_PROVIDER|LLM_MODEL_NAME|LLM_BASE_URL)=" "$ENV_FILE" | sed 's/^/  /'
    echo ""
    echo -e "${BOLD}Logging:${NC}"
    grep -E "^(LOG_LEVEL|LOG_FORMAT|LOG_CONSOLE_ENABLED)=" "$ENV_FILE" | sed 's/^/  /'
}

validate_config() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        exit 1
    fi

    echo -e "${BOLD}${BLUE}🔍 Validating Configuration${NC}"
    echo ""

    # Check required variables
    local errors=0

    # Check LLM Provider
    LLM_PROVIDER=$(grep "LLM_PROVIDER=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')
    echo -e "  Provider: $LLM_PROVIDER"

    if [ "$LLM_PROVIDER" = "openai" ] || [ "$LLM_PROVIDER" = "gemini" ] || [ "$LLM_PROVIDER" = "perplexity" ]; then
        API_KEY=$(grep "LLM_API_KEY=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')
        if [ -z "$API_KEY" ]; then
            echo -e "  ${RED}✗ API Key required for $LLM_PROVIDER${NC}"
            errors=$((errors + 1))
        else
            echo -e "  ${GREEN}✓ API Key configured${NC}"
        fi
    fi

    # Check model name
    MODEL_NAME=$(grep "LLM_MODEL_NAME=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"')
    echo -e "  Model: $MODEL_NAME"

    if [ $errors -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ Configuration is valid${NC}"
    else
        echo ""
        echo -e "${RED}✗ Found $errors configuration errors${NC}"
        exit 1
    fi
}

switch_to_ollama() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        exit 1
    fi

    echo -e "${BOLD}${BLUE}🦙 Switching to Ollama${NC}"

    # Create backup
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d-%H%M%S)"

    # Update configuration
    sed -i.tmp 's/LLM_PROVIDER=".*"/LLM_PROVIDER="ollama"/' "$ENV_FILE"
    sed -i.tmp 's/LLM_MODEL_NAME=".*"/LLM_MODEL_NAME="gemma2:4b"/' "$ENV_FILE"
    sed -i.tmp 's/LLM_API_KEY=".*"/LLM_API_KEY=""/' "$ENV_FILE"
    rm "$ENV_FILE.tmp"

    echo -e "${GREEN}✓ Switched to Ollama provider${NC}"
    echo -e "${BLUE}💡 Run 'make ollama-setup' to install and configure Ollama${NC}"
}

switch_to_openai() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        exit 1
    fi

    echo -e "${BOLD}${BLUE}🤖 Switching to OpenAI${NC}"
    echo ""
    echo -e "${YELLOW}Please enter your OpenAI API key:${NC}"
    read -s -p "API Key: " api_key
    echo

    if [ -z "$api_key" ]; then
        echo -e "${RED}Error: API key cannot be empty${NC}"
        exit 1
    fi

    # Create backup
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d-%H%M%S)"

    # Update configuration
    sed -i.tmp 's/LLM_PROVIDER=".*"/LLM_PROVIDER="openai"/' "$ENV_FILE"
    sed -i.tmp 's/LLM_MODEL_NAME=".*"/LLM_MODEL_NAME="gpt-4o-mini"/' "$ENV_FILE"
    sed -i.tmp "s/LLM_API_KEY=\".*\"/LLM_API_KEY=\"$api_key\"/" "$ENV_FILE"
    rm "$ENV_FILE.tmp"

    echo -e "${GREEN}✓ Switched to OpenAI provider${NC}"
}

switch_to_openai() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        exit 1
    fi

    echo -e "${BOLD}${BLUE}🤖 Switching to OpenAI provider${NC}"
    echo ""

    read -p "$(echo -e ${YELLOW}Enter your OpenAI API key: ${NC})" api_key

    if [ -z "$api_key" ]; then
        echo -e "${RED}Error: API key cannot be empty${NC}"
        exit 1
    fi

    # Create backup
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d-%H%M%S)"

    # Update configuration
    sed -i.tmp 's/LLM_PROVIDER=".*"/LLM_PROVIDER="openai"/' "$ENV_FILE"
    sed -i.tmp 's/LLM_MODEL_NAME=".*"/LLM_MODEL_NAME="gpt-4o-mini"/' "$ENV_FILE"

    # Update or add API key
    if grep -q "LLM_API_KEY=" "$ENV_FILE"; then
        sed -i.tmp "s/LLM_API_KEY=\".*\"/LLM_API_KEY=\"$api_key\"/" "$ENV_FILE"
    else
        echo "LLM_API_KEY=\"$api_key\"" >> "$ENV_FILE"
    fi

    rm "$ENV_FILE.tmp"

    echo -e "${GREEN}✓ Switched to OpenAI provider${NC}"
    echo -e "${BLUE}💡 Using gpt-4o-mini model${NC}"
}

backup_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        exit 1
    fi

    backup_file="$ENV_FILE.backup.$(date +%Y%m%d-%H%M%S)"
    cp "$ENV_FILE" "$backup_file"
    echo -e "${GREEN}✓ Backup created: $backup_file${NC}"
}

restore_env() {
    echo -e "${BOLD}${BLUE}📂 Available backups:${NC}"
    ls -la .env.backup.* 2>/dev/null || {
        echo -e "${YELLOW}No backups found${NC}"
        exit 0
    }

    echo ""
    read -p "$(echo -e ${YELLOW}Enter backup filename to restore: ${NC})" backup_file

    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found${NC}"
        exit 1
    fi

    cp "$backup_file" "$ENV_FILE"
    echo -e "${GREEN}✓ Restored configuration from $backup_file${NC}"
}

case "${1:-help}" in
    "init")
        init_env
        ;;
    "show")
        show_config
        ;;
    "validate")
        validate_config
        ;;
    "ollama")
        switch_to_ollama
        ;;
    "openai")
        switch_to_openai
        ;;
    "backup")
        backup_env
        ;;
    "restore")
        restore_env
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
