#!/bin/bash

# SD MQTT Printer Mac - Run Script
# Usage: ./run.sh [dev|start|test]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🖨️  SD MQTT Printer Mac${NC}"
echo "============================================"

# Get the mode from command line argument
MODE=${1:-start}

case $MODE in
    "dev"|"start")
        echo -e "${GREEN}🚀 Starting SD MQTT Printer Mac client...${NC}"
        echo ""

        # Check if .env exists
        if [ ! -f .env ]; then
            echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
            if [ -f env.example ]; then
                cp env.example .env
                echo -e "${YELLOW}📝 Please edit .env file with your settings${NC}"
                echo ""
            fi
        fi

        # Install dependencies if needed
        if [ ! -d ".venv" ]; then
            echo -e "${YELLOW}📦 Installing dependencies...${NC}"
            poetry install --no-root
            echo ""
        fi

        # Run the client
        poetry run python main.py
        ;;

    "test")
        echo -e "${GREEN}🧪 Running setup verification...${NC}"
        echo ""

        # Install dependencies if needed
        if [ ! -d ".venv" ]; then
            echo -e "${YELLOW}📦 Installing dependencies...${NC}"
            poetry install --no-root
            echo ""
        fi

        # Run tests
        poetry run python test_setup.py
        ;;

    *)
        echo -e "${RED}❌ Invalid mode: $MODE${NC}"
        echo ""
        echo "Usage: $0 [dev|start|test]"
        echo ""
        echo "Modes:"
        echo "  dev   - Start in development mode"
        echo "  start - Start the printer client"
        echo "  test  - Run setup verification"
        echo ""
        exit 1
        ;;
esac
