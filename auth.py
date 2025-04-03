import streamlit as st
import hashlib
import json
from datetime import datetime, timedelta
from credentials import USERS

def get_auth_token(username):
    """Generate an authentication token for the user"""
    # Create a token that includes username and expiration
    expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    token_data = f"{username}:{expiry}"
    # Hash the token data
    return hashlib.sha256(token_data.encode()).hexdigest()

def verify_auth_token(token):
    """Verify if the authentication token is valid"""
    if not token:
        return None
    
    # Check each user's token
    for username, user_data in USERS.items():
        if get_auth_token(username) == token:
            return {
                "username": username,
                "organization": user_data["organization"]
            }
    return None

def find_user(username, password):
    """Find user in credentials and return their information"""
    if username in USERS and USERS[username]["password"] == password:
        return {
            "username": username,
            "organization": USERS[username]["organization"]
        }
    return None

def logout():
    """Clear the session state and authentication cookie"""
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Clear authentication cookie
    st.session_state['authentication_status'] = None
    st.query_params.clear()

def check_password():
    """Returns `True` if the user had a correct password or valid token."""
    
    # First, check if we have a valid token in URL parameters
    auth_token = st.query_params.get("auth", None)
    
    if auth_token:
        user = verify_auth_token(auth_token)
        if user:
            st.session_state["password_correct"] = True
            st.session_state["username_logged"] = user["username"]
            st.session_state["organization"] = user["organization"]
            st.session_state["authentication_status"] = True
            return True

    # Show logout button if user is logged in
    if st.session_state.get("authentication_status", False):
        header_container = st.container()
        with header_container:
            col1, col2, col3 = st.columns([4,2,1])
            with col3:
                if st.button("🚪 Cerrar Sesión"):
                    logout()
                    st.rerun()
            with col1:
                st.write(f"Usuario: {st.session_state.get('username_logged', '')}")
            with col2:
                st.write(f"Organización: {st.session_state.get('organization', '')}")
        return True

    # Show login form if not authenticated
    st.text_input("Usuario", key="username")
    st.text_input("Contraseña", type="password", key="password")
    
    remember_me = st.checkbox("Recordarme en este dispositivo", value=True)
    
    if st.button("Ingresar"):
        user = find_user(st.session_state["username"], st.session_state["password"])
        if user:
            st.session_state["password_correct"] = True
            st.session_state["username_logged"] = user["username"]
            st.session_state["organization"] = user["organization"]
            st.session_state["authentication_status"] = True
            
            if remember_me:
                # Generate and store authentication token
                auth_token = get_auth_token(user["username"])
                st.query_params["auth"] = auth_token
            
            st.rerun()
        else:
            st.error("😕 Usuario o contraseña incorrectos")
            
    return st.session_state.get("authentication_status", False)

def get_current_organization():
    """Helper function to get the current user's organization"""
    return st.session_state.get("organization", None) 