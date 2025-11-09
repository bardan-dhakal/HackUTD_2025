# Test approval endpoint
$vendorId = "21120596-0469-4a2e-bdc7-7046ed782c5e"
$apiUrl = "https://x47tqoty73.execute-api.us-east-1.amazonaws.com/prod"

Write-Host "======================================"
Write-Host "Testing Vendor Approval API"
Write-Host "======================================"
Write-Host ""

# Prepare approval request
$approvalBody = @{
    approved = $true
    comments = "All compliance requirements met. Risk assessment complete."
    approver_email = "approver@gs.com"
} | ConvertTo-Json

Write-Host "[TEST] Approve Vendor"
Write-Host "Endpoint: POST /vendors/$vendorId/approve"
Write-Host "Request:"
Write-Host $approvalBody

try {
    $response = Invoke-WebRequest -Uri "$apiUrl/vendors/$vendorId/approve" `
      -Method POST `
      -Headers @{'Content-Type'='application/json'} `
      -Body $approvalBody `
      -ErrorAction Stop

    Write-Host ""
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Response:"
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
    Write-Host ""
    Write-Host "✅ PASSED" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "❌ FAILED" -ForegroundColor Red
}
