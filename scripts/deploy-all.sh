#!/bin/bash

# =============================================================================
# Deploy All Automations - Jenkins Trigger Script
# =============================================================================
# Purpose: Deploy and validate all automation tools in the repository
# Usage: ./scripts/deploy-all.sh
# Jenkins: Can be called as a deployment pipeline step
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/deploy-all-$(date +%Y%m%d_%H%M%S).log"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log "ERROR: Deployment failed with exit code $exit_code"
        log "Check log file: $LOG_FILE"
    fi
    exit $exit_code
}
trap cleanup EXIT

# Validation functions
validate_python() {
    log "Validating Python installation..."
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        log "✅ Python found: $python_version"
    else
        log "❌ Python 3 not found"
        return 1
    fi
}

validate_git() {
    log "Validating Git repository..."
    if [ -d "$PROJECT_ROOT/.git" ]; then
        local git_branch=$(git -C "$PROJECT_ROOT" branch --show-current)
        local git_commit=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)
        log "✅ Git repository: branch=$git_branch, commit=$git_commit"
    else
        log "❌ Not a Git repository"
        return 1
    fi
}

validate_environment() {
    log "Validating environment variables..."
    local missing_vars=()
    
    if [ -z "${ZENDESK_PASSWORD:-}" ]; then
        missing_vars+=("ZENDESK_PASSWORD")
    fi
    
    if [ -z "${AIRTABLE_API_KEY:-}" ]; then
        log "⚠️  AIRTABLE_API_KEY not set (optional)"
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log "❌ Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    log "✅ Environment validation passed"
}

deploy_dmca_analyzer() {
    log "Deploying DMCA Analyzer..."
    local dmca_dir="$PROJECT_ROOT/src/dmca"
    
    if [ ! -d "$dmca_dir" ]; then
        log "❌ DMCA directory not found: $dmca_dir"
        return 1
    fi
    
    cd "$dmca_dir"
    
    # Install dependencies
    log "Installing DMCA dependencies..."
    pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1
    
    # Test import
    log "Testing DMCA analyzer import..."
    python3 -c "from dmca_analyzer import DMCAAnalyzer; print('✅ Import successful')" 2>&1 | tee -a "$LOG_FILE"
    
    # Run basic validation
    log "Running DMCA analyzer validation..."
    python3 -c "
from dmca_analyzer import DMCAAnalyzer
analyzer = DMCAAnalyzer()
test_url = 'https://opensea.io/assets/ethereum/0x123/1'
result = analyzer.convert_url(test_url)
print(f'✅ URL conversion test: {test_url} → {result}')
" 2>&1 | tee -a "$LOG_FILE"
    
    log "✅ DMCA Analyzer deployed successfully"
}

run_health_checks() {
    log "Running health checks..."
    
    # Check all required scripts are executable
    local scripts=(
        "$SCRIPT_DIR/run-dmca-analyzer.sh"
        "$SCRIPT_DIR/deploy-all.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ -x "$script" ]; then
            log "✅ Script executable: $(basename "$script")"
        else
            log "❌ Script not executable: $(basename "$script")"
            chmod +x "$script"
            log "🔧 Fixed permissions for: $(basename "$script")"
        fi
    done
    
    # Check project structure
    local required_dirs=(
        "$PROJECT_ROOT/src"
        "$PROJECT_ROOT/src/dmca"
        "$PROJECT_ROOT/scripts"
        "$PROJECT_ROOT/logs"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            log "✅ Directory exists: $(basename "$dir")"
        else
            log "❌ Directory missing: $(basename "$dir")"
            return 1
        fi
    done
    
    log "✅ Health checks passed"
}

# Main deployment function
main() {
    log "=========================================="
    log "Starting Open Automations Deployment"
    log "=========================================="
    
    # Run validations
    validate_python
    validate_git
    validate_environment
    
    # Deploy individual components
    deploy_dmca_analyzer
    
    # Run health checks
    run_health_checks
    
    # Final summary
    log "=========================================="
    log "Deployment Summary:"
    log "- DMCA Analyzer: ✅ Deployed"
    log "- Health Checks: ✅ Passed"
    log "- Log File: $LOG_FILE"
    log "=========================================="
    log "🚀 All automations deployed successfully!"
    log "=========================================="
}

# Execute main function
main "$@" 