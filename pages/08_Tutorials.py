import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Protocol
from dataclasses import dataclass, field
from enum import Enum
import logging
from functools import wraps, lru_cache
from contextlib import contextmanager
import weakref

# Advanced type definitions
class VideoType(Enum):
    """Enum for supported video types"""
    MP4 = "mp4"
    MOV = "mov"
    WEBM = "webm"
    AVI = "avi"

class UserRole(Enum):
    """User role enumeration"""
    ARTIST = "artist"
    CUSTOMER = "customer"

@dataclass
class TutorialData:
    """Dataclass for tutorial data with validation"""
    creator: str
    title: str
    content: str
    video_path: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-init validation"""
        self.title = self.title.strip()
        self.content = self.content.strip()
        if not self.title:
            raise ValueError("Title cannot be empty")
        if not self.content:
            raise ValueError("Content cannot be empty")

class DatabaseProtocol(Protocol):
    """Protocol for database operations"""
    def save_tutorial(self, tutorial_data: Dict[str, Any]) -> Optional[int]: ...
    def get_all_tutorials(self) -> List[Dict[str, Any]]: ...
    def update_tutorial(self, tutorial_id: int, data: Dict[str, Any]) -> bool: ...
    def delete_tutorial(self, tutorial_id: int) -> bool: ...

class TutorialError(Exception):
    """Custom exception for tutorial operations"""
    pass

class ValidationError(TutorialError):
    """Exception for validation errors"""
    pass

def handle_tutorial_errors(func):
    """Decorator for error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            st.error(f"Validation Error: {e}")
            return None
        except TutorialError as e:
            st.error(f"Tutorial Error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            st.error(f"An unexpected error occurred: {e}")
            return None
    return wrapper

class TutorialCache:
    """Advanced caching with weak references"""
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
        self._access_order: List[str] = []
    
    @contextmanager
    def cache_context(self, key: str):
        """Context manager for cache operations"""
        try:
            yield self._cache.get(key)
        finally:
            self._update_access_order(key)
    
    def _update_access_order(self, key: str):
        """LRU cache implementation"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        if len(self._access_order) > self._max_size:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

class SingletonMeta(type):
    """Metaclass for singleton pattern"""
    _instances: Dict[type, weakref.ReferenceType] = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = weakref.ref(instance)
            return instance
        else:
            ref = cls._instances[cls]
            instance = ref()
            if instance is None:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = weakref.ref(instance)
            return instance

class TutorialManager(metaclass=SingletonMeta):
    """Advanced tutorial management with singleton pattern and caching"""
    
    def __init__(self):
        self._cache = TutorialCache()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @lru_cache(maxsize=128)
    def get_tutorials(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get tutorials with advanced caching"""
        cache_key = f"tutorials_{datetime.now().strftime('%Y-%m-%d-%H')}"
        
        if not force_refresh:
            with self._cache.cache_context(cache_key) as cached_data:
                if cached_data:
                    self._logger.info("Returning cached tutorials")
                    return cached_data
        
        try:
            from utils import get_all_tutorials
            tutorials = get_all_tutorials()
            self._cache._cache[cache_key] = tutorials
            return tutorials
        except ImportError as e:
            raise TutorialError(f"Database utilities not available: {e}")
    
    @handle_tutorial_errors
    def create_tutorial(self, tutorial_data: TutorialData) -> Optional[int]:
        """Create tutorial with advanced error handling"""
        try:
            from utils import save_tutorial
            
            data_dict = {
                'creator': tutorial_data.creator,
                'title': tutorial_data.title,
                'content': tutorial_data.content,
                'video_path': tutorial_data.video_path
            }
            
            result = save_tutorial(data_dict)
            if result:
                # Invalidate cache
                self.get_tutorials.cache_clear()
                self._cache._cache.clear()
            
            return result
        except Exception as e:
            raise TutorialError(f"Failed to save tutorial: {e}")

class AdvancedTutorialInterface:
    """Advanced UI with design patterns - ALL BROWN COLORS"""
    
    _styles_applied: bool = False
    
    @classmethod
    def apply_styles(cls):
        """Apply enhanced CSS with ALL BROWN COLORS throughout"""
        if cls._styles_applied:
            return
        
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
        
        /* Tutorial Container - REMOVED WHITE BACKGROUND */
        .tutorial-container {
            background: transparent !important;
            border-radius: 16px;
            box-shadow: none !important;
            margin-bottom: 2rem;
            border: none !important;
            backdrop-filter: none !important;
            transition: transform 0.2s ease;
            padding: 1rem 0;
        }
        
        .tutorial-container:hover {
            transform: translateY(-2px);
        }
        
        /* Glass effect for forms and cards */
        .glass {
            background: var(--glass-bg);
            border-radius: 16px;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
            border: 1px solid rgba(139, 69, 19, 0.1);
            backdrop-filter: blur(10px);
        }
        
        /* Tutorial Title - NO WHITE BOX */
        .tutorial-title {
            color: var(--secondary);
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
            padding-bottom: 0.5rem;
            border-bottom: 3px solid var(--primary);
            background: linear-gradient(135deg, var(--accent), var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
            box-shadow: none !important;
            border-radius: 0 !important;
            backdrop-filter: none !important;
        }
        
        /* Tutorial Meta Information */
        .tutorial-meta {
            color: var(--secondary);
            font-size: 0.9rem;
            margin-bottom: 1.2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            align-items: center;
            border-bottom: 1px solid rgba(160, 82, 45, 0.2);
            background: transparent !important;
            padding-bottom: 0.5rem;
        }
        
        .tutorial-meta span {
            display: flex;
            align-items: center;
            gap: 0.3rem;
            font-weight: 500;
        }
        
        /* Tutorial Content */
        .tutorial-content {
            color: var(--dark);
            line-height: 1.7;
            margin: 1.5rem 0;
            font-size: 1rem;
            text-align: justify;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid var(--primary);
            border: 1px solid rgba(139, 69, 19, 0.1);
        }
        
        /* Content Preview */
        .content-preview {
            color: var(--dark);
            line-height: 1.6;
            margin: 1rem 0;
            font-size: 1rem;
            background: linear-gradient(135deg, rgba(205, 133, 63, 0.2), rgba(160, 82, 45, 0.15));
            padding: 0.8rem;
            border-radius: 8px;
            border-left: 3px solid var(--secondary);
            text-align: justify;
            border: 1px solid rgba(160, 82, 45, 0.2);
        }
        
        /* Video Container Styling */
        .stVideo {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: var(--shadow);
            margin: 1rem 0 1.5rem 0;
            border: 2px solid var(--brown-light);
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 3rem 2rem;
            font-style: italic;
            color: var(--secondary);
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.5), rgba(210, 180, 140, 0.3));
            border-radius: 12px;
            border: 2px dashed var(--secondary);
            margin: 2rem 0;
        }
        
        .empty-state::before {
            content: "📚";
            display: block;
            font-size: 3rem;
            margin-bottom: 1rem;
            color: var(--brown-medium);
        }
        
        /* Role Badge - ALL BROWN VARIATIONS */
        .role-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.5rem 1rem;
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
        
        /* ALL BROWN BUTTONS - Enhanced Styling */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            border: 2px solid var(--brown-medium) !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            padding: 14px 28px !important;
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
            padding: 2rem !important;
            text-align: center !important;
            transition: all 0.3s ease !important;
        }
        
        .stFileUploader:hover {
            border-color: var(--primary) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.4), rgba(210, 180, 140, 0.3)) !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.2) !important;
        }
        
        /* Expander Styling - ALL BROWN */
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, var(--brown-light), var(--brown-lightest)) !important;
            border-radius: 10px !important;
            border: 2px solid var(--brown-medium) !important;
            color: var(--brown-darker) !important;
            font-weight: 700 !important;
            transition: all 0.3s ease !important;
        }
        
        .streamlit-expanderHeader:hover {
            background: linear-gradient(135deg, var(--brown-medium), var(--brown-light)) !important;
            border-color: var(--primary) !important;
            color: white !important;
            transform: scale(1.02) !important;
        }
        
        div[data-testid="stExpander"] {
            border: 2px solid var(--brown-light) !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            margin: 1rem 0 !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15) !important;
            background: rgba(245, 222, 179, 0.1) !important;
        }
        
        /* Status Messages - BROWN THEMED */
        .status-message {
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin: 1rem 0;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border: 2px solid;
        }
        
        .status-success {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(160, 82, 45, 0.05));
            border-left: 6px solid var(--brown-medium);
            border-color: var(--brown-medium);
            color: var(--brown-darker);
        }
        
        .status-error {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.15), rgba(92, 64, 51, 0.1));
            border-left: 6px solid var(--accent);
            border-color: var(--accent);
            color: var(--brown-darker);
        }
        
        .status-warning {
            background: linear-gradient(135deg, rgba(205, 133, 63, 0.15), rgba(210, 180, 140, 0.1));
            border-left: 6px solid var(--brown-medium);
            border-color: var(--brown-medium);
            color: var(--brown-darker);
        }
        
        .status-info {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(245, 222, 179, 0.2));
            border-left: 6px solid var(--primary);
            border-color: var(--primary);
            color: var(--brown-darker);
        }
        
        /* Button Container Centering */
        .button-container {
            display: flex;
            justify-content: center;
            margin: 1.5rem 0;
            padding: 1rem;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.2), rgba(210, 180, 140, 0.1));
            border-radius: 12px;
            border: 1px solid var(--brown-light);
        }
        
        /* Spinner - BROWN */
        .stSpinner > div {
            border-color: var(--primary) transparent var(--primary) transparent !important;
        }
        
        /* Success/Info/Warning/Error alerts - ALL BROWN */
        .stAlert {
            border-radius: 12px !important;
            border: 2px solid !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15) !important;
            margin: 1rem 0 !important;
            padding: 1rem 1.5rem !important;
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
        
        /* Sidebar - ALL BROWN */
        .css-1d391kg {
            background: linear-gradient(180deg, var(--brown-lightest), var(--brown-light)) !important;
            border-right: 3px solid var(--brown-medium) !important;
        }
        
        /* Links - BROWN */
        a, a:visited, a:hover {
            color: var(--primary) !important;
            text-decoration: none !important;
            font-weight: 600 !important;
        }
        
        a:hover {
            color: var(--accent) !important;
            text-decoration: underline !important;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .tutorial-title {
                font-size: 1.5rem;
            }
            
            .tutorial-meta {
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
            }
            
            .role-badge {
                margin-left: 0;
                margin-top: 0.5rem;
            }
            
            .tutorial-container {
                padding: 1rem;
            }
            
            .stButton > button {
                padding: 12px 20px !important;
                font-size: 0.9rem !important;
            }
            
            .button-container {
                padding: 0.5rem;
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
        
        .tutorial-container {
            animation: fadeInUp 0.3s ease-out;
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
            padding-bottom: 0.5rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        cls._styles_applied = True
    
    @staticmethod
    def render_status(message: str, status_type: str = "success", tutorial_id: Optional[int] = None):
        """Advanced status message rendering with brown theme"""
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        icon = icon_map.get(status_type, "ℹ️")
        id_text = f" (ID: {tutorial_id})" if tutorial_id else ""
        
        st.markdown(f"""
        <div class="status-message status-{status_type}">
            {icon} <strong>{message}</strong>{id_text}
        </div>
        """, unsafe_allow_html=True)

class SmartTutorialValidator:
    """Advanced validation with custom rules and regex"""
    
    @staticmethod
    def validate_tutorial(title: str, content: str, video_file, video_url: str) -> List[str]:
        """Advanced validation with multiple checks"""
        errors = []
        
        # Title validation with advanced rules
        if not title or len(title.strip()) < 5:
            errors.append("Title must be at least 5 characters")
        elif len(title.strip()) > 255:
            errors.append("Title must be less than 255 characters")
        elif not any(c.isalnum() for c in title):
            errors.append("Title must contain at least one alphanumeric character")
        
        # Content validation
        if not content or len(content.strip()) < 20:
            errors.append("Content must be at least 20 characters")
        elif len(content.strip()) > 5000:
            errors.append("Content must be less than 5000 characters")
        
        # Video validation
        if not video_file and not video_url.strip():
            errors.append("Please provide a video file or URL")
        elif video_url.strip() and not SmartTutorialValidator._is_valid_url(video_url.strip()):
            errors.append("Please provide a valid video URL")
        
        return errors
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Advanced URL validation"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))

# Initialize advanced components
tutorial_manager = TutorialManager()
tutorial_interface = AdvancedTutorialInterface()

# Page configuration with advanced options
st.set_page_config(
    page_title="Art Tutorials | Brush and Soul",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply ALL BROWN styling
tutorial_interface.apply_styles()

# Authentication with advanced error handling
if "user" not in st.session_state or not st.session_state.get("logged_in", False):
    st.warning("🔐 Please login to access tutorials.")
    st.stop()

current_user = st.session_state.user.get("username", "Unknown")
user_role = st.session_state.user.get("user_type", "customer").lower()

# Import utilities with protocol checking
try:
    from utils import save_tutorial, get_all_tutorials, update_tutorial, delete_tutorial, save_uploaded_file
except ImportError:
    st.error("❌ Database connection error.")
    st.stop()

# Advanced header with animation and role display
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="tutorial-container"><h1 class="tutorial-title">🎓 Advanced Art Tutorials</h1></div>', 
               unsafe_allow_html=True)
with col2:
    role_class = f"role-{user_role}"
    st.markdown(f'<span class="role-badge {role_class}">{user_role.title()}</span>', 
               unsafe_allow_html=True)

# Tutorial Upload Form - ONLY FOR ARTISTS
if user_role == "artist":
    with st.expander("➕ Share a New Tutorial", expanded=False):
        with st.form("tutorial_form", clear_on_submit=True):
            st.markdown("### 📝 Create New Tutorial")
            
            title = st.text_input("Tutorial Title*", max_chars=255, 
                                 help="Choose a descriptive title that captures your tutorial's essence")
            content = st.text_area("Tutorial Content*", height=200, max_chars=5000,
                                  help="Share detailed instructions, tips, and techniques")
            
            col1, col2 = st.columns(2)
            with col1:
                video_file = st.file_uploader("Upload Video", 
                                            type=[vtype.value for vtype in VideoType],
                                            help="Supported formats: MP4, MOV, WEBM, AVI")
            with col2:
                video_url = st.text_input("OR Video URL",
                                        help="YouTube, Vimeo, or direct video links")
            
            submitted = st.form_submit_button("📤 Publish Tutorial", 
                                            use_container_width=True)
            
            if submitted:
                # Advanced validation
                errors = SmartTutorialValidator.validate_tutorial(title, content, video_file, video_url)
                
                if errors:
                    for error in errors:
                        tutorial_interface.render_status(error, "error")
                else:
                    try:
                        # Handle video with progress
                        video_path = None
                        with st.spinner("Processing video..."):
                            if video_file:
                                video_path = save_uploaded_file(video_file, "tutorials")
                                if not video_path:
                                    tutorial_interface.render_status("Failed to upload video file", "error")
                                    st.stop()
                            elif video_url.strip():
                                video_path = video_url.strip()
                        
                        # Create tutorial data object
                        tutorial_data = TutorialData(
                            creator=current_user,
                            title=title,
                            content=content,
                            video_path=video_path
                        )
                        
                        # Save using advanced manager
                        with st.spinner("Publishing tutorial..."):
                            result = tutorial_manager.create_tutorial(tutorial_data)
                        
                        if result:
                            tutorial_interface.render_status("Tutorial published successfully!", "success", result)
                            st.balloons()
                            st.rerun()
                        else:
                            tutorial_interface.render_status("Failed to save tutorial", "error")
                            
                    except ValidationError as ve:
                        tutorial_interface.render_status(f"Validation Error: {ve}", "error")
                    except TutorialError as te:
                        tutorial_interface.render_status(f"Tutorial Error: {te}", "error")
                    except Exception as e:
                        tutorial_interface.render_status(f"Unexpected Error: {e}", "error")

# Brown divider
st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
st.markdown("## 📚 Available Tutorials")

try:
    with st.spinner("Loading tutorials..."):
        tutorials = tutorial_manager.get_tutorials()
    
    if tutorials:
        for idx, tutorial in enumerate(tutorials):
            # Tutorial container - brown themed
            st.markdown('<div class="tutorial-container brown-card">', unsafe_allow_html=True)
            
            # Tutorial header with enhanced styling - NO WHITE BOX
            title = tutorial.get('title', 'Untitled')
            creator = tutorial.get('creator', 'Unknown')
            date = tutorial.get('created_at', 'Unknown')
            
            st.markdown(f'<div class="tutorial-title">{title}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tutorial-meta">✍️ {creator} &nbsp;&nbsp; 📅 {date}</div>', 
                       unsafe_allow_html=True)
            
            # Advanced video handling FIRST
            video_path = tutorial.get('video_path')
            if video_path:
                try:
                    st.video(video_path)
                except Exception:
                    tutorial_interface.render_status("Could not load video", "warning")
            
            # Content with brown read more functionality BELOW VIDEO
            content = tutorial.get('content', '')
            max_preview_chars = 200
            
            # Initialize session state for this specific tutorial
            read_more_key = f"read_more_{idx}"
            if read_more_key not in st.session_state:
                st.session_state[read_more_key] = False
            
            # Show content preview or full content with BROWN BUTTONS
            if not st.session_state[read_more_key]:
                if len(content) > max_preview_chars:
                    preview_content = content[:max_preview_chars].rsplit(' ', 1)[0] + "..."
                    st.markdown(f'<div class="content-preview">{preview_content}</div>', 
                               unsafe_allow_html=True)
                    
                    # BROWN READ MORE BUTTON BELOW VIDEO (CENTERED)
                    st.markdown('<div class="button-container">', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([2, 1, 2])
                    with col2:  # Center the button
                        if st.button("📖 Read More", key=f"read_more_btn_{idx}", 
                                    help="Click to read the full tutorial content"):
                            st.session_state[read_more_key] = True
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="tutorial-content">{content}</div>', 
                               unsafe_allow_html=True)
            else:
                # Show full content
                st.markdown(f'<div class="tutorial-content">{content}</div>', 
                           unsafe_allow_html=True)
                
                # BROWN SHOW LESS BUTTON (CENTERED)
                st.markdown('<div class="button-container">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:  # Center the button
                    if st.button("📖 Show Less", key=f"show_less_btn_{idx}",
                                help="Click to collapse the content"):
                        st.session_state[read_more_key] = False
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Creator controls with advanced UI - ONLY FOR TUTORIAL CREATORS
            if tutorial.get('creator') == current_user and user_role == "artist":
                st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("✏️ Edit", key=f"edit_{idx}"):
                        st.session_state[f"editing_{idx}"] = True
                
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{idx}", 
                               help="This action cannot be undone"):
                        with st.spinner("Deleting tutorial..."):
                            if delete_tutorial(tutorial.get('id')):
                                tutorial_interface.render_status("Deleted successfully!", "success")
                                st.rerun()
                            else:
                                tutorial_interface.render_status("Delete failed", "error")
                
                # Advanced edit form
                if st.session_state.get(f"editing_{idx}", False):
                    with st.form(f"edit_form_{idx}"):
                        new_title = st.text_input("Title", value=title)
                        new_content = st.text_area("Content", value=content, height=150)
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_changes = st.form_submit_button("💾 Save Changes")
                        with col_cancel:
                            cancel_edit = st.form_submit_button("❌ Cancel")
                        
                        if save_changes:
                            update_data = {
                                'title': new_title.strip(),
                                'content': new_content.strip(),
                                'creator': creator,
                                'video_path': video_path
                            }
                            
                            with st.spinner("Updating tutorial..."):
                                if update_tutorial(tutorial.get('id'), update_data):
                                    tutorial_interface.render_status("Updated successfully!", "success")
                                    del st.session_state[f"editing_{idx}"]
                                    st.rerun()
                                else:
                                    tutorial_interface.render_status("Update failed", "error")
                        
                        if cancel_edit:
                            del st.session_state[f"editing_{idx}"]
                            st.rerun()
            
            # Show tutorial interaction for customers
            elif user_role == "customer":
                st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("👍 Helpful", key=f"helpful_{idx}", help="Mark this tutorial as helpful"):
                        st.success("Thanks for your feedback! 👍")
                with col2:
                    st.markdown("*💡 Find this tutorial helpful? Let the artist know!*")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
            
    else:
        st.markdown('<div class="empty-state brown-card">', unsafe_allow_html=True)
        if user_role == "artist":
            st.markdown("### No tutorials available")
            st.markdown("📝 Be the first to share your knowledge!")
        else:
            st.markdown("### No tutorials available yet")
            st.markdown("📚 Check back soon for new content from our artists!")
        st.markdown('</div>', unsafe_allow_html=True)
        
except Exception as e:
    tutorial_interface.render_status(f"Error loading tutorials: {e}", "error")

# Brown divider
st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)

# Advanced footer with role-specific messaging
if user_role == "artist":
    st.markdown("*💡 Share your artistic knowledge and help fellow artists grow! Your tutorials make a difference.*")
else:
    st.markdown("*🎨 Explore tutorials created by talented artists and enhance your artistic journey!*")

# Additional footer with brown-themed styling
st.markdown("""
<div class="brown-card" style="text-align: center; padding: 2rem; margin-top: 2rem;">
    <h3 style="color: var(--accent);">🎨 Brush and Soul Tutorials</h3>
    <p style="color: var(--secondary); font-weight: 600; font-size: 1.1rem;">Learn • Create • Share • Inspire</p>
    <p style="font-size: 0.95rem; color: var(--brown-darker); font-weight: 500;">
        Preserving traditional art techniques through modern technology
    </p>
    <div style="margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(210, 180, 140, 0.1)); border-radius: 8px; border: 1px solid var(--brown-light);">
        <p style="color: var(--primary); font-weight: 600; margin: 0;">
            🌟 Join our community of traditional artists and art enthusiasts 🌟
        </p>
    </div>
</div>
""", unsafe_allow_html=True)
