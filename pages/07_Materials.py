from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  TYPE DEFINITIONS & PROTOCOLS
# ─────────────────────────────────────────────────────────────────────────────
class MaterialOpsProtocol(Protocol):
    """Database-side operations required by this page."""
    def get_all_materials(self) -> List[Dict[str, Any]]: ...
    def get_user_materials(self, username: str) -> List[Dict[str, Any]]: ...
    def save_material(self, material: Dict[str, Any]) -> Optional[int]: ...
    def delete_material(self, material_id: int) -> bool: ...
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
#  CONFIG & DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class UIConfig:
    page_title: str = "Art Materials Marketplace"
    layout: str = "wide"
    uploads_dir: str = "uploads/materials"
    columns: int = 3
    allowed_types: List[str] = field(default_factory=lambda: ["jpg", "jpeg", "png"])

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
class Material:
    """Strongly-typed representation of a material."""
    id: int
    name: str
    price: float
    category: str
    description: str
    artist: str
    image: Optional[str] = None
    listed_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Material":
        return cls(
            id=d.get('id', 0),
            name=d.get('name', 'Unknown'),
            price=float(d.get('price', 0)),
            category=d.get('category', 'Other'),
            description=d.get('description', ''),
            artist=d.get('artist', '') or d.get('seller', 'Unknown Artist'),
            image=d.get('image') or d.get('image_path'),
            listed_date=d.get('listed_date', datetime.now().strftime("%Y-%m-%d"))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'seller': self.artist,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_path': self.image,
            'listed_date': self.listed_date
        }

# ─────────────────────────────────────────────────────────────────────────────
#  FILE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class FileManager:
    """Fixed file operations manager with proper error handling"""
    
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

    def save(self, file: Any) -> Optional[str]:
        """Save uploaded file with proper error handling"""
        if not file or not self.operations_available:
            return None
        
        try:
            result = self.save_uploaded_file(file, "materials")
            if result:
                logger.info(f"File saved successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            st.error(f"Error saving file: {e}")
            return None

# ─────────────────────────────────────────────────────────────────────────────
#  FIXED DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """Fixed database operations manager with proper error handling"""
    
    def __init__(self):
        self.operations_available = True
        try:
            from utils import (
                get_all_materials,
                get_user_materials,
                save_material,
                delete_material,
                add_to_cart,
            )
            
            self.get_all_materials = get_all_materials
            self.get_user_materials = get_user_materials
            self.save_material = save_material
            self.delete_material = delete_material
            self.add_to_cart = add_to_cart
            
            logger.info("Database operations initialized successfully")
            
        except ImportError as e:
            logger.error(f"Database utilities not available: {e}")
            self.operations_available = False
            st.error(f"Database operations not available: {e}")

    def fetch_all(self) -> List[Material]:
        """Fetch all materials from database with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return []
        
        try:
            materials_data = self.get_all_materials()
            logger.info(f"Fetched {len(materials_data)} materials from database")
            return [Material.from_dict(m) for m in materials_data]
        except Exception as e:
            logger.error(f"Error fetching materials: {e}")
            st.error(f"Error loading materials: {e}")
            return []

    def fetch_by_artist(self, username: str) -> List[Material]:
        """Fetch materials by artist/seller with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return []
        
        try:
            materials_data = self.get_user_materials(username)
            logger.info(f"Fetched {len(materials_data)} materials for artist {username}")
            return [Material.from_dict(m) for m in materials_data]
        except Exception as e:
            logger.error(f"Error fetching artist materials: {e}")
            st.error(f"Error loading your materials: {e}")
            return []

    def add(self, mat: Material) -> bool:
        """Add new material to database with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            material_data = mat.to_dict()
            logger.info(f"Attempting to save material: {material_data}")
            result = self.save_material(material_data)
            
            if result is not None:
                logger.info(f"Material saved successfully with ID: {result}")
                return True
            else:
                logger.error("Material save failed - database returned None")
                st.error("Failed to save material to database")
                return False
                
        except Exception as e:
            logger.error(f"Error saving material: {e}")
            st.error(f"Database error: {e}")
            return False

    def remove(self, mat_id: int) -> bool:
        """Remove material from database with proper error handling"""
        if not self.operations_available:
            return False
        
        try:
            result = self.delete_material(mat_id)
            if result:
                logger.info(f"Material {mat_id} deleted successfully")
            return result
        except Exception as e:
            logger.error(f"Error deleting material: {e}")
            st.error(f"Error deleting material: {e}")
            return False

    def add_to_cart_item(self, username: str, mat: Material) -> bool:
        """Add material to user's cart with proper error handling"""
        if not self.operations_available:
            return False
        
        try:
            material_dict = mat.to_dict()
            # Ensure proper format for cart
            material_dict['id'] = mat.id
            material_dict['title'] = mat.name  # Map name to title for cart compatibility
            result = self.add_to_cart(username, material_dict)
            if result:
                logger.info(f"Material {mat.name} added to cart for {username}")
            return result
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            st.error(f"Error adding to cart: {e}")
            return False

# ─────────────────────────────────────────────────────────────────────────────
#  ADVANCED UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, cfg: UIConfig, db: DatabaseManager, files: FileManager):
        self.cfg = cfg
        self.db = db
        self.files = files
    
    @abstractmethod
    def render(self, user_ctx: UserCtx) -> None:
        """Render the UI component"""
        pass

class StyleManager(UIComponent):
    """Handles comprehensive brown CSS styling - CORRECTED VERSION"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Apply comprehensive brown CSS styling with all corrections"""
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
        
        /* Material Card - FULLY CORRECTED TRANSPARENT DESIGN */
        .material-card {
            background: transparent !important;
            border-radius: 16px;
            margin-bottom: 2rem;
            border: none !important;
            backdrop-filter: none !important;
            transition: transform 0.3s ease;
            animation: fadeInUp 0.3s ease-out;
        }
        
        .material-card:hover {
            transform: translateY(-3px);
        }
        
        /* Material Title - NO WHITE BOX, PERFECT GRADIENT */
        .material-title {
            color: var(--secondary);
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.6rem;
            border-bottom: 3px solid var(--primary);
            background: linear-gradient(135deg, var(--accent), var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
            text-align: left;
            letter-spacing: -0.3px;
        }
        
        /* Artist Info - CLEAN STYLING */
        .material-artist {
            color: var(--secondary);
            font-size: 1rem;
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 500;
        }
        
        /* Category Badge - PROFESSIONAL STYLING */
        .category-badge {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.15), rgba(160, 82, 45, 0.1));
            padding: 0.4rem 1rem;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent);
            display: inline-block;
            margin: 0.5rem 0;
            border: 1px solid rgba(139, 69, 19, 0.2);
        }
        
        /* Material Image - ENHANCED STYLING */
        .material-image {
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.25);
            margin: 1rem 0 1.5rem 0;
            border: 2px solid var(--brown-light);
            width: 100%;
            height: 220px;
            object-fit: cover;
            transition: transform 0.4s ease;
        }
        
        .material-image:hover {
            transform: scale(1.03);
        }
        
        /* No Image Placeholder - CORRECTED */
        .no-image-placeholder {
            width: 100%;
            height: 220px;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.4), rgba(210, 180, 140, 0.3));
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--brown-medium);
            font-style: italic;
            font-size: 1.1rem;
            border: 2px dashed var(--brown-medium);
            margin: 1rem 0 1.5rem 0;
            transition: all 0.3s ease;
        }
        
        .no-image-placeholder:hover {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.5), rgba(210, 180, 140, 0.4));
            border-color: var(--primary);
        }
        
        /* Price Display - PROFESSIONAL FORMAT */
        .material-price-display {
            color: var(--primary);
            font-size: 1.4rem;
            font-weight: 800;
            margin: 1rem 0;
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.12), rgba(160, 82, 45, 0.08));
            border-radius: 12px;
            display: inline-block;
            border-left: 5px solid var(--primary);
            font-family: 'Inter', -apple-system, monospace;
            letter-spacing: 0.5px;
            box-shadow: 0 3px 10px rgba(139, 69, 19, 0.15);
        }
        
        /* View Details Expander - CORRECTED STYLING */
        div[data-testid="stExpander"] {
            border: 2px solid var(--brown-light) !important;
            border-radius: 16px !important;
            overflow: hidden !important;
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.2) !important;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.15), rgba(210, 180, 140, 0.1)) !important;
        }
        
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, var(--brown-light), var(--brown-lightest)) !important;
            border-radius: 12px !important;
            border: 2px solid var(--brown-medium) !important;
            color: var(--brown-darker) !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            transition: all 0.3s ease !important;
        }
        
        .streamlit-expanderHeader:hover {
            background: linear-gradient(135deg, var(--brown-medium), var(--brown-light)) !important;
            border-color: var(--primary) !important;
            color: white !important;
            transform: scale(1.02) !important;
            box-shadow: 0 4px 15px rgba(139, 69, 19, 0.25) !important;
        }
        
        /* Details Section - CORRECTED LAYOUT */
        .details-section {
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.25), rgba(210, 180, 140, 0.15));
            border-radius: 12px;
            border: 1px solid var(--brown-light);
            margin: 1rem 0;
            box-shadow: inset 0 2px 4px rgba(139, 69, 19, 0.1);
        }
        
        .detail-item {
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
        }
        
        .detail-value {
            color: var(--dark);
            line-height: 1.7;
            text-align: justify;
            font-size: 0.95rem;
        }
        
        /* Description Special Styling - ENHANCED */
        .description-content {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.6), rgba(245, 222, 179, 0.3));
            border-radius: 10px;
            border-left: 4px solid var(--primary);
            text-align: justify;
            line-height: 1.7;
            margin-top: 0.5rem;
            box-shadow: 0 2px 8px rgba(139, 69, 19, 0.1);
            font-size: 0.95rem;
        }
        
        /* ALL BROWN BUTTONS - PERFECTED */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            border: 2px solid var(--brown-medium) !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            font-size: 0.95rem !important;
            box-shadow: 
                0 6px 20px rgba(139, 69, 19, 0.35),
                inset 0 2px 0 rgba(245, 222, 179, 0.3) !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
            width: 100% !important;
            margin-top: 1rem !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, var(--accent), var(--brown-dark)) !important;
            transform: translateY(-4px) scale(1.05) !important;
            box-shadow: 
                0 12px 35px rgba(139, 69, 19, 0.45),
                inset 0 2px 0 rgba(245, 222, 179, 0.4) !important;
            border-color: var(--brown-light) !important;
        }
        
        .stButton > button:active {
            transform: translateY(-1px) scale(1.02) !important;
            box-shadow: 0 4px 15px rgba(139, 69, 19, 0.4) !important;
        }
        
        .stButton > button:focus {
            outline: none !important;
            box-shadow: 
                0 6px 20px rgba(139, 69, 19, 0.35),
                0 0 0 4px rgba(139, 69, 19, 0.3) !important;
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
        
        /* Tab Styling - ALL BROWN */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background: linear-gradient(135deg, rgba(245, 222, 179, 0.3), rgba(210, 180, 140, 0.2));
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: linear-gradient(135deg, var(--brown-light), var(--brown-lightest)) !important;
            border-radius: 8px !important;
            color: var(--brown-darker) !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            border: 2px solid var(--brown-medium) !important;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: linear-gradient(135deg, var(--brown-medium), var(--brown-light)) !important;
            color: white !important;
            transform: scale(1.02) !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
            color: white !important;
            border-color: var(--accent) !important;
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
            content: "🎨";
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
            border-radius: 12p;
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
        
        h2, h3 {
            color: var(--primary) !important;
            border-bottom: 2px solid var(--brown-light) !important;
        }
        
        /* Title divider */
        .title-divider {
            width: 80%;
            height: 4px;
            background: linear-gradient(90deg, transparent 0%, var(--primary) 20%, var(--secondary) 50%, var(--accent) 80%, transparent 100%);
            margin: 1rem auto 2rem auto;
            border-radius: 2px;
            box-shadow: 0 2px 4px rgba(139, 69, 19, 0.2);
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .material-card {
                margin-bottom: 1.5rem;
                border-radius: 12px;
            }
            
            .material-title {
                font-size: 1.4rem;
            }
            
            .material-price-display {
                font-size: 1.2rem;
            }
            
            .stButton > button {
                padding: 12px 24px !important;
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
        
        .material-card {
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

class BrowseTab(UIComponent):
    """Browse materials tab component - CORRECTED VERSION"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render browse materials tab with fully corrected layout"""
        all_materials = self.db.fetch_all()

        if all_materials:
            st.markdown(f'<div class="brown-card" style="text-align: center;">', unsafe_allow_html=True)
            st.markdown(f"**🛍️ Found {len(all_materials)} quality art materials available**")
            st.markdown('</div>', unsafe_allow_html=True)
            
            cols = st.columns(self.cfg.columns)
            for idx, mat in enumerate(all_materials):
                with cols[idx % self.cfg.columns]:
                    # Material container - fully transparent
                    st.markdown('<div class="material-card">', unsafe_allow_html=True)
                    
                    # Material Title - no white box, gradient text
                    st.markdown(f'<div class="material-title">{mat.name}</div>', unsafe_allow_html=True)
                    
                    # Artist info
                    st.markdown(f'<div class="material-artist">🎨 {mat.artist}</div>', unsafe_allow_html=True)
                    
                    # Category badge
                    st.markdown(f'<div class="category-badge">{mat.category}</div>', unsafe_allow_html=True)
                    
                    # Material Image
                    if mat.image and os.path.exists(mat.image):
                        st.image(mat.image, use_container_width=True)
                    else:
                        st.markdown(
                            '<div class="no-image-placeholder">📦<br>No Image Available</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Price display
                    st.markdown(f'<div class="material-price-display">₹{mat.price:.1f}</div>', unsafe_allow_html=True)
                    
                    # View Details Dropdown - corrected structure
                    with st.expander("📋 View Details"):
                        st.markdown('<div class="details-section">', unsafe_allow_html=True)
                        
                        # Description
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">📝 Description</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="description-content">{mat.description}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        
                        # Upload Date
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">📅 Upload Date</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{mat.listed_date}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Add to cart button
                    if st.button("🛒 Add to Cart", key=f"cart_{mat.id}_{user_ctx.username}"):
                        if self.db.add_to_cart_item(user_ctx.username, mat):
                            st.success(f"✅ Added {mat.name} to cart!")
                        else:
                            st.error("❌ Could not add to cart at this time.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-state brown-card">', unsafe_allow_html=True)
            if user_ctx.role == UserRole.ARTIST:
                st.markdown("### No materials available yet")
                st.markdown("🎨 Be the first to list some quality art supplies!")
            else:
                st.markdown("### No materials available yet")
                st.markdown("📦 Check back soon for amazing art supplies from our community!")
            st.markdown('</div>', unsafe_allow_html=True)

class YourMaterialsTab(UIComponent):
    """Your materials tab component - CORRECTED VERSION"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render your materials tab with corrected styling"""
        # Show upload form first
        self._render_upload_form(user_ctx)
        
        st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
        
        # Show existing materials
        self._render_existing_materials(user_ctx)
    
    def _render_existing_materials(self, user_ctx: UserCtx) -> None:
        """Render list of existing materials with corrected layout"""
        yours = self.db.fetch_by_artist(user_ctx.username)

        if yours:
            st.markdown(f'<h3 style="color: var(--primary);">📦 Your Listed Materials ({len(yours)})</h3>', 
                       unsafe_allow_html=True)

            # Use columns layout like browse tab
            cols = st.columns(self.cfg.columns)
            for idx, mat in enumerate(yours):
                with cols[idx % self.cfg.columns]:
                    # Material container - fully transparent
                    st.markdown('<div class="material-card">', unsafe_allow_html=True)
                    
                    # Material Title - no white box
                    st.markdown(f'<div class="material-title">{mat.name}</div>', unsafe_allow_html=True)
                    
                    # Artist info
                    st.markdown(f'<div class="material-artist">🎨 {mat.artist}</div>', unsafe_allow_html=True)
                    
                    # Category badge
                    st.markdown(f'<div class="category-badge">{mat.category}</div>', unsafe_allow_html=True)
                    
                    # Material Image
                    if mat.image and os.path.exists(mat.image):
                        st.image(mat.image, use_container_width=True)
                    else:
                        st.markdown(
                            '<div class="no-image-placeholder">📦<br>No Image</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Price display
                    st.markdown(f'<div class="material-price-display">₹{mat.price:.1f}</div>', unsafe_allow_html=True)
                    
                    # View Details Dropdown
                    with st.expander("📋 View Details"):
                        st.markdown('<div class="details-section">', unsafe_allow_html=True)
                        
                        # Description
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">📝 Description</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="description-content">{mat.description}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Materials
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">🎨 Materials</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{mat.category}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Artist
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">👨‍🎨 Artist</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{mat.artist}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Style
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">🏷️ Style</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{mat.category}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Upload Date
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">📅 Upload Date</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{mat.listed_date}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Delete button with confirmation
                    if st.button("🗑️ Remove", key=f"del_{mat.id}_{user_ctx.username}"):
                        if st.session_state.get(f"confirm_delete_{mat.id}", False):
                            if self.db.remove(mat.id):
                                st.success("✅ Material removed!")
                                st.session_state[f"confirm_delete_{mat.id}"] = False
                                st.rerun()
                            else:
                                st.error("❌ Delete failed.")
                        else:
                            st.session_state[f"confirm_delete_{mat.id}"] = True
                            st.rerun()
                    
                    # Show confirmation message if delete was clicked
                    if st.session_state.get(f"confirm_delete_{mat.id}", False):
                        st.warning("⚠️ Click Remove again to confirm")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-state brown-card">', unsafe_allow_html=True)
            st.markdown("### You haven't listed any materials yet")
            st.markdown("📦 Use the form above to list your first art material!")
            st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_upload_form(self, user_ctx: UserCtx) -> None:
        """Render material upload form with brown theme"""
        st.markdown('<h3 style="color: var(--accent);">➕ List New Art Material</h3>', unsafe_allow_html=True)
        
        # Initialize form counter if not exists
        if 'material_form_counter' not in st.session_state:
            st.session_state.material_form_counter = 0
        
        # Use fixed form key with counter
        form_key = f"new_material_form_{st.session_state.material_form_counter}"
        
        # Form container with brown styling
        st.markdown('<div class="brown-card">', unsafe_allow_html=True)
        
        with st.form(form_key, clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    "Material Name*", 
                    placeholder="e.g., Professional Acrylic Paint Set",
                    help="Choose a descriptive name that buyers will search for"
                )
                price = st.number_input(
                    "Price (₹)*", 
                    min_value=0.0, 
                    step=1.0,
                    help="Set a competitive price for your material"
                )
            
            with col2:
                category_options = [
                    "Select Category",
                    "🎨 Paints & Pigments", 
                    "🖌️ Brushes & Tools",
                    "📄 Canvas & Paper",
                    "✏️ Drawing Materials",
                    "🧱 Sculpture Materials",
                    "📱 Digital Art Tools",
                    "🧪 Art Supplies",
                    "📚 Art Books & Guides",
                    "🎭 Mixed Media",
                    "🧵 Crafting Materials",
                    "📐 Measuring Tools",
                    "🎪 Other"
                ]
                
                category = st.selectbox("Category*", category_options, index=0)
                image_file = st.file_uploader(
                    "Upload Material Image", 
                    type=self.cfg.allowed_types,
                    help="Add a clear photo of your material to attract buyers"
                )

            description = st.text_area(
                "Detailed Description*",
                height=120,
                placeholder="Describe the material in detail: brand, condition, what's included, why it's great for artists...",
                help="Provide comprehensive information to help buyers make informed decisions"
            )

            submitted = st.form_submit_button("📤 List Material", use_container_width=True)
            
            if submitted:
                success = self._handle_material_submission(user_ctx, name, price, category, 
                                               description, image_file)
                if success:
                    # Increment counter to prevent form key conflicts
                    st.session_state.material_form_counter += 1
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _handle_material_submission(self, user_ctx: UserCtx, name: str, price: float, 
                                  category: str, description: str, image_file: Any) -> bool:
        """Handle material form submission with comprehensive validation"""
        
        # Enhanced validation
        validation_errors = []
        
        if not name or len(name.strip()) < 3:
            validation_errors.append("Material name must be at least 3 characters long")
        
        if price <= 0:
            validation_errors.append("Price must be greater than 0")
        
        if category == "Select Category":
            validation_errors.append("Please select a category")
        
        if not description or len(description.strip()) < 10:
            validation_errors.append("Description must be at least 10 characters long")
        
        # Display validation errors
        if validation_errors:
            for error in validation_errors:
                st.error(f"❌ {error}")
            return False

        try:
            with st.spinner("🔄 Listing your material..."):
                # Save image if provided
                img_path = None
                if image_file:
                    img_path = self.files.save(image_file)
                    if not img_path:
                        st.warning("⚠️ Image upload failed, but material will still be listed")

                # Create new material
                new_mat = Material(
                    id=0,  # Will be assigned by database
                    name=name.strip(),
                    price=price,
                    category=category,
                    description=description.strip(),
                    image=img_path,
                    artist=user_ctx.username
                )

                if self.db.add(new_mat):
                    st.success("✅ Material listed successfully!")
                    st.balloons()
                    return True
                else:
                    st.error("❌ Failed to list material. Please check database connection.")
                    return False
                    
        except Exception as e:
            logger.error(f"Error listing material: {e}")
            st.error(f"❌ Failed to list material: {str(e)}")
            return False

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class MaterialsApplication:
    """Fixed main materials application - CORRECTED VERSION"""
    
    def __init__(self):
        self.cfg = UIConfig()
        self.files = FileManager(self.cfg)
        self.db = DatabaseManager()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.style_manager = StyleManager(self.cfg, self.db, self.files)
        self.browse_tab = BrowseTab(self.cfg, self.db, self.files)
        self.your_materials_tab = YourMaterialsTab(self.cfg, self.db, self.files)
    
    def run(self) -> None:
        """Main application entry point with enhanced error handling and brown theme"""
        try:
            # Apply comprehensive brown styling
            self.style_manager.render(None)
            
            # Authentication check
            user_ctx = UserCtx.from_session()
            if not user_ctx:
                st.warning("🔐 Please login to access art materials marketplace.")
                st.stop()
            
            # Render header with brown theme
            self._render_header(user_ctx)
            
            # Render tabs based on user role
            self._render_tabs(user_ctx)
            
            # Footer with brown theme
            self._render_footer()
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"❌ Application error: {e}")
    
    def _render_header(self, user_ctx: UserCtx) -> None:
        """Render page header with brown theme"""
        # Header container
        st.markdown('<div class="brown-card" style="text-align: center; padding: 2rem; margin-bottom: 2rem;">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown('<h1 style="color: var(--accent);">🎨 Art Materials Marketplace</h1>', 
                       unsafe_allow_html=True)
            st.markdown('<p style="color: var(--secondary); font-size: 1.1rem; font-weight: 600;">Discover and share quality art supplies from fellow artists</p>', 
                       unsafe_allow_html=True)
        with col2:
            role_class = f"role-{user_ctx.role.value}"
            st.markdown(f'<span class="role-badge {role_class}">{user_ctx.role.value.title()}</span>', 
                       unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)
    
    def _render_tabs(self, user_ctx: UserCtx) -> None:
        """Render tab interface based on user role with brown theme"""
        if user_ctx.role == UserRole.ARTIST:
            # Artists see both tabs
            tab1, tab2 = st.tabs(["🔍 Browse Materials", "📦 Your Materials"])
            
            with tab1:
                self.browse_tab.render(user_ctx)
            
            with tab2:
                self.your_materials_tab.render(user_ctx)
        else:
            # Customers only see Browse Materials
            st.markdown('<h3 style="color: var(--primary);">🔍 Browse Art Materials</h3>', 
                       unsafe_allow_html=True)
            self.browse_tab.render(user_ctx)
    
    def _render_footer(self) -> None:
        """Render footer with brown theme"""
        st.markdown('<div class="brown-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="brown-card" style="text-align: center; padding: 2rem; margin-top: 2rem;">
            <h3 style="color: var(--accent);">🎨 Brush and Soul Materials</h3>
            <p style="color: var(--secondary); font-weight: 600; font-size: 1.1rem;">Buy • Sell • Create • Inspire</p>
            <p style="font-size: 0.95rem; color: var(--brown-darker); font-weight: 500;">
                Connecting artists with quality materials for creative excellence
            </p>
            <div style="margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(210, 180, 140, 0.1)); border-radius: 8px; border: 1px solid var(--brown-light);">
                <p style="color: var(--primary); font-weight: 600; margin: 0;">
                    🌟 Quality materials, fair prices, artist community 🌟
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def main() -> None:
    """Application main function with page configuration"""
    st.set_page_config(
        page_title="Brush and Soul - Art Materials",
        page_icon="🎨",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    try:
        app = MaterialsApplication()
        app.run()
    except Exception as e:
        logger.error(f"Main application error: {e}")
        st.error("❌ Application failed to load. Please try again.")

if __name__ == "__main__":
    main()
