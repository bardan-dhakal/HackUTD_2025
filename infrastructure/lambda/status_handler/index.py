"""
Lambda Function: Get Vendor Status
Retrieves onboarding status and progress for a vendor
"""
import json
import psycopg2
import os
import boto3

secrets_client = boto3.client('secretsmanager')

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
    Get vendor onboarding status

    Response: {
        "vendor_id": "uuid",
        "status": "under_review",
        "onboarding_progress": 65,
        "documents": [
            {"type": "w9", "status": "verified"},
            {"type": "insurance", "status": "processing"}
        ],
        "next_steps": ["Upload Business Continuity Plan", "Complete ESG questionnaire"]
    }
    """
    try:
        # Get vendor ID from path parameters
        vendor_id = event.get('pathParameters', {}).get('id')

        if not vendor_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing vendor ID'})
            }

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get vendor info
        cursor.execute("""
            SELECT id, company_name, status, onboarding_progress,
                   ky3p_assessment_id, slp_supplier_id, created_at
            FROM vendors
            WHERE id = %s
        """, (vendor_id,))

        vendor = cursor.fetchone()
        if not vendor:
            cursor.close()
            conn.close()
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Vendor not found'})
            }

        # Get documents
        cursor.execute("""
            SELECT document_type, status, uploaded_at
            FROM documents
            WHERE vendor_id = %s
            ORDER BY uploaded_at DESC
        """, (vendor_id,))

        documents = [
            {
                'type': row[0],
                'status': row[1],
                'uploaded_at': row[2].isoformat() if row[2] else None
            }
            for row in cursor.fetchall()
        ]

        # Calculate next steps
        doc_types = {d['type'] for d in documents}
        required_docs = {'w9', 'insurance', 'diversity_cert', 'bcp'}
        missing_docs = required_docs - doc_types

        next_steps = []
        if missing_docs:
            next_steps.extend([f"Upload {doc.replace('_', ' ').title()}" for doc in missing_docs])

        cursor.execute("""
            SELECT id FROM esg_questionnaires
            WHERE vendor_id = %s
        """, (vendor_id,))
        if not cursor.fetchone():
            next_steps.append("Complete ESG Questionnaire")

        # Get risk score if available
        cursor.execute("""
            SELECT overall_score
            FROM risk_scores
            WHERE vendor_id = %s
            ORDER BY calculated_at DESC
            LIMIT 1
        """, (vendor_id,))
        risk_row = cursor.fetchone()
        risk_score = risk_row[0] if risk_row else None

        # Get timeline/activity
        cursor.execute("""
            SELECT action, timestamp
            FROM audit_logs
            WHERE vendor_id = %s
            ORDER BY timestamp DESC
            LIMIT 10
        """, (vendor_id,))
        timeline = [
            {
                'title': row[0].replace('_', ' ').title(),
                'timestamp': row[1].isoformat() if row[1] else None
            }
            for row in cursor.fetchall()
        ]

        cursor.close()
        conn.close()

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'vendor_id': str(vendor[0]),
                'company_name': vendor[1],
                'status': vendor[2],
                'onboarding_progress': vendor[3],
                'ky3p_assessment_id': vendor[4],
                'slp_supplier_id': vendor[5],
                'created_at': vendor[6].isoformat() if vendor[6] else None,
                'documents': documents,
                'next_steps': next_steps,
                'risk_score': risk_score,
                'timeline': timeline
            })
        }

    except Exception as e:
        print(f"Error getting vendor status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Failed to get vendor status',
                'message': str(e)
            })
        }
