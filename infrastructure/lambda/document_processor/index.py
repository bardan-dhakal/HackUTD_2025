"""
Lambda Function: Document Processor with AWS Textract
Processes uploaded documents using AWS Textract for OCR
Extracts key information and stores results in database
"""
import json
import boto3
import psycopg2
import os
from datetime import datetime
import time

textract_client = boto3.client('textract', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

def get_db_connection():
    """Get database connection using Secrets Manager credentials"""
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

def extract_text_with_textract(s3_bucket, s3_key, document_type):
    """
    Use AWS Textract to extract text and structured data from document

    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        document_type: Type of document (w9, insurance, etc.)

    Returns:
        dict: Extracted data with text, forms, tables, confidence scores
    """
    try:
        print(f"Starting Textract analysis for {document_type}")

        # Start document analysis
        response = textract_client.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': s3_bucket,
                    'Name': s3_key
                }
            },
            ClientRequestToken=f"{s3_key.replace('/', '_')}_{int(time.time())}",
            FeatureTypes=[
                'TABLES',
                'FORMS'
            ]
        )

        job_id = response['JobId']
        print(f"Textract job started: {job_id}")

        # Poll for job completion (max 30 seconds)
        max_attempts = 60
        attempt = 0

        while attempt < max_attempts:
            try:
                result = textract_client.get_document_analysis(JobId=job_id)
                job_status = result['JobStatus']

                if job_status == 'SUCCEEDED':
                    print(f"Textract job completed successfully")
                    return parse_textract_response(result, document_type)
                elif job_status == 'FAILED':
                    print(f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}")
                    return {
                        'error': 'Textract processing failed',
                        'status_message': result.get('StatusMessage', 'Unknown error'),
                        'confidence': 0
                    }

                # Still processing, wait and retry
                time.sleep(0.5)
                attempt += 1

            except textract_client.exceptions.InvalidJobId:
                print(f"Invalid job ID: {job_id}")
                return {'error': 'Invalid job ID', 'confidence': 0}

        return {
            'error': 'Textract processing timeout',
            'confidence': 0
        }

    except Exception as e:
        print(f"Error during Textract analysis: {str(e)}")
        return {
            'error': f'Textract error: {str(e)}',
            'confidence': 0
        }

def parse_textract_response(response, document_type):
    """
    Parse Textract response and extract relevant data

    Returns:
        dict: Structured extracted data
    """
    blocks = response.get('Blocks', [])
    extracted_data = {
        'document_type': document_type,
        'extracted_text': [],
        'key_value_pairs': {},
        'tables': [],
        'confidence_scores': [],
        'extraction_timestamp': datetime.utcnow().isoformat(),
        'textract_job_id': response.get('JobId')
    }

    # Extract text blocks
    for block in blocks:
        if block['BlockType'] == 'LINE':
            text = block.get('Text', '')
            confidence = block.get('Confidence', 0)
            extracted_data['extracted_text'].append({
                'text': text,
                'confidence': confidence
            })
            extracted_data['confidence_scores'].append(confidence)

        elif block['BlockType'] == 'KEY_VALUE_SET':
            if block.get('EntityTypes', [None])[0] == 'KEY':
                key_text = block.get('Text', 'Unknown')
                # Find associated value
                for relationship in block.get('Relationships', []):
                    if relationship['Type'] == 'VALUE':
                        for value_block in blocks:
                            if value_block['Id'] == relationship['Ids'][0]:
                                value_text = value_block.get('Text', '')
                                extracted_data['key_value_pairs'][key_text] = {
                                    'value': value_text,
                                    'confidence': value_block.get('Confidence', 0)
                                }

        elif block['BlockType'] == 'TABLE':
            # Store table ID for reference
            table_data = {
                'table_id': block['Id'],
                'rows': 0,
                'columns': 0,
                'content': []
            }

            # Count rows and columns
            for rel in block.get('Relationships', []):
                if rel['Type'] == 'CHILD':
                    table_data['rows'] += 1

            extracted_data['tables'].append(table_data)

    # Calculate average confidence
    if extracted_data['confidence_scores']:
        avg_confidence = sum(extracted_data['confidence_scores']) / len(extracted_data['confidence_scores'])
        extracted_data['average_confidence'] = round(avg_confidence, 2)
    else:
        extracted_data['average_confidence'] = 0

    # Document-specific extraction based on type
    extracted_data['document_specific_fields'] = extract_document_specific_fields(
        extracted_data, document_type
    )

    return extracted_data

def extract_document_specific_fields(extracted_data, document_type):
    """
    Extract document-specific fields based on document type
    """
    specific_fields = {
        'w9': extract_w9_fields,
        'insurance': extract_insurance_fields,
        'diversity_cert': extract_diversity_fields,
        'bcp': extract_bcp_fields,
        'soc2': extract_soc2_fields,
        'iso_cert': extract_iso_fields
    }

    extractor = specific_fields.get(document_type, extract_generic_fields)
    return extractor(extracted_data)

def extract_w9_fields(extracted_data):
    """Extract W-9 specific fields"""
    kvp = extracted_data['key_value_pairs']
    return {
        'tin': extract_value_like(kvp, ['TIN', 'Tax ID', 'EIN', 'SSN']),
        'entity_type': extract_value_like(kvp, ['Entity Type', 'Business Type']),
        'business_name': extract_value_like(kvp, ['Business Name', 'Name']),
        'address': extract_value_like(kvp, ['Address', 'Street Address']),
        'city_state_zip': extract_value_like(kvp, ['City', 'State', 'ZIP', 'Postal Code']),
        'signature': check_signature(extracted_data['extracted_text']),
        'date_signed': extract_date(extracted_data['extracted_text'])
    }

def extract_insurance_fields(extracted_data):
    """Extract Insurance Certificate specific fields"""
    kvp = extracted_data['key_value_pairs']
    return {
        'policy_holder': extract_value_like(kvp, ['Insured', 'Policy Holder', 'Company Name']),
        'policy_number': extract_value_like(kvp, ['Policy Number', 'Policy #']),
        'insurance_company': extract_value_like(kvp, ['Insurance Company', 'Insurer', 'Carrier']),
        'coverage_types': extract_coverage_types(extracted_data['extracted_text']),
        'coverage_limits': extract_coverage_limits(extracted_data['key_value_pairs']),
        'effective_date': extract_date_from_text(extracted_data['extracted_text'], 'effective'),
        'expiration_date': extract_date_from_text(extracted_data['extracted_text'], 'expir'),
        'certificate_holder': extract_value_like(kvp, ['Certificate Holder', 'Additional Insured'])
    }

def extract_diversity_fields(extracted_data):
    """Extract Diversity Certification specific fields"""
    kvp = extracted_data['key_value_pairs']
    return {
        'certification_type': extract_value_like(kvp, ['Certification Type', 'MBE', 'WBE', 'DBE']),
        'certified_organization': extract_value_like(kvp, ['Certified By', 'Issuer']),
        'cert_number': extract_value_like(kvp, ['Certification Number', 'Cert #']),
        'issue_date': extract_date(extracted_data['extracted_text']),
        'expiration_date': extract_date_from_text(extracted_data['extracted_text'], 'expir'),
        'scope_of_certification': extract_value_like(kvp, ['Scope', 'Services'])
    }

def extract_bcp_fields(extracted_data):
    """Extract Business Continuity Plan specific fields"""
    kvp = extracted_data['key_value_pairs']
    return {
        'recovery_time_objective': extract_value_like(kvp, ['RTO', 'Recovery Time']),
        'recovery_point_objective': extract_value_like(kvp, ['RPO', 'Recovery Point']),
        'backup_location': extract_value_like(kvp, ['Backup', 'Backup Location']),
        'disaster_recovery': check_contains(extracted_data['extracted_text'], ['disaster recovery', 'contingency plan']),
        'last_tested': extract_date_from_text(extracted_data['extracted_text'], 'test')
    }

def extract_soc2_fields(extracted_data):
    """Extract SOC 2 Report specific fields"""
    kvp = extracted_data['key_value_pairs']
    return {
        'report_type': extract_value_like(kvp, ['Type I', 'Type II']),
        'service_auditor': extract_value_like(kvp, ['Auditor', 'Service Auditor']),
        'report_period_start': extract_date_from_text(extracted_data['extracted_text'], 'from'),
        'report_period_end': extract_date_from_text(extracted_data['extracted_text'], 'to'),
        'opinion': check_contains(extracted_data['extracted_text'], ['opinion', 'complied']),
        'controls_tested': extract_value_like(kvp, ['Controls', 'Testing'])
    }

def extract_iso_fields(extracted_data):
    """Extract ISO Certification specific fields"""
    kvp = extracted_data['key_value_pairs']
    return {
        'iso_standard': extract_value_like(kvp, ['ISO', 'Standard']),
        'issuing_body': extract_value_like(kvp, ['Issued By', 'Accredited By']),
        'cert_number': extract_value_like(kvp, ['Certification Number', 'Number']),
        'issue_date': extract_date(extracted_data['extracted_text']),
        'expiration_date': extract_date_from_text(extracted_data['extracted_text'], 'expir'),
        'scope': extract_value_like(kvp, ['Scope', 'Services Covered'])
    }

def extract_generic_fields(extracted_data):
    """Extract generic fields for unknown document types"""
    return {
        'text_extracted': len(extracted_data['extracted_text']) > 0,
        'tables_found': len(extracted_data['tables']),
        'key_value_pairs_found': len(extracted_data['key_value_pairs'])
    }

def extract_value_like(kvp, keys):
    """Find value matching any of the given keys"""
    for key in keys:
        for kvp_key, kvp_value in kvp.items():
            if key.lower() in kvp_key.lower():
                return kvp_value.get('value', '')
    return None

def extract_coverage_types(text_blocks):
    """Extract insurance coverage types from text"""
    coverage_keywords = {
        'general_liability': ['general liability', 'GL coverage'],
        'workers_compensation': ['workers comp', 'workers\'s compensation'],
        'professional_liability': ['professional liability', 'errors & omissions', 'E&O'],
        'cyber_liability': ['cyber liability', 'cyber insurance'],
        'umbrella': ['umbrella', 'excess liability']
    }

    full_text = ' '.join([block['text'].lower() for block in text_blocks])
    found_coverage = {}

    for coverage_type, keywords in coverage_keywords.items():
        for keyword in keywords:
            if keyword in full_text:
                found_coverage[coverage_type] = True
                break

    return found_coverage

def extract_coverage_limits(kvp):
    """Extract coverage limits from key-value pairs"""
    limits = {}
    for key, value_obj in kvp.items():
        if 'limit' in key.lower() or 'coverage' in key.lower():
            limits[key] = value_obj.get('value', '')
    return limits

def extract_date(text_blocks):
    """Extract first date found in text blocks"""
    import re
    date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}-\d{1,2}-\d{2,4}'

    for block in text_blocks:
        match = re.search(date_pattern, block.get('text', ''))
        if match:
            return match.group(0)
    return None

def extract_date_from_text(text_blocks, prefix):
    """Extract date that follows a specific prefix"""
    import re
    full_text = ' '.join([block.get('text', '') for block in text_blocks])

    # Find text containing prefix and extract following date
    pattern = rf'{prefix}[^0-9]*(\d{{1,2}}/\d{{1,2}}/\d{{2,4}})'
    match = re.search(pattern, full_text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def check_signature(text_blocks):
    """Check if document appears to be signed"""
    signature_keywords = ['signature', 'signed', 'authorized', 'approved', 'accepted']
    full_text = ' '.join([block.get('text', '').lower() for block in text_blocks])

    return any(keyword in full_text for keyword in signature_keywords)

def check_contains(text_blocks, keywords):
    """Check if text contains any of the given keywords"""
    full_text = ' '.join([block.get('text', '').lower() for block in text_blocks])
    return any(keyword in full_text for keyword in keywords)

def update_document_status(document_id, vendor_id, status, extracted_data):
    """Update document status and extracted data in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE documents
            SET status = %s,
                extracted_data = %s::jsonb,
                processed_at = NOW()
            WHERE id = %s AND vendor_id = %s
            RETURNING id, status
        """, (
            status,
            json.dumps(extracted_data),
            document_id,
            vendor_id
        ))

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        if result:
            print(f"Document {document_id} updated with status: {status}")
            return True
        else:
            print(f"Document {document_id} not found or update failed")
            return False

    except Exception as e:
        print(f"Error updating document status: {str(e)}")
        return False

def handler(event, context):
    """
    Lambda handler triggered by S3 document upload events

    Event from S3:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "bucket-name"},
                "object": {"key": "path/to/file"}
            }
        }]
    }

    Or direct invocation:
    {
        "vendor_id": "uuid",
        "document_id": "uuid",
        "s3_bucket": "bucket-name",
        "s3_key": "path/to/file",
        "document_type": "w9"
    }
    """
    try:
        print(f"Processing document: {json.dumps(event)}")

        # Parse event (handle both S3 and direct invocation)
        if 'Records' in event:
            # S3 event
            record = event['Records'][0]
            s3_bucket = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']

            # Extract vendor_id and document_id from S3 key
            # Format: vendors/{vendor_id}/{document_type}/{document_id}/{filename}
            path_parts = s3_key.split('/')
            vendor_id = path_parts[1] if len(path_parts) > 1 else None
            document_type = path_parts[2] if len(path_parts) > 2 else 'other'
            document_id = path_parts[3] if len(path_parts) > 3 else None

        else:
            # Direct invocation
            vendor_id = event.get('vendor_id')
            document_id = event.get('document_id')
            s3_bucket = event.get('s3_bucket')
            s3_key = event.get('s3_key')
            document_type = event.get('document_type', 'other')

        if not all([vendor_id, document_id, s3_bucket, s3_key]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }

        print(f"Document: {document_id}, Type: {document_type}, Vendor: {vendor_id}")

        # Update status to 'processing'
        update_document_status(document_id, vendor_id, 'processing', {'status': 'processing'})

        # Extract text and data using Textract
        extracted_data = extract_text_with_textract(s3_bucket, s3_key, document_type)

        # Update status to 'extracted' with results
        success = update_document_status(
            document_id,
            vendor_id,
            'extracted',
            extracted_data
        )

        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Document processed successfully',
                    'document_id': document_id,
                    'vendor_id': vendor_id,
                    'status': 'extracted',
                    'confidence': extracted_data.get('average_confidence', 0)
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to update document status'
                })
            }

    except Exception as e:
        print(f"Error processing document: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process document',
                'message': str(e)
            })
        }
