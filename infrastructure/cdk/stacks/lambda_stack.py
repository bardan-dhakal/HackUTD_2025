"""
Lambda Stack - Serverless functions for document processing and business logic
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_kms as kms,
    aws_rds as rds,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct

class LambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        document_bucket: s3.Bucket,
        kms_key: kms.Key,
        database,  # Can be DatabaseCluster or DatabaseInstance
        db_secret: secretsmanager.Secret,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Common environment variables for Lambda functions
        # Handle both DatabaseCluster and DatabaseInstance
        if hasattr(database, 'cluster_endpoint'):
            # DatabaseCluster
            db_host = database.cluster_endpoint.hostname
            db_port = database.cluster_endpoint.port
        else:
            # DatabaseInstance
            db_host = database.db_instance_endpoint_address
            db_port = 5432

        common_env = {
            'DB_HOST': db_host,
            'DB_PORT': str(db_port),
            'DB_NAME': 'onboarding_hub',
            'DB_SECRET_ARN': db_secret.secret_arn,
            'DOCUMENT_BUCKET': document_bucket.bucket_name,
        }

        # ====================
        # Lambda Function: Upload Handler
        # ====================
        self.upload_handler = lambda_.Function(
            self, "UploadHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_asset("../lambda/upload_handler"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                'DOCUMENT_BUCKET': document_bucket.bucket_name,
            },
            description="Generate presigned URLs for document uploads",
        )

        # Grant S3 permissions
        document_bucket.grant_read_write(self.upload_handler)
        kms_key.grant_encrypt_decrypt(self.upload_handler)

        # ====================
        # Lambda Function: Create Vendor
        # ====================
        self.create_vendor_handler = lambda_.Function(
            self, "CreateVendorHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_asset("../lambda/create_vendor"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=common_env,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Create new vendor in database",
        )

        # Grant database access
        db_secret.grant_read(self.create_vendor_handler)
        # Database security group will be modified in database_stack to allow access from Lambda security groups

        # ====================
        # Lambda Function: Status Handler
        # ====================
        self.status_handler = lambda_.Function(
            self, "StatusHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_asset("../lambda/status_handler"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=common_env,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Get vendor onboarding status",
        )

        # Grant database access
        db_secret.grant_read(self.status_handler)
        # Database security group will be modified in database_stack to allow access from Lambda security groups

        # ====================
        # Lambda Function: Risk Scoring
        # ====================
        self.risk_score_handler = lambda_.Function(
            self, "RiskScoreHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_asset("../lambda/risk_scoring"),
            timeout=Duration.seconds(60),
            memory_size=1024,
            environment=common_env,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Calculate vendor risk scores",
        )

        # Grant database access
        db_secret.grant_read(self.risk_score_handler)
        # Database security group will be modified in database_stack to allow access from Lambda security groups

        # Grant Textract permissions (for Person 3's integration)
        self.risk_score_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:AnalyzeDocument",
                    "textract:DetectDocumentText",
                ],
                resources=["*"],
            )
        )

        # Grant Comprehend permissions
        self.risk_score_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "comprehend:DetectEntities",
                    "comprehend:ClassifyDocument",
                ],
                resources=["*"],
            )
        )

        # ====================
        # Lambda Function: Approve Vendor
        # ====================
        self.approve_handler = lambda_.Function(
            self, "ApproveHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_asset("../lambda/approve_vendor"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=common_env,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Approve or reject vendor",
        )

        # Grant database access
        db_secret.grant_read(self.approve_handler)
        # Database security group will be modified in database_stack to allow access from Lambda security groups

        # Grant SES permissions for email notifications
        self.approve_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            )
        )

        # ====================
        # Lambda Function: Database Initialization
        # ====================
        self.db_init_handler = lambda_.Function(
            self, "DbInitHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_asset("../lambda/db_init"),
            timeout=Duration.seconds(120),
            memory_size=512,
            environment=common_env,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            description="Initialize RDS database schema and seed data",
        )

        # Grant database access
        db_secret.grant_read(self.db_init_handler)

        # Outputs
        CfnOutput(
            self, "UploadHandlerArn",
            value=self.upload_handler.function_arn,
            description="Upload Handler Lambda ARN",
        )

        CfnOutput(
            self, "CreateVendorHandlerArn",
            value=self.create_vendor_handler.function_arn,
            description="Create Vendor Handler Lambda ARN",
        )

        CfnOutput(
            self, "RiskScoreHandlerArn",
            value=self.risk_score_handler.function_arn,
            description="Risk Score Handler Lambda ARN",
        )

        CfnOutput(
            self, "DbInitHandlerArn",
            value=self.db_init_handler.function_arn,
            description="Database Initialization Lambda ARN",
        )
