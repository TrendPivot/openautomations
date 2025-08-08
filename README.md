# 🤖 Open Automations

A collection of intelligent automation tools for support operations, DMCA processing, and workflow optimization.

## 📁 Project Structure

```
openautomations/
├── README.md                    # This file
├── scripts/                     # Jenkins trigger scripts
│   ├── run-dmca-analyzer.sh    # DMCA automation trigger
│   └── deploy-all.sh           # Deploy all automations
└── src/                        # Source code for all projects
    └── dmca/                   # DMCA Request Analyzer
        ├── README.md           # DMCA-specific documentation
        ├── dmca_analyzer.py    # Main analyzer script
        ├── requirements.txt    # Dependencies
        └── config/             # Configuration templates
```

## 🚀 Available Automations

### 1. Smart DMCA Request Analyzer
**Location**: `src/dmca/`
**Purpose**: Automates DMCA ticket processing from Zendesk to Airtable

**Features**:
- 🎯 Fetches DMCA tickets from Zendesk automatically
- 🔗 Extracts and converts marketplace URLs (42 blockchain networks)
- 📊 Uploads processed data directly to Airtable
- 🌐 Supports OpenSea, Rarible, and Rarible.fun marketplaces

**Quick Start**:
```bash
cd src/dmca
export ZENDESK_PASSWORD="your_token"
export AIRTABLE_API_KEY="your_key"
python3 dmca_analyzer.py
```

## 🔧 Jenkins Integration

### Trigger Scripts
All automation scripts are located in the `scripts/` directory and are designed for Jenkins CI/CD:

- **`scripts/run-dmca-analyzer.sh`**: Execute DMCA analysis pipeline
- **`scripts/deploy-all.sh`**: Deploy all automation tools

### Environment Variables Required
```bash
# Zendesk Configuration
ZENDESK_PASSWORD=your_zendesk_api_token

# Airtable Configuration  
AIRTABLE_API_KEY=your_airtable_api_key

# Optional: Logging
LOG_LEVEL=INFO
```

## 📈 Adding New Automations

1. Create new directory in `src/your-automation/`
2. Add corresponding trigger script in `scripts/`
3. Update this README with project details
4. Follow the established patterns for environment variables

## 🛠️ Development

### Prerequisites
- Python 3.8+
- Git
- Access to required APIs (Zendesk, Airtable, etc.)

### Setup
```bash
git clone https://github.com/TrendPivot/openautomations.git
cd openautomations
# Navigate to specific project
cd src/dmca
pip install -r requirements.txt
```

## 📞 Support

Each automation project includes its own documentation and troubleshooting guide. Check the respective `README.md` files in each `src/` subdirectory.

---

**🎯 Goal**: Streamline support operations through intelligent automation
**🏗️ Version**: 1.0.0 | **👥 Team**: TrendPivot