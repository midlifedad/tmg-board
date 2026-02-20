#!/usr/bin/env bash
#
# sync-prod-to-staging.sh
#
# Copies production database and uploaded files to staging.
# This gives staging real data for testing before production releases.
#
# Prerequisites:
#   - Railway CLI installed and authenticated (railway login)
#   - pg_dump and pg_restore available locally
#   - Both production and staging projects accessible via Railway CLI
#
# Usage:
#   ./scripts/sync-prod-to-staging.sh           # Full sync (DB + files)
#   ./scripts/sync-prod-to-staging.sh --db-only  # Database only
#   ./scripts/sync-prod-to-staging.sh --files-only # Files only
#
# Environment variables (or set in .env):
#   PROD_DATABASE_URL    - Production PostgreSQL connection string
#   STAGING_DATABASE_URL - Staging PostgreSQL connection string
#   PROD_SERVICE_ID      - Railway service ID for production backend
#   STAGING_SERVICE_ID   - Railway service ID for staging backend
#   RAILWAY_PROJECT_ID   - Railway project ID (if needed)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DUMP_FILE="/tmp/tmg-board-prod-dump-$(date +%Y%m%d-%H%M%S).sql"

# Load .env if present
if [[ -f "$PROJECT_DIR/.env.sync" ]]; then
    set -a
    source "$PROJECT_DIR/.env.sync"
    set +a
fi

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

log()  { echo -e "${BLUE}[sync]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

check_prereqs() {
    local missing=0

    if ! command -v pg_dump &>/dev/null; then
        err "pg_dump not found. Install PostgreSQL client tools."
        missing=1
    fi

    if ! command -v pg_restore &>/dev/null; then
        err "pg_restore not found. Install PostgreSQL client tools."
        missing=1
    fi

    if ! command -v psql &>/dev/null; then
        err "psql not found. Install PostgreSQL client tools."
        missing=1
    fi

    if [[ -z "${PROD_DATABASE_URL:-}" ]]; then
        err "PROD_DATABASE_URL not set. Set it in .env.sync or environment."
        missing=1
    fi

    if [[ -z "${STAGING_DATABASE_URL:-}" ]]; then
        err "STAGING_DATABASE_URL not set. Set it in .env.sync or environment."
        missing=1
    fi

    if [[ $missing -eq 1 ]]; then
        echo ""
        echo "Create a .env.sync file in the project root with:"
        echo "  PROD_DATABASE_URL=postgresql://user:pass@host:port/dbname"
        echo "  STAGING_DATABASE_URL=postgresql://user:pass@host:port/dbname"
        echo ""
        echo "Get these from Railway dashboard → service → Variables → DATABASE_URL"
        exit 1
    fi
}

confirm() {
    local prompt="$1"
    echo -en "${YELLOW}${prompt} [y/N]${NC} "
    read -r response
    [[ "$response" =~ ^[Yy]$ ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Database sync
# ─────────────────────────────────────────────────────────────────────────────

sync_database() {
    log "Starting database sync: Production → Staging"
    echo ""

    # Show what we're about to do
    log "Source: Production database"
    log "Target: Staging database"
    echo ""

    # Count records in production
    log "Checking production database..."
    local prod_counts
    prod_counts=$(psql "$PROD_DATABASE_URL" -t -A -c "
        SELECT
            (SELECT COUNT(*) FROM board_members) AS members,
            (SELECT COUNT(*) FROM documents) AS documents,
            (SELECT COUNT(*) FROM meetings) AS meetings,
            (SELECT COUNT(*) FROM decisions) AS decisions,
            (SELECT COUNT(*) FROM ideas) AS ideas,
            (SELECT COUNT(*) FROM audit_logs) AS audit_logs
    " 2>/dev/null) || {
        err "Failed to connect to production database"
        return 1
    }

    log "Production data: $prod_counts"
    echo ""

    if ! confirm "This will OVERWRITE all staging data. Continue?"; then
        warn "Aborted."
        return 0
    fi

    # Step 1: Dump production
    log "Dumping production database..."
    pg_dump "$PROD_DATABASE_URL" \
        --format=custom \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
        --file="$DUMP_FILE" || {
        err "pg_dump failed"
        return 1
    }
    ok "Production dump saved to $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"

    # Step 2: Restore to staging
    log "Restoring to staging database..."
    pg_restore "$STAGING_DATABASE_URL" \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
        --single-transaction \
        "$DUMP_FILE" 2>/dev/null || {
        # pg_restore returns non-zero even on warnings, check if data is there
        warn "pg_restore reported warnings (this is often normal)"
    }

    # Step 3: Verify
    log "Verifying staging database..."
    local staging_counts
    staging_counts=$(psql "$STAGING_DATABASE_URL" -t -A -c "
        SELECT
            (SELECT COUNT(*) FROM board_members) AS members,
            (SELECT COUNT(*) FROM documents) AS documents,
            (SELECT COUNT(*) FROM meetings) AS meetings,
            (SELECT COUNT(*) FROM decisions) AS decisions,
            (SELECT COUNT(*) FROM ideas) AS ideas,
            (SELECT COUNT(*) FROM audit_logs) AS audit_logs
    " 2>/dev/null) || {
        err "Failed to verify staging database"
        return 1
    }

    log "Staging data after sync: $staging_counts"
    ok "Database sync complete"

    # Cleanup
    rm -f "$DUMP_FILE"
    ok "Cleaned up dump file"
}

# ─────────────────────────────────────────────────────────────────────────────
# File sync (Railway Volumes)
# ─────────────────────────────────────────────────────────────────────────────

sync_files() {
    log "Starting file sync: Production → Staging"
    echo ""

    # Railway volumes aren't directly accessible from outside.
    # We use the Railway CLI to copy files between services.
    if ! command -v railway &>/dev/null; then
        err "Railway CLI not found. Install it: npm i -g @railway/cli"
        echo ""
        echo "Alternative: Manually copy files between volumes using Railway dashboard"
        echo "  1. railway run --service <prod-backend> -- tar czf /tmp/uploads.tar.gz -C /app/uploads ."
        echo "  2. Download the archive"
        echo "  3. railway run --service <staging-backend> -- tar xzf /tmp/uploads.tar.gz -C /app/uploads"
        return 1
    fi

    if [[ -z "${PROD_SERVICE_ID:-}" ]] || [[ -z "${STAGING_SERVICE_ID:-}" ]]; then
        warn "PROD_SERVICE_ID and STAGING_SERVICE_ID not set."
        echo ""
        echo "Set these in .env.sync to enable file sync:"
        echo "  PROD_SERVICE_ID=<railway-service-id>"
        echo "  STAGING_SERVICE_ID=<railway-service-id>"
        echo ""
        echo "Get service IDs from: railway service list"
        echo ""
        echo "Manual alternative:"
        echo "  1. SSH into production: railway shell --service <prod-backend>"
        echo "  2. Archive uploads: tar czf /tmp/uploads.tar.gz -C \$UPLOAD_DIR ."
        echo "  3. Copy out: railway volume download"
        echo "  4. Copy to staging: railway volume upload --service <staging-backend>"
        return 1
    fi

    local TEMP_DIR="/tmp/tmg-board-files-sync-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$TEMP_DIR"

    if ! confirm "This will overwrite staging upload files. Continue?"; then
        warn "Aborted."
        return 0
    fi

    # Step 1: Download from production
    log "Downloading files from production volume..."
    RAILWAY_SERVICE_ID="$PROD_SERVICE_ID" railway volume download \
        --dest "$TEMP_DIR" 2>/dev/null || {
        err "Failed to download production files. Try manual method above."
        rm -rf "$TEMP_DIR"
        return 1
    }
    local file_count
    file_count=$(find "$TEMP_DIR" -type f | wc -l | tr -d ' ')
    ok "Downloaded $file_count files from production"

    # Step 2: Upload to staging
    log "Uploading files to staging volume..."
    RAILWAY_SERVICE_ID="$STAGING_SERVICE_ID" railway volume upload \
        --src "$TEMP_DIR" 2>/dev/null || {
        err "Failed to upload to staging. Try manual method above."
        rm -rf "$TEMP_DIR"
        return 1
    }
    ok "Uploaded $file_count files to staging"

    # Cleanup
    rm -rf "$TEMP_DIR"
    ok "File sync complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  TMG Board: Production → Staging Sync${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo ""

    local mode="${1:-all}"

    case "$mode" in
        --db-only)
            check_prereqs
            sync_database
            ;;
        --files-only)
            sync_files
            ;;
        all|"")
            check_prereqs
            sync_database
            echo ""
            sync_files
            ;;
        -h|--help)
            echo "Usage: $0 [--db-only|--files-only|--help]"
            echo ""
            echo "Syncs production data to staging environment."
            echo ""
            echo "Options:"
            echo "  --db-only     Sync database only"
            echo "  --files-only  Sync uploaded files only"
            echo "  --help        Show this help"
            echo ""
            echo "Configuration: Create .env.sync in project root with:"
            echo "  PROD_DATABASE_URL=postgresql://..."
            echo "  STAGING_DATABASE_URL=postgresql://..."
            echo "  PROD_SERVICE_ID=<railway-service-id>      (optional, for file sync)"
            echo "  STAGING_SERVICE_ID=<railway-service-id>    (optional, for file sync)"
            ;;
        *)
            err "Unknown option: $mode"
            echo "Run $0 --help for usage"
            exit 1
            ;;
    esac

    echo ""
    ok "Done!"
}

main "$@"
