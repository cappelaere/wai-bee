#!/bin/bash
# Setup Python 3.11 using pyenv for the Scholarship Chat Agent project

set -e  # Exit on error

echo "=========================================="
echo "Python 3.11 Setup with pyenv"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo -e "${YELLOW}pyenv not found. Installing pyenv...${NC}"
    
    # Install pyenv based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "Installing pyenv via Homebrew..."
            brew install pyenv
        else
            echo -e "${RED}Homebrew not found. Please install Homebrew first:${NC}"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    else
        # Linux
        echo "Installing pyenv via curl..."
        curl https://pyenv.run | bash
        
        # Add to shell configuration
        echo ""
        echo -e "${YELLOW}Add these lines to your ~/.bashrc or ~/.zshrc:${NC}"
        echo 'export PYENV_ROOT="$HOME/.pyenv"'
        echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
        echo 'eval "$(pyenv init -)"'
        echo ""
        echo -e "${YELLOW}Then run: source ~/.bashrc (or ~/.zshrc)${NC}"
        echo ""
        
        # Try to add to current shell
        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
    fi
else
    echo -e "${GREEN}✓ pyenv is already installed${NC}"
fi

# Verify pyenv is available
if ! command -v pyenv &> /dev/null; then
    echo -e "${RED}pyenv installation failed or not in PATH${NC}"
    echo "Please restart your shell and run this script again"
    exit 1
fi

echo ""
echo "Current Python version: $(python --version)"
echo ""

# Check if Python 3.11 is already installed
if pyenv versions | grep -q "3.11"; then
    echo -e "${GREEN}✓ Python 3.11 is already installed via pyenv${NC}"
    PYTHON_311_VERSION=$(pyenv versions | grep "3.11" | head -1 | xargs)
else
    echo -e "${YELLOW}Installing Python 3.11.9 (latest 3.11 release)...${NC}"
    echo "This may take a few minutes..."
    pyenv install 3.11.9
    PYTHON_311_VERSION="3.11.9"
fi

echo ""
echo -e "${GREEN}✓ Python 3.11 installation complete${NC}"
echo ""

# Set Python 3.11 for this project
echo "Setting Python 3.11 for this project directory..."
pyenv local $PYTHON_311_VERSION

echo ""
echo -e "${GREEN}✓ Python 3.11 is now active for this project${NC}"
echo ""

# Verify
echo "Verifying Python version..."
python --version

echo ""
echo "=========================================="
echo "Setting up virtual environment..."
echo "=========================================="
echo ""

# Create virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Removing old one...${NC}"
    rm -rf venv
fi

echo "Creating new virtual environment with Python 3.11..."
python -m venv venv

echo ""
echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Python version in use:"
python --version
echo ""
echo "To activate this environment in the future, run:"
echo -e "${YELLOW}  source venv/bin/activate${NC}"
echo ""
echo "To start the chat agent server:"
echo -e "${YELLOW}  python chat_agents/run_server.py${NC}"
echo ""
echo "The project will automatically use Python 3.11 when you're in this directory."
echo ""

# Made with Bob
