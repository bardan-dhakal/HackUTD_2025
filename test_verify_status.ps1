# Verify vendor status after approval
$vendorId = "21120596-0469-4a2e-bdc7-7046ed782c5e"
$apiUrl = "https://x47tqoty73.execute-api.us-east-1.amazonaws.com/prod"

Write-Host "Getting updated vendor status after approval..."
$response = Invoke-WebRequest -Uri "$apiUrl/vendors/$vendorId/status" `
  -Method GET `
  -ErrorAction Stop

$result = $response.Content | ConvertFrom-Json
Write-Host ""
Write-Host "Vendor ID: $($result.vendor_id)"
Write-Host "Company: $($result.company_name)"
Write-Host "Status: $($result.status)"
Write-Host "Onboarding Progress: $($result.onboarding_progress)%"
Write-Host ""
Write-Host "✅ Status verification complete"
