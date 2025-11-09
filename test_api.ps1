# Test vendor creation API
$body = @{
    company_name = 'Test Vendor Corp'
    contact_email = 'test@vendor.com'
    ein = '12-3456789'
    address = '123 Test St, Test City, TX 75001'
    contact_phone = '+1-555-123-4567'
} | ConvertTo-Json

Write-Host "Sending request body:"
Write-Host $body

$response = Invoke-WebRequest -Uri 'https://x47tqoty73.execute-api.us-east-1.amazonaws.com/prod/vendors' `
  -Method POST `
  -Headers @{'Content-Type'='application/json'} `
  -Body $body `
  -ErrorAction Continue

Write-Host "Response Status: $($response.StatusCode)"
Write-Host "Response Body:"
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
