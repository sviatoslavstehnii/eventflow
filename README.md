# EventFlow: Scalable Event Management Platform

![architecture](image.png)

## Overview
EventFlow is a microservices-based platform designed for discovering, creating, managing, and registering for various events such as conferences, workshops, meetups, and concerts. It utilizes a suite of specialized microservices to handle different aspects of the event lifecycle, ensuring scalability, resilience, and maintainability.

## Architecture
The platform is built upon a microservice architecture. All client requests are routed through an API Gateway, which acts as a single entry point. Each microservice is developed and deployed independently, communicating with others over a Docker network. This design promotes loose coupling and allows for independent scaling and updating of services.

- **API Gateway**: All client requests are directed to the API Gateway, accessible at `http://localhost:8080`. It routes requests to the appropriate downstream service.
- **Inter-service Communication**: Microservices communicate with each other as needed, typically over the internal Docker network. Some services might use Consul for service discovery.

## Core Microservices

### 1. Authentication Service
- **Purpose**: Manages all aspects of user identity, including registration, login, session management via JWT (JSON Web Tokens), and user profile data.
- **Database**: PostgreSQL is used for its relational capabilities, suitable for storing user credentials, roles, and profile information.
- **Key API Endpoints (via API Gateway)**:
    - `POST /auth/register`: Allows new users to create an account.
        - Request Body: `{ "username": "string", "email": "string", "password": "string" }`
        - Response: `{ "id": "uuid", "username": "string", "email": "string" }` (or error)
    - `POST /auth/login`: Allows registered users to log in.
        - Request Body: `{ "username": "string", "password": "string" }` (Uses form data, not JSON, as per `streamlit_app.py` correction)
        - Response: `{ "access_token": "string", "token_type": "bearer" }` (or error)
    - `GET /auth/validate`: Validates an existing access token. (Primarily for internal or backend use)
        - Headers: `Authorization: Bearer <token>`
        - Response: User details if token is valid (or error)
    - `GET /users/me`: Retrieves the profile of the currently authenticated user.
        - Headers: `Authorization: Bearer <token>`
        - Response: `{ "id": "uuid", "username": "string", "email": "string", ... }` (or error)

### 2. Event Catalog Service
- **Purpose**: Handles the creation, retrieval, updating, deletion (CRUD), searching, and filtering of events.
- **Database**: MongoDB is chosen for its flexible schema, which is well-suited for diverse event details and attributes, and its strong text search capabilities.
- **Fault Tolerance**: MongoDB can be configured with a Replica Set. If a primary node fails, a secondary node is promoted to primary. If the number of nodes falls below the quorum, the remaining set becomes read-only to maintain data consistency.
- **Key API Endpoints (via API Gateway)**:
    - `GET /events`: Lists all events or allows searching/filtering based on query parameters (e.g., `?name=Workshop&location=Online`).
        - Response: `[ { "id": "uuid", "name": "string", "description": "string", "start_time": "iso_datetime", "end_time": "iso_datetime", "location": "string", "capacity": int, "price": float, "organizer_id": "uuid" }, ... ]`
    - `POST /events`: Creates a new event. Requires authentication.
        - Headers: `Authorization: Bearer <token>`
        - Request Body: `{ "name": "string", "description": "string", "start_time": "iso_datetime", "end_time": "iso_datetime", "location": "string", "capacity": int, "price": float }`
        - Response: `{ "id": "uuid", ...event_details }` (or error)
    - `GET /events/{id}`: Retrieves details for a specific event by its ID.
        - Response: `{ "id": "uuid", ...event_details }` (or error)
    - `PUT /events/{id}`: Updates an existing event. Requires authentication and typically authorization (e.g., only event organizer).
        - Headers: `Authorization: Bearer <token>`
        - Request Body: `{ ...fields_to_update }`
        - Response: `{ "id": "uuid", ...updated_event_details }` (or error)
    - `DELETE /events/{id}`: Deletes an event. Requires authentication and authorization.
        - Headers: `Authorization: Bearer <token>`
        - Response: Success message (or error)

### 3. Booking Service
- **Purpose**: Manages event registrations (bookings), handles waiting lists if events reach capacity, and tracks the status of bookings.
- **Database**: Cassandra is used due to its high write throughput capabilities and scalability, which are crucial for handling concurrent bookings for popular events. Common query patterns include fetching bookings by user ID or event ID.
- **High Availability (HA)**: The Booking Service application instances can be duplicated and placed behind a load balancer to ensure continuous availability.
- **Distributed Cache**: Redis serves as an in-memory data grid (distributed cache) to store temporary session-specific data during the booking process (e.g., incomplete booking details, seat selections). If a Booking Service instance fails, the load balancer redirects the user to a healthy instance, which can retrieve the session state from Redis, allowing for a seamless user experience.
- **Key API Endpoints (via API Gateway)**:
    - `POST /bookings`: Creates a new booking for an event by the authenticated user.
        - Headers: `Authorization: Bearer <token>`
        - Request Body: `{ "event_id": "uuid" }`
        - Response: `{ "booking_id": "uuid", "event_id": "uuid", "user_id": "uuid", "status": "string", "created_at": "iso_datetime" }` (or error)
    - `GET /users/{userId}/bookings`: Lists all bookings for a specific user. Requires authentication (user can only see their own bookings, or admin role).
        - Headers: `Authorization: Bearer <token>`
        - Response: `[ { "booking_id": "uuid", ...booking_details }, ... ]` (or error)
    - `GET /events/{eventId}/bookings`: (Optional) Lists all bookings for a specific event. (Requires admin/organizer privileges).
        - Headers: `Authorization: Bearer <token>`
        - Response: `[ { "booking_id": "uuid", ...booking_details }, ... ]` (or error)

### 4. Notification Service
- **Purpose**: Responsible for sending various notifications to users, such as booking confirmations, event reminders, updates, or cancellations.
- **Asynchronous Processing**: Leverages a message queue (RabbitMQ) to receive notification requests. This decouples the notification process from the services that trigger them (e.g., Booking Service), improving responsiveness and resilience.
- **CQRS/Event Sourcing (Conceptual)**: When a significant action occurs (e.g., a booking is confirmed by the Booking Service), an event like `BookingConfirmedEvent` is published to the message queue. The Notification Service subscribes to these events and processes them asynchronously to dispatch notifications.
- **Database**: MongoDB is used to store notification templates, a log of sent messages, and user notification preferences.
- **Key API Endpoints (via API Gateway)**:
    - `GET /notifications/status/{id}`: (Optional) Checks the delivery status of a specific notification.
        - Response: `{ "notification_id": "uuid", "status": "string", "details": "string" }` (or error)
    - (Primarily consumes messages from RabbitMQ, may not have many direct HTTP endpoints for clients)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (for the frontend)
- (Optional) `curl` or `httpie` for direct API testing

### Launch the Backend System
1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url> # Replace <your-repo-url> with the actual repository URL
    cd eventflow
    ```
2.  **Build and run services using Docker Compose**:
    This command will build the images for each microservice (if not already built) and start all the containers defined in `docker-compose.yml`.
    ```bash
    docker compose up --build
    ```
    - The API Gateway will then be available at: `http://localhost:8080`
    - You can view the status of running containers with `docker compose ps`.
    - To view logs for a specific service: `docker compose logs <service_name>` (e.g., `docker compose logs api-gateway`).

## Frontend (Streamlit)

A simple web-based frontend is provided using Streamlit. It allows users to interact with the EventFlow platform.

### Frontend Features:
- **User Authentication**: Register for a new account and log in with existing credentials.
- **Event Browsing**: View a list of available events with details like description, date, location, capacity, and price.
- **Event Creation**: Authenticated users can create new events by providing necessary details.
- **Event Booking**: Authenticated users can book available events.
- **My Bookings**: Authenticated users can view a list of their past and current bookings.
- **Notifications**: A placeholder section for future notification display.

### Launch the Frontend
1.  **Install frontend requirements**:
    Open a new terminal window, navigate to the `eventflow` project directory, and run:
    ```bash
    pip install -r requirements-frontend.txt
    ```
2.  **Start the Streamlit application**:
    ```bash
    streamlit run streamlit_app.py
    ```
3.  **Access the frontend**:
    Open your web browser and go to `http://localhost:8501`.

> **Note**: The frontend application communicates with the API Gateway at `http://localhost:8080`. Ensure the backend services are running before starting the frontend.

## Testing

### Automated Test Script
A shell script is provided to perform basic automated tests against the API endpoints.
-   Ensure the backend system is running (`docker compose up`).
-   Execute the test script:
    ```bash
    bash test_eventflow.sh
    ```
    Or, if you are on Windows with PowerShell:
    ```powershell
    ./test_eventflow.ps1
    ```
> **Important**: The test scripts are configured to use `http://localhost:8080` as the base URL for all API calls. Verify this if you encounter issues.

## Troubleshooting
-   **Service Status**: Use `docker compose ps` to check if all services are up and running.
-   **Service Logs**: If a service is not behaving as expected, check its logs using `docker compose logs <service_name>`. For example, `docker compose logs auth-service`.
-   **Startup Failures**: If a service fails to start, common causes include:
    -   Incorrect environment variables (check `docker-compose.yml` and any `.env` files if used).
    -   Dependencies not being healthy (e.g., a service depending on a database that hasn't started yet). `docker-compose.yml` uses `depends_on` with `service_healthy` conditions to mitigate this.
    -   Port conflicts if other applications on your machine are using the same ports.
-   **Frontend Issues**:
    -   Ensure the API Gateway (`http://localhost:8080`) is running and accessible.
    -   Check the browser's developer console for any JavaScript errors or network request failures.
    -   Verify that the `API_URL` in `streamlit_app.py` is correctly set to the API Gateway's address.

## System Flow and Consistency

### Event Creation
- Events are created via the `/events` endpoint (POST) with fields: `title`, `description`, `start_time`, `end_time`, `location`, `capacity`, `price`.
- The backend, frontend, and test scripts are now consistent in using these fields.

### Booking
- Bookings are created via the `/bookings` endpoint (POST) with field: `event_id`.
- The booking service checks event capacity, updates Redis, and always updates the event-catalog-service about capacity changes on booking and cancellation.
- If any step fails, the system rolls back to ensure consistency.

### Displaying Events and Bookings
- The frontend (Streamlit) and API responses use the same field names (`title`, `start_time`, etc.).
- User bookings are fetched via `/bookings/user/{user_id}`.
- Event details are always up-to-date and consistent across all services.

### API Gateway
- All requests go through the API Gateway at `http://localhost:8080`.
- The gateway transparently proxies requests to the correct service.

### Frontend
- The Streamlit app allows users to register, log in, browse events, create events, book events, and view their bookings, all using the consistent API and data model.

---

# Changelog
- All event and booking flows are now consistent across backend, frontend, and test scripts.
- Capacity management is orchestrated between booking-service and event-catalog-service.
- The frontend and documentation have been updated to match the backend API and data model.

# How the System Works
1. **User registers and logs in via the frontend or API.**
2. **User creates an event** (if authenticated) via the frontend or `/events` API.
3. **User books an event** via the frontend or `/bookings` API. The booking-service checks capacity, updates Redis, and notifies the event-catalog-service.
4. **User can view their bookings** via the frontend or `/bookings/user/{user_id}`.
5. **All actions are routed through the API Gateway.**

---
# For Developers
- See the code in each service's `app/` directory for implementation details.
- All API contracts are now consistent and orchestrated for reliability.

# For Users
- Use the Streamlit app for a seamless experience, or interact with the API directly as documented above.

# For Testers
- Use the provided test scripts (`test_eventflow.sh`, `test_eventflow.ps1`) to verify the full system flow.

# Support
For questions or issues, open an issue or pull request on the repository.

