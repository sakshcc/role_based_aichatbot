import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import time

st.set_page_config(page_title="🧠 Role-Based Chatbot", layout="centered")

# ------------------------------
# Initialize session state
# ------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "response" not in st.session_state:
    st.session_state.response = None
if "history" not in st.session_state:
    st.session_state.history = []  # Chat history

# ------------------------------
# Sidebar Login Section
# ------------------------------
with st.sidebar:
    st.title("🔐 Login Panel")

    if st.session_state.user is None:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            try:
                response = requests.get(
                    "http://127.0.0.1:8000/login",
                    auth=HTTPBasicAuth(username, password)
                )
                if response.status_code == 200:
                    user_data = response.json()
                    st.session_state.user = {
                        "username": username,
                        "role": user_data["role"]
                    }
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Try again.")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

    else:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.user['username']}`")
        st.markdown(f"**🧾 Role:** `{st.session_state.user['role']}`")
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

# ------------------------------
# Main Chat Interface
# ------------------------------
st.title("🧠 FinSolve Role-Based Chatbot")

if st.session_state.user:
    message = st.text_area("💬 Enter your question", height=100)

    if st.button("Send Query") and message.strip():
        with st.spinner("Fetching response..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={
                        "user": st.session_state.user,
                        "message": message
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.response = data.get("response")

                    # Save message and response to history
                    st.session_state.history.append((message, st.session_state.response))

                    # Show response with typing effect
                    st.subheader("🧾 Response")
                    typing_placeholder = st.empty()
                    typed_response = ""
                    for word in st.session_state.response.split(" "):
                        typed_response += word + " "
                        typing_placeholder.markdown(typed_response)
                        time.sleep(0.02)

                else:
                    st.error("❌ Server error while fetching response.")
            except Exception as e:
                st.error(f"🚫 Error: {str(e)}")

    # Show access explanation
    if st.session_state.response:
        with st.expander("📘 Role & Access Explanation", expanded=False):
            role = st.session_state.user["role"].lower()
            if "c-levelexecutives" in role:
                st.info("Unfiltered access — full visibility (C-Level Executives).")
            elif "employee" in role:
                st.info("Filtered access — only general category documents (Employee).")
            else:
                st.info(f"Filtered by department: `{role}`.")

    # Show Chat History
    if st.session_state.history:
        with st.expander("📚 Chat History", expanded=False):
            for i, (q, a) in enumerate(reversed(st.session_state.history[-5:]), 1):
                st.markdown(f"**Q{i}:** {q}")
                st.markdown(f"**A{i}:** {a}")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"👍 Helpful {i}"):
                        st.toast(f"✅ You found answer {i} helpful!", icon="👍")
                with col2:
                    if st.button(f"👎 Not Helpful {i}"):
                        st.toast(f"❌ You found answer {i} not helpful", icon="👎")

        st.markdown("---")

else:
    st.info("🔐 Please log in from the sidebar to continue.")
