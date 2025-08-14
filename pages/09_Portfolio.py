from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  TYPE DEFINITIONS & PROTOCOLS
# ─────────────────────────────────────────────────────────────────────────────
class PortfolioOpsProtocol(Protocol):
    """Database-side operations required by this page."""
    def get_portfolio(self, username: str) -> Optional[Dict[str, Any]]: ...
    def save_portfolio(self, portfolio: Dict[str, Any]) -> Optional[int]: ...
    def update_portfolio(self, data: Dict[str, Any]) -> bool: ...
    def get_artist_artworks(self, username: str) -> List[Dict[str, Any]]: ...
    def save_artwork(self, artwork: Dict[str, Any]) -> Optional[int]: ...
    def update_artwork(self, artwork_id: int, updates: Dict[str, Any]) -> bool: ...
    def remove_artwork(self, artwork_id: int) -> bool: ...
    def get_user_blogs(self, username: str) -> List[Dict[str, Any]]: ...
    def save_blog_entry(self, blog: Dict[str, Any]) -> Optional[int]: ...
    def update_blog(self, blog_id: int, data: Dict[str, Any]) -> bool: ...
    def delete_blog(self, blog_id: int) -> bool: ...
    def get_available_artists(self) -> List[str]: ...
    def add_to_cart(self, username: str, item: Dict[str, Any]) -> bool: ...

class FileOpsProtocol(Protocol):
    """Shared file-utility operations (uploads, deletes, …)."""
    def save_uploaded_file(self, file: Any, subdirectory: str = "") -> Optional[str]: ...

class UserRole(Enum):
    ARTIST = "artist"
    CUSTOMER = "customer"

    @classmethod
    def from_string(cls, raw: str) -> "UserRole":
        try:
            return cls(raw.lower())
        except ValueError:
            return cls.CUSTOMER

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG & DATA MODELS - FIXED
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class UIConfig:
    page_title: str = "🎨 Artist Portfolio"
    page_icon: str = "🎨"
    uploads_dir: str = "uploads"
    allowed_image_types: List[str] = field(default_factory=lambda: ["png", "jpg", "jpeg"])
    max_title_length: int = 100
    max_blog_title_length: int = 150
    columns_count: int = 3

@dataclass
class UserCtx:
    username: str
    role: UserRole
    is_authenticated: bool = True

    @classmethod
    def from_session(cls) -> Optional["UserCtx"]:
        if "user" not in st.session_state or not st.session_state.get("logged_in", False):
            return None
        u = st.session_state.user
        return cls(username=u["username"],
                   role=UserRole.from_string(u.get("user_type", "customer")))

@dataclass
class Portfolio:
    """Strongly-typed representation of a portfolio - FIXED initialization"""
    username: str
    bio: str = ""
    website: str = ""
    last_updated: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Portfolio":
        """Create Portfolio from dictionary with safe defaults"""
        return cls(
            username=d.get('username', ''),
            bio=d.get('bio', ''),
            website=d.get('website', ''),
            last_updated=d.get('last_updated', '')
        )

    @classmethod
    def create_empty(cls, username: str) -> "Portfolio":
        """Create empty portfolio for user - FIXED"""
        return cls(
            username=username,
            bio="",
            website="",
            last_updated=""
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'bio': self.bio,
            'website': self.website,
            'last_updated': self.last_updated
        }

@dataclass
class Artwork:
    """Strongly-typed representation of an artwork."""
    id: Optional[int]
    artist: str
    title: str
    materials: str = ""
    state: str = ""
    style: str = ""
    price: float = 0.0
    image: Optional[str] = None
    description: str = ""
    upload_date: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Artwork":
        return cls(
            id=d.get('id'),
            artist=d.get('artist', ''),
            title=d.get('title', 'Untitled'),
            materials=d.get('materials', ''),
            state=d.get('state', ''),
            style=d.get('style', ''),
            price=float(d.get('price', 0)),
            image=d.get('image'),
            description=d.get('description', ''),
            upload_date=d.get('upload_date', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'artist': self.artist,
            'title': self.title,
            'materials': self.materials,
            'state': self.state,
            'style': self.style,
            'price': self.price,
            'image': self.image,
            'description': self.description,
            'upload_date': self.upload_date
        }

@dataclass
class Blog:
    """Strongly-typed representation of a blog."""
    id: Optional[int]
    author: str
    title: str
    content: str
    image: Optional[str] = None
    timestamp: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Blog":
        return cls(
            id=d.get('id'),
            author=d.get('author', ''),
            title=d.get('title', 'Untitled'),
            content=d.get('content', ''),
            image=d.get('image'),
            timestamp=d.get('timestamp', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'author': self.author,
            'title': self.title,
            'content': self.content,
            'image_path': self.image,  # Map to correct field name
            'date': self.timestamp
        }

# ─────────────────────────────────────────────────────────────────────────────
#  FILE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class FileManager:
    """File operations manager with proper error handling"""
    
    def __init__(self, cfg: UIConfig):
        self.cfg = cfg
        Path(cfg.uploads_dir).mkdir(parents=True, exist_ok=True)
        self.operations_available = True
        try:
            from utils import save_uploaded_file
            self.save_uploaded_file = save_uploaded_file
            logger.info("File operations initialized successfully")
        except ImportError as e:
            logger.error(f"File utilities not available: {e}")
            self.operations_available = False
            st.error(f"File operations not available: {e}")

    def save_image(self, file: Any, subdirectory: str = "") -> Optional[str]:
        """Save uploaded image file with proper error handling"""
        if not file or not self.operations_available:
            return None
        
        try:
            result = self.save_uploaded_file(file, subdirectory)
            if result:
                logger.info(f"Image saved successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            st.error(f"Error saving image: {e}")
            return None

    def get_image_path(self, rel_path: Optional[str]) -> Optional[str]:
        """Get absolute image path with existence check"""
        if not rel_path:
            return None
        
        if os.path.exists(rel_path):
            return rel_path
        
        # Try relative to current directory
        base_dir = Path(__file__).parent
        abs_path = base_dir / rel_path
        return str(abs_path) if abs_path.exists() else None

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE MANAGER - FIXED
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """Database operations manager with proper error handling - FIXED"""
    
    def __init__(self):
        self.operations_available = True
        try:
            from utils import (
                get_portfolio,
                save_portfolio,
                update_portfolio,
                get_artist_artworks,
                save_artwork,
                update_artwork,
                remove_artwork,
                get_user_blogs,
                save_blog_entry,
                update_blog,
                delete_blog,
                get_artists_with_content,
                add_to_cart
            )
            
            self.get_portfolio = get_portfolio
            self.save_portfolio = save_portfolio
            self.update_portfolio = update_portfolio
            self.get_artist_artworks = get_artist_artworks
            self.save_artwork = save_artwork
            self.update_artwork = update_artwork
            self.remove_artwork = remove_artwork
            self.get_user_blogs = get_user_blogs
            self.save_blog_entry = save_blog_entry
            self.update_blog = update_blog
            self.delete_blog = delete_blog
            self.get_artists_with_content = get_artists_with_content
            self.add_to_cart = add_to_cart
            
            logger.info("Database operations initialized successfully")
            
        except ImportError as e:
            logger.error(f"Database utilities not available: {e}")
            self.operations_available = False
            st.error(f"Database operations not available: {e}")

    # FIXED Portfolio operations
    def get_portfolio_data(self, username: str) -> Portfolio:
        """Get portfolio data for user with proper error handling - FIXED"""
        if not self.operations_available:
            st.error("Database operations not available")
            return Portfolio.create_empty(username)
        
        try:
            portfolio_data = self.get_portfolio(username)
            if portfolio_data:
                logger.info(f"Portfolio loaded for user: {username}")
                return Portfolio.from_dict(portfolio_data)
            else:
                logger.info(f"No portfolio found for user: {username}, creating default")
                return Portfolio.create_empty(username)
        except Exception as e:
            logger.error(f"Error fetching portfolio for {username}: {e}")
            st.error(f"Error loading portfolio: {e}")
            return Portfolio.create_empty(username)

    def save_portfolio_data(self, portfolio: Portfolio) -> bool:
        """Save or update portfolio data with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            portfolio.last_updated = datetime.now().strftime("%Y-%m-%d")
            portfolio_dict = portfolio.to_dict()
            logger.info(f"Attempting to save portfolio: {portfolio_dict}")
            
            result = self.save_portfolio(portfolio_dict)
            
            if result is not None:
                logger.info(f"Portfolio saved successfully for user: {portfolio.username}")
                return True
            else:
                logger.error("Portfolio save failed - database returned None")
                st.error("Failed to save portfolio to database")
                return False
                
        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
            st.error(f"Database error: {e}")
            return False

    # Artwork operations -----------------------------------------------------
    def get_artworks_by_artist(self, username: str) -> List[Artwork]:
        """Get artworks for specific artist with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return []
        
        try:
            artworks_data = self.get_artist_artworks(username)
            logger.info(f"Fetched {len(artworks_data)} artworks for artist {username}")
            return [Artwork.from_dict(a) for a in artworks_data]
        except Exception as e:
            logger.error(f"Error fetching artworks for {username}: {e}")
            st.error(f"Error loading artworks: {e}")
            return []

    def save_artwork_data(self, artwork: Artwork) -> bool:
        """Save new artwork with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            artwork_dict = artwork.to_dict()
            # Remove None ID for new artworks
            if 'id' in artwork_dict and artwork_dict['id'] is None:
                del artwork_dict['id']
            
            logger.info(f"Attempting to save artwork: {artwork_dict}")
            result = self.save_artwork(artwork_dict)
            
            if result is not None:
                logger.info(f"Artwork saved successfully with ID: {result}")
                return True
            else:
                logger.error("Artwork save failed - database returned None")
                st.error("Failed to save artwork to database")
                return False
                
        except Exception as e:
            logger.error(f"Error saving artwork: {e}")
            st.error(f"Database error: {e}")
            return False

    def update_artwork_data(self, artwork_id: int, artwork: Artwork) -> bool:
        """Update existing artwork with proper error handling"""
        if not self.operations_available:
            return False
        
        try:
            artwork_dict = artwork.to_dict()
            result = self.update_artwork(artwork_id, artwork_dict)
            if result:
                logger.info(f"Artwork {artwork_id} updated successfully")
            return result
        except Exception as e:
            logger.error(f"Error updating artwork: {e}")
            st.error(f"Error updating artwork: {e}")
            return False

    def delete_artwork_data(self, artwork_id: int) -> bool:
        """Delete artwork with proper error handling"""
        if not self.operations_available:
            return False
        
        try:
            result = self.remove_artwork(artwork_id)
            if result:
                logger.info(f"Artwork {artwork_id} deleted successfully")
            return result
        except Exception as e:
            logger.error(f"Error deleting artwork: {e}")
            st.error(f"Error deleting artwork: {e}")
            return False

    # Blog operations --------------------------------------------------------
    def get_blogs_by_author(self, username: str) -> List[Blog]:
        """Get blogs for specific author with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return []
        
        try:
            blogs_data = self.get_user_blogs(username)
            logger.info(f"Fetched {len(blogs_data)} blogs for author {username}")
            return [Blog.from_dict(b) for b in blogs_data]
        except Exception as e:
            logger.error(f"Error fetching blogs for {username}: {e}")
            st.error(f"Error loading blogs: {e}")
            return []

    def save_blog_data(self, blog: Blog) -> bool:
        """Save new blog with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            blog_dict = blog.to_dict()
            logger.info(f"Attempting to save blog: {blog_dict}")
            result = self.save_blog_entry(blog_dict)
            
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

    def update_blog_data(self, blog_id: int, blog: Blog) -> bool:
        """Update existing blog with proper error handling"""
        if not self.operations_available:
            return False
        
        try:
            blog_dict = blog.to_dict()
            result = self.update_blog(blog_id, blog_dict)
            if result:
                logger.info(f"Blog {blog_id} updated successfully")
            return result
        except Exception as e:
            logger.error(f"Error updating blog: {e}")
            st.error(f"Error updating blog: {e}")
            return False

    def delete_blog_data(self, blog_id: int) -> bool:
        """Delete blog with proper error handling"""
        if not self.operations_available:
            return False
        
        try:
            result = self.delete_blog(blog_id)
            if result:
                logger.info(f"Blog {blog_id} deleted successfully")
            return result
        except Exception as e:
            logger.error(f"Error deleting blog: {e}")
            st.error(f"Error deleting blog: {e}")
            return False

    # ENHANCED: Artist selection for customers
    def get_available_artists(self) -> List[str]:
        """Get list of artists who have portfolios or artworks - ENHANCED"""
        if not self.operations_available:
            return []
        
        try:
            artists = self.get_artists_with_content()
            logger.info(f"Available artists for customer viewing: {artists}")
            return artists
        except Exception as e:
            logger.error(f"Error fetching available artists: {e}")
            return []

    # NEW: Cart functionality for customers
    def add_artwork_to_cart(self, username: str, artwork: Artwork) -> bool:
        """Add artwork to customer's cart"""
        if not self.operations_available:
            return False
        
        try:
            artwork_dict = artwork.to_dict()
            return self.add_to_cart(username, artwork_dict)
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            st.error(f"Error adding to cart: {e}")
            return False

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class SessionManager:
    """Session state management"""
    
    @staticmethod
    def initialize_edit_states():
        """Initialize edit state management"""
        pass
    
    @staticmethod
    def get_edit_key(item_type: str, item_id: int) -> str:
        """Generate unique edit key for session state"""
        return f"edit_{item_type}_{item_id}"

# ─────────────────────────────────────────────────────────────────────────────
#  UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, cfg: UIConfig, db: DatabaseManager, files: FileManager):
        self.cfg = cfg
        self.db = db
        self.files = files
    
    @abstractmethod
    def render(self, user_ctx: UserCtx, selected_artist: str, is_owner: bool) -> None:
        """Render the UI component"""
        pass

class StyleManager(UIComponent):
    """Handles comprehensive brown CSS styling - FIXED HTML entities and enhanced design"""
    
    def render(self, user_ctx: UserCtx, selected_artist: str = "", is_owner: bool = False) -> None:
        """Apply comprehensive brown CSS styling with all fixes"""
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
        .main-title, .portfolio-title {
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
        
        /* Customer artist selector styling */
        .artist-selector {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border-radius: 12px;
            border: 2px solid rgba(139, 69, 19, 0.15);
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
            padding: 1.5rem;
        }
        
        /* Portfolio Section Styling */
        .portfolio-section {
            background: transparent !important;
            margin-bottom: 1.5rem !important;
            transition: all 0.3s ease;
        }
        
        .portfolio-section:hover {
            transform: translateY(-2px);
        }
        
        /* Portfolio Info Display */
        .portfolio-info {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border: 2px solid rgba(139, 69, 19, 0.15);
            border-radius: 12px;
            margin-bottom: 1.5rem !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
        }
        
        /* Brown Cards */
        .brown-card {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border: 2px solid var(--brown-light);
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
        }
        
        /* Enhanced Art/Blog Cards - TRANSPARENT DESIGN */
        .artwork-card, .blog-card {
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
        
        .artwork-card:hover, .blog-card:hover {
            transform: translateY(-8px) scale(1.02);
        }
        
        /* Image Container - Enhanced */
        .artwork-card img, .blog-card img {
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.25);
            transition: transform 0.4s ease;
            margin-bottom: 1.2rem;
            width: 100%;
            object-fit: cover;
            height: 220px;
        }
        
        .artwork-card:hover img, .blog-card:hover img {
            transform: scale(1.05);
        }
        
        /* Art/Blog Titles - NO WHITE BOX */
        .art-title, .blog-title-display {
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
            padding-bottom: 0.5rem;
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
        
        /* CORRECTED BUTTONS - Enhanced styling */
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
        
        /* Form Styling - IMPROVED */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            border-radius: 10px !important;
            border: 2px solid var(--brown-light) !important;
            background: rgba(255, 255, 255, 0.95) !important;
            padding: 0.75rem !important;
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
            padding: 2rem !important;
            text-align: center !important;
            transition: all 0.3s ease !important;
        }
        
        .stFileUploader:hover {
            border-color: var(--primary) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.4), rgba(210, 180, 140, 0.3)) !important;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.2) !important;
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
        
        /* Role Badge */
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
        
        /* Mobile Responsiveness - ENHANCED */
        @media (max-width: 768px) {
            .portfolio-title {
                font-size: 2.2rem;
            }
            
            .artwork-card, .blog-card {
                margin-bottom: 1.5rem;
            }
            
            .art-title, .blog-title-display {
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
        
        .artwork-card, .blog-card {
            animation: fadeInUp 0.6s ease-out;
        }
        </style>
        """, unsafe_allow_html=True)

class ArtistSelector(UIComponent):
    """ENHANCED: Artist selection component for customers with improved UI"""
    
    def render(self, user_ctx: UserCtx, selected_artist: str = "", is_owner: bool = False) -> str:
        """Render artist selection dropdown for customers with enhanced styling"""
        if user_ctx.role == UserRole.ARTIST:
            return user_ctx.username
        
        # Customer can browse different artist portfolios
        try:
            available_artists = self.db.get_available_artists()
            
            if not available_artists:
                st.warning("🔍 No artist portfolios available to view.")
                return user_ctx.username
            
            # st.markdown('<div class="artist-selector">', unsafe_allow_html=True)
            st.markdown('### 🎨 Select Artist Portfolio to View')
            
            # Set default selection
            default_idx = 0
            if selected_artist in available_artists:
                default_idx = available_artists.index(selected_artist)
            
            selected_artist = st.selectbox(
                "Choose an artist:",
                options=available_artists,
                index=default_idx,
                help="Select an artist whose portfolio you'd like to explore",
                key="artist_selector"
            )
            
            if selected_artist:
                st.success(f"✅ Now viewing **{selected_artist}**'s portfolio")
            
            st.markdown('</div>', unsafe_allow_html=True)
            return selected_artist
            
        except Exception as e:
            logger.error(f"Error loading artists: {e}")
            st.error("Unable to load artist portfolios.")
            return user_ctx.username

class PortfolioEditForms(UIComponent):
    """Portfolio editing forms for artists - IN DROPDOWNS with enhanced UI"""
    
    def render(self, user_ctx: UserCtx, selected_artist: str, is_owner: bool) -> None:
        """Render edit forms for portfolio owner in dropdowns with enhanced styling"""
        if not is_owner:
            return
        
        # Initialize form counters
        if 'portfolio_form_counter' not in st.session_state:
            st.session_state.portfolio_form_counter = 0
        if 'artwork_form_counter' not in st.session_state:
            st.session_state.artwork_form_counter = 0
        if 'blog_form_counter' not in st.session_state:
            st.session_state.blog_form_counter = 0
        
        portfolio = self.db.get_portfolio_data(selected_artist)
        
        # Portfolio info edit form IN DROPDOWN
        with st.expander("📝 Edit Portfolio Info", expanded=False):
            form_key = f"portfolio_info_form_{st.session_state.portfolio_form_counter}"
            
            with st.form(form_key, clear_on_submit=False):
                new_bio = st.text_area("Artist Bio", value=portfolio.bio, height=120,
                                     placeholder="Tell people about your artistic journey, your inspiration, and what makes your work unique...")
                new_website = st.text_input("Website / Social Link", value=portfolio.website,
                                          placeholder="https://your-website.com or social media link")
                submitted_info = st.form_submit_button("💾 Save Portfolio Info", use_container_width=True)
                
                if submitted_info:
                    success = self._handle_portfolio_update(selected_artist, new_bio, new_website)
                    if success:
                        st.session_state.portfolio_form_counter += 1
                        st.rerun()

        # Artwork upload form IN DROPDOWN
        with st.expander("➕ Upload New Artwork", expanded=False):
            form_key = f"upload_artwork_form_{st.session_state.artwork_form_counter}"
            
            with st.form(form_key, clear_on_submit=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("Artwork Title*", max_chars=self.cfg.max_title_length,
                                        placeholder="e.g., Sunset Over Mountains")
                    materials = st.text_input("Materials", placeholder="e.g., Oil on canvas, 30x40cm")
                    state = st.text_input("Condition", placeholder="e.g., Excellent, Original")
                
                with col2:
                    style = st.text_input("Style/Genre", placeholder="e.g., Landscape, Abstract")
                    price = st.number_input("Price (₹)*", min_value=0.0, step=1.0)
                    image_file = st.file_uploader("Artwork Image*", type=self.cfg.allowed_image_types)
                
                description = st.text_area("Description", height=100,
                                         placeholder="Describe your artwork, the inspiration behind it, techniques used...")

                submitted_artwork = st.form_submit_button("📤 Upload Artwork", use_container_width=True)

                if submitted_artwork:
                    success = self._handle_artwork_upload(user_ctx, title, materials, state, style, 
                                              price, image_file, description)
                    if success:
                        st.session_state.artwork_form_counter += 1
                        st.rerun()

        # Blog upload form IN DROPDOWN
        with st.expander("➕ Upload New Blog", expanded=False):
            form_key = f"upload_blog_form_{st.session_state.blog_form_counter}"
            
            with st.form(form_key, clear_on_submit=False):
                blog_title = st.text_input("Blog Title*", max_chars=self.cfg.max_blog_title_length,
                                         placeholder="Share your artistic journey or insights...")
                blog_content = st.text_area("Content*", height=150,
                                          placeholder="Write about your artistic experiences, techniques, inspirations, or stories behind your artworks...")
                blog_image_file = st.file_uploader("Blog Image (optional)", 
                                                 type=self.cfg.allowed_image_types)

                submitted_blog = st.form_submit_button("📤 Upload Blog", use_container_width=True)

                if submitted_blog:
                    success = self._handle_blog_upload(user_ctx, blog_title, blog_content, blog_image_file)
                    if success:
                        st.session_state.blog_form_counter += 1
                        st.rerun()

    def _handle_portfolio_update(self, username: str, bio: str, website: str) -> bool:
        """Handle portfolio update with enhanced validation"""
        try:
            with st.spinner("🔄 Updating portfolio..."):
                updated_portfolio = Portfolio(
                    username=username,
                    bio=bio.strip(),
                    website=website.strip()
                )
                
                if self.db.save_portfolio_data(updated_portfolio):
                    st.success("✅ Portfolio info updated successfully!")
                    return True
                else:
                    st.error("❌ Failed to update portfolio info.")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            st.error(f"❌ Failed to update portfolio: {str(e)}")
            return False

    def _handle_artwork_upload(self, user_ctx: UserCtx, title: str, materials: str, 
                             state: str, style: str, price: float, image_file: Any, 
                             description: str) -> bool:
        """Handle artwork upload submission with enhanced validation"""
        
        # Enhanced validation
        validation_errors = []
        
        if not title or len(title.strip()) < 3:
            validation_errors.append("Artwork title must be at least 3 characters long")
        
        if not image_file:
            validation_errors.append("Please upload an artwork image")
        
        if price <= 0:
            validation_errors.append("Price must be greater than zero")
        
        # Display validation errors
        if validation_errors:
            for error in validation_errors:
                st.error(f"❌ {error}")
            return False

        try:
            with st.spinner("🔄 Uploading artwork..."):
                # Save image
                image_path = self.files.save_image(image_file, "artworks")
                if not image_path:
                    st.error("❌ Failed to save image.")
                    return False

                # Create artwork
                artwork = Artwork(
                    id=None,
                    artist=user_ctx.username,
                    title=title.strip(),
                    materials=materials.strip(),
                    state=state.strip(),
                    style=style.strip(),
                    price=price,
                    image=image_path,
                    description=description.strip(),
                    upload_date=str(date.today())
                )

                if self.db.save_artwork_data(artwork):
                    st.success("✅ Artwork uploaded successfully!")
                    st.balloons()
                    return True
                else:
                    st.error("❌ Failed to upload artwork.")
                    return False

        except Exception as e:
            logger.error(f"Error uploading artwork: {e}")
            st.error(f"❌ Failed to upload artwork: {str(e)}")
            return False

    def _handle_blog_upload(self, user_ctx: UserCtx, blog_title: str, 
                          blog_content: str, blog_image_file: Any) -> bool:
        """Handle blog upload submission with enhanced validation"""
        
        # Enhanced validation
        validation_errors = []
        
        if not blog_title or len(blog_title.strip()) < 5:
            validation_errors.append("Blog title must be at least 5 characters long")
        
        if not blog_content or len(blog_content.strip()) < 20:
            validation_errors.append("Blog content must be at least 20 characters long")
        
        # Display validation errors
        if validation_errors:
            for error in validation_errors:
                st.error(f"❌ {error}")
            return False

        try:
            with st.spinner("🔄 Uploading blog..."):
                # Save image if provided
                blog_image_path = None
                if blog_image_file:
                    blog_image_path = self.files.save_image(blog_image_file, "blogs")

                # Create blog
                blog = Blog(
                    id=None,
                    author=user_ctx.username,
                    title=blog_title.strip(),
                    content=blog_content.strip(),
                    image=blog_image_path,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
                )

                if self.db.save_blog_data(blog):
                    st.success("✅ Blog uploaded successfully!")
                    st.balloons()
                    return True
                else:
                    st.error("❌ Failed to upload blog.")
                    return False

        except Exception as e:
            logger.error(f"Error uploading blog: {e}")
            st.error(f"❌ Failed to upload blog: {str(e)}")
            return False

class PortfolioInfoDisplay(UIComponent):
    """Portfolio information display with enhanced brown theme"""
    
    def render(self, user_ctx: UserCtx, selected_artist: str, is_owner: bool) -> None:
        """Render portfolio bio and website info with enhanced brown styling"""
        portfolio = self.db.get_portfolio_data(selected_artist)
        
        st.markdown('<div class="portfolio-section">', unsafe_allow_html=True)
        st.markdown('<div class="portfolio-info">', unsafe_allow_html=True)
        
        st.markdown('<h3 style="color: var(--accent); margin: 0 0 1rem 0;">👨‍🎨 Artist Bio</h3>', unsafe_allow_html=True)
        if portfolio.bio:
            st.markdown(f'<div class="detail-value" style="line-height: 1.7; text-align: justify;">{portfolio.bio}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="detail-value" style="font-style: italic; color: var(--secondary);">*No bio provided yet.*</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
        
        st.markdown('<h3 style="color: var(--accent); margin: 0 0 1rem 0;">🌐 Website / Social Link</h3>', unsafe_allow_html=True)
        if portfolio.website:
            st.markdown(f'<div class="detail-value">🔗 <a href="{portfolio.website}" target="_blank" style="color: var(--primary); text-decoration: none; font-weight: 600;">{portfolio.website}</a></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="detail-value" style="font-style: italic; color: var(--secondary);">*No website or social link provided.*</div>', unsafe_allow_html=True)
        
        if portfolio.last_updated:
            st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color: var(--secondary); font-size: 0.85rem;"><strong>Last updated:</strong> {portfolio.last_updated}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

class ArtworkDisplay(UIComponent):
    """Artwork display and management with enhanced brown theme and customer features"""
    
    def render(self, user_ctx: UserCtx, selected_artist: str, is_owner: bool) -> None:
        """Render artworks display with conditional edit/delete for owner and add to cart for customers"""
        artworks = self.db.get_artworks_by_artist(selected_artist)
        
        st.markdown('<div class="portfolio-section">', unsafe_allow_html=True)
        st.markdown('<h3 style="color: var(--accent); margin: 0 0 1rem 0;">🎨 Artworks</h3>', unsafe_allow_html=True)
        
        if not artworks:
            st.markdown('<div class="empty-state">', unsafe_allow_html=True)
            if is_owner:
                st.markdown("### No artworks uploaded yet")
                st.markdown("📝 Use the form above to upload your first artwork!")
            else:
                st.markdown("### No artworks available")
                st.markdown("🎨 This artist hasn't uploaded any artworks yet.")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="brown-card" style="text-align: center;">', unsafe_allow_html=True)
            st.markdown(f"**📚 Total artworks: {len(artworks)}**")
            st.markdown('</div>', unsafe_allow_html=True)
            
            cols = st.columns(self.cfg.columns_count)
            for idx, artwork in enumerate(artworks):
                col = cols[idx % self.cfg.columns_count]
                self._render_artwork_card(artwork, col, is_owner, user_ctx)
        
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_artwork_card(self, artwork: Artwork, col, is_owner: bool, user_ctx: UserCtx) -> None:
        """Render individual artwork card with enhanced brown theme and customer features"""
        edit_key = SessionManager.get_edit_key("artwork", artwork.id)
        
        with col:
            st.markdown('<div class="artwork-card">', unsafe_allow_html=True)
            
            if is_owner and st.session_state.get(edit_key, False):
                self._render_artwork_edit_form(artwork, edit_key)
            else:
                self._render_artwork_display(artwork, is_owner, edit_key, user_ctx)
            
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_artwork_edit_form(self, artwork: Artwork, edit_key: str) -> None:
        """Render artwork edit form with enhanced brown styling"""
        st.markdown('<h4 style="color: var(--accent); margin: 0 0 1rem 0;">✏️ Edit Artwork</h4>', unsafe_allow_html=True)
        
        with st.form(f"edit_form_{artwork.id}", clear_on_submit=False):
            new_title = st.text_input("Artwork Title", value=artwork.title)
            new_materials = st.text_input("Materials Used", value=artwork.materials)
            new_state = st.text_input("State / Condition", value=artwork.state)
            new_style = st.text_input("Art Style/Genre", value=artwork.style)
            new_price = st.number_input("Price (₹)", min_value=0.0, step=1.0, value=float(artwork.price))
            new_description = st.text_area("Description", value=artwork.description, height=80)

            col1, col2 = st.columns(2)
            with col1:
                submitted_edit = st.form_submit_button("💾 Save", use_container_width=True)
            with col2:
                cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)

            if submitted_edit:
                updated_artwork = Artwork(
                    id=artwork.id,
                    artist=artwork.artist,
                    title=new_title.strip(),
                    materials=new_materials.strip(),
                    state=new_state.strip(),
                    style=new_style.strip(),
                    price=new_price,
                    image=artwork.image,
                    description=new_description.strip(),
                    upload_date=artwork.upload_date
                )
                
                if self.db.update_artwork_data(artwork.id, updated_artwork):
                    st.session_state[edit_key] = False
                    st.success("✅ Artwork updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to update artwork.")

            if cancel_edit:
                st.session_state[edit_key] = False
                st.rerun()

    def _render_artwork_display(self, artwork: Artwork, is_owner: bool, edit_key: str, user_ctx: UserCtx) -> None:
        """Render artwork display view with enhanced brown theme and customer features"""
        # Title with brown styling
        st.markdown(f'<div class="art-title">{artwork.title}</div>', unsafe_allow_html=True)
        
        # Image display
        if artwork.image and os.path.exists(artwork.image):
            st.image(artwork.image, use_container_width=True)
        else:
            st.markdown(
                '<div class="no-image-placeholder">🖼️<br>No Image Available</div>',
                unsafe_allow_html=True
            )
        
        # Price display
        st.markdown(f'<div class="art-price">₹{artwork.price:.1f}</div>', unsafe_allow_html=True)

        # Details in expander
        with st.expander("📋 View Details"):
            st.markdown('<div style="padding: 1rem;">', unsafe_allow_html=True)
            
            if artwork.description:
                st.markdown(f"**📝 Description:** {artwork.description}")
            if artwork.materials:
                st.markdown(f"**🎨 Materials:** {artwork.materials}")
            if artwork.state:
                st.markdown(f"**🏷️ State:** {artwork.state}")
            if artwork.style:
                st.markdown(f"**🎭 Style:** {artwork.style}")
            if artwork.upload_date:
                st.markdown(f"**📅 Upload Date:** {artwork.upload_date}")

            if is_owner:
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit", key=f"edit_btn_{artwork.id}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_btn_{artwork.id}", use_container_width=True):
                        if st.session_state.get(f"confirm_delete_artwork_{artwork.id}", False):
                            if self.db.delete_artwork_data(artwork.id):
                                st.success("✅ Artwork deleted successfully!")
                                st.session_state[f"confirm_delete_artwork_{artwork.id}"] = False
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete artwork.")
                        else:
                            st.session_state[f"confirm_delete_artwork_{artwork.id}"] = True
                            st.rerun()
                
                # Show confirmation message if delete was clicked
                if st.session_state.get(f"confirm_delete_artwork_{artwork.id}", False):
                    st.warning("⚠️ Click Delete again to confirm deletion")
            
            st.markdown('</div>', unsafe_allow_html=True)

        # ENHANCED: Add to Cart button for customers BELOW the expander
        if not is_owner and user_ctx.role == UserRole.CUSTOMER:
            if st.button("🛒 Add to Cart", key=f"cart_{artwork.id}_{user_ctx.username}", use_container_width=True):
                if self.db.add_artwork_to_cart(user_ctx.username, artwork):
                    st.toast(f"✅ '{artwork.title}' added to cart!", icon="🛒")
                    st.switch_page("pages/10_Cart.py")
                else:
                    st.error("❌ Failed to add to cart")

class BlogDisplay(UIComponent):
    """Blog display and management with enhanced brown theme"""
    
    def render(self, user_ctx: UserCtx, selected_artist: str, is_owner: bool) -> None:
        """Render blogs display with conditional edit/delete for owner"""
        blogs = self.db.get_blogs_by_author(selected_artist)
        
        st.markdown('<div class="portfolio-section">', unsafe_allow_html=True)
        st.markdown('<h3 style="color: var(--accent); margin: 0 0 1rem 0;">📝 Blogs</h3>', unsafe_allow_html=True)
        
        if not blogs:
            st.markdown('<div class="empty-state">', unsafe_allow_html=True)
            if is_owner:
                st.markdown("### No blogs written yet")
                st.markdown("📝 Use the form above to share your first blog!")
            else:
                st.markdown("### No blogs available")
                st.markdown("📚 This artist hasn't written any blogs yet.")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="brown-card" style="text-align: center;">', unsafe_allow_html=True)
            st.markdown(f"**📚 Total blogs: {len(blogs)}**")
            st.markdown('</div>', unsafe_allow_html=True)
            
            for blog in blogs:
                self._render_blog_card(blog, is_owner)
        
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_blog_card(self, blog: Blog, is_owner: bool) -> None:
        """Render individual blog card with enhanced brown theme"""
        edit_key = SessionManager.get_edit_key("blog", blog.id)
        
        with st.container():
            st.markdown('<div class="blog-card">', unsafe_allow_html=True)
            
            if is_owner and st.session_state.get(edit_key, False):
                self._render_blog_edit_form(blog, edit_key)
            else:
                self._render_blog_display(blog, is_owner, edit_key)
            
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_blog_edit_form(self, blog: Blog, edit_key: str) -> None:
        """Render blog edit form with enhanced brown styling"""
        st.markdown('<h4 style="color: var(--accent); margin: 0 0 1rem 0;">✏️ Edit Blog</h4>', unsafe_allow_html=True)
        
        with st.form(f"edit_blog_form_{blog.id}", clear_on_submit=False):
            new_title = st.text_input("Blog Title", value=blog.title)
            new_content = st.text_area("Content", value=blog.content, height=120)
            st.markdown("*Note: Image editing currently not supported.*")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted_edit = st.form_submit_button("💾 Save", use_container_width=True)
            with col2:
                cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)

            if submitted_edit:
                updated_blog = Blog(
                    id=blog.id,
                    author=blog.author,
                    title=new_title.strip(),
                    content=new_content.strip(),
                    image=blog.image,
                    timestamp=blog.timestamp
                )
                
                if self.db.update_blog_data(blog.id, updated_blog):
                    st.session_state[edit_key] = False
                    st.success("✅ Blog updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to update blog.")

            if cancel_edit:
                st.session_state[edit_key] = False
                st.rerun()

    def _render_blog_display(self, blog: Blog, is_owner: bool, edit_key: str) -> None:
        """Render blog display view with enhanced brown theme"""
        # Title with brown styling
        st.markdown(f'<div class="blog-title-display">{blog.title}</div>', unsafe_allow_html=True)
        
        if blog.timestamp:
            st.markdown(f'<div style="color: var(--secondary); font-style: italic; margin-bottom: 0.8rem;">📅 Published: {blog.timestamp}</div>', unsafe_allow_html=True)
        
        if blog.image and os.path.exists(blog.image):
            st.image(blog.image, use_container_width=True)
        
        with st.expander("📖 Read Blog", expanded=False):
            st.markdown('<div style="padding: 1rem;">', unsafe_allow_html=True)
            
            st.markdown(f"**Content:** {blog.content}")
            
            if is_owner:
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit", key=f"edit_blog_btn_{blog.id}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_blog_btn_{blog.id}", use_container_width=True):
                        if st.session_state.get(f"confirm_delete_blog_{blog.id}", False):
                            if self.db.delete_blog_data(blog.id):
                                st.success("✅ Blog deleted successfully!")
                                st.session_state[f"confirm_delete_blog_{blog.id}"] = False
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete blog.")
                        else:
                            st.session_state[f"confirm_delete_blog_{blog.id}"] = True
                            st.rerun()
                
                # Show confirmation message if delete was clicked
                if st.session_state.get(f"confirm_delete_blog_{blog.id}", False):
                    st.warning("⚠️ Click Delete again to confirm deletion")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION - ENHANCED
# ─────────────────────────────────────────────────────────────────────────────
class PortfolioApplication:
    """Main portfolio application with customer browsing capabilities - ENHANCED"""
    
    def __init__(self):
        self.cfg = UIConfig()
        self.files = FileManager(self.cfg)
        self.db = DatabaseManager()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.style_manager = StyleManager(self.cfg, self.db, self.files)
        self.artist_selector = ArtistSelector(self.cfg, self.db, self.files)
        self.edit_forms = PortfolioEditForms(self.cfg, self.db, self.files)
        self.info_display = PortfolioInfoDisplay(self.cfg, self.db, self.files)
        self.artwork_display = ArtworkDisplay(self.cfg, self.db, self.files)
        self.blog_display = BlogDisplay(self.cfg, self.db, self.files)
    
    def run(self) -> None:
        """Main application entry point - ENHANCED"""
        try:
            # Apply comprehensive brown styling
            self.style_manager.render(None)
            
            # Authentication check
            user_ctx = UserCtx.from_session()
            if not user_ctx:
                st.warning("🔐 Please log in to view portfolios.")
                st.stop()
            
            # Get artist selection (ENHANCED: includes customer browsing)
            selected_artist, is_owner = self._get_artist_selection(user_ctx)
            
            # SAFETY CHECK: Ensure we have a valid artist name
            if not selected_artist:
                st.error("❌ Unable to determine selected artist.")
                return
            
            # Render page header
            self._render_header(selected_artist, user_ctx.role, is_owner)
            
            # Render components - forms first (only for owners), then displays
            self.edit_forms.render(user_ctx, selected_artist, is_owner)
            self.info_display.render(user_ctx, selected_artist, is_owner)
            self.artwork_display.render(user_ctx, selected_artist, is_owner)
            self.blog_display.render(user_ctx, selected_artist, is_owner)
            
            # Footer
            self._render_footer()
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"❌ Application error: {e}")
    
    def _get_artist_selection(self, user_ctx: UserCtx) -> tuple[str, bool]:
        """Get selected artist and ownership status with customer browsing - ENHANCED"""
        try:
            if user_ctx.role == UserRole.ARTIST:
                return user_ctx.username, True
            else:
                # For customers, show artist selector
                selected_artist = self.artist_selector.render(user_ctx)
                if not selected_artist:
                    # Fallback to first available artist or current user
                    available_artists = self.db.get_available_artists()
                    if available_artists:
                        selected_artist = available_artists[0]
                    else:
                        selected_artist = user_ctx.username
                return selected_artist, False
        except Exception as e:
            logger.error(f"Error in artist selection: {e}")
            return user_ctx.username, user_ctx.role == UserRole.ARTIST
    
    def _render_header(self, selected_artist: str, user_role: UserRole, is_owner: bool) -> None:
        """Render page header with enhanced styling"""
        st.markdown(f'<h1 class="portfolio-title">{self.cfg.page_title}</h1>', unsafe_allow_html=True)
        st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="brown-card" style="text-align: center;">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if user_role == UserRole.ARTIST:
                st.markdown('<h2 style="color: var(--accent); margin: 0 0 0.5rem 0;">Your Portfolio</h2>', unsafe_allow_html=True)
                st.markdown('<p style="color: var(--secondary); font-size: 1.1rem; font-weight: 600; margin: 0;">Manage your artistic portfolio, showcase your work and share your journey</p>', 
                           unsafe_allow_html=True)
            else:
                st.markdown(f'<h2 style="color: var(--accent); margin: 0 0 0.5rem 0;">{selected_artist}\'s Portfolio</h2>', unsafe_allow_html=True)
                st.markdown('<p style="color: var(--secondary); font-size: 1.1rem; font-weight: 600; margin: 0;">Discover amazing artworks and artistic journeys</p>', 
                           unsafe_allow_html=True)
        
        with col2:
            role_class = f"role-{user_role.value}"
            st.markdown(f'<span class="role-badge {role_class}">{user_role.value.title()}</span>', 
                       unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_footer(self) -> None:
        """Render footer with enhanced styling"""
        st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="brown-card" style="text-align: center;">
            <h3 style="color: var(--accent); margin: 0 0 0.5rem 0;">🎨 Brush and Soul Portfolio</h3>
            <p style="color: var(--secondary); font-weight: 600; font-size: 1.1rem; margin: 0 0 0.5rem 0;">Create • Showcase • Inspire • Connect</p>
            <p style="font-size: 0.95rem; color: var(--brown-darker); font-weight: 500; margin: 0;">
                Your artistic journey deserves to be shared with the world
            </p>
            <div style="margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(210, 180, 140, 0.1)); border-radius: 8px; border: 1px solid var(--brown-light);">
                <p style="color: var(--primary); font-weight: 600; margin: 0;">
                    🌟 Where art meets inspiration, and artists find their audience 🌟
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def main() -> None:
    """Application main function with page configuration - ENHANCED"""
    st.set_page_config(
        page_title="Brush and Soul - Portfolio",
        page_icon="🎨",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    try:
        app = PortfolioApplication()
        app.run()
    except Exception as e:
        logger.error(f"Main application error: {e}")
        st.error("❌ Application failed to load. Please try again.")

if __name__ == "__main__":
    main()
