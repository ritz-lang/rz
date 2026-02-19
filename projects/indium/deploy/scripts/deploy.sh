#!/bin/bash
# Harland EC2 Deployment Script
#
# Builds the Harland disk image and deploys to AWS EC2.
#
# Usage:
#   ./deploy.sh           # Full deployment
#   ./deploy.sh build     # Just build the disk image
#   ./deploy.sh init      # Just terraform init
#   ./deploy.sh apply     # Just terraform apply
#   ./deploy.sh console   # Get serial console output
#   ./deploy.sh destroy   # Tear down all resources
#   ./deploy.sh status    # Show instance status

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$DEPLOY_DIR/terraform"
INDIUM_DIR="$(dirname "$DEPLOY_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[!]${NC} $1"; exit 1; }

# Build the EC2-compatible disk image and initramfs
build_image() {
    log "Building Harland kernel, userspace, and EC2 boot disk..."
    cd "$INDIUM_DIR"

    # Build kernel first
    make kernel || error "Failed to build kernel"

    # Build userspace programs and rzsh
    make userspace || error "Failed to build userspace"
    make rzsh || error "Failed to build rzsh"

    # Build initramfs TAR (contains /bin/init and other programs)
    make build/initramfs.tar || error "Failed to build initramfs"

    # Build EC2-compatible disk image
    make ec2-disk || error "Failed to build EC2 disk image"

    # Verify the images
    if [ ! -f "build/ec2-boot.img" ]; then
        error "Boot disk image not found at build/ec2-boot.img"
    fi
    if [ ! -f "build/initramfs.tar" ]; then
        error "Initramfs not found at build/initramfs.tar"
    fi

    log "Images created:"
    log "  Boot disk: $INDIUM_DIR/build/ec2-boot.img"
    file "$INDIUM_DIR/build/ec2-boot.img"
    log "  Initramfs: $INDIUM_DIR/build/initramfs.tar"
    tar tvf "$INDIUM_DIR/build/initramfs.tar" 2>/dev/null | head -20
}

# Initialize Terraform
terraform_init() {
    log "Initializing Terraform..."
    cd "$TERRAFORM_DIR"

    # Check if S3 bucket exists, if not try to create it
    BUCKET_NAME="ritz-harland-terraform-state"
    REGION="us-west-2"

    if ! aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
        log "Creating S3 bucket for Terraform state..."
        aws s3 mb "s3://$BUCKET_NAME" --region "$REGION" || {
            warn "Could not create S3 bucket. Using local state instead."
            warn "Comment out the backend 's3' block in main.tf and re-run."
            return 1
        }
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
        log "S3 bucket created: $BUCKET_NAME"
    fi

    terraform init
}

# Apply Terraform
terraform_apply() {
    log "Applying Terraform configuration..."
    cd "$TERRAFORM_DIR"

    # Check that disk images exist
    if [ ! -f "$INDIUM_DIR/build/ec2-boot.img" ]; then
        error "Boot disk image not found. Run './deploy.sh build' first."
    fi
    if [ ! -f "$INDIUM_DIR/build/initramfs.tar" ]; then
        error "Initramfs not found. Run './deploy.sh build' first."
    fi

    terraform apply -auto-approve

    log "Deployment complete!"
    echo ""
    terraform output
}

# Get console output
get_console_output() {
    cd "$TERRAFORM_DIR"

    # Check if terraform state exists
    if [ ! -f "terraform.tfstate" ] && [ ! -d ".terraform" ]; then
        error "Terraform not initialized. Run './deploy.sh apply' first."
    fi

    INSTANCE_ID=$(terraform output -raw harland_instance_id 2>/dev/null) || {
        error "Could not get Harland instance ID. Is the deployment complete?"
    }
    REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-west-2")

    log "Getting console output for instance $INSTANCE_ID..."
    echo ""

    # Get console output - it's base64 encoded
    OUTPUT=$(aws ec2 get-console-output \
        --instance-id "$INSTANCE_ID" \
        --region "$REGION" \
        --query 'Output' \
        --output text 2>/dev/null)

    if [ -z "$OUTPUT" ] || [ "$OUTPUT" = "None" ]; then
        warn "No console output yet. The instance may still be booting."
        warn "Wait a minute and try again."
        echo ""
        log "Instance status:"
        aws ec2 describe-instances \
            --instance-ids "$INSTANCE_ID" \
            --region "$REGION" \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text
    else
        # Decode base64 output
        echo "$OUTPUT" | base64 -d 2>/dev/null || echo "$OUTPUT"
    fi
}

# Show instance status
show_status() {
    cd "$TERRAFORM_DIR"

    if [ ! -f "terraform.tfstate" ] && [ ! -d ".terraform" ]; then
        error "Terraform not initialized."
    fi

    HARLAND_ID=$(terraform output -raw harland_instance_id 2>/dev/null || echo "")
    BUILDER_ID=$(terraform output -raw builder_instance_id 2>/dev/null || echo "")
    REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-west-2")

    log "Instance Status:"
    echo ""

    if [ -n "$HARLAND_ID" ]; then
        echo "Harland Instance ($HARLAND_ID):"
        aws ec2 describe-instances \
            --instance-ids "$HARLAND_ID" \
            --region "$REGION" \
            --query 'Reservations[0].Instances[0].[State.Name,InstanceType,LaunchTime]' \
            --output table 2>/dev/null || echo "  Not found"
    fi

    if [ -n "$BUILDER_ID" ]; then
        echo ""
        echo "Builder Instance ($BUILDER_ID):"
        aws ec2 describe-instances \
            --instance-ids "$BUILDER_ID" \
            --region "$REGION" \
            --query 'Reservations[0].Instances[0].[State.Name,InstanceType,LaunchTime]' \
            --output table 2>/dev/null || echo "  Not found"
    fi
}

# Destroy all resources
terraform_destroy() {
    cd "$TERRAFORM_DIR"

    warn "This will destroy all Harland EC2 resources!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Destroying Terraform resources..."
        terraform destroy -auto-approve
        log "All resources destroyed."
    else
        log "Cancelled."
    fi
}

# Main
case "${1:-}" in
    build)
        build_image
        ;;
    init)
        terraform_init
        ;;
    apply)
        terraform_apply
        ;;
    console)
        get_console_output
        ;;
    status)
        show_status
        ;;
    destroy)
        terraform_destroy
        ;;
    help|-h|--help)
        echo "Harland EC2 Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (none)    Full deployment (build + init + apply + console)"
        echo "  build     Build the Harland disk image"
        echo "  init      Initialize Terraform"
        echo "  apply     Apply Terraform configuration"
        echo "  console   Get serial console output from Harland instance"
        echo "  status    Show instance status"
        echo "  destroy   Destroy all resources"
        echo "  help      Show this help"
        ;;
    *)
        # Full deployment
        log "Starting full Harland EC2 deployment..."
        echo ""

        build_image
        echo ""

        terraform_init
        echo ""

        terraform_apply
        echo ""

        log "Waiting 60 seconds for Harland to boot..."
        sleep 60

        get_console_output
        ;;
esac
