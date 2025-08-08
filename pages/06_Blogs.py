from __future__ import annotations

import datetime
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Advanced Type Definitions and Protocols                                   #
# --------------------------------------------------------------------------- #
class BlogOperationProtocol(Protocol):
    """Protocol for blog database operations"""
    def save_blog_entry(self, blog_data: Dict[str, Any]) -> Optional[int]: ...
    def get_all_blogs(self) -> List[Dict[str, Any]]: ...
    def update_blog(self, blog_id: int, data: Dict[str, Any]) -> bool: ...
    def delete_blog(self, blog_id: int) -> bool: ...

class UserRole(Enum):
    """Enhanced user role enumeration"""
    ARTIST = "artist"
    CUSTOMER = "customer"
    
    @classmethod
    def from_string(cls, role_str: str) -> 'UserRole':
        """Convert string to UserRole with validation"""
        try:
            return cls(role_str.lower())
        except ValueError:
            logger.warning(f"Unknown user role: {role_str}")
            return cls.CUSTOMER

@dataclass(frozen=True)
class UIConfiguration:
    """Immutable UI configuration dataclass"""
    page_title: str = "Art Community Blogs"
    page_icon: str = "🎨"
    layout: str = "wide"
    upload_dir: str = "uploads"
    allowed_file_types: List[str] = None
    
    def __post_init__(self):
        if self.allowed_file_types is None:
            object.__setattr__(self, 'allowed_file_types', ["jpg", "jpeg", "png"])

@dataclass
class UserContext:
    """User context information"""
    username: str
    role: UserRole
    is_authenticated: bool = True
    
    @classmethod
    def from_session_state(cls) -> Optional['UserContext']:
        """Create UserContext from session state with validation"""
        if "user" not in st.session_state or not st.session_state.get("logged_in", False):
            return None
        
        user_data = st.session_state.user
        return cls(
            username=user_data.get("username", ""),
            role=UserRole.from_string(user_data.get("user_type", "customer")),
            is_authenticated=True
        )

@dataclass
class BlogEntry:
    """Comprehensive blog entry data structure"""
    blog_id: str
    title: str
    content: str
    author: str
    timestamp: str
    image_path: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlogEntry':
        """Create BlogEntry from dictionary"""
        return cls(
            blog_id=str(data.get('id', '')),
            title=data.get('title', 'Untitled'),
            content=data.get('content', ''),
            author=data.get('author', 'Unknown'),
            timestamp=data.get('timestamp', ''),
            image_path=data.get('image')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        return {
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "image_path": self.image_path,
            "date": self.timestamp
        }

# --------------------------------------------------------------------------- #
#  Fixed File Manager                                                         #
# --------------------------------------------------------------------------- #
class FileManager:
    """Fixed file operations manager"""
    
    def __init__(self, config: UIConfiguration):
        self.config = config
        self.operations_available = True
        try:
            from utils import save_uploaded_file, delete_file
            self.save_uploaded_file = save_uploaded_file
            self.delete_file = delete_file
            logger.info("File operations initialized successfully")
        except ImportError as e:
            logger.error(f"File utilities not available: {e}")
            self.operations_available = False
            st.error(f"File operations not available: {e}")
    
    def save_blog_image(self, image_file: Any) -> Optional[str]:
        """Save blog image using database file manager"""
        if not image_file or not self.operations_available:
            return None
        
        try:
            return self.save_uploaded_file(image_file, "blogs")
        except Exception as e:
            logger.error(f"Error saving blog image: {e}")
            st.error(f"Error saving image: {e}")
            return None
    
    def delete_file_if_exists(self, filepath: Optional[str]) -> None:
        """Delete file if it exists"""
        if not filepath or not self.operations_available:
            return
        
        try:
            self.delete_file(filepath)
        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {e}")

# --------------------------------------------------------------------------- #
#  Fixed Blog Manager                                                         #
# --------------------------------------------------------------------------- #
class BlogManager:
    """Fixed blog operations manager with proper error handling"""
    
    def __init__(self, config: UIConfiguration):
        self.config = config
        self.operations_available = True
        try:
            from utils import save_blog_entry, get_all_blogs, update_blog, delete_blog
            self.save_blog_entry = save_blog_entry
            self.get_all_blogs = get_all_blogs
            self.update_blog = update_blog
            self.delete_blog = delete_blog
            logger.info("Database blog operations initialized successfully")
        except ImportError as e:
            logger.error(f"Blog utilities not available: {e}")
            self.operations_available = False
            st.error(f"Database operations not available: {e}")
    
    def load_blogs(self) -> List[BlogEntry]:
        """Load blogs from database with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return []
        
        try:
            raw_blogs = self.get_all_blogs()
            logger.info(f"Loaded {len(raw_blogs)} blogs from database")
            return [BlogEntry.from_dict(blog) for blog in raw_blogs]
        except Exception as e:
            logger.error(f"Error loading blogs: {e}")
            st.error(f"Error loading blogs: {e}")
            return []
    
    def save_blog(self, blog: BlogEntry) -> bool:
        """Save blog to database with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            blog_data = blog.to_dict()
            logger.info(f"Attempting to save blog: {blog_data}")
            result = self.save_blog_entry(blog_data)
            
            if result is not None:
                logger.info(f"Blog saved successfully with ID: {result}")
                return True
            else:
                logger.error("Blog save failed - database returned None")
                st.error("Failed to save blog to database")
                return False
                
        except Exception as e:
            logger.error(f"Error saving blog: {e}")
            st.error(f"Database error: {e}")
            return False
    
    def update_blog_entry(self, blog_id: str, updated_blog: BlogEntry) -> bool:
        """Update existing blog in database"""
        if not self.operations_available:
            return False
        
        try:
            numeric_id = int(blog_id) if blog_id.isdigit() else hash(blog_id) % 2**31
            result = self.update_blog(numeric_id, updated_blog.to_dict())
            if result:
                logger.info(f"Blog {blog_id} updated successfully")
            return result
        except Exception as e:
            logger.error(f"Error updating blog: {e}")
            st.error(f"Error updating blog: {e}")
            return False
    
    def delete_blog_entry(self, blog_id: str) -> bool:
        """Delete blog from database"""
        if not self.operations_available:
            return False
        
        try:
            numeric_id = int(blog_id) if blog_id.isdigit() else hash(blog_id) % 2**31
            result = self.delete_blog(numeric_id)
            if result:
                logger.info(f"Blog {blog_id} deleted successfully")
            return result
        except Exception as e:
            logger.error(f"Error deleting blog: {e}")
            st.error(f"Error deleting blog: {e}")
            return False

# --------------------------------------------------------------------------- #
#  Session Management                                                         #
# --------------------------------------------------------------------------- #
class SessionManager:
    """Session state management with validation"""
    
    @staticmethod
    def validate_authentication() -> Optional[UserContext]:
        """Validate user authentication and return user context"""
        user_context = UserContext.from_session_state()
        if not user_context:
            st.warning("Please log in to view or write blogs.")
            st.stop()
        return user_context
    
    @staticmethod
    def initialize_blog_states() -> None:
        """Initialize blog-specific session states"""
        if "edit_blog_id" not in st.session_state:
            st.session_state.edit_blog_id = None
        if "delete_blog_id" not in st.session_state:
            st.session_state.delete_blog_id = None

# --------------------------------------------------------------------------- #
#  UI Components                                                              #
# --------------------------------------------------------------------------- #
class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, config: UIConfiguration, blog_manager: BlogManager, file_manager: FileManager):
        self.config = config
        self.blog_manager = blog_manager
        self.file_manager = file_manager
    
    @abstractmethod
    def render(self, user_context: UserContext) -> None:
        """Render the UI component"""
        pass

class StyleManager(UIComponent):
    """Handles CSS styling with form-in-dropdown support"""
    
    def render(self, user_context: UserContext) -> None:
        """Apply comprehensive brown CSS styling with dropdown form support"""
        st.markdown("""
        <style>
        :root {
            --primary: #8B4513;
            --secondary: #A0522D;
            --accent: #5C4033;
            --light: #F8F4E8;
            --dark: #343434;
            --glass-bg: rgba(255, 255, 255, 0.9);
            --shadow: 0 8px 32px rgba(139, 69, 19, 0.1);
            --brown-light: #D2B48C;
            --brown-medium: #CD853F;
            --brown-dark: #8B4513;
            --brown-darker: #5C4033;
            --brown-lightest: #F5DEB3;
        }
        
        .stApp {
            background: linear-gradient(160deg, #f5f1e8 0%, #e8e0d0 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: var(--dark);
        }
        
        /* FORM CONTAINER INSIDE DROPDOWN - Enhanced */
        .form-container {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.4), rgba(210, 180, 140, 0.25));
            border-radius: 16px;
            border: 2px solid rgba(139, 69, 19, 0.2);
            margin: 1.5rem 0;
            box-shadow: 0 4px 15px rgba(139, 69, 19, 0.15);
        }
        
        /* Enhanced Expander Styling for Form Dropdown */
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            font-size: 1rem !important;
            transition: all 0.4s ease !important;
            text-align: center !important;
            margin-bottom: 0 !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.25) !important;
        }
        
        .streamlit-expanderHeader:hover {
            background: linear-gradient(135deg, var(--accent), var(--primary)) !important;
            transform: scale(1.02) translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(139, 69, 19, 0.35) !important;
        }
        
        div[data-testid="stExpander"] {
            border: 2px solid rgba(139, 69, 19, 0.2) !important;
            border-radius: 16px !important;
            overflow: hidden !important;
            margin: 2rem 0 !important;
            box-shadow: 0 8px 25px rgba(139, 69, 19, 0.2) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.1), rgba(210, 180, 140, 0.05)) !important;
        }
        
        /* Blog Container - BROWN THEMED */
        .blog-container {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border: 2px solid var(--brown-light);
            border-radius: 16px;
            margin: 1rem 0;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .blog-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(139, 69, 19, 0.25);
        }
        
        /* Blog Title - NO WHITE BOX */
        .blog-title {
            color: var(--secondary);
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
            border-bottom: 3px solid var(--primary);
            background: linear-gradient(135deg, var(--accent), var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }
        
        /* Blog Meta Information */
        .blog-meta {
            color: var(--secondary);
            font-size: 0.9rem;
            margin-bottom: 1.2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            align-items: center;
            border-bottom: 1px solid rgba(160, 82, 45, 0.2);
            font-weight: 500;
        }
        
        .blog-meta span {
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        
        /* Blog Content */
        .blog-content {
            color: var(--dark);
            line-height: 1.7;
            margin: 1.5rem 0;
            font-size: 1rem;
            text-align: justify;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border-radius: 8px;
            border-left: 4px solid var(--primary);
            border: 1px solid rgba(139, 69, 19, 0.1);
        }
        
        /* Blog Image Styling */
        .blog-image {
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.25);
            transition: transform 0.4s ease;
            margin-bottom: 1.2rem;
            width: 100%;
            object-fit: cover;
            border: 2px solid var(--brown-light);
        }
        
        .blog-image:hover {
            transform: scale(1.02);
        }
        
        /* ALL BROWN BUTTONS - Enhanced Styling */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            border: 2px solid var(--brown-medium) !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            font-size: 0.95rem !important;
            box-shadow: 
                0 6px 18px rgba(139, 69, 19, 0.35),
                inset 0 2px 0 rgba(245, 222, 179, 0.3) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, var(--accent), var(--brown-dark)) !important;
            transform: translateY(-4px) scale(1.08) !important;
            box-shadow: 
                0 10px 30px rgba(139, 69, 19, 0.45),
                inset 0 2px 0 rgba(245, 222, 179, 0.4) !important;
            border-color: var(--brown-light) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0) scale(0.98) !important;
            box-shadow: 0 3px 12px rgba(139, 69, 19, 0.4) !important;
        }
        
        .stButton > button:focus {
            outline: none !important;
            box-shadow: 
                0 6px 18px rgba(139, 69, 19, 0.35),
                0 0 0 4px rgba(139, 69, 19, 0.25) !important;
        }
        
        /* Form Styling - ALL BROWN */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {
            border-radius: 10px !important;
            border: 2px solid var(--brown-light) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.8), rgba(255, 255, 255, 0.9)) !important;
            transition: all 0.3s ease !important;
            color: var(--brown-darker) !important;
            font-weight: 500 !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stSelectbox > div > div > select:focus,
        .stNumberInput > div > div > input:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(139, 69, 19, 0.15) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.9), white) !important;
            outline: none !important;
        }
        
        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder {
            color: var(--brown-medium) !important;
            font-style: italic !important;
        }
        
        /* File Uploader - ALL BROWN */
        .stFileUploader {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2)) !important;
            border: 3px dashed var(--secondary) !important;
            border-radius: 16px !important;
            text-align: center !important;
            transition: all 0.3s ease !important;
        }
        
        .stFileUploader:hover {
            border-color: var(--primary) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.4), rgba(210, 180, 140, 0.3)) !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.2) !important;
        }
        
        /* Success/Info/Warning/Error alerts - ALL BROWN */
        .stAlert {
            border-radius: 12px !important;
            border: 2px solid !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15) !important;
            margin: 1rem 0 !important;
        }
        
        .stSuccess {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(160, 82, 45, 0.05)) !important;
            border-color: var(--brown-medium) !important;
            color: var(--brown-darker) !important;
        }
        
        .stError {
            background: linear-gradient(135deg, rgba(92, 64, 51, 0.15), rgba(139, 69, 19, 0.1)) !important;
            border-color: var(--accent) !important;
            color: var(--brown-darker) !important;
        }
        
        .stWarning {
            background: linear-gradient(135deg, rgba(205, 133, 63, 0.15), rgba(210, 180, 140, 0.1)) !important;
            border-color: var(--brown-medium) !important;
            color: var(--brown-darker) !important;
        }
        
        .stInfo {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(245, 222, 179, 0.2)) !important;
            border-color: var(--primary) !important;
            color: var(--brown-darker) !important;
        }
        
        /* Role Badge - ALL BROWN VARIATIONS */
        .role-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-left: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.3);
            transition: all 0.2s ease;
            border: 2px solid rgba(139, 69, 19, 0.3);
        }
        
        .role-badge:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 18px rgba(139, 69, 19, 0.4);
        }
        
        .role-artist {
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white;
            border-color: var(--brown-medium);
        }
        
        .role-customer {
            background: linear-gradient(135deg, var(--secondary), var(--brown-medium));
            color: white;
            border-color: var(--brown-dark);
        }
        
        /* Spinner - BROWN */
        .stSpinner > div {
            border-color: var(--primary) transparent var(--primary) transparent !important;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            font-style: italic;
            color: var(--secondary);
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.5), rgba(210, 180, 140, 0.3));
            border-radius: 16px;
            border: 2px dashed var(--secondary);
            margin: 2rem 0;
        }
        
        .empty-state::before {
            content: "📝";
            display: block;
            font-size: 3rem;
            margin-bottom: 1rem;
            color: var(--brown-medium);
        }
        
        /* Custom brown elements */
        .brown-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--primary), var(--secondary), var(--primary), transparent);
            margin: 2rem 0;
            border-radius: 1px;
        }
        
        .brown-card {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border: 2px solid var(--brown-light);
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
        }
        
        /* Headers - ALL BROWN */
        h1, h2, h3, h4, h5, h6 {
            color: var(--brown-darker) !important;
            font-weight: 700 !important;
        }
        
        h1 {
            background: linear-gradient(135deg, var(--accent), var(--primary)) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
        }
        
        h2 {
            color: var(--primary) !important;
            border-bottom: 2px solid var(--brown-light) !important;
        }
        
        /* Writing Tips Section */
        .writing-tips {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.08), rgba(210, 180, 140, 0.1));
            border-radius: 12px;
            border-left: 4px solid var(--primary);
            margin-top: 1rem;
        }
        
        .writing-tips h4 {
            color: var(--accent) !important;
            margin-bottom: 1rem !important;
        }
        
        .writing-tips ul {
            margin: 0;
        }
        
        .writing-tips li {
            color: var(--brown-darker);
            margin-bottom: 0.5rem;
            line-height: 1.5;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .form-container {
            }
            
            .blog-title {
                font-size: 1.5rem;
            }
            
            .blog-meta {
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
            }
            
            .blog-container {
                margin-bottom: 1.5rem;
                border-radius: 12px;
            }
            
            .stButton > button {
                font-size: 0.9rem !important;
            }
            
            .streamlit-expanderHeader {
                font-size: 0.9rem !important;
            }
        }
        
        /* Animation for loading states */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .blog-container, .form-container {
            animation: fadeInUp 0.4s ease-out;
        }
        
        /* Scrollbar Styling - ALL BROWN */
        ::-webkit-scrollbar {
            width: 12px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--brown-lightest);
            border-radius: 6px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, var(--secondary), var(--primary));
            border-radius: 6px;
            border: 2px solid var(--brown-lightest);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, var(--primary), var(--accent));
        }
        </style>
        """, unsafe_allow_html=True)

class BlogUploadForm(UIComponent):
    """Blog upload form component - NOW IN DROPDOWN"""
    
    def render(self, user_context: UserContext) -> None:
        """Render blog upload form in dropdown/expander"""
        if user_context.role != UserRole.ARTIST:
            return
        
        # Header with brown styling
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown('<h2 style="color: var(--accent);">📝 Share Your Artistic Journey</h2>', unsafe_allow_html=True)
        with col2:
            role_class = f"role-{user_context.role.value}"
            st.markdown(f'<span class="role-badge {role_class}">{user_context.role.value.title()}</span>', 
                       unsafe_allow_html=True)
        
        st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
        
        # FORM IN DROPDOWN - as requested
        with st.expander("✍️ Create New Blog Post", expanded=False):
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            
            # Initialize form counter in session state
            if 'blog_form_counter' not in st.session_state:
                st.session_state.blog_form_counter = 0
            
            # Use session state counter for unique form key
            form_key = f"blog_upload_{user_context.username}_form_{st.session_state.blog_form_counter}"
            
            with st.form(form_key, clear_on_submit=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    title = st.text_input(
                        "Blog Title*", 
                        placeholder="My journey with watercolor painting...",
                        help="Choose a compelling title that captures your artistic experience"
                    )
                    content = st.text_area(
                        "Content*", 
                        height=200,
                        placeholder="Share your story, techniques, inspiration, challenges you overcame...",
                        help="Write about your artistic process, what inspired you, challenges you faced"
                    )
                
                with col2:
                    image_file = st.file_uploader(
                        "Featured Image (Optional)", 
                        type=self.config.allowed_file_types,
                        help="Add an image to make your blog post more engaging"
                    )
                    
                    st.markdown('<div class="writing-tips">', unsafe_allow_html=True)
                    st.markdown("#### 💡 Blog Writing Tips")
                    st.markdown("""
                    - Share your creative process
                    - Discuss challenges & solutions
                    - Include techniques you learned
                    - Inspire fellow artists
                    - Be authentic and personal
                    - Tell your story with emotion
                    """)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                submitted = st.form_submit_button("📤 Publish Blog", use_container_width=True)
                
                if submitted:
                    success = self._handle_blog_submission(user_context, title, content, image_file)
                    if success:
                        # Increment counter to prevent form key conflicts
                        st.session_state.blog_form_counter += 1
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def _handle_blog_submission(self, user_context: UserContext, title: str, content: str, image_file: Any) -> bool:
        """Handle blog submission with proper error handling"""
        # Enhanced validation
        validation_errors = []
        
        if not title or len(title.strip()) < 5:
            validation_errors.append("Title must be at least 5 characters long")
        
        if not content or len(content.strip()) < 50:
            validation_errors.append("Content must be at least 50 characters long")
        
        # Display validation errors
        if validation_errors:
            for error in validation_errors:
                st.error(f"❌ {error}")
            return False
        
        try:
            with st.spinner("🔄 Publishing blog..."):
                # Save image if provided
                image_path = None
                if image_file:
                    image_path = self.file_manager.save_blog_image(image_file)
                    if not image_path:
                        st.warning("⚠️ Image upload failed, but blog will still be published")
                
                # Create blog entry
                blog_entry = BlogEntry(
                    blog_id=f"{user_context.username}_{int(time.time())}",
                    title=title.strip(),
                    content=content.strip(),
                    author=user_context.username,
                    timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    image_path=image_path
                )
                
                # Save to database
                if self.blog_manager.save_blog(blog_entry):
                    st.success("✅ Blog published successfully!")
                    st.balloons()
                    return True
                else:
                    st.error("❌ Failed to save blog. Please check database connection.")
                    return False
                    
        except Exception as e:
            logger.error(f"Error submitting blog: {e}")
            st.error(f"❌ Failed to publish blog: {str(e)}")
            return False

class BlogDisplay(UIComponent):
    """Blog display component with brown theme"""
    
    def render(self, user_context: UserContext) -> None:
        """Render blog display with brown styling"""
        try:
            blogs = self.blog_manager.load_blogs()
        except Exception as e:
            logger.error(f"Error loading blogs: {e}")
            st.error(f"Error loading blogs: {e}")
            return
        
        if not blogs:
            st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
            st.markdown("## 🎨 Art Community Blogs")
            st.markdown('<div class="empty-state brown-card">', unsafe_allow_html=True)
            st.markdown("### No blogs available yet")
            st.markdown("📝 Be the first to share your artistic journey!")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
        st.markdown("## 🎨 Art Community Blogs")
        st.markdown(f"*📚 {len(blogs)} inspiring stories from our artist community*")
        
        # Display blogs in reverse order (newest first)
        for idx, blog in enumerate(reversed(blogs)):
            self._render_blog_entry(blog, user_context, len(blogs) - 1 - idx)
    
    def _render_blog_entry(self, blog: BlogEntry, user_context: UserContext, blog_index: int) -> None:
        """Render individual blog entry with brown theme"""
        st.markdown('<div class="blog-container">', unsafe_allow_html=True)
        
        # Blog header with brown styling
        st.markdown(f'<div class="blog-title">{blog.title}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="blog-meta"><span>✍️ {blog.author}</span><span>📅 {blog.timestamp[:10]}</span></div>',
            unsafe_allow_html=True
        )
        
        # Blog image with brown styling
        if blog.image_path and os.path.exists(blog.image_path):
            st.image(blog.image_path, use_container_width=True, caption="")
        
        # Edit mode or display mode
        if st.session_state.edit_blog_id == blog.blog_id:
            self._render_edit_form(blog, user_context)
        else:
            st.markdown(f'<div class="blog-content">{blog.content}</div>', unsafe_allow_html=True)
            
            # Show edit/delete buttons for author
            if (user_context.role == UserRole.ARTIST and 
                blog.author == user_context.username):
                st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
                self._render_blog_controls(blog)
        
        # Delete confirmation
        self._render_delete_confirmation(blog)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
    
    def _render_blog_controls(self, blog: BlogEntry) -> None:
        """Render blog edit/delete controls with brown styling"""
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✏️ Edit", key=f"edit_{blog.blog_id}"):
                st.session_state.edit_blog_id = blog.blog_id
                st.rerun()
        
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{blog.blog_id}"):
                st.session_state.delete_blog_id = blog.blog_id
                st.rerun()
    
    def _render_edit_form(self, blog: BlogEntry, user_context: UserContext) -> None:
        """Render blog edit form with brown styling"""
        edit_form_key = f"edit_{blog.blog_id}_{user_context.username}"
        
        st.markdown('<div class="brown-card">', unsafe_allow_html=True)
        st.markdown("### ✏️ Edit Blog")
        
        with st.form(edit_form_key):
            new_title = st.text_input("Edit Title", value=blog.title)
            new_content = st.text_area("Edit Content", value=blog.content, height=200)
            new_image_file = st.file_uploader(
                "Replace Image (Optional)",
                type=self.config.allowed_file_types
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)
            with col2:
                cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if submit_edit:
                self._handle_blog_update(blog, new_title, new_content, new_image_file)
            
            if cancel_edit:
                st.session_state.edit_blog_id = None
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _handle_blog_update(self, original_blog: BlogEntry, new_title: str, new_content: str, new_image_file: Any) -> None:
        """Handle blog update with enhanced validation"""
        # Validation
        if not new_title or len(new_title.strip()) < 5:
            st.error("❌ Title must be at least 5 characters long")
            return
        
        if not new_content or len(new_content.strip()) < 50:
            st.error("❌ Content must be at least 50 characters long")
            return
        
        try:
            with st.spinner("🔄 Updating blog..."):
                updated_blog = BlogEntry(
                    blog_id=original_blog.blog_id,
                    title=new_title.strip(),
                    content=new_content.strip(),
                    author=original_blog.author,
                    timestamp=original_blog.timestamp,
                    image_path=original_blog.image_path
                )
                
                # Handle new image if provided
                if new_image_file:
                    self.file_manager.delete_file_if_exists(original_blog.image_path)
                    new_image_path = self.file_manager.save_blog_image(new_image_file)
                    if new_image_path:
                        updated_blog.image_path = new_image_path
                    else:
                        st.warning("⚠️ Image upload failed, keeping existing image")
                
                # Update in database
                if self.blog_manager.update_blog_entry(original_blog.blog_id, updated_blog):
                    st.success("✅ Blog updated successfully!")
                    st.session_state.edit_blog_id = None
                    st.rerun()
                else:
                    st.error("❌ Failed to update blog")
                    
        except Exception as e:
            logger.error(f"Error updating blog: {e}")
            st.error(f"❌ Failed to update blog: {str(e)}")
    
    def _render_delete_confirmation(self, blog: BlogEntry) -> None:
        """Render delete confirmation dialog with brown styling"""
        if st.session_state.delete_blog_id == blog.blog_id:
            st.markdown('<div class="brown-card">', unsafe_allow_html=True)
            st.warning("⚠️ Are you sure you want to delete this blog? This action cannot be undone.")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("✅ Yes, Delete", key=f"confirm_delete_{blog.blog_id}"):
                    try:
                        self.file_manager.delete_file_if_exists(blog.image_path)
                        
                        if self.blog_manager.delete_blog_entry(blog.blog_id):
                            st.success("✅ Blog deleted successfully.")
                            st.session_state.delete_blog_id = None
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete blog")
                    except Exception as e:
                        logger.error(f"Error deleting blog: {e}")
                        st.error(f"❌ Failed to delete blog: {str(e)}")
            
            with col2:
                if st.button("❌ Cancel", key=f"cancel_delete_{blog.blog_id}"):
                    st.session_state.delete_blog_id = None
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Main Blog Application                                                      #
# --------------------------------------------------------------------------- #
class BlogApplication:
    """Fixed main blog application with form in dropdown"""
    
    def __init__(self):
        self.config = UIConfiguration()
        
        # Initialize managers with proper error handling
        self.blog_manager = BlogManager(self.config)
        self.file_manager = FileManager(self.config)
        
        # Initialize UI components
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.style_manager = StyleManager(self.config, self.blog_manager, self.file_manager)
        self.upload_form = BlogUploadForm(self.config, self.blog_manager, self.file_manager)
        self.blog_display = BlogDisplay(self.config, self.blog_manager, self.file_manager)
    
    def run(self) -> None:
        """Main application entry point with brown theme"""
        try:
            # Apply brown styling
            self.style_manager.render(None)
            
            # Validate authentication
            user_context = SessionManager.validate_authentication()
            
            # Initialize session states
            SessionManager.initialize_blog_states()
            
            # App header with brown theme
            st.markdown('<div class="brown-card" style="text-align: center; padding: 2rem; margin-bottom: 2rem;">', unsafe_allow_html=True)
            st.markdown('<h1 style="color: var(--accent);">🎨 Brush and Soul Blogs</h1>', unsafe_allow_html=True)
            st.markdown('<p style="color: var(--secondary); font-size: 1.1rem; font-weight: 600;">Where Artists Share Their Creative Journey</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Render components - form in dropdown, then blog display
            self.upload_form.render(user_context)
            self.blog_display.render(user_context)
            
            # Footer with brown theme
            st.markdown("""
            <div class="brown-card" style="text-align: center; padding: 2rem; margin-top: 2rem;">
                <h3 style="color: var(--accent);">🎨 Brush and Soul Community</h3>
                <p style="color: var(--secondary); font-weight: 600; font-size: 1.1rem;">Create • Share • Inspire • Connect</p>
                <p style="font-size: 0.95rem; color: var(--brown-darker); font-weight: 500;">
                    Building bridges between traditional art and modern storytelling
                </p>
                <div style="margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(210, 180, 140, 0.1)); border-radius: 8px; border: 1px solid var(--brown-light);">
                    <p style="color: var(--primary); font-weight: 600; margin: 0;">
                        ✨ Every story matters, every artist has a voice ✨
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"❌ Application error: {e}")

# --------------------------------------------------------------------------- #
#  Application Entry Point                                                    #
# --------------------------------------------------------------------------- #
def main() -> None:
    """Application main function with page configuration"""
    st.set_page_config(
        page_title="Brush and Soul - Blogs",
        page_icon="🎨",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    try:
        app = BlogApplication()
        app.run()
    except Exception as e:
        logger.error(f"Main application error: {e}")
        st.error("❌ Application failed to load. Please try again.")

if __name__ == "__main__":
    main()
