#!/bin/bash

# =============================================================================
# DMCA Analyzer Jenkins Trigger Script
# =============================================================================
# Purpose: Execute DMCA ticket analysis and Airtable upload automation
# Usage: ./scripts/run-dmca-analyzer.sh
# Jenkins: Can be called directly as a build step
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DMCA_DIR="$PROJECT_ROOT/src/dmca"
LOG_FILE="$PROJECT_ROOT/logs/dmca-$(date +%Y%m%d_%H%M%S).log"

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
        log "ERROR: DMCA analyzer failed with exit code $exit_code"
        log "Check log file: $LOG_FILE"
    fi
    exit $exit_code
}
trap cleanup EXIT

# Main execution
main() {
    log "=========================================="
    log "Starting DMCA Analyzer Automation"
    log "=========================================="
    
    # Validate environment
    if [ -z "${ZENDESK_PASSWORD:-}" ]; then
        log "ERROR: ZENDESK_PASSWORD environment variable is required"
        exit 1
    fi
    
    if [ -z "${AIRTABLE_API_KEY:-}" ]; then
        log "WARNING: AIRTABLE_API_KEY not set - records will be prepared but not uploaded"
    fi
    
    # Navigate to DMCA directory
    log "Changing to DMCA directory: $DMCA_DIR"
    cd "$DMCA_DIR"
    
    # Install dependencies
    log "Installing Python dependencies..."
    pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1
    
    # Run DMCA analyzer
    log "Executing DMCA analyzer..."
    python3 dmca_analyzer.py 2>&1 | tee -a "$LOG_FILE"
    
    # Check for output files
    if ls dmca_analysis_*.json 1> /dev/null 2>&1; then
        log "SUCCESS: Analysis completed, output files generated"
        log "Generated files:"
        ls -la dmca_analysis_*.json | tee -a "$LOG_FILE"
    else
        log "WARNING: No output files found"
    fi
    
    log "=========================================="
    log "DMCA Analyzer completed successfully"
    log "Log file: $LOG_FILE"
    log "=========================================="
}

# Execute main function
main "$@" 