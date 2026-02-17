# Nexus Wiki - AWS Deployment

Deploy the Nexus Wiki to AWS with Terraform and systemd.

## Architecture

```
                    ┌─────────────────┐
                    │    Internet     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   AWS EC2       │
                    │   t3.micro      │
                    │   Ubuntu 22.04  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌─────▼─────┐       ┌─────▼─────┐
    │  Nexus  │◄──────►│ Mausoleum │       │  (future) │
    │  :80    │        │   :7777   │       │   Zeus    │
    │  HTTP   │        │ Document  │       │   Spire   │
    └─────────┘        │    DB     │       └───────────┘
                       └───────────┘
```

## Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- SSH key at `~/.ssh/id_ed25519.pub`

## Quick Start

```bash
cd deploy/scripts
./deploy.sh
```

This will:
1. Build release binaries for mausoleum and nexus
2. Create AWS infrastructure (EC2, security group, elastic IP)
3. Copy binaries to the server
4. Install and start systemd services
5. Output the wiki URL

## Commands

```bash
# Full deploy (build + terraform + provision)
./deploy.sh

# Just build binaries
./deploy.sh build

# Just run terraform
./deploy.sh terraform

# Just provision (after terraform)
./deploy.sh provision

# SSH into server
./deploy.sh ssh
```

## Manual Operations

### SSH Access
```bash
ssh ubuntu@<IP>
```

### View Logs
```bash
# Mausoleum logs
sudo journalctl -u mausoleum -f

# Nexus logs
sudo journalctl -u nexus -f
```

### Service Management
```bash
# Status
sudo systemctl status mausoleum nexus

# Restart
sudo systemctl restart nexus

# Stop
sudo systemctl stop nexus mausoleum
```

### Update Binaries
```bash
# Build locally
./rz build mausoleum nexus --release

# Copy to server
scp projects/mausoleum/build/release/mausoleum ubuntu@<IP>:/opt/ritz/bin/
scp projects/nexus/build/release/nexus ubuntu@<IP>:/opt/ritz/bin/

# Restart services
ssh ubuntu@<IP> 'sudo systemctl restart mausoleum nexus'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MAUSOLEUM_HOST | 127.0.0.1 | Mausoleum server host |
| MAUSOLEUM_PORT | 7777 | Mausoleum server port |
| NEXUS_PORT | 80 | HTTP listen port |

### Terraform Variables

Edit `terraform/main.tf` or use `-var`:

```bash
terraform apply -var="instance_type=t3.small"
```

| Variable | Default | Description |
|----------|---------|-------------|
| aws_region | us-west-2 | AWS region |
| instance_type | t3.micro | EC2 instance type |
| environment | production | Environment name |

## Costs

- **t3.micro**: ~$7.50/month (free tier eligible)
- **Elastic IP**: Free when attached to running instance
- **EBS (8GB gp3)**: ~$0.64/month
- **Data transfer**: First 100GB/month free

**Total**: ~$8/month (or free for first year with free tier)

## Cleanup

```bash
cd deploy/terraform
terraform destroy
```

## Files

```
deploy/
├── README.md           # This file
├── terraform/
│   └── main.tf         # AWS infrastructure
├── systemd/
│   ├── mausoleum.service
│   └── nexus.service
└── scripts/
    └── deploy.sh       # Deployment script
```
