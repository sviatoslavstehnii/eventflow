import streamlit as st
import requests
import datetime
from bson import ObjectId

API_URL = "http://localhost:8080"

st.set_page_config(page_title="EventFlow", layout="wide")
st.title("EventFlow: Event Management Platform")

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

# --- Auth ---
def login():
    st.subheader("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        resp = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
        if resp.status_code == 200:
            st.session_state.token = resp.json()["access_token"]
            st.success("Logged in!")
            get_profile()
        else:
            st.error("Login failed")

def register():
    st.subheader("Register")
    username = st.text_input("Username", key="reg_username")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_password")
    username_exists = None
    if username:
        check_resp = requests.get(f"{API_URL}/users/check-username", params={"username": username})
        if check_resp.status_code == 200:
            username_exists = check_resp.json().get("exists", False)
    if username_exists:
        st.warning("Username already exists. Please choose another.")
    if st.button("Register"):
        if username_exists:
            st.error("Username already exists. Please choose another.")
        else:
            resp = requests.post(f"{API_URL}/auth/register", json={"username": username, "email": email, "password": password})
            if resp.status_code == 200:
                st.success("Registered! Please log in.")
            else:
                try:
                    detail = resp.json().get("detail", "Registration failed")
                except Exception:
                    detail = resp.text or "Registration failed"
                st.error(detail)

def get_profile():
    if st.session_state.token:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        resp = requests.get(f"{API_URL}/users/me", headers=headers)
        if resp.status_code == 200:
            st.session_state.user = resp.json()
        else:
            st.session_state.user = None

def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.success("Logged out!")

# --- Event Catalog ---
def list_events():
    st.subheader("Browse Events")
    params = {"is_active": True}
    resp = requests.get(f"{API_URL}/events", params=params)
    if resp.status_code == 200:
        events = resp.json()
        user_id = st.session_state.user.get("id") or st.session_state.user.get("_id") if st.session_state.user else None
        headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
        for ev in events:
            event_id = ev.get("id") or ev.get("_id") or ""
            capacity = ev.get("capacity", 0)
            with st.expander(ev.get("title", ev.get('title', ''))):
                st.write(f"**Description:** {ev.get('description', '')}")
                st.write(f"**Date:** {ev.get('start_time', '')} to {ev.get('end_time', '')}")
                st.write(f"**Location:** {ev.get('location', '')}")
                st.write(f"**Capacity:** {capacity}")
                st.write(f"**Organizer:** {ev.get('organizer_id', 'N/A')}")
                if st.session_state.token and event_id and ObjectId.is_valid(event_id) and user_id:
                    # Check if user already booked this event
                    booking_resp = requests.get(f"{API_URL}/bookings/user/{user_id}/event/{event_id}", headers=headers)
                    if booking_resp.status_code == 200 and booking_resp.json():
                        booking = booking_resp.json()
                        st.success("You have already booked this event.")
                        if st.button(f"Cancel Booking", key=f"cancel_{event_id}"):
                            booking_id = booking.get("id") or booking.get("_id")
                            cancel_resp = requests.delete(f"{API_URL}/bookings/user/{user_id}/event/{event_id}", headers=headers)
                            if cancel_resp.status_code == 200:
                                st.success("Booking cancelled!")
                            else:
                                st.error(cancel_resp.json().get("detail", "Failed to cancel booking"))
                    else:
                        if capacity <= 0:
                            st.error("No spaces available for this event.")
                            st.button(f"Book this event", key=f"book_{event_id}", disabled=True)
                        else:
                            if st.button(f"Book this event", key=f"book_{event_id}"):
                                book_event(event_id)
    else:
        st.error("Failed to load events")

def create_event():
    st.subheader("Create Event")
    title = st.text_input("Event Title")
    description = st.text_area("Description")
    location = st.text_input("Location")
    # Combine date and time inputs for start_time
    start_date = st.date_input("Start Date", value=datetime.date.today())
    start_time = st.time_input("Start Time", value=datetime.datetime.now().time())
    end_date = st.date_input("End Date", value=datetime.date.today())
    end_time = st.time_input("End Time", value=datetime.datetime.now().time())
    capacity = st.number_input("Capacity", min_value=1, value=10)
    price = st.number_input("Price", min_value=0.0, value=0.0, format="%.2f")
    if st.button("Create Event"):
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        start_dt = datetime.datetime.combine(start_date, start_time)
        end_dt = datetime.datetime.combine(end_date, end_time)
        data = {
            "title": title,
            "description": description,
            "location": location,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "capacity": int(capacity),
            "price": float(price)
        }
        resp = requests.post(f"{API_URL}/events", json=data, headers=headers)
        if resp.status_code == 201:
            st.success("Event created!")
        else:
            st.error(resp.json().get("detail", "Failed to create event"))

def book_event(event_id):
    # Ensure event_id is a valid ObjectId string before sending
    if not ObjectId.is_valid(event_id):
        st.error("Invalid event ID format. Please select a valid event.")
        return
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    resp = requests.post(f"{API_URL}/bookings", json={"event_id": event_id}, headers=headers)
    if resp.status_code == 200:
        st.success("Booking successful!")
    else:
        st.error(resp.json().get("detail", "Booking failed"))

def my_bookings():
    st.subheader("My Bookings")
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    user_id = st.session_state.user.get("id") or st.session_state.user.get("_id") if st.session_state.user else None
    if user_id:
        resp = requests.get(f"{API_URL}/bookings/user/{user_id}", headers=headers)
        if resp.status_code == 200:
            bookings = resp.json()
            for b in bookings:
                event_id = b.get('event_id', b.get('_id', ''))
                st.write(f"Event: {event_id} | Status: {b.get('status', '')} | Booked at: {b.get('created_at', '')}")
                if b.get('status', '') == 'confirmed':
                    if st.button(f"Cancel", key=f"cancel_my_{event_id}"):
                        cancel_resp = requests.delete(f"{API_URL}/bookings/user/{user_id}/event/{event_id}", headers=headers)
                        if cancel_resp.status_code == 200:
                            st.success("Booking cancelled!")
                        else:
                            st.error(cancel_resp.json().get("detail", "Failed to cancel booking"))
        else:
            st.error("Failed to load bookings")

def notifications():
    st.subheader("Notifications")
    # This is a placeholder; you may want to implement notification status polling
    st.info("Notification status and history coming soon!")

# --- Main UI ---
menu = ["Login", "Register", "Browse Events"]
if st.session_state.token:
    menu += ["Create Event", "My Bookings", "Notifications", "Logout"]
choice = st.sidebar.radio("Menu", menu)

if choice == "Login":
    login()
elif choice == "Register":
    register()
elif choice == "Browse Events":
    list_events()
elif choice == "Create Event":
    create_event()
elif choice == "My Bookings":
    my_bookings()
elif choice == "Notifications":
    notifications()
elif choice == "Logout":
    logout()
