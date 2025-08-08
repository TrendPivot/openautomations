#!/bin/bash

# =============================================================================
# DMCA Analyzer Jenkins Trigger Script
# =============================================================================
# Purpose: Execute DMCA ticket analysis and Airtable upload automation
# Usage: ./scripts/run-dmca-analyzer.sh
# Jenkins: Can be called directly as a build step
# Mode: Continuous loop with 3-minute intervals
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DMCA_DIR="$PROJECT_ROOT/src/dmca"
LOG_FILE="$PROJECT_ROOT/logs/dmca-$(date +%Y%m%d_%H%M%S).log"
LOOP_INTERVAL=180  # 3 minutes in seconds

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling for individual runs
run_cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log "ERROR: DMCA analyzer run failed with exit code $exit_code"
        log "Will retry in $LOOP_INTERVAL seconds..."
    fi
    return 0  # Don't exit the loop on individual run failures
}

# Main cleanup on script exit
cleanup() {
    local exit_code=$?
    log "=========================================="
    log "DMCA Analyzer loop terminated"
    log "Final log file: $LOG_FILE"
    log "=========================================="
    exit $exit_code
}
trap cleanup EXIT

# Single run execution
run_dmca_analyzer() {
    local run_number=$1
    
    log "=========================================="
    log "DMCA Analyzer - Run #$run_number"
    log "=========================================="
    
    # Validate environment (only check on first run to avoid spam)
    if [ $run_number -eq 1 ]; then
        if [ -z "${ZENDESK_PASSWORD:-}" ]; then
            log "ERROR: ZENDESK_PASSWORD environment variable is required"
            exit 1
        fi
        
        if [ -z "${AIRTABLE_API_KEY:-}" ]; then
            log "WARNING: AIRTABLE_API_KEY not set - records will be prepared but not uploaded"
        fi
    fi
    
    # Navigate to DMCA directory
    log "Changing to DMCA directory: $DMCA_DIR"
    cd "$DMCA_DIR"
    
    # Install dependencies (only on first run)
    if [ $run_number -eq 1 ]; then
        log "Installing Python dependencies..."
        pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1
    fi
    
    # Run DMCA analyzer with error handling
    (
        set -e
        log "Executing DMCA analyzer..."
        python3 dmca_analyzer.py 2>&1 | tee -a "$LOG_FILE"
    ) || run_cleanup
    
    log "DMCA Analyzer run #$run_number completed"
}

# Main execution loop
main() {
    log "=========================================="
    log "Starting DMCA Analyzer Continuous Mode"
    log "Loop interval: $LOOP_INTERVAL seconds (3 minutes)"
    log "Log file: $LOG_FILE"
    log "=========================================="
    
    local run_count=1
    
    while true; do
        run_dmca_analyzer $run_count
        
        log "----------------------------------------"
        log "Waiting $LOOP_INTERVAL seconds before next run..."
        log "Next run will be #$((run_count + 1)) at $(date -d "+$LOOP_INTERVAL seconds" '+%Y-%m-%d %H:%M:%S')"
        log "----------------------------------------"
        
        sleep $LOOP_INTERVAL
        run_count=$((run_count + 1))
    done
}

# Execute main function
main "$@" 
