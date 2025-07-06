#!/bin/bash
# SD MQTT Printer Mac - Run Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🖨️  SD MQTT Printer Mac Client${NC}"
echo -e "${BLUE}================================${NC}"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry is not installed. Please install Poetry first:${NC}"
    echo -e "${YELLOW}   curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from example...${NC}"
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Created .env file. Please edit it with your settings.${NC}"
        echo -e "${YELLOW}   nano .env${NC}"
        exit 0
    else
        echo -e "${RED}❌ No env.example file found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Install dependencies if needed
echo -e "${BLUE}📦 Checking dependencies...${NC}"
poetry install --no-dev

# Run the application
echo -e "${GREEN}🚀 Starting SD MQTT Printer Mac client...${NC}"
poetry run python main.py

echo -e "${BLUE}👋 SD MQTT Printer Mac client stopped.${NC}"
