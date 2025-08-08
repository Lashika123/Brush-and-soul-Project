from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Protocol, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  TYPE DEFINITIONS & PROTOCOLS
# ─────────────────────────────────────────────────────────────────────────────
class ProfileOpsProtocol(Protocol):
    """Database-side operations required by this page."""
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]: ...
    def update_password(self, email: str, new_password: str) -> bool: ...
    def is_valid_password(self, password: str) -> Tuple[bool, str]: ...
    def update_user_field(self, username: str, field: str, value: str) -> bool: ...

class UserRole(Enum):
    ARTIST = "artist"
    CUSTOMER = "customer"

    @classmethod
    def from_string(cls, raw: str) -> "UserRole":
        try:
            return cls(raw.lower())
        except ValueError:
            return cls.CUSTOMER

    def display_name(self) -> str:
        """Get display name for the role"""
        return self.value.capitalize()

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG & DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class UIConfig:
    page_title: str = "My Profile"
    page_icon: str = "👤"
    max_bio_length: int = 300

@dataclass
class UserCtx:
    username: str
    email: str
    role: UserRole
    bio: str = ""
    is_authenticated: bool = True

    @classmethod
    def from_session(cls) -> Optional["UserCtx"]:
        if "user" not in st.session_state or not st.session_state.get("logged_in", False):
            return None
        
        u = st.session_state.user
        return cls(
            username=u.get("username", ""),
            email=u.get("email", ""),
            role=UserRole.from_string(u.get("user_type", "customer")),
            bio=u.get("bio", "")
        )

    def update_session_bio(self, new_bio: str) -> None:
        """Update bio in session state"""
        if "user" in st.session_state:
            st.session_state.user["bio"] = new_bio

@dataclass
class PasswordChangeRequest:
    """Data structure for password change requests"""
    current_password: str
    new_password: str
    confirm_password: str

    def validate(self) -> Tuple[bool, str]:
        """Validate password change request"""
        if not all([self.current_password, self.new_password, self.confirm_password]):
            return False, "Please fill in all the fields."
        
        if self.new_password != self.confirm_password:
            return False, "New passwords do not match."
        
        return True, ""

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """Advanced database operations manager with comprehensive error handling."""
    
    def __init__(self):
        self.operations_available = self._initialize_operations()

    def _initialize_operations(self) -> bool:
        """Initialize database operations with graceful error handling"""
        try:
            from utils import (
                authenticate,
                update_password,
                is_valid_password,
                update_user_field,
            )
            
            # Create operations wrapper
            class DatabaseOperations:
                def __init__(self):
                    self.authenticate = authenticate
                    self.update_password = update_password
                    self.is_valid_password = is_valid_password
                    self.update_user_field = update_user_field
            
            self.ops = DatabaseOperations()
            logger.info("Database operations initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Database utilities not available: {e}")
            return False

    @contextmanager
    def _error_handler(self, op: str):
        """Context manager for database operation error handling"""
        try:
            yield
        except Exception as exc:
            logger.error(f"Database op '{op}' failed: {exc}")
            pass

    # Authentication operations ----------------------------------------------
    def verify_user_password(self, username: str, password: str) -> bool:
        """Verify user's current password"""
        if not self.operations_available:
            return False
        
        with self._error_handler("authenticate"):
            try:
                result = self.ops.authenticate(username, password)
                return bool(result)
            except Exception:
                return False

    def change_user_password(self, email: str, new_password: str) -> bool:
        """Change user's password"""
        if not self.operations_available:
            return False
        
        with self._error_handler("update_password"):
            try:
                return self.ops.update_password(email, new_password)
            except Exception:
                return False

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if not self.operations_available:
            return False, "Password validation unavailable"
        
        with self._error_handler("is_valid_password"):
            try:
                return self.ops.is_valid_password(password)
            except Exception:
                return False, "Password validation failed"

    # User field operations --------------------------------------------------
    def update_user_bio(self, username: str, bio: str) -> bool:
        """Update user's bio"""
        if not self.operations_available:
            return False
        
        with self._error_handler("update_user_field"):
            try:
                return self.ops.update_user_field(username, "bio", bio)
            except Exception:
                return False

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class SessionManager:
    """Advanced session state management"""
    
    @staticmethod
    def logout_user() -> None:
        """Logout user and clear session"""
        st.session_state.logged_in = False
        st.session_state.user = None

    @staticmethod
    def validate_authentication() -> Optional[UserCtx]:
        """Validate user authentication and return user context"""
        user_ctx = UserCtx.from_session()
        if not user_ctx:
            st.warning("Please log in to access your profile.")
            st.stop()
        return user_ctx

# ─────────────────────────────────────────────────────────────────────────────
#  ADVANCED UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, cfg: UIConfig, db: DatabaseManager):
        self.cfg = cfg
        self.db = db
    
    @abstractmethod
    def render(self, user_ctx: UserCtx) -> None:
        """Render the UI component"""
        pass

class StyleManager(UIComponent):
    """Handles CSS styling for the application"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Apply custom CSS styling exactly as original"""
        st.markdown("""
        <style>
        :root {
            --primary: #8B4513;
            --secondary: #A0522D;
            --accent: #5C4033;
            --light: #F8F4E8;
            --dark: #343434;
            --brown-box-bg: linear-gradient(135deg, rgba(139, 69, 19, 0.15), rgba(210, 180, 140, 0.2));
        }
        
        .stApp {
            background: linear-gradient(160deg, #f5f1e8 0%, #e8e0d0 100%);
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* ALL BUTTONS - BROWN THEME */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            border: 2px solid rgba(139, 69, 19, 0.3) !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            padding: 14px 28px !important;
            font-size: 0.95rem !important;
            box-shadow: 0 6px 18px rgba(139, 69, 19, 0.35) !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, var(--accent), var(--primary)) !important;
            transform: translateY(-3px) scale(1.05) !important;
            box-shadow: 0 10px 25px rgba(139, 69, 19, 0.45) !important;
        }
        
        /* Profile Cards */
        .profile-card {
            background: var(--brown-box-bg) !important;
            border: 2px solid rgba(139, 69, 19, 0.25) !important;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
        }
        
        /* Form Elements */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border: 2px solid rgba(139, 69, 19, 0.2) !important;
            border-radius: 10px !important;
            background: rgba(255, 255, 255, 0.95) !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(139, 69, 19, 0.15) !important;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: var(--accent) !important;
            font-weight: 700;
        }
        
        /* Success/Error Messages */
        .stSuccess {
            background: var(--brown-box-bg) !important;
            border-left: 4px solid #4CAF50 !important;
            color: var(--dark) !important;
        }
        
        .stError {
            background: var(--brown-box-bg) !important;
            border-left: 4px solid #F44336 !important;
            color: var(--dark) !important;
        }
        </style>
        """, unsafe_allow_html=True)

class AccountInfoDisplay(UIComponent):
    """Account information display component"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render account information section"""
        with st.container():
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='header'><h2>📄 Account Information</h2></div>", unsafe_allow_html=True)
            st.write(f"**Username:** {user_ctx.username}")
            st.write(f"**Email:** {user_ctx.email}")
            st.write(f"**Role:** {user_ctx.role.display_name()}")
            st.markdown("</div>", unsafe_allow_html=True)

class BioUpdateForm(UIComponent):
    """Bio update form component"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render bio update form"""
        with st.container():
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='header'><h2>📝 About You</h2></div>", unsafe_allow_html=True)
            
            new_bio = st.text_area(
                f"Bio (max {self.cfg.max_bio_length} characters):", 
                value=user_ctx.bio, 
                max_chars=self.cfg.max_bio_length
            )
            
            if st.button("Save Bio"):
                self._handle_bio_update(user_ctx, new_bio)
            
            st.markdown("</div>", unsafe_allow_html=True)

    def _handle_bio_update(self, user_ctx: UserCtx, new_bio: str) -> None:
        """Handle bio update submission"""
        try:
            if self.db.update_user_bio(user_ctx.username, new_bio):
                user_ctx.update_session_bio(new_bio)
                st.success("✅ Bio updated successfully!")
            else:
                st.error("❌ Could not update your bio.")
        except Exception as e:
            logger.error(f"Error updating bio: {e}")
            st.error("❌ Could not update your bio.")

class PasswordChangeForm(UIComponent):
    """Password change form component"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render password change form"""
        with st.container():
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            
            with st.expander("🔐 Change Password"):
                st.markdown("Update your password below:")
                
                # Use unique form key to prevent conflicts
                form_key = f"change_password_form_{user_ctx.username}"
                
                with st.form(form_key):
                    current_pw = st.text_input("Current Password", type="password")
                    new_pw = st.text_input("New Password", type="password")
                    confirm_pw = st.text_input("Confirm New Password", type="password")
                    submitted = st.form_submit_button("Update Password")

                    if submitted:
                        self._handle_password_change(user_ctx, current_pw, new_pw, confirm_pw)
            
            st.markdown("</div>", unsafe_allow_html=True)

    def _handle_password_change(self, user_ctx: UserCtx, current_pw: str, 
                              new_pw: str, confirm_pw: str) -> None:
        """Handle password change submission"""
        # Create password change request
        request = PasswordChangeRequest(current_pw, new_pw, confirm_pw)
        
        # Validate request format
        is_valid, error_msg = request.validate()
        if not is_valid:
            st.warning(f"⚠️ {error_msg}")
            return

        try:
            # Verify current password
            if not self.db.verify_user_password(user_ctx.username, current_pw):
                st.error("❌ Current password is incorrect.")
                return

            # Validate new password strength
            valid, message = self.db.validate_password_strength(new_pw)
            if not valid:
                st.warning(f"⚠️ {message}")
                return

            # Update password
            if self.db.change_user_password(user_ctx.email, new_pw):
                st.success("✅ Password updated successfully!")
            else:
                st.error("❌ Could not update password. Please try again later.")

        except Exception as e:
            logger.error(f"Error changing password: {e}")
            st.error("❌ Could not update password. Please try again later.")

class LogoutSection(UIComponent):
    """Logout section component"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render logout section"""
        st.markdown("---")
        if st.button("🚪 Logout"):
            SessionManager.logout_user()
            st.switch_page("pages/Login.py")

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class ProfileApplication:
    """Main profile application with component-based architecture"""
    
    def __init__(self):
        self.cfg = UIConfig()
        self.db = DatabaseManager()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.style_manager = StyleManager(self.cfg, self.db)
        self.account_info = AccountInfoDisplay(self.cfg, self.db)
        self.bio_form = BioUpdateForm(self.cfg, self.db)
        self.password_form = PasswordChangeForm(self.cfg, self.db)
        self.logout_section = LogoutSection(self.cfg, self.db)
    
    def run(self) -> None:
        """Main application entry point"""
        # Apply styling
        self.style_manager.render(None)
        
        # Validate authentication
        user_ctx = SessionManager.validate_authentication()
        
        # Render page content
        self._render_content(user_ctx)
    
    def _render_content(self, user_ctx: UserCtx) -> None:
        """Render main page content"""
        # Page title
        st.title(f"{self.cfg.page_icon} {self.cfg.page_title}")
        st.markdown("---")
        
        # Render components
        self.account_info.render(user_ctx)
        self.bio_form.render(user_ctx)
        self.password_form.render(user_ctx)
        self.logout_section.render(user_ctx)

def main() -> None:
    """Application main function"""
    try:
        app = ProfileApplication()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("Application failed to load. Please try again.")

if __name__ == "__main__":
    main()
