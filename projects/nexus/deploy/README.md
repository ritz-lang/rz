# Nexus Wiki - AWS Deployment

Deploy the Nexus Wiki to AWS with Terraform and systemd.

## Architecture

The full MTSZV stack (Mausoleum-Tome-Spire-Zeus-Valet):

```
                    ┌─────────────────┐
                    │    Internet     │
                    │   HTTPS :443    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   AWS EC2       │
                    │   t3.micro      │
                    │   Ubuntu 22.04  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐   ┌─────▼─────┐  ┌─────▼─────┐
         │  Valet  │   │   Zeus    │  │ Mausoleum │
         │  :443   │──►│  workers  │──►│   :7777   │
         │  TLS    │   │  (Nexus)  │  │ Document  │
         └─────────┘   └───────────┘  │    DB     │
                                      └───────────┘
```

**Components:**
- **Valet**: TLS 1.3 HTTP server with io_uring (1.47M req/sec)
- **Zeus**: Application server managing Nexus worker processes
- **Nexus**: Wiki application (Spire web framework)
- **Mausoleum**: Document database (persistent storage)

## Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- SSH key at `~/.ssh/id_ed25519.pub`
- Domain configured (ritz-lang.org) with nameservers pointing to AWS Route53

## Quick Start

```bash
cd deploy/scripts

# Full deploy (build + terraform + provision)
./deploy.sh

# Setup TLS certificates (Let's Encrypt)
./deploy.sh certbot
```

This will:
1. Build release binaries for mausoleum, zeus, nexus, valet
2. Create AWS infrastructure (EC2, security group, elastic IP, Route53)
3. Copy binaries and configuration to the server
4. Install and start systemd services
5. (Optional) Setup Let's Encrypt certificates for HTTPS

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

# Setup Let's Encrypt certificates
./deploy.sh certbot

# SSH into server
./deploy.sh ssh
```

## TLS/HTTPS Setup

After the initial deployment, enable HTTPS with Let's Encrypt:

```bash
# Get certificates for ritz-lang.org
./deploy.sh certbot
```

This will:
1. Install certbot on the server
2. Request certificates for ritz-lang.org and www.ritz-lang.org
3. Configure Valet to use the certificates
4. Setup automatic certificate renewal

## Manual Operations

### SSH Access
```bash
ssh ubuntu@<IP>
# or
./deploy.sh ssh
```

### View Logs
```bash
# All services
sudo journalctl -f -u valet -u zeus -u mausoleum

# Individual services
sudo journalctl -u valet -f
sudo journalctl -u zeus -f
sudo journalctl -u mausoleum -f
```

### Service Management
```bash
# Status
sudo systemctl status valet zeus mausoleum

# Restart all
sudo systemctl restart valet zeus mausoleum

# Stop all (reverse dependency order)
sudo systemctl stop valet
sudo systemctl stop zeus
sudo systemctl stop mausoleum
```

### Update Binaries
```bash
# Build locally
cd ~/dev/ritz-lang/rz
python3 projects/ritz/build.py build projects/mausoleum --release
python3 projects/ritz/build.py build projects/zeus --release
python3 projects/ritz/build.py build projects/nexus --release
python3 projects/ritz/build.py build projects/valet --release

# Copy to server
scp projects/*/build/release/* ubuntu@<IP>:/opt/ritz/bin/

# Restart services
ssh ubuntu@<IP> 'sudo systemctl restart mausoleum zeus valet'
```

### Certificate Renewal
Certificates auto-renew via cron. To manually renew:
```bash
ssh ubuntu@<IP>
sudo certbot renew
sudo systemctl restart valet
```

## Configuration

### Valet Configuration (`/etc/ritz/valet.json`)
```json
{
  "server": {
    "port": 443,
    "workers": 1,
    "multishot": true
  },
  "tls": {
    "enabled": true,
    "cert": "/etc/ritz/certs/fullchain.pem",
    "key": "/etc/ritz/certs/privkey.pem"
  },
  "zeus": {
    "enabled": true,
    "socket": "/run/zeus/zeus.sock"
  }
}
```

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
| domain_name | ritz-lang.org | Domain name |

## Costs

- **t3.micro**: ~$7.50/month (free tier eligible)
- **Elastic IP**: Free when attached to running instance
- **EBS (8GB gp3)**: ~$0.64/month
- **Route53 hosted zone**: ~$0.50/month
- **Data transfer**: First 100GB/month free

**Total**: ~$9/month (or ~$1/month with free tier)

## Cleanup

```bash
cd deploy/terraform
terraform destroy
```

## Files

```
deploy/
├── README.md               # This file
├── config/
│   └── valet.json          # Valet configuration
├── terraform/
│   └── main.tf             # AWS infrastructure
├── systemd/
│   ├── mausoleum.service   # Database service
│   ├── zeus.service        # App server service
│   └── valet.service       # HTTP server service
└── scripts/
    └── deploy.sh           # Deployment script
```
