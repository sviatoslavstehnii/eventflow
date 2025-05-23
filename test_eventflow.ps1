# test_eventflow.ps1
# End-to-end smoke tests for EventFlow services

# Stop on any error
$ErrorActionPreference = 'Stop'

# Base URL for API Gateway
$BASE_URL = 'http://localhost:8080'
$AUTH_URL =  "$BASE_URL"
$EVENT_URL = "$BASE_URL"
$BOOK_URL =  "$BASE_URL"
$NOTIF_URL = "$BASE_URL"

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
    title       = 'Test Event'
    description = 'A simple test'
    start_time  = '2025-06-01T10:00:00Z'
    end_time    = '2025-06-01T12:00:00Z'
    location    = 'Online'
    capacity    = 5
    price       = 0
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
    title       = 'Booking Event'
    description = 'Event for booking tests'
    start_time  = '2025-06-02T10:00:00Z'
    end_time    = '2025-06-02T12:00:00Z'
    location    = 'Online'
    capacity    = 2
    price       = 0
} | ConvertTo-Json
$evResp2 = Invoke-RestMethod -Method Post -Uri "$EVENT_URL/events" `
    -Headers $authHeader -ContentType 'application/json' -Body $evBody2
Write-Host ($evResp2 | ConvertTo-Json -Depth 5)
$eventId2 = $evResp2.id

Write-Host "`n13) Book a spot on the event"
$bookBody = @{
    event_id = $eventId2
} | ConvertTo-Json
$bookResp = Invoke-RestMethod -Method Post -Uri "$BOOK_URL/bookings" `
    -Headers $authHeader -ContentType 'application/json' -Body $bookBody
Write-Host ($bookResp | ConvertTo-Json -Depth 5)

Write-Host "`n14) List all bookings for the user"
Invoke-RestMethod -Uri "$BOOK_URL/bookings" -Headers $authHeader | ConvertTo-Json -Depth 5 | Write-Host

Write-Host "`n15) Cancel the booking"
Invoke-RestMethod -Method Delete -Uri "$BOOK_URL/bookings/$($bookResp.id)" -Headers $authHeader
Write-Host "Booking cancelled"

Write-Host "`n16) Re-instate the booking"
$bookResp2 = Invoke-RestMethod -Method Post -Uri "$BOOK_URL/bookings" `
    -Headers $authHeader -ContentType 'application/json' -Body $bookBody
Write-Host ($bookResp2 | ConvertTo-Json -Depth 5)

Write-Host "`n17) Create a notification"
$notifBody = @{
    username = 'alice'
    event_id = $eventId2
    type     = 'email'
    data     = @{ subject = 'Event Reminder'; body = 'Don''t forget the event!' }
} | ConvertTo-Json
$notifResp = Invoke-RestMethod -Method Post -Uri "$NOTIF_URL/notifications" `
    -Headers $authHeader -ContentType 'application/json' -Body $notifBody
Write-Host ($notifResp | ConvertTo-Json -Depth 5)

Write-Host "`n18) List all notifications for the user"
Invoke-RestMethod -Uri "$NOTIF_URL/notifications" -Headers $authHeader | ConvertTo-Json -Depth 5 | Write-Host

Write-Host "`n19) Delete the notification"
Invoke-RestMethod -Method Delete -Uri "$NOTIF_URL/notifications/$($notifResp.id)" -Headers $authHeader
Write-Host "Notification deleted"

Write-Host "`n20) Attempt to access a protected resource without token"
try {
    Invoke-RestMethod -Method Get -Uri "$AUTH_URL/auth/validate"
    Write-Host "Unexpected success"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "Got HTTP $code as expected"
}

Write-Host "`n21) Cleanup - delete user"
Invoke-RestMethod -Method Delete -Uri "$AUTH_URL/auth/alice" -Headers $authHeader
Write-Host "User deleted"

Write-Host "`n22) Verify user deletion"
try {
    Invoke-RestMethod -Method Get -Uri "$AUTH_URL/auth/validate" -Headers $authHeader
    Write-Host "Unexpected success"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "Got HTTP $code as expected"
}

Write-Host "`n23) Done"