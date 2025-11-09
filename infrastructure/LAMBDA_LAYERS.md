# Lambda Layers Setup - psycopg2

## Problem

The Lambda functions require `psycopg2` to connect to PostgreSQL RDS. However, psycopg2 has C dependencies and cannot be bundled directly with Lambda function code. It must be provided as a Lambda Layer.

## Solution Options

### Option 1: Use Public psycopg2 Layer (Fastest)

Use a pre-built public layer from AWS community:

```bash
# For Python 3.11 (recommended)
arn:aws:lambda:us-east-1:898466741470:layer:psycopg2-py311:1

# For Python 3.9 (if using older runtime)
arn:aws:lambda:us-east-1:898466741470:layer:psycopg2-py39:1
```

**Steps:**
1. Go to AWS Lambda Console
2. Navigate to each Lambda function (create_vendor, status_handler, risk_scoring, approve_vendor, db_init)
3. Scroll to "Layers" section → Click "Add a layer"
4. Select "Specify an ARN"
5. Paste the ARN above
6. Click "Add"

### Option 2: Build Your Own Layer

If you prefer to build and control your own layer:

#### On Linux/Mac:

```bash
# Create directory structure
mkdir -p psycopg2-layer/python/lib/python3.11/site-packages

# Install psycopg2-binary (pre-compiled version)
pip install psycopg2-binary -t psycopg2-layer/python/lib/python3.11/site-packages

# Create zip file
cd psycopg2-layer
zip -r ../psycopg2-layer.zip python/
cd ..

# Upload to AWS Lambda Layers (via Console or CLI)
aws lambda publish-layer-version \
    --layer-name psycopg2-layer \
    --description "PostgreSQL adapter for Python" \
    --zip-file fileb://psycopg2-layer.zip \
    --compatible-runtimes python3.11 \
    --region us-east-1
```

#### On Windows:

```powershell
# Use Docker to build for Lambda runtime
docker run --rm -v ${PWD}:/var/task public.ecr.aws/lambda/python:3.11 `
    pip install psycopg2-binary -t /var/task/python/lib/python3.11/site-packages

# Zip the python directory
Compress-Archive -Path python -DestinationPath psycopg2-layer.zip

# Upload via AWS CLI or Console
aws lambda publish-layer-version `
    --layer-name psycopg2-layer `
    --description "PostgreSQL adapter for Python" `
    --zip-file fileb://psycopg2-layer.zip `
    --compatible-runtimes python3.11 `
    --region us-east-1
```

### Option 3: Add to CDK Stack (Most Automated)

Update `lambda_stack.py` to programmatically create the layer:

```python
from aws_cdk import (
    aws_lambda as lambda_,
    # ... other imports
)

# Create psycopg2 layer (in __init__ method)
psycopg2_layer = lambda_.LayerVersion(
    self, "Psycopg2Layer",
    code=lambda_.Code.from_asset("../layers/psycopg2"),
    compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
    description="PostgreSQL adapter for Python (psycopg2)"
)

# Then add to each function:
self.create_vendor_handler = lambda_.Function(
    self, "CreateVendorHandler",
    # ... other config
    layers=[psycopg2_layer],  # Add this line
)
```

Then prepare the layer directory:
```bash
mkdir -p infrastructure/layers/psycopg2/python/lib/python3.11/site-packages
pip install psycopg2-binary -t infrastructure/layers/psycopg2/python/lib/python3.11/site-packages
```

## Affected Lambda Functions

The following Lambda functions require the psycopg2 layer:
- ✅ `create_vendor` - Creates vendor records in RDS
- ✅ `status_handler` - Queries vendor status from RDS
- ✅ `risk_scoring` - Reads/writes risk scores to RDS
- ✅ `approve_vendor` - Updates vendor approval status in RDS
- ✅ `db_init` - Initializes database schema and seed data

⚠️ **Important:** The `upload_handler` function does NOT need psycopg2 (only uses S3).

## Verification

After adding the layer, test each function:

```bash
# Test via AWS CLI
aws lambda invoke \
    --function-name CreateVendorHandler \
    --payload '{"body": "{\"company_name\": \"Test Corp\", \"contact_email\": \"test@test.com\"}"}' \
    response.json

# Check response
cat response.json
```

If the layer is working correctly, you should see a successful response instead of:
```json
{"errorType": "Runtime.ImportModuleError", "errorMessage": "Unable to import module 'index': No module named 'psycopg2'"}
```

## Alternative: Use psycopg2-binary in Lambda

If you absolutely cannot use layers, you can try bundling psycopg2-binary directly:

```bash
# In each Lambda function directory
pip install psycopg2-binary -t .
```

However, this approach:
- Increases deployment package size
- May have compatibility issues
- Is less maintainable than layers

**Recommendation:** Use Option 1 (public layer) for simplicity.

## References

- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [Public Lambda Layers Repository](https://github.com/keithrozario/Klayers)
