# Installation Guide

Complete installation instructions for the SonarCloud SAST Report Generator.

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Network**: Internet access to reach SonarCloud API
- **SonarCloud**: Active account with API access

## Installation Methods

### Method 1: Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/sonar-reports.git
cd sonar-reports

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### Method 2: Install as Package

```bash
# Install directly from source
pip install -e git+https://github.com/your-org/sonar-reports.git#egg=sonar-reports

# Or if you have a wheel/sdist
pip install sonar-reports-1.0.0.tar.gz
```

## Verify Installation

```bash
# Check if the command is available
sonar-report --version

# Or use as module
python -m sonar_reports version

# Expected output:
# SonarCloud SAST Report Generator v1.0.0
```

## Configuration Setup

### Step 1: Get Your SonarCloud API Token

1. Log in to SonarCloud: https://sonarcloud.io
2. Go to **My Account** → **Security**
3. Generate a new token with a descriptive name (e.g., "SAST Report Generator")
4. Copy the token (you won't be able to see it again!)

### Step 2: Configure the Tool

Choose one of these configuration methods:

#### Option A: Environment Variables

```bash
# Create .env file
cat > .env << EOF
SONARCLOUD_TOKEN=your-token-here
SONARCLOUD_ORGANIZATION=your-org
EOF

# Or export directly
export SONARCLOUD_TOKEN="your-token-here"
export SONARCLOUD_ORGANIZATION="your-org"
```

#### Option B: Configuration File

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit the file
nano config/config.yaml
```

Edit `config/config.yaml`:
```yaml
sonarcloud:
  token: "your-token-here"
  organization: "your-org"
  project_key: "your-org_your-project"
```

### Step 3: Validate Configuration

```bash
# Test your configuration
sonar-report validate-config

# Or with config file
sonar-report validate-config --config config/config.yaml
```

Expected output:
```
✓ Configuration file is valid: config/config.yaml

Configuration Details:
  Organization: your-org
  Project Key: your-org_your-project
  Base URL: https://sonarcloud.io/api
  Output Path: ./reports
  Severity Filter: BLOCKER, CRITICAL, MAJOR
  Include Resolved: False

Testing API connection...
✓ Successfully connected to SonarCloud API
```

## Directory Structure

After installation, your directory should look like this:

```
sonar-reports/
├── src/
│   └── sonar_reports/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── issue.py
│       │   ├── metric.py
│       │   ├── project.py
│       │   └── report_data.py
│       ├── processors/
│       │   ├── __init__.py
│       │   └── data_processor.py
│       └── report/
│           ├── __init__.py
│           ├── generator.py
│           └── templates/
│               └── report.md.j2
├── config/
│   ├── config.example.yaml
│   └── .env.example
├── reports/
│   └── .gitkeep
├── requirements.txt
├── setup.py
├── README.md
├── QUICKSTART.md
└── .gitignore
```

## Troubleshooting Installation

### Issue: Python Version Too Old

```
ERROR: Python 3.8 or higher is required
```

**Solution**: Upgrade Python:
```bash
# Check current version
python --version

# Install Python 3.8+ from python.org or use package manager
# On Ubuntu/Debian:
sudo apt-get install python3.8

# On macOS with Homebrew:
brew install python@3.8
```

### Issue: pip Not Found

```
bash: pip: command not found
```

**Solution**:
```bash
# Use python -m pip instead
python -m pip install -r requirements.txt

# Or install pip
python -m ensurepip --upgrade
```

### Issue: Permission Denied

```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solution**: Use virtual environment or --user flag:
```bash
# Option 1: Virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Option 2: User installation
pip install --user -r requirements.txt
```

### Issue: SSL Certificate Error

```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution**:
```bash
# Update certificates
pip install --upgrade certifi

# Or temporarily disable SSL verification (not recommended for production)
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## Uninstallation

```bash
# If installed with pip install -e .
pip uninstall sonar-reports

# Remove virtual environment
deactivate
rm -rf venv

# Remove configuration (optional)
rm -rf config/config.yaml .env

# Remove generated reports (optional)
rm -rf reports/*.md
```

## Upgrading

```bash
# Pull latest changes
git pull origin main

# Upgrade dependencies
pip install --upgrade -r requirements.txt

# Reinstall package
pip install -e .
```

## Docker Installation (Optional)

If you prefer to use Docker:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

ENTRYPOINT ["sonar-report"]
```

Build and run:
```bash
# Build image
docker build -t sonar-reports .

# Run with environment variables
docker run --rm \
  -e SONARCLOUD_TOKEN="your-token" \
  -v $(pwd)/reports:/app/reports \
  sonar-reports generate --project-key your-org_your-project
```

## Next Steps

1. ✅ Installation complete
2. ✅ Configuration validated
3. 📖 Read the [Quick Start Guide](QUICKSTART.md)
4. 🚀 Generate your first report
5. 📊 Review the [Sample Report](SAMPLE_REPORT.md)

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting-installation) section above
2. Review the [README.md](README.md) for detailed documentation
3. Check existing issues on GitHub
4. Create a new issue with:
   - Python version (`python --version`)
   - Operating system
   - Error message
   - Steps to reproduce

---

**Ready to generate reports?** See [QUICKSTART.md](QUICKSTART.md) for usage examples.