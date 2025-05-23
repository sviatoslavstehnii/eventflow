#!/bin/bash
# test_eventflow.sh
# End-to-end smoke tests for EventFlow services via API Gateway
set -e
BASE_URL="http://localhost:8080"

# 1) Register a new user
curl -s -X POST "$BASE_URL/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","password":"password"}'

# 2) Login
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" -F "username=alice" -F "password=password" | jq -r .access_token)
echo "Token: $TOKEN"
AUTH_HEADER="Authorization: Bearer $TOKEN"

# 3) Validate token
curl -s -H "$AUTH_HEADER" "$BASE_URL/auth/validate"

# 4) Create event
EVENT_ID=$(curl -s -X POST "$BASE_URL/events" \
  -H "$AUTH_HEADER" -H 'Content-Type: application/json' \
  -d '{"title":"Test Event","description":"A simple test","start_time":"2025-06-01T10:00:00Z","end_time":"2025-06-01T12:00:00Z","location":"Online","capacity":5,"price":0}' | jq -r .id)
echo "Event ID: $EVENT_ID"

# 5) List events
curl -s "$BASE_URL/events"

# 6) Book event
curl -s -X POST "$BASE_URL/bookings" \
  -H "$AUTH_HEADER" -H 'Content-Type: application/json' \
  -d '{"event_id":"'$EVENT_ID'"}'

# 7) List user bookings
curl -s -H "$AUTH_HEADER" "$BASE_URL/users/me/bookings"
