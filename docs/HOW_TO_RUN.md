# How to Run - Simple Steps

Follow these exact steps to generate your first report:

## Step 1: Install the Package

Open a terminal in the project directory and run:

```bash
pip install -e .
```

This installs the package and all required dependencies in development mode.

## Step 2: Get Your SonarCloud API Token

1. Go to https://sonarcloud.io
2. Log in to your account
3. Click your profile icon → **My Account** → **Security** tab
4. Under "Generate Tokens", enter a name like "SAST Reports"
5. Click **Generate**
6. **Copy the token** (you won't see it again!)

## Step 3: Create a .env File

**Option A: Create .env file manually**

Create a file named `.env` in the project root directory with this content:

```bash
SONARCLOUD_TOKEN=your-token-here
```

Replace `your-token-here` with the token you copied in Step 2.

**Option B: Copy from example**

```bash
# Copy the example file
cp config/.env.example .env

# Edit it with your token
# On Windows: notepad .env
# On Mac/Linux: nano .env
```

Then edit the file and replace `your-sonarcloud-api-token-here` with your actual token.

## Step 4: Find Your Project Key

Your SonarCloud project key is in the format: `organization_project-name`

To find it:
1. Go to https://sonarcloud.io
2. Open your project
3. Look at the URL or project settings
4. Example: `my-company_my-app`

## Step 5: Generate Your First Report

Run this command (replace `YOUR_PROJECT_KEY` with your actual project key):

```bash
python -m sonar_reports generate --project-key YOUR_PROJECT_KEY
```

**Example:**
```bash
python -m sonar_reports generate --project-key my-company_my-app
```

## Step 6: View Your Report

The report will be saved in the `reports/` directory:

```bash
# On Windows
type reports\YOUR_PROJECT_KEY_2025-12-03.md

# On Mac/Linux
cat reports/YOUR_PROJECT_KEY_2025-12-03.md
```

Or just open the file in any text editor or Markdown viewer.

## Complete Example

Here's a complete example from start to finish:

```bash
# 1. Install the package
pip install -e .

# 2. Create .env file
echo "SONARCLOUD_TOKEN=squ_abc123xyz..." > .env

# 3. Generate report
python -m sonar_reports generate --project-key my-org_my-project

# 4. View report
cat reports/my-org_my-project_2025-12-03.md
```

## Troubleshooting

### Error: "SONARCLOUD_TOKEN environment variable is required"

**Solution:** Make sure your `.env` file exists and contains your token:
```bash
# Check if .env exists
ls -la .env

# View contents (be careful not to share this!)
cat .env
```

### Error: "401 Unauthorized"

**Solution:** Your token is invalid or expired. Generate a new token at https://sonarcloud.io/account/security

### Error: "404 Not Found - Project does not exist"

**Solution:** Check your project key format. It should be `organization_project-name`. You can find it in SonarCloud project settings.

### Error: "Module not found"

**Solution:** Install the package:
```bash
pip install -e .
```

## Alternative: Using Config File Instead of .env

If you prefer using a YAML config file instead of .env:

```bash
# 1. Copy example config
cp config/config.example.yaml config/config.yaml

# 2. Edit config.yaml and add your token
# On Windows: notepad config\config.yaml
# On Mac/Linux: nano config/config.yaml

# 3. Generate report with config file
python -m sonar_reports generate --project-key my-org_my-project --config config/config.yaml
```

## Quick Reference

### Basic Commands

```bash
# Generate report (simplest)
python -m sonar_reports generate --project-key YOUR_PROJECT_KEY

# Generate with custom output path
python -m sonar_reports generate --project-key YOUR_PROJECT_KEY --output my-report.md

# Filter by severity (only show critical issues)
python -m sonar_reports generate --project-key YOUR_PROJECT_KEY --severity BLOCKER --severity CRITICAL

# Include resolved issues
python -m sonar_reports generate --project-key YOUR_PROJECT_KEY --include-resolved

# Validate your configuration
python -m sonar_reports validate-config

# Show version
python -m sonar_reports version
```

## What You Need

✅ Python 3.8 or higher  
✅ SonarCloud account  
✅ SonarCloud API token  
✅ Project key from SonarCloud  

## Next Steps

Once you've generated your first report:

1. ✅ Review the report content
2. 📧 Share with your team or customers
3. 🔄 Set up automated report generation
4. 🎨 Customize the template if needed (see `src/sonar_reports/report/templates/report.md.j2`)

## Need Help?

- Check [QUICKSTART.md](QUICKSTART.md) for more examples
- Read [README.md](README.md) for full documentation
- See [SAMPLE_REPORT.md](SAMPLE_REPORT.md) for example output

---

**That's it!** You should now have a professional SAST report generated from your SonarCloud project. 🎉