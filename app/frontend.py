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
if "history" not in st.session_state:
    st.session_state.history = []  # list of (user_message, ai_response)


# ------------------------------
# Sidebar: Login Panel
# ------------------------------
with st.sidebar:
    st.title("🔐 Login Panel")

    # If not logged in, show login form
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
                    st.error("❌ Invalid credentials. Please try again.")
            except Exception as e:
                st.error(f"🚫 Connection error: {str(e)}")

    # If logged in, show user details
    else:
        st.markdown(f"**👤 Logged in as:** `{st.session_state.user['username']}`")
        st.markdown(f"**🧾 Role:** `{st.session_state.user['role']}`")

        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.history = []
            st.rerun()


# ------------------------------
# Main Chat Interface
# ------------------------------
st.title("🤖 AI Assistant")
st.caption("Ask me anything about your documents.")

if st.session_state.user:

    # Ensure greeting shows once after login
    if len(st.session_state.history) == 0:
        st.session_state.history.append((
            "initial_greeting", 
            "Hello! I am your AI assistant. How can I help you today?"
        ))

    # Show role explanation
    with st.expander("📘 Role & Access Explanation", expanded=False):
        user_role = st.session_state.user["role"].lower()
        if "c-levelexecutives" in user_role:
            st.info("Unfiltered access — full visibility (C-Level Executives).")
        elif "employee" in user_role:
            st.info("Filtered access — only general category documents (Employee).")
        else:
            st.info(f"Filtered by department: `{user_role}`.")

    # Display chat history
    with st.container():
        for i, (question, answer) in enumerate(st.session_state.history[-10:]):
            if question == "initial_greeting":
                with st.chat_message("ai"):
                    st.markdown(answer)
            else:
                with st.chat_message("user"):
                    st.markdown(question)
                with st.chat_message("ai"):
                    st.markdown(answer)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"👍 Helpful {i}", key=f"yes_{i}"):
                            st.toast("✅ You found this helpful!", icon="👍")
                    with col2:
                        if st.button(f"👎 Not Helpful {i}", key=f"no_{i}"):
                            st.toast("❌ You found this unhelpful", icon="👎")

    # Chat input
    user_input = st.chat_input("💬 Type your question here")

    if user_input:
        st.chat_message("user").markdown(user_input)

        with st.chat_message("ai"):
            with st.spinner("🤖 Thinking..."):
                try:
                    response = requests.post(
                        "http://127.0.0.1:8000/chat",
                        json={
                            "user": st.session_state.user,
                            "message": user_input
                        }
                    )

                    if response.status_code == 200:
                        reply = response.json().get("response", "⚠️ No response.")

                        # Typing animation
                        typed_text = ""
                        container = st.empty()
                        for word in reply.split(" "):
                            typed_text += word + " "
                            container.markdown(typed_text)
                            time.sleep(0.02)

                        st.session_state.history.append((user_input, reply))
                    else:
                        st.error("❌ Server error while fetching response.")
                except Exception as e:
                    st.error(f"🚫 Error: {str(e)}")

else:
    st.info("🔐 Please log in from the sidebar to continue.")
