# test_eventflow.ps1
# End-to-end smoke tests for EventFlow services

# Stop on any error
$ErrorActionPreference = 'Stop'

# Base URLs
$AUTH_URL =  'http://localhost:8001'
$EVENT_URL = 'http://localhost:8002'
$BOOK_URL =  'http://localhost:8003'
$NOTIF_URL = 'http://localhost:8004'

Write-Host "`n1) Register a new user"
$regBody = @{
    username = 'alice'
    email    = 'alice@example.com'
    password = 'password'
} | ConvertTo-Json

try {
    $regResp = Invoke-RestMethod -Method Post -Uri "$AUTH_URL/auth/register" `
        -ContentType 'application/json' -Body $regBody
    Write-Host "Registered: $($regResp | ConvertTo-Json -Depth 3)"
} catch {
    # If user already exists, skip
    if ($_.Exception.Response) {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 409) {
            Write-Host "→ User already exists (409), skipping registration"
        } else {
            throw
        }
    } else {
        throw
    }
}

Write-Host "`n2) Login as alice"
$loginResp = Invoke-RestMethod -Method Post -Uri "$AUTH_URL/auth/login" `
    -Form @{ username = 'alice'; password = 'password' }
$token = $loginResp.access_token
Write-Host "Token: $token"

$authHeader = @{ Authorization = "Bearer $token" }

Write-Host "`n3) Validate token"
$val = Invoke-RestMethod -Method Get -Uri "$AUTH_URL/auth/validate" -Headers $authHeader
Write-Host ($val | ConvertTo-Json -Depth 5)

Write-Host "`n4) Logout"
Invoke-RestMethod -Method Post -Uri "$AUTH_URL/auth/logout" -Headers $authHeader
Write-Host "Logged out"

Write-Host "`n5) Validate again (expect 401)"
try {
    Invoke-RestMethod -Method Get -Uri "$AUTH_URL/auth/validate" -Headers $authHeader
    Write-Host "Unexpected success"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "Got HTTP $code as expected"
}

Write-Host "`n6) Login again to get a fresh token"
$loginResp2 = Invoke-RestMethod -Method Post -Uri "$AUTH_URL/auth/login" `
    -Form @{ username = 'alice'; password = 'password' }
$token = $loginResp2.access_token
Write-Host "New Token: $token"
$authHeader = @{ Authorization = "Bearer $token" }

# --- Event tests ---
Write-Host "`n7) Create a test event"
$evBody = @{
    name        = 'Test Event'
    description = 'A simple test'
    date        = '2025-06-01T10:00:00Z'
    location    = 'Online'
    category    = 'Testing'
    capacity    = 5
} | ConvertTo-Json
$evResp = Invoke-RestMethod -Method Post -Uri "$EVENT_URL/events" `
    -Headers $authHeader -ContentType 'application/json' -Body $evBody
Write-Host ($evResp | ConvertTo-Json -Depth 5)
$eventId = $evResp.id

Write-Host "`n8) List all events"
Invoke-RestMethod -Uri "$EVENT_URL/events" | ConvertTo-Json -Depth 5 | Write-Host

Write-Host "`n9) Get event by ID"
Invoke-RestMethod -Uri "$EVENT_URL/events/$eventId" | ConvertTo-Json -Depth 5 | Write-Host

Write-Host "`n10) Update event capacity -> 3"
$updBody = @{ capacity = 3 } | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri "$EVENT_URL/events/$eventId" `
    -Headers $authHeader -ContentType 'application/json' -Body $updBody `
    | ConvertTo-Json -Depth 5 | Write-Host

Write-Host "`n11) Delete event"
Invoke-RestMethod -Method Delete -Uri "$EVENT_URL/events/$eventId" -Headers $authHeader
Write-Host "Deleted"

Write-Host "`n12) Re-create event for booking"
$evBody2 = @{
    name        = 'Booking Event'
    description = 'Event for booking tests'
    date        = '2025-06-02T10:00:00Z'
    location    = 'Online'
    category    = 'Booking'
    capacity    = 2
}