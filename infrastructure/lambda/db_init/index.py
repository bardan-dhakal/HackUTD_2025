"""
Database Initialization Lambda Function
Initializes RDS schema and seeds sample data
This function runs inside the VPC and has network access to the RDS database
"""

import boto3
import psycopg2
import json
import os
from psycopg2 import sql

# Environment variables (set by CDK)
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'onboarding_hub')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_SECRET_ARN = os.environ.get('DB_SECRET_ARN')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

def get_db_password():
    """Retrieve database password from AWS Secrets Manager"""
    try:
        client = boto3.client('secretsmanager', region_name=REGION)
        response = client.get_secret_value(SecretId=DB_SECRET_ARN)
        secret = json.loads(response['SecretString'])
        return secret['password']
    except Exception as e:
        print(f"Error retrieving password: {e}")
        raise

def connect_to_database(password):
    """Connect to RDS PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=password
        )
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

def read_sql_file(filename):
    """Read SQL file from Lambda deployment package"""
    try:
        # Lambda has the infrastructure folder in /var/task due to CDK packaging
        # We'll receive the SQL content as part of environment or embedded
        return None  # We'll pass SQL content directly instead
    except Exception as e:
        print(f"Error reading SQL file: {e}")
        return None

def execute_sql_statements(conn, statements, description):
    """Execute SQL statements safely"""
    cursor = conn.cursor()
    try:
        for i, statement in enumerate(statements, 1):
            if not statement.strip():
                continue
            try:
                cursor.execute(statement)
                conn.commit()
                print(f"[OK] Statement {i} executed")
            except Exception as e:
                # Some statements might fail if they already exist
                if "already exists" in str(e).lower():
                    print(f"[~] Statement {i}: Already exists (skipping)")
                    conn.commit()  # Commit to clear the error state
                else:
                    print(f"[!] Statement {i}: {e}")
                    conn.rollback()
        print(f"[OK] {description} completed")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        cursor.close()

def verify_tables(conn):
    """Verify tables were created"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        found_tables = [table[0] for table in tables]

        expected_tables = [
            'vendors',
            'documents',
            'risk_scores',
            'esg_questionnaires',
            'audit_logs',
            'approval_workflows'
        ]

        print(f"[+] Found {len(found_tables)} tables: {found_tables}")

        # Count sample data
        cursor.execute("SELECT COUNT(*) FROM vendors;")
        vendor_count = cursor.fetchone()[0]
        print(f"[+] Vendors in database: {vendor_count}")

        missing = set(expected_tables) - set(found_tables)
        return len(missing) == 0 and vendor_count > 0

    except Exception as e:
        print(f"Verification error: {e}")
        return False
    finally:
        cursor.close()

def handler(event, context):
    """Lambda handler for database initialization"""
    print("Starting database initialization...")

    try:
        # Get database password
        password = get_db_password()
        print("[OK] Retrieved database password")

        # Connect to database
        conn = connect_to_database(password)
        print(f"[OK] Connected to database at {DB_HOST}:{DB_PORT}")

        # SCHEMA SQL STATEMENTS
        schema_sql = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    ein VARCHAR(20),
    address TEXT,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    status VARCHAR(50) DEFAULT 'submitted' CHECK (status IN ('submitted', 'documents_pending', 'under_review', 'risk_assessment', 'approved', 'rejected', 'onboarding_complete')),
    onboarding_progress INT DEFAULT 0 CHECK (onboarding_progress >= 0 AND onboarding_progress <= 100),
    ky3p_assessment_id VARCHAR(100),
    slp_supplier_id VARCHAR(100),
    ariba_account_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vendors_status ON vendors(status);
CREATE INDEX idx_vendors_created_at ON vendors(created_at);
CREATE INDEX idx_vendors_email ON vendors(contact_email);
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN ('w9', 'insurance', 'diversity_cert', 'bcp', 'soc2', 'iso_cert', 'financial_stmt', 'other')),
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'extracted', 'verified', 'failed')),
    extracted_data JSONB,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);
CREATE INDEX idx_documents_vendor ON documents(vendor_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE TABLE risk_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    overall_score INT CHECK (overall_score >= 0 AND overall_score <= 100),
    financial_score INT CHECK (financial_score >= 0 AND financial_score <= 100),
    compliance_score INT CHECK (compliance_score >= 0 AND compliance_score <= 100),
    cyber_score INT CHECK (cyber_score >= 0 AND cyber_score <= 100),
    esg_score INT CHECK (esg_score >= 0 AND esg_score <= 100),
    sanctions_result JSONB,
    red_flags TEXT[],
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
CREATE INDEX idx_risk_scores_vendor ON risk_scores(vendor_id);
CREATE INDEX idx_risk_scores_overall ON risk_scores(overall_score);
CREATE INDEX idx_risk_scores_level ON risk_scores(risk_level);
CREATE TABLE esg_questionnaires (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    questions JSONB NOT NULL,
    auto_filled BOOLEAN DEFAULT FALSE,
    total_questions INT,
    answered_questions INT,
    completion_percentage DECIMAL(5,2),
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(255)
);
CREATE INDEX idx_esg_vendor ON esg_questionnaires(vendor_id);
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID,
    action VARCHAR(100) NOT NULL,
    actor VARCHAR(255),
    actor_ip VARCHAR(50),
    metadata JSONB,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_vendor ON audit_logs(vendor_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_actor ON audit_logs(actor);
CREATE TABLE approval_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    current_step VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'escalated')),
    required_approvers TEXT[],
    completed_approvals JSONB,
    final_decision BOOLEAN,
    decision_comments TEXT,
    decision_by VARCHAR(255),
    decision_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_approval_vendor ON approval_workflows(vendor_id);
CREATE INDEX idx_approval_status ON approval_workflows(status);
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END; $$ language 'plpgsql';
CREATE TRIGGER update_vendors_updated_at BEFORE UPDATE ON vendors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_approval_workflows_updated_at BEFORE UPDATE ON approval_workflows FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE VIEW vendor_dashboard AS SELECT v.id, v.company_name, v.contact_email, v.status, v.onboarding_progress, v.created_at, COUNT(DISTINCT d.id) as document_count, COUNT(DISTINCT CASE WHEN d.status = 'verified' THEN d.id END) as verified_documents, rs.overall_score as risk_score, rs.risk_level, rs.calculated_at as risk_assessed_at FROM vendors v LEFT JOIN documents d ON v.id = d.vendor_id LEFT JOIN risk_scores rs ON v.id = rs.vendor_id GROUP BY v.id, rs.overall_score, rs.risk_level, rs.calculated_at;
CREATE VIEW high_risk_vendors AS SELECT v.*, rs.overall_score, rs.red_flags, rs.calculated_at FROM vendors v INNER JOIN risk_scores rs ON v.id = rs.vendor_id WHERE rs.risk_level IN ('high', 'critical') AND v.status NOT IN ('rejected', 'approved') ORDER BY rs.overall_score DESC;
        """

        # SEED SQL STATEMENTS - Minimal seeding
        seed_sql = """
INSERT INTO vendors (company_name, ein, address, contact_email, contact_phone, status, onboarding_progress, created_at) VALUES
('TechVendor Inc', '12-3456789', '123 Silicon Valley, CA', 'contact@techvendor.com', '+1-650-555-0100', 'submitted', 25, NOW());
INSERT INTO vendors (company_name, ein, address, contact_email, contact_phone, status, onboarding_progress, created_at) VALUES
('EcoFriendly Products', '23-4567890', '321 Green Lane, OR', 'contact@ecofriendly.com', '+1-503-555-0400', 'submitted', 0, NOW());
        """

        # Execute schema
        schema_statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        execute_sql_statements(conn, schema_statements, "Creating database schema")

        # Execute seed data
        seed_statements = [stmt.strip() for stmt in seed_sql.split(';') if stmt.strip()]
        execute_sql_statements(conn, seed_statements, "Seeding sample data")

        # Verify
        success = verify_tables(conn)

        conn.close()

        if success:
            print("[OK] Database initialization completed successfully")
            return {
                'statusCode': 200,
                'body': json.dumps('Database initialized successfully')
            }
        else:
            print("[FAIL] Database initialization had issues")
            return {
                'statusCode': 500,
                'body': json.dumps('Database initialization failed verification')
            }

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

if __name__ == "__main__":
    # For local testing (not used in Lambda)
    handler({}, {})
