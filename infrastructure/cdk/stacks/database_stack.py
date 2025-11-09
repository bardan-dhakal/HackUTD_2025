"""
Database Stack - Aurora PostgreSQL Serverless for vendor data
"""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create database credentials secret
        self.db_secret = secretsmanager.Secret(
            self, "DbCredentialsSecret",
            description="Master credentials for Aurora PostgreSQL database",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password",
                exclude_characters="\"@/\\ '",
                password_length=32,
            ),
        )

        # Create RDS PostgreSQL instance (free tier compatible)
        self.database = rds.DatabaseInstance(
            self, "VendorDatabase",
            engine=rds.DatabaseInstanceEngine.POSTGRES,
            credentials=rds.Credentials.from_secret(self.db_secret),
            database_name="onboarding_hub",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO
            ),  # Free tier eligible
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED  # No internet access
            ),
            backup_retention=Duration.days(1),  # Minimal backup for hackathon
            cloudwatch_logs_exports=["postgresql"],  # Enable CloudWatch logs
            storage_encrypted=True,  # Encrypt data at rest
            allocated_storage=20,  # Free tier eligible (up to 20 GB)
            removal_policy=RemovalPolicy.DESTROY,  # For hackathon
            deletion_protection=False,  # Allow deletion
            multi_az=False,  # Single AZ for cost
        )

        # Allow traffic from the VPC to the database
        self.database.connections.allow_from(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(5432)
        )

        # Outputs
        CfnOutput(
            self, "DatabaseEndpoint",
            value=self.database.db_instance_endpoint_address,
            description="RDS PostgreSQL instance endpoint",
            export_name="OnboardingHubDatabaseEndpoint",
        )

        CfnOutput(
            self, "DatabasePort",
            value="5432",
            description="Database port",
            export_name="OnboardingHubDatabasePort",
        )

        CfnOutput(
            self, "DatabaseName",
            value="onboarding_hub",
            description="Default database name",
            export_name="OnboardingHubDatabaseName",
        )

        CfnOutput(
            self, "DatabaseSecretArn",
            value=self.db_secret.secret_arn,
            description="ARN of the secret containing database credentials",
            export_name="OnboardingHubDatabaseSecretArn",
        )

        # Store database configuration for Lambda initialization
        self.db_endpoint = self.database.db_instance_endpoint_address
        self.db_port = 5432
