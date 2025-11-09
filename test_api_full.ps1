# Full API integration test
$vendorId = "21120596-0469-4a2e-bdc7-7046ed782c5e"
$apiUrl = "https://x47tqoty73.execute-api.us-east-1.amazonaws.com/prod"

Write-Host "======================================"
Write-Host "Testing Vendor Onboarding API"
Write-Host "======================================"
Write-Host ""

# Test 1: Get Vendor Status
Write-Host "[TEST 1] Get Vendor Status"
Write-Host "Endpoint: GET /vendors/$vendorId/status"
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/vendors/$vendorId/status" `
      -Method GET `
      -ErrorAction Stop

    Write-Host "Status: $($response.StatusCode)"
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
    Write-Host "✅ PASSED`n" -ForegroundColor Green
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 2: Calculate Risk Score
Write-Host "[TEST 2] Calculate Risk Score"
Write-Host "Endpoint: POST /vendors/$vendorId/risk-score"
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/vendors/$vendorId/risk-score" `
      -Method POST `
      -Headers @{'Content-Type'='application/json'} `
      -Body "{}" `
      -ErrorAction Stop

    Write-Host "Status: $($response.StatusCode)"
    $result = $response.Content | ConvertFrom-Json
    Write-Host "Overall Score: $($result.overall_score)"
    Write-Host "Risk Level: $($result.risk_level)"
    Write-Host "✅ PASSED`n" -ForegroundColor Green
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 3: Get Presigned Upload URL
Write-Host "[TEST 3] Get Presigned Upload URL"
Write-Host "Endpoint: POST /documents/upload"
$uploadBody = @{
    vendor_id = $vendorId
    document_type = "w9"
    filename = "w9_form.pdf"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$apiUrl/documents/upload" `
      -Method POST `
      -Headers @{'Content-Type'='application/json'} `
      -Body $uploadBody `
      -ErrorAction Stop

    Write-Host "Status: $($response.StatusCode)"
    $result = $response.Content | ConvertFrom-Json
    Write-Host "Document ID: $($result.document_id)"
    Write-Host "Upload URL provided: $(if ($result.upload_url) { 'Yes' } else { 'No' })"
    Write-Host "✅ PASSED`n" -ForegroundColor Green
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 4: Get Risk Score (retrieve existing)
Write-Host "[TEST 4] Get Existing Risk Score"
Write-Host "Endpoint: GET /vendors/$vendorId/risk-score"
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/vendors/$vendorId/risk-score" `
      -Method GET `
      -ErrorAction Stop

    Write-Host "Status: $($response.StatusCode)"
    $result = $response.Content | ConvertFrom-Json
    Write-Host "Overall Score: $($result.overall_score)"
    Write-Host "Risk Level: $($result.risk_level)"
    Write-Host "✅ PASSED`n" -ForegroundColor Green
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)`n" -ForegroundColor Red
}

Write-Host "======================================"
Write-Host "API Integration Tests Complete"
Write-Host "======================================"
