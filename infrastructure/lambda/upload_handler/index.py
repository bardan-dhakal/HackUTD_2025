"""
Lambda Function: Document Upload Handler
Generates presigned S3 URLs for secure document uploads
"""
import json
import boto3
import os
from datetime import datetime, timedelta
import uuid

s3_client = boto3.client('s3')

BUCKET_NAME = os.environ['DOCUMENT_BUCKET']
EXPIRATION = 3600  # URL valid for 1 hour

def handler(event, context):
    """
    Generate presigned URL for document upload

    Request: {
        "document_type": "w9" | "insurance" | "diversity_cert" | "bcp",
        "filename": "w9_form.pdf"
    }

    Response: {
        "upload_url": "https://s3.amazonaws.com/...",
        "document_id": "uuid",
        "expires_in": 3600
    }
    """
    try:
        # Get vendor ID from path parameters (from /vendors/{id}/upload)
        path_params = event.get('pathParameters', {})
        vendor_id = path_params.get('id') if path_params else None

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        # Allow vendor_id to be passed in body as fallback
        if not vendor_id:
            vendor_id = body.get('vendor_id')
        document_type = body.get('document_type')
        filename = body.get('filename', 'document.pdf')

        if not vendor_id or not document_type:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing required fields: vendor_id, document_type'
                })
            }

        # Generate unique document ID and S3 key
        document_id = str(uuid.uuid4())
        s3_key = f"vendors/{vendor_id}/{document_type}/{document_id}/{filename}"

        # Generate presigned POST URL
        presigned_post = s3_client.generate_presigned_post(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Fields={
                "x-amz-meta-vendor-id": vendor_id,
                "x-amz-meta-document-type": document_type,
                "x-amz-meta-document-id": document_id
            },
            Conditions=[
                {"x-amz-meta-vendor-id": vendor_id},
                {"x-amz-meta-document-type": document_type},
                ["content-length-range", 0, 10485760]  # Max 10MB
            ],
            ExpiresIn=EXPIRATION
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'upload_url': presigned_post['url'],
                'upload_fields': presigned_post['fields'],
                'document_id': document_id,
                's3_key': s3_key,
                'expires_in': EXPIRATION
            })
        }

    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Failed to generate upload URL',
                'message': str(e)
            })
        }
