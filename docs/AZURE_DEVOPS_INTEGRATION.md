# Azure DevOps Pipeline Integration

This guide explains how to integrate the SonarCloud SAST Report Generator into your Azure DevOps pipelines.

## Overview

You can use this report generator in Azure DevOps pipelines to:
- Generate SAST reports after SonarCloud analysis
- Publish reports as pipeline artifacts
- Schedule automated report generation
- Send reports to stakeholders

## Prerequisites

1. **Azure DevOps Project** with pipelines enabled
2. **SonarCloud Account** with your project configured
3. **SonarCloud API Token** (generate at https://sonarcloud.io/account/security)
4. **Python 3.8+** available in your pipeline agent

## Quick Start

### 1. Store Your SonarCloud Token Securely

In Azure DevOps:
1. Go to **Pipelines** → **Library** → **Variable groups**
2. Create a new variable group named `SonarCloud-Credentials`
3. Add a variable:
   - Name: `SONARCLOUD_TOKEN`
   - Value: Your SonarCloud API token
   - **Important**: Click the lock icon to make it secret

### 2. Create Pipeline YAML

Create a file named `azure-pipelines-sonar-report.yml` in your repository root:

```yaml
# Basic pipeline to generate SonarCloud SAST report
trigger:
  branches:
    include:
    - main
    - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: SonarCloud-Credentials
  - name: SONARCLOUD_PROJECT_KEY
    value: 'your-org_your-project'  # Replace with your project key

steps:
- task: UsePythonVersion@0
  displayName: 'Use Python 3.11'
  inputs:
    versionSpec: '3.11'

- script: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- script: |
    python -m sonar_reports generate \
      --project-key $(SONARCLOUD_PROJECT_KEY) \
      --output $(Build.ArtifactStagingDirectory)/sonar-report.md
  displayName: 'Generate SAST Report'
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)

- task: PublishBuildArtifacts@1
  displayName: 'Publish SAST Report'
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)'
    ArtifactName: 'sast-reports'
    publishLocation: 'Container'
```

## Integration Scenarios

### Scenario 1: Generate Report After SonarCloud Analysis

This pipeline runs SonarCloud analysis first, then generates a customer-facing report:

```yaml
trigger:
  branches:
    include:
    - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: SonarCloud-Credentials
  - name: SONARCLOUD_PROJECT_KEY
    value: 'your-org_your-project'

steps:
# Step 1: Prepare SonarCloud
- task: SonarCloudPrepare@1
  displayName: 'Prepare SonarCloud Analysis'
  inputs:
    SonarCloud: 'SonarCloud-Connection'
    organization: 'your-org'
    scannerMode: 'CLI'
    configMode: 'manual'
    cliProjectKey: '$(SONARCLOUD_PROJECT_KEY)'
    cliProjectName: 'Your Project'

# Step 2: Build your project
- script: |
    # Your build commands here
    npm install
    npm run build
  displayName: 'Build Project'

# Step 3: Run SonarCloud Analysis
- task: SonarCloudAnalyze@1
  displayName: 'Run SonarCloud Analysis'

# Step 4: Wait for Quality Gate
- task: SonarCloudPublish@1
  displayName: 'Publish Quality Gate Result'
  inputs:
    pollingTimeoutSec: '300'

# Step 5: Generate Customer Report
- task: UsePythonVersion@0
  displayName: 'Use Python 3.11'
  inputs:
    versionSpec: '3.11'

- script: |
    pip install requests python-dotenv pyyaml jinja2 click tabulate
  displayName: 'Install Report Generator'

- script: |
    python -m sonar_reports generate \
      --project-key $(SONARCLOUD_PROJECT_KEY) \
      --output $(Build.ArtifactStagingDirectory)/SAST-Report-$(Build.BuildNumber).md \
      --severity BLOCKER --severity CRITICAL --severity MAJOR
  displayName: 'Generate SAST Report'
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)

# Step 6: Publish Report
- task: PublishBuildArtifacts@1
  displayName: 'Publish SAST Report'
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)'
    ArtifactName: 'sast-reports'
```

### Scenario 2: Scheduled Weekly Reports

Create a pipeline that runs on a schedule to generate weekly reports:

```yaml
# Scheduled pipeline for weekly SAST reports
trigger: none  # Disable CI triggers

schedules:
- cron: "0 9 * * 1"  # Every Monday at 9 AM UTC
  displayName: Weekly SAST Report
  branches:
    include:
    - main
  always: true

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: SonarCloud-Credentials
  - name: SONARCLOUD_PROJECT_KEY
    value: 'your-org_your-project'

steps:
- task: UsePythonVersion@0
  displayName: 'Use Python 3.11'
  inputs:
    versionSpec: '3.11'

- script: |
    pip install requests python-dotenv pyyaml jinja2 click tabulate
  displayName: 'Install Report Generator'

- script: |
    REPORT_DATE=$(date +%Y-%m-%d)
    python -m sonar_reports generate \
      --project-key $(SONARCLOUD_PROJECT_KEY) \
      --output $(Build.ArtifactStagingDirectory)/Weekly-SAST-Report-${REPORT_DATE}.md
  displayName: 'Generate Weekly SAST Report'
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)

- task: PublishBuildArtifacts@1
  displayName: 'Publish Report'
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)'
    ArtifactName: 'weekly-sast-reports'

# Optional: Send email notification
- task: SendEmail@1
  displayName: 'Email Report to Stakeholders'
  inputs:
    To: 'security-team@company.com'
    Subject: 'Weekly SAST Report - $(Build.BuildNumber)'
    Body: 'Weekly SAST report is available in pipeline artifacts'
```

### Scenario 3: Multi-Project Reports

Generate reports for multiple projects in a single pipeline:

```yaml
trigger:
  branches:
    include:
    - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: SonarCloud-Credentials

steps:
- task: UsePythonVersion@0
  displayName: 'Use Python 3.11'
  inputs:
    versionSpec: '3.11'

- script: |
    pip install requests python-dotenv pyyaml jinja2 click tabulate
  displayName: 'Install Report Generator'

- script: |
    # Define your projects
    PROJECTS=(
      "org_project1"
      "org_project2"
      "org_project3"
    )
    
    # Generate report for each project
    for project in "${PROJECTS[@]}"; do
      echo "Generating report for $project..."
      python -m sonar_reports generate \
        --project-key "$project" \
        --output "$(Build.ArtifactStagingDirectory)/${project}_report.md" \
        --severity BLOCKER --severity CRITICAL
    done
  displayName: 'Generate Reports for All Projects'
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)

- task: PublishBuildArtifacts@1
  displayName: 'Publish All Reports'
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)'
    ArtifactName: 'multi-project-reports'
```

### Scenario 4: Release Pipeline Integration

Add report generation to your release pipeline:

```yaml
# Release pipeline stage
stages:
- stage: SecurityReporting
  displayName: 'Generate Security Report'
  dependsOn: Build
  jobs:
  - job: GenerateReport
    displayName: 'Generate SAST Report'
    pool:
      vmImage: 'ubuntu-latest'
    
    variables:
      - group: SonarCloud-Credentials
    
    steps:
    - task: UsePythonVersion@0
      displayName: 'Use Python 3.11'
      inputs:
        versionSpec: '3.11'
    
    - script: |
        pip install requests python-dotenv pyyaml jinja2 click tabulate
      displayName: 'Install Report Generator'
    
    - script: |
        python -m sonar_reports generate \
          --project-key $(SONARCLOUD_PROJECT_KEY) \
          --output $(Build.ArtifactStagingDirectory)/Release-SAST-Report-$(Release.ReleaseName).md
      displayName: 'Generate Release SAST Report'
      env:
        SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)
    
    - task: PublishPipelineArtifact@1
      displayName: 'Publish Report'
      inputs:
        targetPath: '$(Build.ArtifactStagingDirectory)'
        artifact: 'release-sast-report'
```

## Advanced Configuration

### Using Config File in Pipeline

Store configuration in your repository:

1. Create `config/pipeline-config.yaml`:
```yaml
sonarcloud:
  token: "${SONARCLOUD_TOKEN}"  # Will be replaced by env var
  base_url: "https://sonarcloud.io/api"

report:
  output_path: "./reports"
  include_resolved: false
  severity_filter:
    - BLOCKER
    - CRITICAL
    - MAJOR
  max_issues_per_section: 10
```

2. Use in pipeline:
```yaml
- script: |
    python -m sonar_reports generate \
      --project-key $(SONARCLOUD_PROJECT_KEY) \
      --config config/pipeline-config.yaml \
      --output $(Build.ArtifactStagingDirectory)/report.md
  displayName: 'Generate Report with Config'
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)
```

### Conditional Report Generation

Only generate reports when quality gate fails:

```yaml
- task: SonarCloudPublish@1
  displayName: 'Publish Quality Gate Result'
  name: QualityGate

- script: |
    python -m sonar_reports generate \
      --project-key $(SONARCLOUD_PROJECT_KEY) \
      --output $(Build.ArtifactStagingDirectory)/failed-quality-gate-report.md
  displayName: 'Generate Report (Quality Gate Failed)'
  condition: eq(variables['QualityGate.status'], 'failed')
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)
```

### Publishing to Wiki

Publish reports to Azure DevOps Wiki:

```yaml
- script: |
    # Generate report
    python -m sonar_reports generate \
      --project-key $(SONARCLOUD_PROJECT_KEY) \
      --output report.md
    
    # Clone wiki repository
    git clone https://$(System.AccessToken)@dev.azure.com/your-org/your-project/_git/your-project.wiki wiki
    
    # Copy report to wiki
    cp report.md wiki/SAST-Report-$(date +%Y-%m-%d).md
    
    # Commit and push
    cd wiki
    git config user.email "pipeline@azuredevops.com"
    git config user.name "Azure Pipeline"
    git add .
    git commit -m "Update SAST report $(date +%Y-%m-%d)"
    git push
  displayName: 'Publish Report to Wiki'
  env:
    SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)
```

## Best Practices

### 1. Security
- ✅ Always store tokens in Azure DevOps Variable Groups
- ✅ Mark tokens as secret variables
- ✅ Use service connections when possible
- ✅ Limit token permissions to read-only
- ✅ Rotate tokens regularly

### 2. Performance
- ✅ Cache Python dependencies
- ✅ Use severity filters to reduce data fetching
- ✅ Run reports in parallel for multiple projects
- ✅ Schedule heavy reports during off-peak hours

### 3. Artifact Management
- ✅ Use meaningful artifact names with dates/versions
- ✅ Set retention policies for old reports
- ✅ Organize reports by project/team
- ✅ Consider archiving to Azure Blob Storage

### 4. Notifications
- ✅ Send reports to relevant stakeholders
- ✅ Create work items for critical findings
- ✅ Integrate with Teams/Slack for alerts
- ✅ Set up email notifications for scheduled reports

## Troubleshooting

### Issue: "SONARCLOUD_TOKEN not found"
**Solution**: Ensure the variable group is linked to your pipeline:
```yaml
variables:
  - group: SonarCloud-Credentials  # Add this line
```

### Issue: "Module 'sonar_reports' not found"
**Solution**: Install the package in your pipeline:
```yaml
- script: |
    pip install -r requirements.txt
    # Or install from repository
    pip install -e .
  displayName: 'Install Report Generator'
```

### Issue: "401 Unauthorized"
**Solution**: 
1. Verify token is correct in Variable Group
2. Check token hasn't expired
3. Ensure token has read access to the project

### Issue: Pipeline timeout
**Solution**: Increase timeout for large projects:
```yaml
- script: |
    python -m sonar_reports generate --project-key $(PROJECT_KEY)
  displayName: 'Generate Report'
  timeoutInMinutes: 10  # Increase as needed
```

## Example: Complete CI/CD Pipeline

Here's a complete example combining build, test, analysis, and reporting:

```yaml
trigger:
  branches:
    include:
    - main
    - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: SonarCloud-Credentials
  - name: SONARCLOUD_PROJECT_KEY
    value: 'your-org_your-project'

stages:
- stage: Build
  displayName: 'Build and Test'
  jobs:
  - job: BuildJob
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '3.11'
    
    - script: |
        pip install -r requirements.txt
        pytest --cov=src --cov-report=xml
      displayName: 'Build and Test'

- stage: Analysis
  displayName: 'SonarCloud Analysis'
  dependsOn: Build
  jobs:
  - job: SonarAnalysis
    steps:
    - task: SonarCloudPrepare@1
      inputs:
        SonarCloud: 'SonarCloud-Connection'
        organization: 'your-org'
        scannerMode: 'CLI'
        configMode: 'manual'
        cliProjectKey: '$(SONARCLOUD_PROJECT_KEY)'
    
    - task: SonarCloudAnalyze@1
    
    - task: SonarCloudPublish@1
      inputs:
        pollingTimeoutSec: '300'

- stage: Reporting
  displayName: 'Generate SAST Report'
  dependsOn: Analysis
  jobs:
  - job: GenerateReport
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '3.11'
    
    - script: |
        pip install requests python-dotenv pyyaml jinja2 click tabulate
      displayName: 'Install Report Generator'
    
    - script: |
        python -m sonar_reports generate \
          --project-key $(SONARCLOUD_PROJECT_KEY) \
          --output $(Build.ArtifactStagingDirectory)/SAST-Report.md \
          --severity BLOCKER --severity CRITICAL --severity MAJOR
      displayName: 'Generate SAST Report'
      env:
        SONARCLOUD_TOKEN: $(SONARCLOUD_TOKEN)
    
    - task: PublishBuildArtifacts@1
      inputs:
        PathtoPublish: '$(Build.ArtifactStagingDirectory)'
        ArtifactName: 'sast-reports'
```

## Additional Resources

- [Azure Pipelines Documentation](https://docs.microsoft.com/azure/devops/pipelines/)
- [SonarCloud Azure DevOps Extension](https://marketplace.visualstudio.com/items?itemName=SonarSource.sonarcloud)
- [Project README](README.md)
- [Configuration Guide](HOW_TO_RUN.md)

## Support

For issues specific to:
- **Report Generator**: Check project documentation
- **Azure DevOps**: Contact your DevOps team
- **SonarCloud**: Visit https://community.sonarsource.com/

---

**Ready to integrate?** Start with the Quick Start section and customize based on your needs!