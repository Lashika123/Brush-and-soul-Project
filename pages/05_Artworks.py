from __future__ import annotations
import datetime
import logging
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  TYPE DEFINITIONS & PROTOCOLS
# ─────────────────────────────────────────────────────────────────────────────
class FileOperationProtocol(Protocol):
    """Protocol for file operations"""
    def save_uploaded_file(self, file: Any, subdirectory: str = "") -> Optional[str]: ...
    def delete_file(self, filepath: str) -> bool: ...

class ArtworkOperationProtocol(Protocol):
    """Protocol for artwork database operations"""
    def save_artwork(self, artwork_data: Dict[str, Any]) -> Optional[int]: ...
    def get_artist_artworks(self, username: str) -> List[Dict[str, Any]]: ...
    def update_artwork(self, artwork_id: int, updates: Dict[str, Any]) -> bool: ...
    def remove_artwork(self, artwork_id: int) -> bool: ...
    def add_to_cart(self, username: str, item: Dict[str, Any]) -> bool: ...
    def get_all_artworks(self) -> List[Dict[str, Any]]: ...

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
    page_title: str = "🎨 Artworks Gallery"
    columns_count: int = 3
    uploads_directory: str = "uploads"
    max_file_size_mb: int = 10
    allowed_file_types: List[str] = field(default_factory=lambda: ["png", "jpg", "jpeg"])

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
class ArtworkData:
    """Comprehensive artwork data structure"""
    title: str
    artist: str
    price: float
    description: str = ""
    materials: str = ""
    state: str = ""
    style: str = ""
    image_path: Optional[str] = None
    upload_date: str = field(default_factory=lambda: str(datetime.date.today()))
    artwork_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        return {
            "id": self.artwork_id,
            "title": self.title,
            "artist": self.artist,
            "description": self.description,
            "materials": self.materials,
            "state": self.state,
            "style": self.style,
            "price": self.price,
            "image": self.image_path,
            "upload_date": self.upload_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtworkData':
        """Create ArtworkData from dictionary"""
        return cls(
            artwork_id=data.get('id'),
            title=data.get('title', 'Untitled'),
            artist=data.get('artist', 'Unknown Artist'),
            description=data.get('description', ''),
            materials=data.get('materials', ''),
            state=data.get('state', ''),
            style=data.get('style', ''),
            price=float(data.get('price', 0)),
            image_path=data.get('image'),
            upload_date=data.get('upload_date', str(datetime.date.today()))
        )

# ─────────────────────────────────────────────────────────────────────────────
#  FILE MANAGER - FIXED
# ─────────────────────────────────────────────────────────────────────────────
class FileManager:
    """FIXED - File operations manager with comprehensive error handling"""
    
    def __init__(self, config: UIConfiguration):
        self.config = config
        self._ensure_uploads_directory()
        self.operations_available = True
        try:
            from utils import save_uploaded_file
            self.save_uploaded_file_util = save_uploaded_file
            logger.info("File operations initialized successfully")
        except ImportError as e:
            logger.error(f"File utilities not available: {e}")
            self.operations_available = False
            st.error(f"File operations not available: {e}")
    
    def _ensure_uploads_directory(self) -> None:
        """Ensure uploads directory exists"""
        uploads_path = Path(self.config.uploads_directory)
        uploads_path.mkdir(exist_ok=True)
    
    def save_uploaded_file(self, file: Any, username: str) -> Optional[str]:
        """FIXED - Save uploaded file with enhanced error handling"""
        if not file:
            logger.warning("No file provided to save")
            return None
        
        if not self.operations_available:
            logger.error("File operations not available")
            st.error("File operations are not available")
            return None
        
        # Validate file size (max 10MB)
        if hasattr(file, 'size') and file.size > self.config.max_file_size_mb * 1024 * 1024:
            error_msg = f"File size too large. Maximum {self.config.max_file_size_mb}MB allowed."
            logger.error(error_msg)
            st.error(error_msg)
            return None
        
        try:
            logger.info(f"Saving file: {file.name} for user: {username}")
            result = self.save_uploaded_file_util(file, "artworks")
            if result:
                logger.info(f"File saved successfully: {result}")
                return result
            else:
                logger.error("File save utility returned None")
                return None
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            st.error(f"Error saving file: {e}")
            return None
    
    def file_exists(self, filepath: Optional[str]) -> bool:
        """Check if file exists safely"""
        if not filepath:
            return False
        return Path(filepath).exists()

    def delete_file(self, filepath: str) -> bool:
        """Delete file if it exists"""
        try:
            if filepath and Path(filepath).exists():
                Path(filepath).unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {e}")
            return False

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE MANAGER - FIXED
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """FIXED - Database operations manager with comprehensive error handling"""
    
    def __init__(self):
        self._operations = self._initialize_database_operations()
        if not self._operations:
            logger.error("Failed to initialize database operations")
            st.error("Failed to initialize database operations. Please check your database connection.")
    
    def _initialize_database_operations(self) -> Optional[ArtworkOperationProtocol]:
        """FIXED - Initialize database operations with proper error handling"""
        try:
            from utils import (save_artwork, get_artist_artworks, update_artwork, 
                             remove_artwork, add_to_cart, get_all_artworks)
            
            class DatabaseOperations:
                def save_artwork(self, artwork_data: Dict[str, Any]) -> Optional[int]:
                    logger.info(f"DatabaseOperations.save_artwork called with: {artwork_data}")
                    result = save_artwork(artwork_data)
                    logger.info(f"save_artwork result: {result}")
                    return result
                
                def get_artist_artworks(self, username: str) -> List[Dict[str, Any]]:
                    result = get_artist_artworks(username)
                    logger.info(f"get_artist_artworks called for {username}, found {len(result)} artworks")
                    return result
                
                def update_artwork(self, artwork_id: int, updates: Dict[str, Any]) -> bool:
                    return update_artwork(artwork_id, updates)
                
                def remove_artwork(self, artwork_id: int) -> bool:
                    return remove_artwork(artwork_id)
                
                def add_to_cart(self, username: str, item: Dict[str, Any]) -> bool:
                    return add_to_cart(username, item)
                
                def get_all_artworks(self) -> List[Dict[str, Any]]:
                    result = get_all_artworks()
                    logger.info(f"get_all_artworks called, found {len(result)} artworks")
                    return result
            
            logger.info("Database operations initialized successfully")
            return DatabaseOperations()
            
        except ImportError as e:
            logger.error(f"Failed to import database utilities: {e}")
            st.error(f"Database import error: {e}")
            return None
    
    def create_artwork(self, artwork: ArtworkData) -> bool:
        """FIXED - Create new artwork in database with comprehensive error handling"""
        if not self._operations:
            logger.error("Database operations not available")
            st.error("Database operations not available")
            return False
            
        try:
            # Prepare artwork data
            artwork_dict = artwork.to_dict()
            
            # Remove None artwork_id for new artworks
            if 'id' in artwork_dict and artwork_dict['id'] is None:
                del artwork_dict['id']
            
            logger.info(f"Attempting to save artwork to database: {artwork_dict}")
            
            # Call database operation
            result = self._operations.save_artwork(artwork_dict)
            
            logger.info(f"Database save result: {result}")
            
            # Check result thoroughly
            if result is not None and isinstance(result, int) and result > 0:
                logger.info(f"✅ Artwork saved successfully with ID: {result}")
                return True
            else:
                logger.error(f"❌ Database save failed - result: {result}")
                st.error("Failed to save artwork to database")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception in create_artwork: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            st.error(f"Database error: {e}")
            return False
    
    def fetch_artist_artworks(self, username: str) -> List[ArtworkData]:
        """Fetch artworks for specific artist"""
        if not self._operations:
            logger.error("Database operations not available")
            return []
            
        try:
            raw_artworks = self._operations.get_artist_artworks(username)
            logger.info(f"Fetched {len(raw_artworks)} artworks for artist {username}")
            artworks = [ArtworkData.from_dict(art) for art in raw_artworks]
            return artworks
        except Exception as e:
            logger.error(f"Error fetching artist artworks: {e}")
            st.error(f"Error fetching artworks: {e}")
            return []
    
    def fetch_all_artworks(self) -> List[ArtworkData]:
        """Fetch all artworks from database"""
        if not self._operations:
            logger.error("Database operations not available")
            return []
            
        try:
            raw_artworks = self._operations.get_all_artworks()
            logger.info(f"Fetched {len(raw_artworks)} total artworks")
            artworks = [ArtworkData.from_dict(art) for art in raw_artworks]
            return artworks
        except Exception as e:
            logger.error(f"Error fetching all artworks: {e}")
            st.error(f"Error fetching artworks: {e}")
            return []
    
    def update_artwork_data(self, artwork_id: int, artwork: ArtworkData) -> bool:
        """Update existing artwork"""
        if not self._operations:
            return False
            
        try:
            artwork_dict = artwork.to_dict()
            result = self._operations.update_artwork(artwork_id, artwork_dict)
            if result:
                logger.info(f"Artwork {artwork_id} updated successfully")
            return result
        except Exception as e:
            logger.error(f"Error updating artwork: {e}")
            st.error(f"Error updating artwork: {e}")
            return False
    
    def delete_artwork_data(self, artwork_id: int) -> bool:
        """Delete artwork from database"""
        if not self._operations:
            return False
            
        try:
            result = self._operations.remove_artwork(artwork_id)
            if result:
                logger.info(f"Artwork {artwork_id} deleted successfully")
            return result
        except Exception as e:
            logger.error(f"Error deleting artwork: {e}")
            st.error(f"Error deleting artwork: {e}")
            return False
    
    def add_artwork_to_cart(self, username: str, artwork: ArtworkData) -> bool:
        """Add artwork to user's cart"""
        if not self._operations:
            return False
            
        try:
            artwork_dict = artwork.to_dict()
            # Ensure proper format for cart
            artwork_dict['title'] = artwork.title  # Map title for cart compatibility
            result = self._operations.add_to_cart(username, artwork_dict)
            if result:
                logger.info(f"Artwork {artwork.title} added to cart for {username}")
            return result
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            st.error(f"Error adding to cart: {e}")
            return False

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
class SessionManager:
    """Advanced session state management with validation"""
    
    @staticmethod
    def validate_authentication() -> Optional[UserContext]:
        """Validate user authentication and return user context"""
        user_context = UserContext.from_session_state()
        if not user_context:
            st.warning("Please login to view or upload artworks.")
            st.stop()
        return user_context
    
    @staticmethod
    def initialize_edit_forms(artworks: List[ArtworkData]) -> None:
        """Initialize edit form toggle states"""
        if 'show_edit_form' not in st.session_state:
            st.session_state['show_edit_form'] = {}
        
        for artwork in artworks:
            if artwork.artwork_id is not None and artwork.artwork_id not in st.session_state['show_edit_form']:
                st.session_state['show_edit_form'][artwork.artwork_id] = False
    
    @staticmethod
    def toggle_edit_form(artwork_id: int) -> None:
        """Toggle edit form visibility for specific artwork"""
        if 'show_edit_form' not in st.session_state:
            st.session_state['show_edit_form'] = {}
        
        current_state = st.session_state['show_edit_form'].get(artwork_id, False)
        st.session_state['show_edit_form'][artwork_id] = not current_state

# ─────────────────────────────────────────────────────────────────────────────
#  UI COMPONENTS - FULLY FIXED
# ─────────────────────────────────────────────────────────────────────────────
class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, config: UIConfiguration, db_manager: DatabaseManager, file_manager: FileManager):
        self.config = config
        self.db_manager = db_manager
        self.file_manager = file_manager
    
    @abstractmethod
    def render(self, user_context: UserContext) -> None:
        """Render the UI component"""
        pass

class StyleManager(UIComponent):
    """Handles comprehensive brown CSS styling - FULLY CORRECTED VERSION"""
    
    def render(self, user_context: UserContext) -> None:
        """Apply comprehensive brown CSS styling with all corrections"""
        st.markdown("""
        <style>
        :root {
            --primary: #8B4513;
            --secondary: #A0522D;
            --accent: #5C4033;
            --light: #F8F4E8;
            --dark: #343434;
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
        
        /* Main Title with Gradient */
        .main-title {
            color: var(--accent) !important;
            font-size: 2.8rem;
            font-weight: 800;
            text-align: center !important;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent), var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }
        
        .title-divider {
            width: 80%;
            height: 4px;
            background: linear-gradient(90deg, transparent 0%, var(--primary) 20%, var(--secondary) 50%, var(--accent) 80%, transparent 100%);
            margin: 1rem auto 2rem auto;
            border-radius: 2px;
            box-shadow: 0 2px 4px rgba(139, 69, 19, 0.2);
        }
        
        /* Enhanced Art Card - TRANSPARENT DESIGN */
        .art-card {
            background: transparent !important;
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: none !important;
            border: none !important;
            backdrop-filter: none !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
            position: relative;
            animation: fadeInUp 0.6s ease-out;
        }
        
        .art-card:hover {
            transform: translateY(-8px) scale(1.02);
        }
        
        /* Art Card Image Container - ENHANCED */
        .art-card img {
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.25);
            transition: transform 0.4s ease;
            margin-bottom: 1.2rem;
            width: 100%;
            object-fit: cover;
            height: 220px;
        }
        
        .art-card:hover img {
            transform: scale(1.05);
        }
        
        /* Enhanced Art Title - NO WHITE BOX */
        .art-title {
            color: var(--accent) !important;
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            line-height: 1.3;
            background: linear-gradient(135deg, var(--accent), var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.3px;
            text-align: center !important;
            border-bottom: 3px solid var(--primary);
        }
        
        /* Enhanced Artist Name */
        .art-artist {
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: var(--secondary) !important;
            font-style: italic;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-align: left !important;
        }
        
        /* Enhanced Price Display */
        .art-price {
            font-weight: 800;
            font-size: 1.4rem;
            color: var(--primary) !important;
            margin: 1rem 0;
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(160, 82, 45, 0.15));
            border-radius: 12px;
            border-left: 4px solid var(--primary);
            display: inline-block;
            text-shadow: none;
            box-shadow: 0 2px 8px rgba(139, 69, 19, 0.1);
            font-family: 'Inter', monospace;
            letter-spacing: 0.5px;
            text-align: left !important;
        }
        
        /* No Image Placeholder - CORRECTED */
        .no-image-placeholder {
            width: 100%;
            height: 220px;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.4), rgba(210, 180, 140, 0.3));
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--secondary);
            font-style: italic;
            font-size: 1.1rem;
            border: 2px dashed var(--secondary);
            margin-bottom: 1.2rem;
            transition: all 0.3s ease;
            text-align: center !important;
        }
        
        .no-image-placeholder:hover {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.5), rgba(210, 180, 140, 0.4));
            border-color: var(--primary);
        }
        
        /* CORRECTED BUTTONS - Add to Cart */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            border-radius: 12px !important;
            border: 2px solid var(--primary) !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            width: 100% !important;
            margin: 0.8rem 0 !important;
            cursor: pointer !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.25) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            min-height: 48px !important;
            text-align: center !important;
            display: block !important;
            position: relative !important;
            z-index: 1 !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, var(--accent), var(--primary)) !important;
            transform: translateY(-3px) scale(1.03) !important;
            box-shadow: 0 8px 25px rgba(139, 69, 19, 0.35) !important;
            border-color: var(--accent) !important;
        }
        
        .stButton > button:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 4px 15px rgba(139, 69, 19, 0.3) !important;
        }
        
        .stButton > button:focus {
            outline: 3px solid var(--primary) !important;
            outline-offset: 2px !important;
        }
        
        /* Enhanced Expander - CORRECTED */
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 12px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            font-size: 0.9rem !important;
            transition: all 0.3s ease !important;
            text-align: center !important;
            margin-top: 1rem !important;
        }
        
        .streamlit-expanderHeader:hover {
            background: linear-gradient(135deg, var(--accent), var(--primary)) !important;
            transform: scale(1.02) !important;
        }
        
        div[data-testid="stExpander"] {
            border: 2px solid rgba(139, 69, 19, 0.15) !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            margin: 1rem 0 !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.1) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.15), rgba(210, 180, 140, 0.1)) !important;
        }
        
        /* Details Section - CORRECTED */
        .details-section {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.25), rgba(210, 180, 140, 0.15));
            border-radius: 12px;
            border: 1px solid rgba(139, 69, 19, 0.15);
            margin: 1rem 0;
            box-shadow: inset 0 2px 4px rgba(139, 69, 19, 0.1);
        }
        
        .detail-item {
            padding: 1rem;
            margin-bottom: 1.2rem;
            border-bottom: 1px solid rgba(139, 69, 19, 0.15);
            transition: background-color 0.2s ease;
        }
        
        .detail-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        
        .detail-item:hover {
            background-color: rgba(245, 222, 179, 0.1);
            border-radius: 8px;
            margin: 0 -0.5rem 1.2rem -0.5rem;
        }
        
        .detail-label {
            font-weight: 700;
            color: var(--accent);
            font-size: 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-align: left !important;
        }
        
        .detail-value {
            color: var(--dark);
            line-height: 1.7;
            text-align: justify !important;
            text-justify: inter-word !important;
            font-size: 0.95rem;
        }
        
        /* Description Special Styling - ENHANCED */
        .description-content {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.6), rgba(245, 222, 179, 0.3));
            border-radius: 10px;
            border-left: 4px solid var(--primary);
            text-align: justify !important;
            text-justify: inter-word !important;
            line-height: 1.7;
            margin-top: 0.5rem;
            box-shadow: 0 2px 8px rgba(139, 69, 19, 0.1);
            font-size: 0.95rem;
        }
        
        /* Form Container - ENHANCED */
        .form-container {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border-radius: 12px;
            border: 1px solid rgba(139, 69, 19, 0.2);
            margin: 1rem 0;
        }
        
        /* Form Styling - IMPROVED */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            border-radius: 10px !important;
            border: 2px solid var(--brown-light) !important;
            background: rgba(255, 255, 255, 0.95) !important;
            font-size: 1rem !important;
            transition: all 0.3s ease !important;
            color: var(--dark) !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stNumberInput > div > div > input:focus,
        .stSelectbox > div > div > select:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px rgba(139, 69, 19, 0.15) !important;
            background: white !important;
            outline: none !important;
        }
        
        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder {
            color: var(--brown-medium) !important;
            font-style: italic !important;
        }
        
        /* File Uploader - ENHANCED */
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
        
        /* Brown Cards */
        .brown-card {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border: 2px solid var(--brown-light);
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
        }
        
        /* Gallery Header */
        .gallery-header {
            color: var(--primary) !important;
            font-size: 2rem;
            font-weight: 700;
            text-align: center !important;
            margin-bottom: 1.5rem;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center !important;
            font-style: italic;
            color: var(--secondary);
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.5), rgba(210, 180, 140, 0.3));
            border-radius: 16px;
            border: 2px dashed var(--secondary);
            margin: 2rem 0;
        }
        
        .empty-state::before {
            content: "🎨";
            display: block;
            font-size: 3rem;
            margin-bottom: 1rem;
            color: var(--secondary);
        }
        
        /* Mobile Responsiveness - ENHANCED */
        @media (max-width: 768px) {
            .main-title {
                font-size: 2.2rem;
            }
            
            .art-card {
                margin-bottom: 1.5rem;
            }
            
            .art-title {
                font-size: 1.4rem;
            }
            
            .art-price {
                font-size: 1.2rem;
                padding: 0.6rem 1rem;
            }
            
            .stButton > button {
                font-size: 0.9rem !important;
                min-height: 44px !important;
            }
        }
        
        /* Animation */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .art-card {
            animation: fadeInUp 0.6s ease-out;
        }
        </style>
        """, unsafe_allow_html=True)

class ArtworkUploadForm(UIComponent):
    """COMPLETELY FIXED - Artwork upload form without session state conflicts"""
    
    def render(self, user_context: UserContext) -> None:
        """Render artwork upload form with FIXED session state handling"""
        
        with st.expander("➕ Upload New Artwork", expanded=False):
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            
            # FIXED: Use simple, static form key with clear_on_submit
            form_key = "upload_artwork_form"
            
            with st.form(key=form_key, clear_on_submit=True):  # ✅ Auto-clear form
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input(
                        "Title*", 
                        placeholder="e.g., Sunset Landscape",
                        help="Choose a descriptive title for your artwork"
                        # ✅ No key parameter to avoid session state conflicts
                    )
                    materials = st.text_input(
                        "Materials", 
                        placeholder="e.g., Oil on Canvas",
                        help="Specify the materials and medium used"
                    )
                    state = st.text_input(
                        "State ", 
                        placeholder="e.g., Excellent",
                        help="Describe the condition of the artwork"
                    )
                
                with col2:
                    price = st.number_input(
                        "Price (₹)*", 
                        min_value=0.0, 
                        step=1.0,
                        help="Set a fair price for your artwork"
                    )
                    style = st.text_input(
                        "Art Style ", 
                        placeholder="e.g., Abstract",
                        help="Specify the artistic style or genre"
                    )
                    image_file = st.file_uploader(
                        "Artwork Image*", 
                        type=self.config.allowed_file_types,
                        help="Upload a clear, high-quality image of your artwork"
                    )
                
                description = st.text_area(
                    "Description",
                    height=120,
                    placeholder="Describe your artwork, inspiration, techniques used, story behind it...",
                    help="Provide detailed information to help buyers understand your artwork"
                )
                
                # ✅ Simple submit button
                submitted = st.form_submit_button("🎨 Upload Artwork", use_container_width=True)
                
                # ✅ Handle submission immediately in the form block
                if submitted:
                    # ✅ Comprehensive validation first
                    validation_errors = self._validate_form_data(title, price, image_file)
                    
                    if validation_errors:
                        for error in validation_errors:
                            st.error(f"❌ {error}")
                    else:
                        # ✅ Process submission with detailed logging
                        success = self._process_artwork_submission(
                            user_context, title, price, image_file, description,
                            materials, state, style
                        )
                        
                        if success:
                            st.success("✅ Artwork uploaded successfully!")
                            st.balloons()
                            # ✅ Form will clear automatically due to clear_on_submit=True
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def _validate_form_data(self, title: str, price: float, image_file: Any) -> list:
        """Comprehensive form validation"""
        errors = []
        
        if not title or len(title.strip()) < 3:
            errors.append("Title must be at least 3 characters long")
        
        if not image_file:
            errors.append("Image is required")
        
        if price <= 0:
            errors.append("Price must be greater than 0")
        
        return errors
    
    def _process_artwork_submission(
        self, user_context: UserContext, title: str, price: float,
        image_file: Any, description: str, materials: str, state: str, style: str
    ) -> bool:
        """Process artwork submission with enhanced error handling"""
        
        try:
            logger.info(f"Starting artwork upload for user: {user_context.username}")
            logger.info(f"Artwork data: title={title}, price={price}")
            
            # Save uploaded file first
            image_path = None
            if image_file:
                logger.info(f"Saving image file: {image_file.name}")
                image_path = self.file_manager.save_uploaded_file(image_file, user_context.username)
                if not image_path:
                    logger.error("Failed to save image file")
                    st.error("❌ Failed to save image file")
                    return False
                logger.info(f"Image saved successfully: {image_path}")
            
            # Create artwork data
            artwork = ArtworkData(
                title=title.strip(),
                artist=user_context.username,
                description=description.strip(),
                materials=materials.strip(),
                state=state.strip(),
                style=style.strip(),
                price=price,
                image_path=image_path
            )
            
            # Test database connection first
            logger.info("Testing database connection...")
            if not self.db_manager._operations:
                logger.error("Database operations not available")
                st.error("❌ Database not available. Please check your connection.")
                return False
            
            # Save to database with detailed logging
            logger.info(f"Attempting to save artwork: {artwork.to_dict()}")
            success = self.db_manager.create_artwork(artwork)
            
            if success:
                logger.info("Artwork saved successfully to database")
                return True
            else:
                logger.error("Failed to save artwork to database")
                st.error("❌ Failed to save artwork to database")
                return False
                
        except Exception as e:
            logger.error(f"Exception in artwork submission: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            st.error(f"❌ Upload failed: {str(e)}")
            return False

class ArtworkCard:
    """Individual artwork card component - CORRECTED WITH BUTTON BELOW VIEW DETAILS"""
    
    def __init__(self, config: UIConfiguration, db_manager: DatabaseManager, file_manager: FileManager):
        self.config = config
        self.db_manager = db_manager
        self.file_manager = file_manager
    
    def render_card(self, artwork: ArtworkData, user_context: UserContext, is_artist_view: bool = False) -> None:
        """Render individual artwork card with Add to Cart button BELOW View Details"""
        # Title and artist
        st.markdown(f'<div class="art-title">{artwork.title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="art-artist">🎨 {artwork.artist}</div>', unsafe_allow_html=True)
        
        # Image display
        self._render_artwork_image(artwork)
        
        # Price display
        st.markdown(f'<div class="art-price">₹{artwork.price:.1f}</div>', unsafe_allow_html=True)
        
        # View Details dropdown FIRST
        with st.expander("📋 View Details", expanded=False):
            st.markdown('<div class="details-section">', unsafe_allow_html=True)
            
            # Description
            st.markdown('<div class="detail-item">', unsafe_allow_html=True)
            st.markdown('<div class="detail-label">📝 Description</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="description-content">{artwork.description or "No description provided."}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Materials
            st.markdown('<div class="detail-item">', unsafe_allow_html=True)
            st.markdown('<div class="detail-label">🎨 Materials</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="detail-value">{artwork.materials or "Not specified"}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Artist (for customer view only)
            if not is_artist_view:
                st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                st.markdown('<div class="detail-label">👨‍🎨 Artist</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="detail-value">{artwork.artist}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # State/Condition
            st.markdown('<div class="detail-item">', unsafe_allow_html=True)
            st.markdown('<div class="detail-label">🏷️ State</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="detail-value">{artwork.state or "Not specified"}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Style
            st.markdown('<div class="detail-item">', unsafe_allow_html=True)
            st.markdown('<div class="detail-label">🎭 Style</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="detail-value">{artwork.style or "Not specified"}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Upload Date
            st.markdown('<div class="detail-item">', unsafe_allow_html=True)
            st.markdown('<div class="detail-label">📅 Upload Date</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="detail-value">{artwork.upload_date}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Artist controls (only for artist view)
            if is_artist_view and artwork.artist == user_context.username:
                st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                st.markdown('<div class="detail-label">⚙️ Actions</div>', unsafe_allow_html=True)
                self._render_artist_controls(artwork, user_context)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # MOVED: Add to Cart button BELOW the expander (for customers only)
        if not is_artist_view and user_context.role == UserRole.CUSTOMER:
            if st.button("🛒 Add to Cart", key=f"addtocart_{artwork.artwork_id}_{user_context.username}"):
                if self.db_manager.add_artwork_to_cart(user_context.username, artwork):
                    # Show toast notification
                    st.toast(f"✅ '{artwork.title}' added to cart!", icon="🛒")
                    # Switch to cart page
                    st.switch_page("pages/10_Cart.py")
                else:
                    st.error("❌ Failed to add to cart")
    
    def _render_artwork_image(self, artwork: ArtworkData) -> None:
        """Render artwork image with proper fallback"""
        if artwork.image_path and self.file_manager.file_exists(artwork.image_path):
            st.image(artwork.image_path, use_container_width=True)
        else:
            st.markdown(
                '<div class="no-image-placeholder">🖼️<br>No Image Available</div>',
                unsafe_allow_html=True
            )
    
    def _render_artist_controls(self, artwork: ArtworkData, user_context: UserContext) -> None:
        """Render artist edit/delete controls with corrected styling"""
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✏️ Edit", key=f"edit_{artwork.artwork_id}", use_container_width=True):
                SessionManager.toggle_edit_form(artwork.artwork_id)
        
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{artwork.artwork_id}", use_container_width=True):
                if st.session_state.get(f"confirm_delete_{artwork.artwork_id}", False):
                    if self.db_manager.delete_artwork_data(artwork.artwork_id):
                        st.success("✅ Artwork deleted!")
                        # Reset confirmation
                        st.session_state[f"confirm_delete_{artwork.artwork_id}"] = False
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete artwork")
                else:
                    st.session_state[f"confirm_delete_{artwork.artwork_id}"] = True
                    st.rerun()
        
        # Show confirmation message if delete was clicked
        if st.session_state.get(f"confirm_delete_{artwork.artwork_id}", False):
            st.warning("⚠️ Click Delete again to confirm deletion")
        
        # Show edit form if toggled
        if st.session_state.get('show_edit_form', {}).get(artwork.artwork_id, False):
            st.markdown("---")
            self._render_edit_form(artwork, user_context)
    
    def _render_edit_form(self, artwork: ArtworkData, user_context: UserContext) -> None:
        """Render artwork edit form with proper validation"""
        st.subheader("✏️ Edit Artwork")
        
        with st.form(key=f"edit_form_{artwork.artwork_id}"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_title = st.text_input("Title", value=artwork.title)
                new_materials = st.text_input("Materials", value=artwork.materials)
                new_state = st.text_input("State", value=artwork.state)
            
            with col2:
                new_price = st.number_input("Price (₹)", min_value=0.0, value=float(artwork.price))
                new_style = st.text_input("Art Style", value=artwork.style)
                new_image_file = st.file_uploader(
                    "Change Image (optional)",
                    type=self.config.allowed_file_types
                )
            
            new_description = st.text_area("Description", value=artwork.description)
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if submitted:
                self._handle_edit_submission(artwork, user_context, new_title, new_description,
                                           new_materials, new_state, new_style, new_price, new_image_file)
            
            if cancel:
                st.session_state['show_edit_form'][artwork.artwork_id] = False
                st.rerun()
    
    def _handle_edit_submission(
        self, original_artwork: ArtworkData, user_context: UserContext,
        new_title: str, new_description: str, new_materials: str,
        new_state: str, new_style: str, new_price: float, new_image_file: Any
    ) -> None:
        """Handle edit form submission with proper validation"""
        
        # Validation
        if not new_title or len(new_title.strip()) < 3:
            st.error("❌ Title must be at least 3 characters long")
            return
        
        if new_price <= 0:
            st.error("❌ Price must be greater than 0")
            return
        
        try:
            with st.spinner("🔄 Updating artwork..."):
                # Create updated artwork
                updated_artwork = ArtworkData(
                    artwork_id=original_artwork.artwork_id,
                    title=new_title.strip(),
                    artist=user_context.username,
                    description=new_description.strip(),
                    materials=new_materials.strip(),
                    state=new_state.strip(),
                    style=new_style.strip(),
                    price=new_price,
                    image_path=original_artwork.image_path,  # Keep old image by default
                    upload_date=original_artwork.upload_date
                )
                
                # Handle new image if provided
                if new_image_file:
                    new_image_path = self.file_manager.save_uploaded_file(new_image_file, user_context.username)
                    if new_image_path:
                        updated_artwork.image_path = new_image_path
                    else:
                        st.warning("⚠️ Image upload failed, keeping existing image")
                
                # Update in database
                if self.db_manager.update_artwork_data(original_artwork.artwork_id, updated_artwork):
                    st.success("✅ Artwork updated successfully!")
                    st.session_state['show_edit_form'][original_artwork.artwork_id] = False
                    st.rerun()
                else:
                    st.error("❌ Failed to update artwork")
                    
        except Exception as e:
            logger.error(f"Error updating artwork: {e}")
            st.error("❌ Failed to update artwork. Please try again.")

class ArtworkGallery(UIComponent):
    """Main artwork gallery component - CORRECTED VERSION"""
    
    def render(self, user_context: UserContext) -> None:
        """Render artwork gallery based on user role"""
        if user_context.role == UserRole.ARTIST:
            self._render_artist_view(user_context)
        else:
            self._render_customer_view(user_context)
    
    def _render_artist_view(self, user_context: UserContext) -> None:
        """Render artist's artworks with corrected functionality"""
        st.markdown('<h2 class="gallery-header">Your Artworks</h2>', unsafe_allow_html=True)
        
        try:
            artworks = self.db_manager.fetch_artist_artworks(user_context.username)
            SessionManager.initialize_edit_forms(artworks)
            
            if not artworks:
                st.markdown('<div class="empty-state brown-card">', unsafe_allow_html=True)
                st.markdown("### You haven't uploaded any artworks yet")
                st.markdown("🎨 Use the form above to upload your first artwork!")
                st.markdown('</div>', unsafe_allow_html=True)
                return
            
            st.markdown('<div class="brown-card" style="text-align: center;">', unsafe_allow_html=True)
            st.markdown(f"**📚 Total artworks: {len(artworks)}**")
            st.markdown('</div>', unsafe_allow_html=True)
            
            self._render_artwork_grid(artworks, user_context, is_artist_view=True)
            
        except Exception as e:
            logger.error(f"Error in artist view: {e}")
            st.error(f"❌ Error loading your artworks: {e}")
    
    def _render_customer_view(self, user_context: UserContext) -> None:
        """Render all artworks for customers"""
        st.markdown('<h2 class="gallery-header">Featured Artworks</h2>', unsafe_allow_html=True)
        
        try:
            artworks = self.db_manager.fetch_all_artworks()
            
            if not artworks:
                st.markdown('<div class="empty-state brown-card">', unsafe_allow_html=True)
                st.markdown("### No artworks available yet")
                st.markdown("🎨 Check back soon for amazing artworks from talented artists!")
                st.markdown('</div>', unsafe_allow_html=True)
                return
            
            # No message displayed - clean display of artworks
            
            self._render_artwork_grid(artworks, user_context, is_artist_view=False)
            
        except Exception as e:
            logger.error(f"Error in customer view: {e}")
            st.error(f"❌ Error loading artworks: {e}")
    
    def _render_artwork_grid(self, artworks: List[ArtworkData], user_context: UserContext, is_artist_view: bool) -> None:
        """Render artworks in grid layout"""
        cols = st.columns(self.config.columns_count)
        artwork_card = ArtworkCard(self.config, self.db_manager, self.file_manager)
        
        for idx, artwork in enumerate(artworks):
            col = cols[idx % self.config.columns_count]
            with col:
                with st.container():
                    st.markdown('<div class="art-card">', unsafe_allow_html=True)
                    artwork_card.render_card(artwork, user_context, is_artist_view)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class ArtworkApplication:
    """Main artwork application with corrected components"""
    
    def __init__(self):
        self.config = UIConfiguration()
        self.db_manager = DatabaseManager()
        self.file_manager = FileManager(self.config)
        
        # Initialize UI components
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.style_manager = StyleManager(self.config, self.db_manager, self.file_manager)
        self.upload_form = ArtworkUploadForm(self.config, self.db_manager, self.file_manager)
        self.gallery = ArtworkGallery(self.config, self.db_manager, self.file_manager)
    
    def run(self) -> None:
        """Main application entry point with error handling"""
        try:
            # Apply styling
            self.style_manager.render(None)
            
            # Set page title with horizontal line
            st.markdown(f'<h1 class="main-title">{self.config.page_title}</h1>', unsafe_allow_html=True)
            st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)
            
            # Validate authentication
            user_context = SessionManager.validate_authentication()
            
            # Render appropriate view based on user role
            if user_context.role == UserRole.ARTIST:
                # Upload form in dropdown for artists
                self.upload_form.render(user_context)
            
            # Render gallery for all users
            self.gallery.render(user_context)
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"❌ Application error: {e}")

def main():
    """Application main function"""
    st.set_page_config(
        page_title="Brush and Soul - Artworks",
        page_icon="🎨",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    try:
        app = ArtworkApplication()
        app.run()
    except Exception as e:
        logger.error(f"Main application error: {e}")
        st.error(f"❌ Application failed to start: {e}")

if __name__ == "__main__":
    main()
