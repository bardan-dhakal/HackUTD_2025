# Configure S3 event notifications to trigger DocumentProcessor Lambda

$bucketName = "onboardinghubstoragestack-vendordocumentbucket0e7c-kgvdteuuvehh"
$lambdaArn = "arn:aws:lambda:us-east-1:560271561576:function:OnboardingHubLambdaStack-DocumentProcessor3D49A083-jyyz7GgBTIZj"
$region = "us-east-1"

Write-Host "Setting up S3 event notifications..."
Write-Host "Bucket: $bucketName"
Write-Host "Lambda: $lambdaArn"
Write-Host ""

# Step 1: Grant S3 permission to invoke Lambda
Write-Host "[1] Granting S3 permission to invoke Lambda..."
$cmd = @"
& 'C:\Program Files\Amazon\AWSCLIV2\aws.exe' lambda add-permission --function-name $lambdaArn --principal s3.amazonaws.com --action lambda:InvokeFunction --statement-id AllowS3Invoke --source-arn "arn:aws:s3:::$bucketName" --region $region 2>&1
"@
Invoke-Expression $cmd | Out-Null
Write-Host "✓ Permission configured"

# Step 2: Create notification configuration JSON
Write-Host "[2] Configuring S3 event notifications..."

$config = @"
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "$lambdaArn",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            { "Name": "prefix", "Value": "vendors/" },
            { "Name": "suffix", "Value": ".pdf" }
          ]
        }
      }
    },
    {
      "LambdaFunctionArn": "$lambdaArn",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            { "Name": "prefix", "Value": "vendors/" },
            { "Name": "suffix", "Value": ".jpg" }
          ]
        }
      }
    },
    {
      "LambdaFunctionArn": "$lambdaArn",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            { "Name": "prefix", "Value": "vendors/" },
            { "Name": "suffix", "Value": ".jpeg" }
          ]
        }
      }
    },
    {
      "LambdaFunctionArn": "$lambdaArn",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            { "Name": "prefix", "Value": "vendors/" },
            { "Name": "suffix", "Value": ".png" }
          ]
        }
      }
    }
  ]
}
"@

$tempFile = "$env:TEMP\s3-notification-$([System.DateTime]::Now.Ticks).json"
Set-Content -Path $tempFile -Value $config

# Apply configuration
$cmd2 = @"
& 'C:\Program Files\Amazon\AWSCLIV2\aws.exe' s3api put-bucket-notification-configuration --bucket $bucketName --notification-configuration file://$tempFile --region $region 2>&1
"@
Invoke-Expression $cmd2 | Out-Null
Write-Host "✓ Notification configuration applied"

# Step 3: Verify
Write-Host "[3] Verifying configuration..."
& 'C:\Program Files\Amazon\AWSCLIV2\aws.exe' s3api get-bucket-notification-configuration --bucket $bucketName --region $region 2>&1 | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Cleanup
Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================"
Write-Host "✓ S3 Event Notifications Configured"
Write-Host "========================================"
Write-Host ""
Write-Host "Triggers configured for:"
Write-Host "- *.pdf files in vendors/ folder"
Write-Host "- *.jpg files in vendors/ folder"
Write-Host "- *.jpeg files in vendors/ folder"
Write-Host "- *.png files in vendors/ folder"
Write-Host ""
Write-Host "Next: Upload a document to test OCR"
