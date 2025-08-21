from __future__ import annotations

import base64
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Configuration and Enums                                                   #
# --------------------------------------------------------------------------- #
class LoginView(Enum):
    """Available login page views"""
    LOGIN = "login"
    RESET = "reset"
    REGISTERED_SUCCESS = "registered_success"

@dataclass(frozen=True)
class UIConfig:
    """UI configuration settings"""
    page_title: str = "Login - Brush and Soul"
    layout: str = "centered"
    background_image: str = r"D:\Brush and soul\uploads\53b691e2-6023-4fc8-9c87-cc378544d4d8.jpg"
    max_container_width: int = 400
    blur_intensity: int = 15

@dataclass
class LoginResult:
    """Result of login attempt"""
    success: bool
    user_data: Optional[Dict] = None
    error_message: Optional[str] = None

# --------------------------------------------------------------------------- #
#  Database Integration                                                       #
# --------------------------------------------------------------------------- #
class AuthenticationManager:
    """Handles authentication operations with database backend"""
    
    def __init__(self):
        self._import_utils()
    
    def _import_utils(self) -> None:
        """Import database utilities with error handling"""
        try:
            from utils import authenticate, update_password, is_valid_password
            self.authenticate = authenticate
            self.update_password = update_password
            self.is_valid_password = is_valid_password
            logger.info("Database utilities imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import utilities: {e}")
            st.error("Database connection error. Please check system configuration.")
            raise

    def login_user(self, username: str, password: str) -> LoginResult:
        """Authenticate user credentials against database"""
        try:
            user_data = self.authenticate(username.strip(), password.strip())
            if user_data:
                logger.info(f"Successful login for user: {username}")
                return LoginResult(success=True, user_data=user_data)
            else:
                logger.warning(f"Failed login attempt for user: {username}")
                return LoginResult(success=False, error_message="Invalid username or password.")
        except Exception as e:
            logger.error(f"Login error for user {username}: {e}")
            return LoginResult(success=False, error_message="Authentication service unavailable.")

    def reset_user_password(self, email: str, new_password: str) -> Tuple[bool, str]:
        """Reset user password in database"""
        try:
            # Validate password strength
            is_valid, validation_message = self.is_valid_password(new_password)
            if not is_valid:
                return False, validation_message
            
            # Update password in database
            if self.update_password(email.strip(), new_password.strip()):
                logger.info(f"Password reset successful for email: {email}")
                return True, "Password reset successful!"
            else:
                logger.warning(f"Password reset failed - email not found: {email}")
                return False, "Email not found in system."
        except Exception as e:
            logger.error(f"Password reset error for email {email}: {e}")
            return False, "Password reset service unavailable."

# --------------------------------------------------------------------------- #
#  Session Management                                                         #
# --------------------------------------------------------------------------- #
class SessionManager:
    """Advanced session state management"""
    
    @staticmethod
    def initialize_session() -> None:
        """Initialize session state variables"""
        session_defaults = {
            "logged_in": False,
            "user": None,
            "show_welcome": True
        }
        
        for key, default_value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def login_user(user_data: Dict) -> None:
        """Set user as logged in"""
        st.session_state.logged_in = True
        st.session_state.user = user_data
        logger.info(f"Session established for user: {user_data.get('username', 'Unknown')}")

    @staticmethod
    def logout_user() -> None:
        """Clear user session"""
        st.session_state.logged_in = False
        st.session_state.user = None
        logger.info("User session cleared")

# --------------------------------------------------------------------------- #
#  UI Management                                                              #
# --------------------------------------------------------------------------- #
class BackgroundManager:
    """Handles background image and styling"""
    
    def __init__(self, config: UIConfig):
        self.config = config
    
    @contextmanager
    def error_handling(self):
        """Context manager for error handling"""
        try:
            yield
        except Exception as e:
            logger.error(f"Background processing error: {e}")
            st.warning("Background image could not be loaded")

    def load_background_image(self) -> Optional[str]:
        """Load and encode background image"""
        with self.error_handling():
            image_path = Path(self.config.background_image)
            if not image_path.exists():
                logger.warning(f"Background image not found: {image_path}")
                return None
            
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
                return f"data:image/jpg;base64,{encoded}"
        return None

    def apply_styling(self) -> None:
        """Apply glassmorphism styling with background"""
        background_data = self.load_background_image()
        
        background_style = (
            f'background-image: url("{background_data}");' if background_data
            else 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);'
        )
        
        st.markdown(f"""
            <style>
            .stApp {{
                {background_style}
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            .block-container {{
                background: rgba(255, 255, 255, 0.07);
                backdrop-filter: blur({self.config.blur_intensity}px);
                -webkit-backdrop-filter: blur({self.config.blur_intensity}px);
                border-radius: 20px;
                margin: auto;
                width: 100%;
                max-width: {self.config.max_container_width}px;
                padding: 2rem;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
            }}
            section.main > div {{
                padding: 0rem !important;
            }}
            .stTextInput > div > div > input {{
                background-color: rgba(255,255,255,0.2) !important;
                color: #000 !important;
                border-radius: 10px;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #000 !important;
            }}
            p, label {{
                color: #000 !important;
            }}
            button {{
                background-color: #4CAF50 !important;
                color: white !important;
                border-radius: 10px;
            }}
            a {{
                color: #00f !important;
                text-decoration: underline;
            }}
            </style>
        """, unsafe_allow_html=True)

class LoginInterface:
    """Main login interface controller"""
    
    def __init__(self):
        self.config = UIConfig()
        self.auth_manager = AuthenticationManager()
        self.session_manager = SessionManager()
        self.background_manager = BackgroundManager(self.config)
    
    def get_current_view(self) -> LoginView:
        """Get current view from query parameters"""
        params = st.query_params
        view_param = params.get("view", "login")
        
        try:
            return LoginView(view_param)
        except ValueError:
            logger.warning(f"Unknown view parameter: {view_param}")
            return LoginView.LOGIN
    
    def render_password_reset_view(self) -> None:
        """Render password reset form"""
        st.markdown("## 🔒 Reset Password")
        
        with st.form("reset_form"):
            email = st.text_input("Registered Email")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Reset Password")
        
        if submitted:
            if not all([email, new_password, confirm_password]):
                st.warning("All fields are required.")
            elif new_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                success, message = self.auth_manager.reset_user_password(email, new_password)
                if success:
                    st.success(message)
                    st.markdown('[Back to Login](?view=login)', unsafe_allow_html=True)
                else:
                    st.error(message)
        
        st.markdown('[← Back to Login](?view=login)', unsafe_allow_html=True)
    
    def render_login_view(self) -> None:
        """Render main login form"""
        st.markdown("## 🔐 Login to Brush and Soul")
        
        # Show success message if redirected from registration
        if self.get_current_view() == LoginView.REGISTERED_SUCCESS:
            st.success("✅ Registration successful! Please login.")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        
        if submitted:
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                login_result = self.auth_manager.login_user(username, password)
                
                if login_result.success:
                    self.session_manager.login_user(login_result.user_data)
                    st.success(f"Welcome {login_result.user_data['username']}!")
                    st.switch_page("pages/04_Dashboard.py")
                else:
                    st.error(login_result.error_message)
        
        # Navigation links
        st.markdown('[Forgot Password?](?view=reset)', unsafe_allow_html=True)
        st.markdown(
            '[Don\'t have an account? <span style="color:#00f;text-decoration:underline;">'
            'Register here</span>](Register)', 
            unsafe_allow_html=True
        )
    
    def run(self) -> None:
        """Main application entry point"""
        # Configure page
        st.set_page_config(
            page_title=self.config.page_title,
            layout=self.config.layout
        )
        
        # Initialize session and apply styling
        self.session_manager.initialize_session()
        self.background_manager.apply_styling()
        
        # Main container
        st.markdown('<div class="block-container">', unsafe_allow_html=True)
        
        try:
            # Route to appropriate view
            current_view = self.get_current_view()
            
            if current_view == LoginView.RESET:
                self.render_password_reset_view()
            else:
                self.render_login_view()
                
        
        finally:
            # Close container
            st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Application Entry Point                                                    #
# --------------------------------------------------------------------------- #
def main():
    """Application main function"""
    try:
        app = LoginInterface()
        app.run()
    except Exception as e:
        logger.error(f"Critical application error: {e}")
        st.error("Application failed to start. Please contact support.")

if __name__ == "__main__":
    main()


