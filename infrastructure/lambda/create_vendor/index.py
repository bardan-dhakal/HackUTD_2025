"""
Lambda Function: Create Vendor
Creates a new vendor record in the database
"""
import json
import psycopg2
import os
import boto3
from datetime import datetime

secrets_client = boto3.client('secretsmanager')

# Get database credentials from Secrets Manager
def get_db_connection():
    secret_arn = os.environ['DB_SECRET_ARN']
    response = secrets_client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response['SecretString'])

    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ['DB_PORT'],
        database=os.environ['DB_NAME'],
        user=secret['username'],
        password=secret['password']
    )

def handler(event, context):
    """
    Create a new vendor

    Request: {
        "company_name": "ABC Corp",
        "contact_email": "contact@abc.com",
        "ein": "12-3456789",
        "address": "123 Main St",
        "contact_phone": "+1-555-0100"
    }

    Response: {
        "id": "uuid",
        "status": "submitted",
        "onboarding_progress": 0
    }
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        company_name = body.get('company_name')
        contact_email = body.get('contact_email')
        ein = body.get('ein')
        address = body.get('address')
        contact_phone = body.get('contact_phone')

        if not company_name or not contact_email:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing required fields: company_name, contact_email'
                })
            }

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert vendor
        cursor.execute("""
            INSERT INTO vendors (company_name, ein, address, contact_email, contact_phone)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, status, onboarding_progress, created_at
        """, (company_name, ein, address, contact_email, contact_phone))

        vendor = cursor.fetchone()
        vendor_id, status, progress, created_at = vendor

        # Log audit event
        cursor.execute("""
            INSERT INTO audit_logs (vendor_id, action, actor, metadata, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            vendor_id,
            'vendor_created',
            contact_email,
            json.dumps({"source": "api", "company_name": company_name}),
            datetime.utcnow()
        ))

        conn.commit()
        cursor.close()
        conn.close()

        # Mock KY3P and SLP submission (for demo)
        ky3p_id = f"KY3P-{str(vendor_id)[:8].upper()}"
        slp_id = f"SLP-{str(vendor_id)[:8].upper()}"

        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'id': str(vendor_id),
                'status': status,
                'onboarding_progress': progress,
                'created_at': created_at.isoformat(),
                'ky3p_assessment_id': ky3p_id,
                'slp_supplier_id': slp_id
            })
        }

    except Exception as e:
        print(f"Error creating vendor: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Failed to create vendor',
                'message': str(e)
            })
        }
