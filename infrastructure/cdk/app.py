#!/usr/bin/env python3
"""
AWS CDK App for Goldman Sachs Vendor Onboarding Hub
Infrastructure as Code for the hackathon project
"""
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3, aws_s3_notifications as s3_notifications
from stacks.vpc_stack import VpcStack
from stacks.storage_stack import StorageStack
from stacks.database_stack import DatabaseStack
from stacks.lambda_stack import LambdaStack
from stacks.api_stack import ApiStack
from stacks.bastion_stack import BastionStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account="560271561576",  # Replace with your AWS account ID
    region="us-east-1"  # Or your preferred region
)

# Stack 1: VPC and Networking
vpc_stack = VpcStack(
    app, "OnboardingHubVpcStack",
    description="VPC with public/private/isolated subnets for vendor onboarding",
    env=env
)

# Stack 2: Storage (S3 + KMS)
storage_stack = StorageStack(
    app, "OnboardingHubStorageStack",
    description="S3 bucket with customer-managed KMS encryption for documents",
    env=env
)

# Stack 3: Database (RDS Aurora PostgreSQL)
database_stack = DatabaseStack(
    app, "OnboardingHubDatabaseStack",
    vpc=vpc_stack.vpc,
    description="Aurora PostgreSQL Serverless for vendor data",
    env=env
)

# Stack 4: Lambda Functions
lambda_stack = LambdaStack(
    app, "OnboardingHubLambdaStack",
    vpc=vpc_stack.vpc,
    document_bucket=storage_stack.document_bucket,
    kms_key=storage_stack.kms_key,
    database=database_stack.database,
    db_secret=database_stack.db_secret,
    description="Lambda functions for document processing and business logic",
    env=env
)

# Note: S3 event notifications for document processor are configured
# in a separate manual step after deployment to avoid circular dependencies
# See: infrastructure/scripts/setup_s3_notifications.sh

# Stack 5: API Gateway
api_stack = ApiStack(
    app, "OnboardingHubApiStack",
    upload_handler=lambda_stack.upload_handler,
    status_handler=lambda_stack.status_handler,
    risk_score_handler=lambda_stack.risk_score_handler,
    approve_handler=lambda_stack.approve_handler,
    create_vendor_handler=lambda_stack.create_vendor_handler,
    db_init_handler=lambda_stack.db_init_handler,
    description="REST API Gateway for vendor onboarding portal",
    env=env
)

# Stack 6: Bastion Host (Optional - for database access via Session Manager)
bastion_stack = BastionStack(
    app, "OnboardingHubBastionStack",
    vpc=vpc_stack.vpc,
    database_security_group=database_stack.database.connections.security_groups[0],
    description="Bastion EC2 instance for secure RDS access via Session Manager",
    env=env
)

# Add dependencies
storage_stack.add_dependency(vpc_stack)
database_stack.add_dependency(vpc_stack)
# bastion_stack depends on database implicitly through security group reference
lambda_stack.add_dependency(storage_stack)
lambda_stack.add_dependency(database_stack)
api_stack.add_dependency(lambda_stack)

# Tags for all resources
cdk.Tags.of(app).add("Project", "VendorOnboardingHub")
cdk.Tags.of(app).add("Team", "HackUTD")
cdk.Tags.of(app).add("Environment", "Hackathon")

app.synth()
