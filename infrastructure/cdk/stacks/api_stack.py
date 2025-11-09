"""
API Gateway Stack - REST API for vendor onboarding portal
"""
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    CfnOutput,
)
from constructs import Construct

class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        upload_handler: lambda_.Function,
        status_handler: lambda_.Function,
        risk_score_handler: lambda_.Function,
        approve_handler: lambda_.Function,
        create_vendor_handler: lambda_.Function,
        db_init_handler: lambda_.Function,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create REST API
        self.api = apigw.RestApi(
            self, "VendorOnboardingApi",
            rest_api_name="Vendor Onboarding Hub API",
            description="API for Goldman Sachs Vendor Onboarding Hub",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Amz-Date"],
            ),
        )

        # ====================
        # /vendors Resource
        # ====================
        vendors = self.api.root.add_resource("vendors")

        # POST /vendors - Create vendor
        vendors.add_method(
            "POST",
            apigw.LambdaIntegration(create_vendor_handler),
        )

        # ====================
        # /vendors/{id} Resource
        # ====================
        vendor_by_id = vendors.add_resource("{id}")

        # GET /vendors/{id}/status - Get vendor status
        vendor_status = vendor_by_id.add_resource("status")
        vendor_status.add_method(
            "GET",
            apigw.LambdaIntegration(status_handler),
        )

        # GET /vendors/{id}/risk-score - Get risk score
        vendor_risk = vendor_by_id.add_resource("risk-score")
        vendor_risk.add_method(
            "GET",
            apigw.LambdaIntegration(risk_score_handler),
        )

        # POST /vendors/{id}/risk-score - Calculate risk score
        vendor_risk.add_method(
            "POST",
            apigw.LambdaIntegration(risk_score_handler),
        )

        # POST /vendors/{id}/approve - Approve/reject vendor
        vendor_approve = vendor_by_id.add_resource("approve")
        vendor_approve.add_method(
            "POST",
            apigw.LambdaIntegration(approve_handler),
        )

        # ====================
        # /documents Resource
        # ====================
        documents = self.api.root.add_resource("documents")

        # POST /documents/upload - Get presigned URL
        documents_upload = documents.add_resource("upload")
        documents_upload.add_method(
            "POST",
            apigw.LambdaIntegration(upload_handler),
        )

        # ====================
        # /admin/init Resource
        # ====================
        admin = self.api.root.add_resource("admin")
        init = admin.add_resource("init")

        # POST /admin/init - Initialize database
        init.add_method(
            "POST",
            apigw.LambdaIntegration(db_init_handler),
        )

        # Outputs
        CfnOutput(
            self, "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name="OnboardingHubApiUrl",
        )

        CfnOutput(
            self, "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway ID",
            export_name="OnboardingHubApiId",
        )
