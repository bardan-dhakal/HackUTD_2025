"""
Bastion Stack - EC2 instance for secure access to RDS in private VPC
Uses AWS Systems Manager Session Manager (no SSH keys required)
"""
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ssm as ssm,
    CfnOutput,
)
from constructs import Construct


class BastionStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        database_security_group: ec2.ISecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ===========================================
        # IAM Role for EC2 Instance (SSM Access)
        # ===========================================
        bastion_role = iam.Role(
            self,
            "BastionRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Role for bastion host with SSM Session Manager access",
        )

        # Attach SSM Session Manager policy (allows CloudWatch Logs and SSM)
        bastion_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        # Allow CloudWatch Logs (for Session Manager logging)
        bastion_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=["arn:aws:logs:*:*:*"],
            )
        )

        # Allow S3 access for Session Manager (optional but good practice)
        bastion_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetEncryptionConfiguration"],
                resources=["*"],
            )
        )

        # ===========================================
        # Security Group for Bastion
        # ===========================================
        bastion_security_group = ec2.SecurityGroup(
            self,
            "BastionSecurityGroup",
            vpc=vpc,
            description="Security group for bastion host",
            allow_all_outbound=True,  # Allow outbound to reach RDS
        )

        # ===========================================
        # Allow Database Security Group to Accept from Bastion
        # ===========================================
        database_security_group.add_ingress_rule(
            peer=bastion_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow bastion to connect to RDS on port 5432",
        )

        # ===========================================
        # EC2 Bastion Instance (t3.micro - free tier)
        # ===========================================
        # Get the latest Amazon Linux 2 AMI
        ami = ec2.AmazonLinuxImage(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            virtualization=ec2.AmazonLinuxVirt.HVM,
        )

        bastion_instance = ec2.Instance(
            self,
            "BastionInstance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            machine_image=ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC  # Public subnet for SSM access
            ),
            role=bastion_role,
            security_group=bastion_security_group,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=20,  # 20 GB (free tier)
                        volume_type=ec2.EbsDeviceVolumeType.GP2,
                        delete_on_termination=True,
                    ),
                )
            ],
            key_name=None,  # No SSH key - use Session Manager instead
        )

        # ===========================================
        # User Data - Install PostgreSQL client
        # ===========================================
        bastion_instance.user_data.add_commands(
            "#!/bin/bash",
            "yum update -y",
            "yum install -y postgresql",  # Install PostgreSQL client for psql command
            "echo 'Bastion host ready for database access'",
        )

        # ===========================================
        # Outputs
        # ===========================================
        CfnOutput(
            self,
            "BastionInstanceId",
            value=bastion_instance.instance_id,
            description="Bastion EC2 Instance ID",
            export_name="OnboardingHubBastionInstanceId",
        )

        CfnOutput(
            self,
            "BastionPublicIp",
            value=bastion_instance.instance_public_ip,
            description="Bastion public IP address",
            export_name="OnboardingHubBastionPublicIp",
        )

        CfnOutput(
            self,
            "BastionSecurityGroupId",
            value=bastion_security_group.security_group_id,
            description="Bastion security group ID",
            export_name="OnboardingHubBastionSecurityGroupId",
        )

        CfnOutput(
            self,
            "SSMSessionCommand",
            value=f"aws ssm start-session --target {bastion_instance.instance_id} --region us-east-1",
            description="Command to start SSM Session Manager session",
            export_name="OnboardingHubSSMSessionCommand",
        )

        # Export instance reference for other stacks
        self.bastion_instance = bastion_instance
        self.bastion_security_group = bastion_security_group
