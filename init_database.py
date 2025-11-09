#!/usr/bin/env python3
"""
Database Initialization Script
Connects to RDS, creates schema, and seeds sample data
"""

import boto3
import psycopg2
import json
import sys
from pathlib import Path

# Configuration
DB_HOST = "onboardinghubdatabasestack-vendordatabase6a1ca1c3-akncbtikc7zq.cs1oouckekys.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "onboarding_hub"
DB_USER = "postgres"
REGION = "us-east-1"
SECRET_ID = "arn:aws:secretsmanager:us-east-1:560271561576:secret:DbCredentialsSecret4110FA1D-22P18mgcfwIb"

# Schema and seed files
SCHEMA_FILE = Path(__file__).parent / "infrastructure" / "database" / "schema.sql"
SEED_FILE = Path(__file__).parent / "infrastructure" / "database" / "seed.sql"

def get_db_password():
    """Retrieve database password from AWS Secrets Manager"""
    print("[*] Retrieving database password from Secrets Manager...")
    try:
        client = boto3.client('secretsmanager', region_name=REGION)
        response = client.get_secret_value(SecretId=SECRET_ID)
        secret = json.loads(response['SecretString'])
        password = secret['password']
        print("[OK] Password retrieved successfully")
        return password
    except Exception as e:
        print(f"[FAIL] Failed to retrieve password: {e}")
        sys.exit(1)

def connect_to_database(password):
    """Connect to RDS PostgreSQL database"""
    print(f"\n[*] Connecting to database at {DB_HOST}:{DB_PORT}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=password
        )
        print("[OK] Connected successfully!")
        return conn
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        sys.exit(1)

def execute_sql_file(conn, filepath, description):
    """Execute SQL script from file"""
    print(f"\n[*] {description}...")
    try:
        with open(filepath, 'r') as f:
            sql_script = f.read()

        cursor = conn.cursor()
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]

        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                conn.commit()
            except Exception as e:
                # Some statements might fail if they already exist (which is OK)
                if "already exists" in str(e) or "ALREADY EXISTS" in str(e):
                    print(f"   [~] Statement {i}: Already exists (skipping)")
                else:
                    print(f"   [!] Statement {i}: {e}")

        print(f"[OK] {description} completed")
        cursor.close()
    except FileNotFoundError:
        print(f"[FAIL] File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Error executing SQL: {e}")
        sys.exit(1)

def verify_tables(conn):
    """Verify all tables were created"""
    print("\n[*] Verifying tables...")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        expected_tables = [
            'vendors',
            'documents',
            'risk_scores',
            'esg_questionnaires',
            'audit_logs',
            'approval_workflows'
        ]

        found_tables = [table[0] for table in tables]

        print(f"\n[+] Found {len(found_tables)} tables:")
        for table in found_tables:
            status = "OK" if table in expected_tables else "?"
            print(f"    [{status}] {table}")

        missing = set(expected_tables) - set(found_tables)
        if missing:
            print(f"\n[!] Missing tables: {missing}")
            return False

        # Count sample data
        cursor.execute("SELECT COUNT(*) FROM vendors;")
        vendor_count = cursor.fetchone()[0]
        print(f"\n[+] Sample data:")
        print(f"    [{'OK' if vendor_count > 0 else 'FAIL'}] Vendors: {vendor_count}")

        cursor.execute("SELECT COUNT(*) FROM documents;")
        doc_count = cursor.fetchone()[0]
        print(f"    [{'OK' if doc_count > 0 else 'FAIL'}] Documents: {doc_count}")

        cursor.execute("SELECT COUNT(*) FROM risk_scores;")
        risk_count = cursor.fetchone()[0]
        print(f"    [{'OK' if risk_count > 0 else 'FAIL'}] Risk Scores: {risk_count}")

        cursor.close()
        return True
    except Exception as e:
        print(f"[FAIL] Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("="*60)
    print("Database Initialization Script")
    print("="*60)

    # Step 1: Get password
    password = get_db_password()

    # Step 2: Connect
    conn = connect_to_database(password)

    # Step 3: Execute schema
    execute_sql_file(conn, SCHEMA_FILE, "Creating database schema")

    # Step 4: Execute seed data
    execute_sql_file(conn, SEED_FILE, "Seeding sample data")

    # Step 5: Verify
    success = verify_tables(conn)

    # Cleanup
    conn.close()

    print("\n" + "="*60)
    if success:
        print("[OK] Database initialization completed successfully!")
        print("="*60)
        return 0
    else:
        print("[FAIL] Database initialization had issues")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
