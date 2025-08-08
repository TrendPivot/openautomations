# 🤖 Smart DMCA Request Analyzer

An intelligent Python script that automatically analyzes DMCA requests from Zendesk, extracts marketplace URLs, converts them to standardized format, and prepares them for automated removal through Airtable.

## 🎯 What it does

1. **Fetches DMCA tickets** from Zendesk using the search API
2. **Extracts URLs** from ticket descriptions using smart regex patterns
3. **Converts URLs** from various marketplaces to standardized format
4. **Prepares data** for Airtable automation (Stage 2)

## 📁 Project Structure

```
DMCA/
├── README.md              # This file
├── dmca_analyzer.py      # Main analyzer script
├── requirements.txt       # Python dependencies
└── config/
    └── config.example    # Configuration template
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export ZENDESK_PASSWORD="your_zendesk_api_token"

# 3. Run analysis
python3 dmca_analyzer.py
```

## 🔧 Configuration

### Required Environment Variables
- `ZENDESK_PASSWORD`: Your Zendesk API token

### Optional (for Airtable Upload)
- `AIRTABLE_API_KEY`: Airtable API key for automatic upload

### Hardcoded Airtable Configuration
The script is pre-configured to upload to your specific Airtable:
- **App ID**: `appjPNekcQqLmNfu6`
- **Table ID**: `tblo8hUjb3o9ppRBt`
- **View ID**: `viwyVw493gKptuXmE`
- **URL**: [https://airtable.com/appjPNekcQqLmNfu6/tblo8hUjb3o9ppRBt/viwyVw493gKptuXmE?blocks=hide](https://airtable.com/appjPNekcQqLmNfu6/tblo8hUjb3o9ppRBt/viwyVw493gKptuXmE?blocks=hide)

### Airtable Column Mapping
- **item**: Converted format (e.g., `ABSTRACT-0x1234567890abcdef1234567890abcdef12345678`)
- **Date Received**: Ticket creation date
- **Zendesk**: Ticket URL  
- **Status**: Set to "Done"
- **Notes**: Ticket details and original URL

See `config/config.example` for a complete configuration template.

## 📝 Supported URL Formats

### OpenSea
✅ `https://opensea.io/assets/ethereum/0xabc123/1234` → `ETHEREUM-0xabc123:1234`
✅ `https://opensea.io/collection/cool-collection` → `cool-collection`

### Rarible
✅ `https://rarible.com/token/polygon/0xdef456:789` → `POLYGON-0xdef456:789`
✅ `https://rarible.com/collection/arbitrum/0x123abc` → `ARBITRUM-0x123abc`
✅ `https://rarible.com/user/ethereum/0x456def` → `ETHEREUM-0x456def`

### Rarible.fun
✅ `https://rarible.fun/collections/base/0x789xyz` → `BASE-0x789xyz`

### Supported Chains
- Abstract, Aleph Zero, Aptos, Apechain, Arbitrum One
- Arena-Z, Astar zkEVM, Base, Berachain, Camp (Base Camp Testnet)
- Celo, Chiliz Chain, CrossFi, Eclipse, Ethereum
- Etherlink, Flow, Goat Network, Hedera EVM, HyperEVM
- Immutable X, Kroma, LightLink Phoenix, Lisk, Mantle
- Matchain, MegaETH (Testnet), Moonbeam, Oasys, Palm
- Polygon, RARI Chain, Saakuru, Sei, Settlus
- Shape, Somnia (Testnet), Telos EVM, Viction, zkSync
- ZKcandy

**Total: 42 blockchain networks supported**

## 📊 Output

### JSON Analysis File
```json
{
  "ticket_id": "12345",
  "subject": "DMCA Request - Infringing NFTs",
  "description": "Please remove the following items...",
  "extracted_urls": ["https://opensea.io/assets/ethereum/0xabc/1"],
  "converted_urls": [
    {
      "original_url": "https://opensea.io/assets/ethereum/0xabc/1",
      "converted": "ETHEREUM-0xabc:1"
    }
  ],
  "total_urls_found": 1,
  "total_converted": 1
}
```

### Console Summary
```
DMCA ANALYSIS SUMMARY
==================================================

Ticket #12345
Subject: DMCA Request - Infringing NFTs
URLs found: 3
URLs converted: 3
Converted URLs:
  • ETHEREUM-0xabc123:1 (from https://opensea.io/assets/ethereum/0xabc123/1...)
  • POLYGON-0xdef456:2 (from https://rarible.com/token/polygon/0xdef456:2...)
```

## 🔬 Testing

Test the URL conversion logic directly in Python:
```python
from dmca_analyzer import DMCAAnalyzer

analyzer = DMCAAnalyzer()

# Test URL conversion
test_url = "https://opensea.io/assets/ethereum/0xabc123/1234"
converted = analyzer.convert_url(test_url)
print(f"{test_url} → {converted}")

# Test URL extraction
sample_text = "Check out https://rarible.com/token/polygon/0xdef456:789"
urls = analyzer.extract_urls_from_description(sample_text)
print(f"Found URLs: {urls}")
```

## 🎛️ Advanced Usage

### Custom Zendesk Query
Modify the search query in `dmca_analyzer.py`:
```python
query = "type:ticket form:360003074771 status:open status:pending"
```

### Filter by Date
Add date filters to the query:
```python
query = "type:ticket form:360003074771 status:open created>2024-01-01"
```

## 📈 Stage 2: Airtable Integration ✅

**Fully implemented and ready to use!**

The script automatically uploads analyzed DMCA data to your Airtable with the following workflow:

### Upload Process
1. **Analyzes** DMCA tickets from Zendesk
2. **Converts** marketplace URLs to standardized format
3. **Uploads** each converted URL as a separate Airtable record
4. **Includes** ticket details and original URLs in Notes

### Data Format
Each record contains:
- **item**: `ETHEREUM-0xabc123:1234` (standardized format)
- **Date Received**: `2024-01-15T10:30:00Z` (ticket creation)
- **Zendesk**: `https://rariblecom.zendesk.com/agent/tickets/12345`
- **Status**: `Done` (automatically set)
- **Notes**: `Ticket #12345: DMCA Request\nOriginal URL: https://opensea.io/...`

### Batch Upload
- Processes up to 10 records per batch (Airtable limit)
- Includes rate limiting (200ms between batches)
- Comprehensive error handling and logging

## 🛠️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Zendesk API   │ →  │  DMCA Analyzer  │ →  │   Airtable      │
│  (DMCA Tickets) │    │  (URL Converter)│    │  (Automation)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚨 Error Handling

- **Connection Issues**: Retries with exponential backoff
- **Invalid URLs**: Skipped with logging
- **API Limits**: Respects rate limits
- **Malformed Data**: Graceful degradation

## 📋 Files Generated

- `dmca_analysis_YYYYMMDD_HHMMSS.json`: Complete analysis results
- Logs to console with timestamps and status updates

## 📞 Support

Check logs for detailed error messages. Common issues:
- Missing `ZENDESK_PASSWORD` environment variable
- Network connectivity problems
- Invalid API credentials

---

**🎯 Goal**: Automate DMCA request processing to reduce manual work and speed up removal of infringing content.

**🏗️ Version**: 1.0.0 | **👥 Team**: Rarible Support