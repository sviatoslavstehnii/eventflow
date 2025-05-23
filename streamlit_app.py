import streamlit as st
import requests
import datetime

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
    if st.button("Register"):
        resp = requests.post(f"{API_URL}/auth/register", json={"username": username, "email": email, "password": password})
        if resp.status_code == 200:
            st.success("Registered! Please log in.")
        else:
            st.error(resp.json().get("detail", "Registration failed"))

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
    resp = requests.get(f"{API_URL}/events")
    if resp.status_code == 200:
        events = resp.json()
        for ev in events:
            # Use 'id' if present, else '_id', else fallback to empty string
            event_id = ev.get("id") or ev.get("_id") or ""
            with st.expander(ev.get("title", str(event_id))):
                st.write(f"**Description:** {ev.get('description', '')}")
                st.write(f"**Date:** {ev.get('start_time', '')} to {ev.get('end_time', '')}")
                st.write(f"**Location:** {ev.get('location', '')}")
                st.write(f"**Capacity:** {ev.get('capacity', '')}")
                st.write(f"**Organizer:** {ev.get('organizer_id', 'N/A')}")
                if st.session_state.token and event_id:
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
                st.write(f"Event: {b.get('event_id', b.get('_id', ''))} | Status: {b.get('status', '')} | Booked at: {b.get('created_at', '')}")
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
