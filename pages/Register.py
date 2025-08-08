from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Optional

import streamlit as st

# ------------------------------------------------------------------ #
#  PAGE CONFIGURATION                                                #
# ------------------------------------------------------------------ #
st.set_page_config(page_title="Register", layout="centered")

# ------------------------------------------------------------------ #
#  TRY TO IMPORT BACKEND HELPERS                                     #
# ------------------------------------------------------------------ #
try:
    from utils import register_user, is_valid_password  # database wrappers
    UTILS_OK = True
except ImportError as exc:
    UTILS_OK = False
    st.error(f"Import Error → {exc}")
    st.error(
        "utils.py is missing the following call-level wrappers that this page "
        "relies on:\n"
        " • register_user(username, email, password, user_type)\n"
        " • is_valid_password(password)"
    )

# ------------------------------------------------------------------ #
#  HELPER FUNCTIONS                                                  #
# ------------------------------------------------------------------ #
def _img_to_base64(path: str | Path) -> Optional[str]:
    """Return an image file as a base64 data-URI or None if unavailable."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            st.warning(f"Background image not found ➜ {file_path}")
            return None

        encoded = base64.b64encode(file_path.read_bytes()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as err:  # pragma: no cover
        st.error(f"Error loading background image: {err}")
        return None

def _set_background() -> None:
    """Apply glassmorphism background; fallback to gradient if image missing."""
    img_path = r"D:\Brush and soul\uploads\53b691e2-6023-4fc8-9c87-cc378544d4d8.jpg"
    encoded = _img_to_base64(img_path)

    background_css = (
        f"""
        background-image: url("{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        """
        if encoded
        else """
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        """
    )

    st.markdown(
        f"""
        <style>
        .stApp {{
            {background_css}
        }}
        .block-container {{
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 2rem;
            max-width: 400px;
            margin: 5vh auto;
            box-shadow: 0 8px 32px 0 rgba(31,38,135,0.37);
        }}
        h2 {{
            color: white;
            text-align: center;
        }}
        .stTextInput > div > div > input,
        .stSelectbox  > div > div > div > div {{
            background-color: rgba(255,255,255,0.7) !important;
            border-radius: 10px;
        }}
        .stButton > button {{
            background-color: #4CAF50;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            margin-top: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def validate_email(email: str) -> bool:
    """RFC-style email validation."""
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.match(pattern, email.strip()))

def validate_username(username: str) -> tuple[bool, str]:
    """Username length & charset checks."""
    username = username.strip()
    if not (3 <= len(username) <= 20):
        return False, "Username must be 3 – 20 characters long."
    if not re.match(r"^[A-Za-z0-9_]+$", username):
        return False, "Username may contain only letters, numbers, and underscores."
    return True, "OK"

# ------------------------------------------------------------------ #
#  PAGE LAYOUT                                                       #
# ------------------------------------------------------------------ #
_set_background()

if not UTILS_OK:
    st.stop()

with st.container():
    st.markdown("<div class='block-container'>", unsafe_allow_html=True)
    st.markdown("<h2>User Registration</h2>", unsafe_allow_html=True)

    with st.form("register_form"):
        username = st.text_input("Username", max_chars=20)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        user_type = st.selectbox("User Type", ["artist", "customer"])
        submit = st.form_submit_button("Register")

        if submit:
            try:
                # ---------- field completeness ---------- #
                if not all([username, email, password, confirm]):
                    st.warning("Please fill all fields.")
                    st.stop()

                # ---------- email / username validation ---------- #
                if not validate_email(email):
                    st.warning("Please enter a valid email.")
                    st.stop()

                ok, msg = validate_username(username)
                if not ok:
                    st.warning(msg)
                    st.stop()

                # ---------- password checks ---------- #
                if password != confirm:
                    st.warning("Passwords do not match.")
                    st.stop()

                valid_pwd, pwd_msg = is_valid_password(password)
                if not valid_pwd:
                    st.warning(pwd_msg)
                    st.stop()

                # ---------- FIXED: register with correct parameters and return handling ---------- #
                success, message = register_user(
                    username.strip(), 
                    email.strip(), 
                    password.strip(), 
                    user_type
                )
                
                if success:
                    st.success(f"✅ {message} Redirecting to login…")
                    # Add a small delay to show success message
                    import time
                    time.sleep(1)
                    st.switch_page("pages/Login.py")
                else:
                    st.error(f"❌ Registration failed: {message}")

            except Exception as err:  # pragma: no cover
                st.error(f"Registration error: {err}")
                st.error("Check your database connection and utils.py file.")

    # Navigation button
    if st.button("Back to Login"):
        st.switch_page("pages/Login.py")

    st.markdown("</div>", unsafe_allow_html=True)
