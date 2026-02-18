#!/bin/bash
# deploy.sh - Deploy Nexus Wiki to AWS
#
# Usage:
#   ./deploy.sh              # Full deploy (terraform + provision)
#   ./deploy.sh provision    # Just provision (skip terraform)
#   ./deploy.sh build        # Just build binaries
#   ./deploy.sh ssh          # SSH into the server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$DEPLOY_DIR/terraform"
SYSTEMD_DIR="$DEPLOY_DIR/systemd"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[!]${NC} $1"; exit 1; }

# Get instance IP from terraform
get_ip() {
    cd "$TERRAFORM_DIR"
    terraform output -raw public_ip 2>/dev/null || echo ""
}

# Build release binaries
build_binaries() {
    log "Building release binaries..."
    cd "$PROJECT_ROOT"

    # Build mausoleum
    log "Building mausoleum..."
    python3 projects/ritz/build.py build projects/mausoleum --release --no-cache 2>&1 | tail -5

    # Build zeus
    log "Building zeus..."
    python3 projects/ritz/build.py build projects/zeus --release --no-cache 2>&1 | tail -5

    # Build nexus
    log "Building nexus..."
    python3 projects/ritz/build.py build projects/nexus --release --no-cache 2>&1 | tail -5

    # Build valet
    log "Building valet..."
    python3 projects/ritz/build.py build projects/valet --release --no-cache 2>&1 | tail -5

    # Verify binaries exist
    if [[ ! -f "projects/mausoleum/build/release/mausoleum" ]]; then
        # Fall back to debug build
        warn "Release build not found, using debug build"
        MAUSOLEUM_BIN="projects/mausoleum/build/debug/mausoleum"
        ZEUS_BIN="projects/zeus/build/debug/zeus"
        NEXUS_BIN="projects/nexus/build/debug/nexus"
        VALET_BIN="projects/valet/build/debug/valet"
    else
        MAUSOLEUM_BIN="projects/mausoleum/build/release/mausoleum"
        ZEUS_BIN="projects/zeus/build/release/zeus"
        NEXUS_BIN="projects/nexus/build/release/nexus"
        VALET_BIN="projects/valet/build/release/valet"
    fi

    if [[ ! -f "$PROJECT_ROOT/$MAUSOLEUM_BIN" ]]; then
        error "Mausoleum binary not found at $MAUSOLEUM_BIN"
    fi
    if [[ ! -f "$PROJECT_ROOT/$ZEUS_BIN" ]]; then
        error "Zeus binary not found at $ZEUS_BIN"
    fi
    if [[ ! -f "$PROJECT_ROOT/$NEXUS_BIN" ]]; then
        error "Nexus binary not found at $NEXUS_BIN"
    fi
    if [[ ! -f "$PROJECT_ROOT/$VALET_BIN" ]]; then
        error "Valet binary not found at $VALET_BIN"
    fi

    log "Binaries ready:"
    ls -lh "$PROJECT_ROOT/$MAUSOLEUM_BIN" "$PROJECT_ROOT/$ZEUS_BIN" "$PROJECT_ROOT/$NEXUS_BIN" "$PROJECT_ROOT/$VALET_BIN"
}

# Run terraform
run_terraform() {
    log "Running Terraform..."
    cd "$TERRAFORM_DIR"

    # Check if state bucket exists
    if ! aws s3 ls s3://ritz-nexus-terraform-state 2>/dev/null; then
        log "Creating S3 bucket for Terraform state..."
        aws s3 mb s3://ritz-nexus-terraform-state --region us-west-2
        aws s3api put-bucket-versioning \
            --bucket ritz-nexus-terraform-state \
            --versioning-configuration Status=Enabled
    fi

    terraform init
    terraform apply -auto-approve

    # Wait for instance to be ready
    IP=$(get_ip)
    log "Instance IP: $IP"
    log "Waiting for SSH to be ready..."

    for i in {1..30}; do
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@"$IP" "echo ready" 2>/dev/null; then
            log "SSH is ready!"
            return 0
        fi
        echo -n "."
        sleep 5
    done

    error "SSH not ready after 150 seconds"
}

# Provision the server
provision() {
    IP=$(get_ip)
    if [[ -z "$IP" ]]; then
        error "No IP found. Run terraform first."
    fi

    log "Provisioning server at $IP..."

    # Determine binary paths
    if [[ -f "$PROJECT_ROOT/projects/mausoleum/build/release/mausoleum" ]]; then
        MAUSOLEUM_BIN="$PROJECT_ROOT/projects/mausoleum/build/release/mausoleum"
        NEXUS_BIN="$PROJECT_ROOT/projects/nexus/build/release/nexus"
        ZEUS_BIN="$PROJECT_ROOT/projects/zeus/build/release/zeus"
        VALET_BIN="$PROJECT_ROOT/projects/valet/build/release/valet"
    else
        MAUSOLEUM_BIN="$PROJECT_ROOT/projects/mausoleum/build/debug/mausoleum"
        NEXUS_BIN="$PROJECT_ROOT/projects/nexus/build/debug/nexus"
        ZEUS_BIN="$PROJECT_ROOT/projects/zeus/build/debug/zeus"
        VALET_BIN="$PROJECT_ROOT/projects/valet/build/debug/valet"
    fi

    SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    SSH="ssh $SSH_OPTS ubuntu@$IP"
    SCP="scp $SSH_OPTS"

    # Wait for cloud-init to finish
    log "Waiting for cloud-init to complete..."
    $SSH "cloud-init status --wait" || true

    # Stop existing services (reverse order of start)
    log "Stopping existing services..."
    $SSH "sudo systemctl stop valet 2>/dev/null || true"
    $SSH "sudo systemctl stop zeus 2>/dev/null || true"
    $SSH "sudo systemctl stop mausoleum 2>/dev/null || true"

    # Create directories
    log "Creating directories..."
    $SSH "sudo mkdir -p /opt/ritz/bin /var/lib/mausoleum /var/log/ritz"
    $SSH "sudo chown -R ubuntu:ubuntu /opt/ritz"

    # Copy binaries
    log "Copying binaries..."
    $SCP "$MAUSOLEUM_BIN" ubuntu@"$IP":/opt/ritz/bin/mausoleum
    $SCP "$NEXUS_BIN" ubuntu@"$IP":/opt/ritz/bin/nexus
    $SCP "$ZEUS_BIN" ubuntu@"$IP":/opt/ritz/bin/zeus
    $SCP "$VALET_BIN" ubuntu@"$IP":/opt/ritz/bin/valet
    $SSH "chmod +x /opt/ritz/bin/*"

    # Copy systemd services
    log "Installing systemd services..."
    $SCP "$SYSTEMD_DIR/mausoleum.service" ubuntu@"$IP":/tmp/
    $SCP "$SYSTEMD_DIR/zeus.service" ubuntu@"$IP":/tmp/
    $SCP "$SYSTEMD_DIR/valet.service" ubuntu@"$IP":/tmp/
    $SSH "sudo mv /tmp/mausoleum.service /etc/systemd/system/"
    $SSH "sudo mv /tmp/zeus.service /etc/systemd/system/"
    $SSH "sudo mv /tmp/valet.service /etc/systemd/system/"

    # Fix permissions for mausoleum data dir
    log "Setting up permissions..."
    $SSH "sudo useradd -r -s /bin/false ritz 2>/dev/null || true"
    $SSH "sudo chown -R ritz:ritz /var/lib/mausoleum /var/log/ritz"

    # Reload systemd and start services
    log "Starting services..."
    $SSH "sudo systemctl daemon-reload"
    $SSH "sudo systemctl enable mausoleum zeus valet"
    $SSH "sudo systemctl start mausoleum"
    sleep 2
    $SSH "sudo systemctl start zeus"
    sleep 2
    $SSH "sudo systemctl start valet"

    # Verify services
    log "Verifying services..."
    sleep 3
    $SSH "sudo systemctl status mausoleum --no-pager" || true
    $SSH "sudo systemctl status zeus --no-pager" || true
    $SSH "sudo systemctl status valet --no-pager" || true

    # Check if Zeus workers are running
    log "Checking Zeus workers..."
    $SSH "pgrep -a nexus" || true
    $SSH "pgrep -a valet" || true

    echo ""
    log "Deployment complete!"
    echo ""
    echo "  URL:       http://$IP/"
    echo "  SSH:       ssh ubuntu@$IP"
    echo "  Valet:     ssh ubuntu@$IP 'sudo journalctl -u valet -f'"
    echo "  Zeus logs: ssh ubuntu@$IP 'sudo journalctl -u zeus -f'"
    echo "  M7M logs:  ssh ubuntu@$IP 'sudo journalctl -u mausoleum -f'"
    echo ""
}

# SSH into server
do_ssh() {
    IP=$(get_ip)
    if [[ -z "$IP" ]]; then
        error "No IP found. Run terraform first."
    fi
    exec ssh -o StrictHostKeyChecking=no ubuntu@"$IP"
}

# Main
case "${1:-}" in
    build)
        build_binaries
        ;;
    provision)
        provision
        ;;
    ssh)
        do_ssh
        ;;
    terraform)
        run_terraform
        ;;
    *)
        # Full deploy
        build_binaries
        run_terraform
        provision
        ;;
esac
