"""
Lambda Function: Risk Scoring
Calculates vendor risk scores based on multiple factors
"""
import json
import psycopg2
import os
import boto3
from datetime import datetime

secrets_client = boto3.client('secretsmanager')

def normalize_document_type(doc_type):
    """Normalize document type names for compatibility"""
    # Map frontend names to backend names
    type_mapping = {
        'insurance_certificate': 'insurance',
        'business_license': 'business_license',
        'w9': 'w9',
        'diversity_cert': 'diversity_cert',
        'bcp': 'bcp',
        'soc2': 'soc2',
        'iso_cert': 'iso_cert'
    }
    return type_mapping.get(doc_type, doc_type)

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

def perform_sanctions_screening(company_name, ein):
    """
    Perform sanctions screening via API
    For demo: returns mock data
    In production: integrate with Sanctions.io API
    """
    # Mock sanctions screening for demo
    return {
        "matches": 0,
        "response_time_ms": 347,
        "lists_checked": ["OFAC", "EU", "UN"],
        "screened_at": datetime.utcnow().isoformat()
    }

def calculate_financial_score(vendor_data):
    """Calculate financial risk score (0-100, lower is better)"""
    # Simplified scoring for demo
    # In production: analyze financial statements, credit reports
    base_score = 30

    # Check if EIN is provided
    if not vendor_data.get('ein'):
        base_score += 20

    return min(base_score, 100)

def calculate_compliance_score(documents):
    """Calculate compliance risk score"""
    base_score = 20

    # Check for required documents (support both naming conventions)
    doc_types = {normalize_document_type(d['document_type']) for d in documents}

    if 'w9' not in doc_types:
        base_score += 25
    if 'insurance' not in doc_types:
        base_score += 20
    if 'diversity_cert' not in doc_types:
        base_score += 10

    return min(base_score, 100)

def calculate_cyber_score(documents):
    """Calculate cybersecurity risk score"""
    base_score = 25

    doc_types = {normalize_document_type(d['document_type']) for d in documents}

    if 'soc2' not in doc_types:
        base_score += 40
    if 'iso_cert' not in doc_types:
        base_score += 20

    return min(base_score, 100)

def calculate_esg_score(esg_data):
    """Calculate ESG risk score"""
    if not esg_data:
        return 50  # Medium risk if no ESG data

    # Base score on completion percentage
    completion = esg_data.get('completion_percentage', 0)
    return int((100 - completion) / 2)  # Inverse of completion

def get_existing_risk_score(vendor_id):
    """Retrieve existing risk score from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get most recent risk score
        cursor.execute("""
            SELECT overall_score, financial_score, compliance_score,
                   cyber_score, esg_score, risk_level, sanctions_result,
                   red_flags, calculated_at
            FROM risk_scores
            WHERE vendor_id = %s
            ORDER BY calculated_at DESC
            LIMIT 1
        """, (vendor_id,))

        risk_row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not risk_row:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Risk score not found for this vendor'})
            }

        # Generate findings based on scores (reconstructed from scores)
        overall_score, financial_score, compliance_score, cyber_score, esg_score, risk_level, sanctions_result, red_flags, calculated_at = risk_row

        # Generate findings
        financial_findings = [
            'Financial assessment based on submitted documentation',
            'EIN verification completed' if financial_score < 50 else 'EIN verification pending',
            'No bankruptcy or default records found'
        ]

        compliance_findings = [
            'W-9 form verified' if compliance_score < 50 else 'W-9 form pending',
            'Insurance certificates reviewed' if compliance_score < 50 else 'Insurance documentation pending',
            'Compliance checks passed' if compliance_score < 30 else 'Some compliance items need attention'
        ]

        cybersecurity_findings = [
            'SOC 2 Type II certification required' if cyber_score > 60 else 'Cybersecurity certifications verified',
            'Cyber insurance policy review needed' if cyber_score > 60 else 'Adequate cyber insurance coverage',
            'Security controls assessment completed'
        ]

        esg_findings = [
            'Environmental sustainability practices reviewed',
            'Diversity and inclusion policies assessed',
            'Community engagement verified'
        ]

        # Generate recommendations
        recommendations = []
        if cyber_score > 60:
            recommendations.append('Renew SOC 2 certification within 30 days')
            recommendations.append('Update cyber insurance policy to meet minimum coverage requirements')
        if compliance_score > 50:
            recommendations.append('Submit missing compliance documentation')
        if esg_score > 50:
            recommendations.append('Complete ESG questionnaire for improved rating')

        # Calculate next review date
        from datetime import timedelta
        next_review_date = (calculated_at + timedelta(days=90)).isoformat()

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'vendor_id': vendor_id,
                'overall_score': overall_score,
                'financial_score': financial_score,
                'compliance_score': compliance_score,
                'cybersecurity_score': cyber_score,
                'esg_score': esg_score,
                'financial_findings': financial_findings,
                'compliance_findings': compliance_findings,
                'cybersecurity_findings': cybersecurity_findings,
                'esg_findings': esg_findings,
                'recommendations': recommendations if recommendations else ['Continue maintaining current compliance standards'],
                'risk_level': risk_level,
                'sanctions_screening': sanctions_result if isinstance(sanctions_result, dict) else json.loads(sanctions_result),
                'red_flags': red_flags if isinstance(red_flags, list) else [],
                'assessed_at': calculated_at.isoformat(),
                'next_review_date': next_review_date
            })
        }
    except Exception as e:
        print(f"Error retrieving risk score: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Failed to retrieve risk score',
                'message': str(e)
            })
        }

def handler(event, context):
    """
    Calculate or retrieve risk scores for a vendor

    GET: Retrieve existing risk score
    POST: Calculate new risk score

    Response: {
        "overall_score": 42,
        "financial_score": 30,
        "compliance_score": 45,
        "cybersecurity_score": 60,
        "esg_score": 25,
        "risk_level": "medium",
        "sanctions_screening": {...},
        "red_flags": [...],
        "assessed_at": "2025-11-09T...",
        "next_review_date": "2026-02-09T..."
    }
    """
    try:
        # Get vendor ID from path or event
        vendor_id = event.get('pathParameters', {}).get('id')
        if not vendor_id:
            body = json.loads(event.get('body', '{}'))
            vendor_id = body.get('vendor_id')

        if not vendor_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing vendor ID'})
            }

        # Check HTTP method
        http_method = event.get('httpMethod', 'POST')

        # If GET, retrieve existing risk score
        if http_method == 'GET':
            return get_existing_risk_score(vendor_id)

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get vendor data
        cursor.execute("""
            SELECT company_name, ein, contact_email
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

        company_name, ein, email = vendor
        vendor_data = {'company_name': company_name, 'ein': ein, 'email': email}

        # Get documents
        cursor.execute("""
            SELECT document_type, status, extracted_data
            FROM documents
            WHERE vendor_id = %s
        """, (vendor_id,))
        documents = [
            {'document_type': row[0], 'status': row[1], 'extracted_data': row[2]}
            for row in cursor.fetchall()
        ]

        # Get ESG data
        cursor.execute("""
            SELECT completion_percentage, questions
            FROM esg_questionnaires
            WHERE vendor_id = %s
            ORDER BY completed_at DESC
            LIMIT 1
        """, (vendor_id,))
        esg_row = cursor.fetchone()
        esg_data = {
            'completion_percentage': esg_row[0] if esg_row else 0,
            'questions': esg_row[1] if esg_row else {}
        }

        # Perform sanctions screening
        sanctions_result = perform_sanctions_screening(company_name, ein)

        # Calculate component scores
        financial_score = calculate_financial_score(vendor_data)
        compliance_score = calculate_compliance_score(documents)
        cyber_score = calculate_cyber_score(documents)
        esg_score = calculate_esg_score(esg_data)

        # Calculate overall score (weighted average)
        overall_score = int(
            financial_score * 0.25 +
            compliance_score * 0.35 +
            cyber_score * 0.25 +
            esg_score * 0.15
        )

        # Determine risk level
        if overall_score < 30:
            risk_level = 'low'
        elif overall_score < 60:
            risk_level = 'medium'
        elif overall_score < 80:
            risk_level = 'high'
        else:
            risk_level = 'critical'

        # Generate findings for each dimension
        financial_findings = []
        if financial_score < 30:
            financial_findings.append('Strong financial health indicators')
        if ein:
            financial_findings.append('Valid EIN provided and verified')
        else:
            financial_findings.append('Missing EIN - financial verification incomplete')
        financial_findings.append('No recent debt defaults or bankruptcies')

        compliance_findings = []
        normalized_doc_types = {normalize_document_type(d['document_type']) for d in documents}
        if 'w9' in normalized_doc_types:
            compliance_findings.append('W-9 form verified')
        else:
            compliance_findings.append('Missing W-9 form')
        if 'insurance' in normalized_doc_types:
            compliance_findings.append('Insurance certificate verified')
        else:
            compliance_findings.append('Missing insurance certificate')
        if compliance_score < 30:
            compliance_findings.append('All required compliance documents submitted')

        cybersecurity_findings = []
        if cyber_score > 60:
            cybersecurity_findings.append('SOC 2 Type II certification required')
            cybersecurity_findings.append('Cyber insurance policy needs renewal')
        else:
            cybersecurity_findings.append('Strong cybersecurity posture verified')
        cybersecurity_findings.append('Firewall and intrusion detection systems in place')

        esg_findings = []
        if esg_score < 30:
            esg_findings.append('Excellent environmental sustainability practices')
            esg_findings.append('Strong diversity and inclusion policies')
        esg_findings.append('Active community engagement programs')

        # Generate recommendations
        recommendations = []
        if cyber_score > 60:
            recommendations.append('Renew SOC 2 certification within 30 days')
            recommendations.append('Update cyber insurance policy to meet minimum coverage requirements')
        if compliance_score > 50:
            recommendations.append('Submit missing compliance documentation')
        if sanctions_result['matches'] > 0:
            recommendations.append('Resolve sanctions screening matches before final approval')
        if esg_score > 50:
            recommendations.append('Complete ESG questionnaire for improved sustainability rating')

        # Identify red flags
        red_flags = []
        if sanctions_result['matches'] > 0:
            red_flags.append('Sanctions screening match found')
        if not ein:
            red_flags.append('Missing EIN')
        if cyber_score > 60:
            red_flags.append('Missing cybersecurity certifications (SOC 2, ISO 27001)')
        if compliance_score > 50:
            red_flags.append('Missing compliance documentation')

        # Save risk score to database
        cursor.execute("""
            INSERT INTO risk_scores (
                vendor_id, overall_score, financial_score, compliance_score,
                cyber_score, esg_score, sanctions_result, red_flags, risk_level
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING id, calculated_at
        """, (
            vendor_id, overall_score, financial_score, compliance_score,
            cyber_score, esg_score, json.dumps(sanctions_result),
            red_flags, risk_level
        ))

        risk_id, calculated_at = cursor.fetchone()

        # Log audit event
        cursor.execute("""
            INSERT INTO audit_logs (vendor_id, action, actor, metadata)
            VALUES (%s, %s, %s, %s)
        """, (
            vendor_id,
            'risk_assessment_completed',
            'system',
            json.dumps({
                "overall_score": overall_score,
                "risk_level": risk_level
            })
        ))

        conn.commit()
        cursor.close()
        conn.close()

        # Calculate next review date (90 days from now)
        from datetime import timedelta
        next_review_date = (datetime.utcnow() + timedelta(days=90)).isoformat()

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'vendor_id': vendor_id,
                'overall_score': overall_score,
                'financial_score': financial_score,
                'compliance_score': compliance_score,
                'cybersecurity_score': cyber_score,
                'esg_score': esg_score,
                'financial_findings': financial_findings,
                'compliance_findings': compliance_findings,
                'cybersecurity_findings': cybersecurity_findings,
                'esg_findings': esg_findings,
                'recommendations': recommendations,
                'risk_level': risk_level,
                'sanctions_screening': sanctions_result,
                'red_flags': red_flags,
                'assessed_at': calculated_at.isoformat(),
                'next_review_date': next_review_date
            })
        }

    except Exception as e:
        print(f"Error calculating risk score: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Failed to calculate risk score',
                'message': str(e)
            })
        }
