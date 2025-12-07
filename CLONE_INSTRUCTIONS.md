# How to Clone This Project

## Scenario 1: Clone from GitHub (After Repository is Created)

Once you've pushed this project to GitHub, others can clone it with:

```bash
# Clone the repository
git clone https://github.com/yourusername/poly-maker.git

# Navigate into the project
cd poly-maker

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies for position merging
cd poly_merger
npm install
cd ..

# Set up environment variables
cp .env.example .env  # If you create a .env.example file
# Or create .env manually with:
# PK=your_private_key_here
# BROWSER_ADDRESS=your_wallet_address_here
# SPREADSHEET_URL=your_spreadsheet_url_here

# Set up Google Sheets credentials
# Download credentials.json from Google Cloud Console
# Place it in the project root

# Run the bot
python main.py
```

---

## Scenario 2: Create a Clean Copy for GitHub (Current Project)

If you want to create a clean copy of your current project to push to GitHub:

### Option A: Use Git (Recommended)

```bash
# 1. Ensure .gitignore is up to date (already done)
# 2. Initialize git if not already done
cd /Users/terrylee/PycharmProjects/PythonProject/poly-maker-prod
git init  # Only if not already a git repo

# 3. Add all safe files
git add .

# 4. Check what will be committed (verify no sensitive files)
git status

# 5. Commit
git commit -m "Initial commit: Polymarket market-making bot"

# 6. Create repository on GitHub, then:
git remote add origin https://github.com/yourusername/poly-maker.git
git branch -M main
git push -u origin main
```

### Option B: Manual Copy (If you want a separate clean directory)

```bash
# 1. Create new directory
mkdir ~/poly-maker-clean
cd ~/poly-maker-clean

# 2. Copy all safe files (using rsync to exclude sensitive files)
rsync -av --exclude='.env' \
          --exclude='credentials.json' \
          --exclude='*.log' \
          --exclude='data/' \
          --exclude='data_updater/data/' \
          --exclude='data_updater/data_*/' \
          --exclude='positions/' \
          --exclude='__pycache__/' \
          --exclude='.idea/' \
          --exclude='node_modules/' \
          --exclude='.DS_Store' \
          /Users/terrylee/PycharmProjects/PythonProject/poly-maker-prod/ .

# 3. Initialize git
git init
git add .
git commit -m "Initial commit: Polymarket market-making bot"

# 4. Create repository on GitHub, then:
git remote add origin https://github.com/yourusername/poly-maker.git
git branch -M main
git push -u origin main
```

---

## Scenario 3: Clone Your Own Project Locally (Backup/Copy)

If you want to clone your current project to another location on your machine:

```bash
# Method 1: Using git (if it's already a git repo)
cd /path/to/new/location
git clone /Users/terrylee/PycharmProjects/PythonProject/poly-maker-prod poly-maker-backup

# Method 2: Using rsync (excludes sensitive files automatically via .gitignore patterns)
rsync -av --exclude='.env' \
          --exclude='credentials.json' \
          --exclude='*.log' \
          --exclude='data/' \
          --exclude='data_updater/data/' \
          --exclude='positions/' \
          --exclude='__pycache__/' \
          --exclude='.idea/' \
          --exclude='node_modules/' \
          /Users/terrylee/PycharmProjects/PythonProject/poly-maker-prod/ \
          /path/to/new/location/poly-maker/
```

---

## Quick Setup Script

Create a `setup.sh` script for new users:

```bash
#!/bin/bash
# setup.sh - Quick setup script for new users

echo "Setting up Poly-Maker bot..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install Python 3.9+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required. Please install Node.js"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd poly_merger
npm install
cd ..

# Check for .env
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
PK=your_private_key_here
BROWSER_ADDRESS=your_wallet_address_here
SPREADSHEET_URL=your_spreadsheet_url_here
POLYGON_RPC_URL=https://polygon-rpc.com
TWO_SIDED_MARKET_MAKING=false
AGGRESSIVE_MODE=false
EOF
    echo "✅ Created .env template. Please edit it with your credentials."
else
    echo "✅ .env file found"
fi

# Check for credentials.json
if [ ! -f credentials.json ]; then
    echo "⚠️  credentials.json not found. Please download from Google Cloud Console."
else
    echo "✅ credentials.json found"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your credentials"
echo "2. Add credentials.json from Google Cloud Console"
echo "3. Run: python update_markets.py"
echo "4. Run: python update_selected_markets.py"
echo "5. Run: python main.py"
```

Make it executable:
```bash
chmod +x setup.sh
```

---

## Verification Checklist

Before pushing to GitHub, verify:

```bash
# 1. Check .gitignore is working
git status
# Should NOT show: .env, credentials.json, *.log, data/, positions/

# 2. Verify no sensitive files in staging
git diff --cached --name-only | grep -E "\.env|credentials|\.log"

# 3. Check for hardcoded secrets (should return nothing)
grep -r "0x[a-fA-F0-9]\{64\}" . --exclude-dir=.git
grep -r "PK=" . --exclude=".env" --exclude-dir=.git

# 4. List what will be committed
git ls-files | head -20
```

---

## Common Issues

### Issue: "fatal: not a git repository"
**Solution:**
```bash
git init
```

### Issue: Sensitive files showing in git status
**Solution:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "credentials.json" >> .gitignore
echo "*.log" >> .gitignore

# Remove from git cache (if already tracked)
git rm --cached .env credentials.json *.log
```

### Issue: Large files (data directories)
**Solution:**
```bash
# Add to .gitignore
echo "data/" >> .gitignore
echo "data_updater/data/" >> .gitignore
echo "positions/" >> .gitignore

# Remove from git cache
git rm -r --cached data/ data_updater/data/ positions/
```

---

## Recommended Workflow

1. **Create .env.example** (template for users):
```bash
cat > .env.example << EOF
# Polymarket Credentials
PK=your_private_key_here
BROWSER_ADDRESS=your_wallet_address_here

# Google Sheets
SPREADSHEET_URL=your_spreadsheet_url_here

# Optional
POLYGON_RPC_URL=https://polygon-rpc.com
TWO_SIDED_MARKET_MAKING=false
AGGRESSIVE_MODE=false
EOF
```

2. **Verify .gitignore** includes all sensitive files

3. **Commit and push:**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

4. **Test clone:**
```bash
cd /tmp
git clone https://github.com/yourusername/poly-maker.git test-clone
cd test-clone
# Verify no .env, credentials.json, or log files
ls -la | grep -E "\.env|credentials|\.log"
```

