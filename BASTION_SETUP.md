# Bastion Host Setup Guide - RDS Database Access

This guide shows you how to deploy a bastion host and use it to access your RDS database in a private VPC.

## What is a Bastion Host?

A bastion host is a lightweight EC2 instance that sits in a PUBLIC subnet and acts as a "jump server" to access resources in private subnets. In your case:
- **Bastion** (public subnet) → **RDS Database** (private subnet)
- Uses **AWS Systems Manager Session Manager** (no SSH keys required!)
- Free tier eligible (t2.micro)

## What's Been Created

### 1. New File: `bastion_stack.py`
Located at: `infrastructure/cdk/stacks/bastion_stack.py`

**Features:**
- EC2 instance (t2.micro, free tier)
- Placed in PUBLIC subnet (for SSM access)
- IAM role with Session Manager permissions
- PostgreSQL client pre-installed (psql)
- Security group configured to reach RDS on port 5432
- Automatic RDS security group rule creation

### 2. Updated: `app.py`
- Imports BastionStack
- Instantiates bastion stack after database stack
- Properly configures security group access

---

## Step 1: Deploy the Bastion Host

### Command to Deploy

```bash
cd C:\Users\barda\Documents\Hack-UTD_local\HackUTD_2025\infrastructure\cdk

# Deploy only the bastion stack
cdk deploy OnboardingHubBastionStack --require-approval never

# OR deploy all stacks including bastion
cdk deploy --require-approval never
```

### What Happens During Deploy

1. ✅ EC2 instance created in public subnet
2. ✅ IAM role created with Session Manager permissions
3. ✅ Security group created for bastion
4. ✅ Security group rule added to RDS (allows bastion → RDS on 5432)
5. ✅ PostgreSQL client installed via user data
6. ✅ Outputs shown with instance ID and Session Manager command

### Expected Output

```
✅  OnboardingHubBastionStack

Outputs:
OnboardingHubBastionStack.BastionInstanceId = i-0123456789abcdef0
OnboardingHubBastionStack.BastionPublicIp = 54.123.45.67
OnboardingHubBastionStack.BastionSecurityGroupId = sg-0123456789abcdef0
OnboardingHubBastionStack.SSMSessionCommand = aws ssm start-session --target i-0123456789abcdef0 --region us-east-1
```

**Save these values!** You'll need the instance ID for the next steps.

---

## Step 2: Connect to Bastion via Session Manager

You have **two options** to access the bastion:

### Option A: Using AWS Console (Easiest)

1. Go to **AWS Console** → **EC2**
2. Find your bastion instance (look for the instance ID from the deploy output)
3. Click the instance → **Connect** tab
4. Click **Session Manager** → **Connect**
5. You'll get a terminal in your browser!

### Option B: Using AWS CLI (From PowerShell)

```powershell
# Get your instance ID from the deploy output, then run:
& 'C:\Program Files\Amazon\AWSCLIV2\aws.exe' ssm start-session --target i-0123456789abcdef0 --region us-east-1
```

You'll see:
```
Starting session with AWS Systems Manager Session Manager
Connect to i-0123456789abcdef0
sh-4.2$
```

---

## Step 3: Connect from Bastion to Your RDS Database

Once you're connected to the bastion (via Session Manager), you're now on the bastion server. You can now access your RDS database!

### Option A: Using psql (PostgreSQL CLI)

```bash
# Once you're in the bastion terminal, run:
psql -h onboardinghubdatabasestack-vendordatabase6a1ca1c3-akncbtikc7zq.cs1oouckekys.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d onboarding_hub

# It will prompt for password
# Password is stored in AWS Secrets Manager (you don't have it locally)
# But you can retrieve it from the bastion!
```

### Option B: Get Password from Secrets Manager (from Bastion)

Since you're on the bastion (which has an IAM role), you can retrieve the password:

```bash
# From within the bastion Session Manager session:
aws secretsmanager get-secret-value \
    --secret-id arn:aws:secretsmanager:us-east-1:560271561576:secret:DbCredentialsSecret4110FA1D-22P18mgcfwIb \
    --region us-east-1 \
    --query SecretString \
    --output text | grep -o '"password":"[^"]*"' | cut -d'"' -f4
```

This outputs the password you can use for psql.

---

## Step 4: Run Database Initialization Script (Best Approach)

Since you already have Python on the bastion, and it has network access to RDS, **copy your init script to the bastion and run it!**

### On Your Laptop (PowerShell):

```powershell
# First, start a Session Manager session
& 'C:\Program Files\Amazon\AWSCLIV2\aws.exe' ssm start-session --target i-0123456789abcdef0 --region us-east-1
```

### Inside the Bastion Session:

```bash
# Clone your git repo
cd /tmp
git clone git@github.com:bardan-dhakal/HackUTD_2025.git
cd HackUTD_2025

# Run the database initialization script
python3 init_database.py
```

**That's it!** The database will be initialized, all tables created, and sample data seeded!

Expected output:
```
============================================================
Database Initialization Script
============================================================
[*] Retrieving database password from Secrets Manager...
[OK] Password retrieved successfully
[*] Connecting to database...
[OK] Connected successfully!
[*] Creating database schema...
[OK] Schema created successfully
[*] Seeding sample data...
[OK] Sample data inserted successfully
[*] Verifying tables...
[+] Found 6 tables: vendors, documents, risk_scores, esg_questionnaires, audit_logs, approval_workflows
[+] Vendors in database: 2

============================================================
[OK] Database initialization completed successfully!
============================================================
```

---

## Step 5: Verify Database Initialization

You can verify the database is initialized by querying it:

```bash
# From bastion terminal:
psql -h onboardinghubdatabasestack-vendordatabase6a1ca1c3-akncbtikc7zq.cs1oouckekys.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d onboarding_hub \
     -c "SELECT COUNT(*) FROM vendors;"
```

You should see:
```
 count
-------
      2
(1 row)
```

---

## Troubleshooting

### Issue: Session Manager Not Connecting

**Error:** `Failed to connect to target`

**Solution:**
- Wait 2-3 minutes after deployment for IAM permissions to propagate
- Check that EC2 instance is in a public subnet
- Verify SSM agent is running: `sudo systemctl status amazon-ssm-agent`

### Issue: Can't Connect to RDS from Bastion

**Error:** `could not connect to server: Connection timed out`

**Solution:**
- Verify security group rule was created (check AWS Console → Security Groups)
- Confirm RDS endpoint is correct
- Check RDS is in AVAILABLE state

### Issue: psql Command Not Found

**Error:** `command not found: psql`

**Solution:**
```bash
# Install PostgreSQL client from bastion terminal
sudo yum install -y postgresql
```

---

## Cleanup (When Done)

To remove the bastion host and save costs:

```bash
# Destroy only bastion stack
cdk destroy OnboardingHubBastionStack --force

# OR destroy all stacks
cdk destroy --force
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Laptop (PowerShell)                 │
│                                                                   │
│  AWS CLI / Session Manager Session                              │
│         ↓                                                         │
└─────────────────────────────────────────────────────────────────┘
           ↓ (AWS Systems Manager)
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Account (us-east-1)                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    VPC (10.0.0.0/16)                    │   │
│  │                                                          │   │
│  │  ┌───────────────────────────────────────────────────┐ │   │
│  │  │        PUBLIC SUBNET (10.0.0.0/24)               │ │   │
│  │  │  ┌─────────────────────────────────────────────┐ │ │   │
│  │  │  │  BASTION (t2.micro)                        │ │ │   │
│  │  │  │  - EC2 Instance                            │ │ │   │
│  │  │  │ - IAM Role (SSM Access)                    │ │ │   │
│  │  │  │  - Port 5432 → RDS                         │ │ │   │
│  │  │  │  - psql installed                          │ │ │   │
│  │  │  └─────────────────────────────────────────────┘ │ │   │
│  │  └───────────────────────────────────────────────────┘ │   │
│  │                                 ↓                      │   │
│  │  ┌───────────────────────────────────────────────────┐ │   │
│  │  │   PRIVATE ISOLATED SUBNET (10.0.3.0/24)          │ │   │
│  │  │  ┌─────────────────────────────────────────────┐ │ │   │
│  │  │  │  RDS PostgreSQL                            │ │ │   │
│  │  │  │  - Port 5432                               │ │ │   │
│  │  │  │  - onboarding_hub database                 │ │ │   │
│  │  │  │  - Accepts only from Bastion SG           │ │ │   │
│  │  │  └─────────────────────────────────────────────┘ │ │   │
│  │  └───────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Points

✅ **Security:**
- Database stays in private subnet (no public access)
- Bastion in public subnet, can only reach RDS (port 5432)
- Session Manager uses IAM authentication (no SSH keys!)
- All communication encrypted

✅ **Cost:**
- t2.micro = free tier eligible
- Only pay for RDS database itself

✅ **Access:**
- Use AWS Console (easiest) or AWS CLI
- No SSH key management
- Session logging available for audit

---

## Commands Cheat Sheet

```bash
# Deploy bastion
cdk deploy OnboardingHubBastionStack --require-approval never

# Get instance ID (from CDK output or AWS Console)
INSTANCE_ID="i-0123456789abcdef0"

# Start Session Manager session
aws ssm start-session --target $INSTANCE_ID --region us-east-1

# (From inside bastion) Clone repo
git clone git@github.com:bardan-dhakal/HackUTD_2025.git

# (From inside bastion) Initialize database
cd HackUTD_2025
python3 init_database.py

# (From inside bastion) Connect to database
psql -h onboardinghubdatabasestack-vendordatabase6a1ca1c3-akncbtikc7zq.cs1oouckekys.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d onboarding_hub

# Cleanup when done
cdk destroy OnboardingHubBastionStack --force
```

---

## Next Steps

1. ✅ Deploy bastion: `cdk deploy OnboardingHubBastionStack --require-approval never`
2. ✅ Connect via Session Manager (Console or CLI)
3. ✅ Clone your repo in the bastion
4. ✅ Run `python3 init_database.py`
5. ✅ Done! Database is initialized

Good luck! 🚀
