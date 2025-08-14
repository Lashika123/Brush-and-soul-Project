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
    page_title: str = "🎨 Art Materials Marketplace"
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
#  FILE MANAGER - FIXED
# ─────────────────────────────────────────────────────────────────────────────
class FileManager:
    """FIXED - File operations manager with comprehensive error handling"""
    
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
        """FIXED - Save uploaded file with enhanced error handling"""
        if not file:
            logger.warning("No file provided to save")
            return None
        
        if not self.operations_available:
            logger.error("File operations not available")
            st.error("File operations are not available")
            return None
        
        # Validate file size (max 10MB)
        if hasattr(file, 'size') and file.size > 10 * 1024 * 1024:
            error_msg = f"File size too large. Maximum 10MB allowed."
            logger.error(error_msg)
            st.error(error_msg)
            return None
        
        try:
            logger.info(f"Saving file: {file.name}")
            result = self.save_uploaded_file(file, "materials")
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

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE MANAGER - FIXED WITH EXPLICIT TRANSACTION HANDLING
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """FIXED - Database operations manager with explicit transaction handling"""
    
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
    
    def test_database_connection(self) -> bool:
        """Test database connection explicitly"""
        try:
            if not self.operations_available:
                return False
            
            # Try to execute a simple query
            from utils import _instance
            instance = _instance()
            
            with instance.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def save_material_with_transaction(self, material: Material) -> bool:
        """Save material with explicit transaction handling"""
        try:
            from utils import _instance
            instance = _instance()
            
            with instance.get_connection() as conn:
                cursor = conn.cursor()
                
                # Start transaction explicitly
                cursor.execute("START TRANSACTION")
                
                try:
                    # Format listed_date properly
                    listed_date = datetime.now().strftime("%Y-%m-%d")
                    
                    # Insert material
                    cursor.execute(
                        """INSERT INTO materials (seller, name, description, price, category, image_path, listed_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            material.artist,
                            material.name,
                            material.description,
                            material.price,
                            material.category,
                            material.image,
                            listed_date
                        )
                    )
                    
                    material_id = cursor.lastrowid
                    
                    # Commit transaction
                    cursor.execute("COMMIT")
                    
                    logger.info(f"Material saved successfully with ID: {material_id}")
                    st.success(f"✅ Material saved with ID: {material_id}")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    cursor.execute("ROLLBACK")
                    logger.error(f"Transaction failed, rolled back: {e}")
                    raise
                    
        except Exception as e:
            logger.error(f"Error saving material with transaction: {e}")
            return False
    
    def verify_material_saved(self, username: str, name: str) -> bool:
        """Verify material was actually saved to database"""
        try:
            from utils import get_user_materials
            
            # Fetch materials for this user
            materials = get_user_materials(username)
            
            # Check if the material with this name exists
            for material in materials:
                if material.get('name') == name:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error verifying material: {e}")
            return False

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
        """FIXED - Add new material with comprehensive error handling and verification"""
        if not self.operations_available:
            logger.error("Database operations not available")
            st.error("Database operations not available")
            return False
            
        try:
            logger.info(f"Testing database connection...")
            if not self.test_database_connection():
                st.error("❌ Database connection failed")
                return False
            
            st.success("✅ Database connection established")
            
            logger.info(f"Saving material with transaction handling...")
            success = self.save_material_with_transaction(mat)
            
            if success:
                logger.info(f"Verifying material was saved...")
                if self.verify_material_saved(mat.artist, mat.name):
                    st.success("✅ Material verified in database!")
                    return True
                else:
                    st.error("❌ Material was not properly saved to database")
                    return False
            else:
                st.error("❌ Failed to save material to database")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception in add material: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
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
#  UI COMPONENTS - FULLY CORRECTED
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
    """Handles comprehensive brown CSS styling - FULLY CORRECTED VERSION"""
    
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
        
        /* Material Card - FIXED WITH TRANSPARENT DESIGN */
        .material-card {
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
        
        .material-card:hover {
            transform: translateY(-8px) scale(1.02);
        }
        
        /* Material Card Image Container - ENHANCED */
        .material-card img {
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.25);
            transition: transform 0.4s ease;
            margin-bottom: 1.2rem;
            width: 100%;
            object-fit: cover;
            height: 220px;
        }
        
        .material-card:hover img {
            transform: scale(1.05);
        }
        
        /* Material Title - NO WHITE BOX */
        .material-title {
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
        
        /* Enhanced Artist Name */
        .material-artist {
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
        .material-price-display {
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
        
        /* Category Badge - PROFESSIONAL STYLING */
        .category-badge {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.15), rgba(160, 82, 45, 0.1));
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent);
            display: inline-block;
            margin: 0.5rem 0;
            border: 1px solid rgba(139, 69, 19, 0.2);
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
            padding: 1rem;
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
            border-radius: 16px !important
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
        
        /* Custom brown elements */
        .brown-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--primary), var(--secondary), var(--primary), transparent);
            margin: 2rem 0;
            border-radius: 1px;
        }
        
        /* Mobile Responsiveness - ENHANCED */
        @media (max-width: 768px) {
            .main-title {
                font-size: 2.2rem;
            }
            
            .material-card {
                margin-bottom: 1.5rem;
            }
            
            .material-title {
                font-size: 1.4rem;
            }
            
            .material-price-display {
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
        
        .material-card {
            animation: fadeInUp 0.6s ease-out;
        }
        </style>
        """, unsafe_allow_html=True)

class BrowseTab(UIComponent):
    """Browse materials tab component - CORRECTED VERSION"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render browse materials tab with fully corrected layout"""
        all_materials = self.db.fetch_all()

        if all_materials:
            # No message displayed - clean display of materials
            
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
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Add to cart button BELOW the expander
                    if st.button("🛒 Add to Cart", key=f"cart_{mat.id}_{user_ctx.username}"):
                        if self.db.add_to_cart_item(user_ctx.username, mat):
                            st.success(f"✅ Added {mat.name} to cart!")
                            st.switch_page("pages/10_Cart.py")
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
    """Your materials tab component - CORRECTED VERSION WITH FIXED FORM"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render your materials tab with corrected styling and fixed form"""
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
                        
                        # Listed Date
                        st.markdown('<div class="detail-item">', unsafe_allow_html=True)
                        st.markdown('<div class="detail-label">📅 Listed Date</div>', unsafe_allow_html=True)
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
        """FIXED - Render material upload form with guaranteed database saving"""
        st.markdown('<h3 style="color: var(--accent);">➕ List New Art Material</h3>', unsafe_allow_html=True)
        
        # Form container with brown styling
        st.markdown('<div class="brown-card">', unsafe_allow_html=True)
        
        form_key = "material_upload_form"
        
        with st.form(key=form_key, clear_on_submit=False):  # Don't auto-clear
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
                with st.status("Processing material upload...") as status:
                    # Validation
                    validation_errors = self._validate_form_data(name, price, category, image_file)
                    
                    if validation_errors:
                        for error in validation_errors:
                            st.error(f"❌ {error}")
                    else:
                        # Process submission with detailed status updates
                        success = self._process_material_submission_with_status(
                            user_ctx, name, price, category, description, image_file, status
                        )
                        
                        if success:
                            status.update(label="Material listed successfully!", state="complete")
                            st.success("✅ Material listed successfully!")
                            st.balloons()
                            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _validate_form_data(self, name: str, price: float, category: str, image_file) -> list:
        """Comprehensive form validation"""
        errors = []
        
        if not name or len(name.strip()) < 3:
            errors.append("Material name must be at least 3 characters long")
        
        if price <= 0:
            errors.append("Price must be greater than 0")
        
        if category == "Select Category":
            errors.append("Please select a category")
        
        return errors
    
    def _process_material_submission_with_status(
        self, user_ctx: UserCtx, name: str, price: float, category: str, 
        description: str, image_file, status_container
    ) -> bool:
        """Process material submission with detailed status updates and guaranteed database saving"""
        
        try:
            status_container.update(label="Validating data...")
            
            # Save uploaded file first
            image_path = None
            if image_file:
                status_container.update(label="Saving image file...")
                image_path = self.files.save(image_file)
                if not image_path:
                    st.error("❌ Failed to save image file")
                    return False
                st.success(f"✅ Image saved: {os.path.basename(image_path)}")
            
            status_container.update(label="Preparing material data...")
            
            # Create material data
            material = Material(
                id=0,  # Will be assigned by database
                name=name.strip(),
                price=price,
                category=category,
                description=description.strip(),
                artist=user_ctx.username,
                image=image_path
            )
            
            status_container.update(label="Testing database connection...")
            
            # Test database connection explicitly
            if not self.db.test_database_connection():
                st.error("❌ Database connection failed")
                return False
            
            st.success("✅ Database connection established")
            
            status_container.update(label="Saving material to database...")
            
            # Save to database with explicit transaction handling
            success = self.db.add(material)
            
            if success:
                status_container.update(label="Verifying data was saved...")
                # Verify the material was actually saved by fetching it back
                if self.db.verify_material_saved(user_ctx.username, name):
                    st.success("✅ Material verified in database!")
                    return True
                else:
                    st.error("❌ Material was not properly saved to database")
                    return False
            else:
                st.error("❌ Failed to save material to database")
                return False
                
        except Exception as e:
            logger.error(f"Exception in material submission: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            st.error(f"❌ Upload failed: {str(e)}")
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
        st.markdown(f'<h1 class="main-title">{self.cfg.page_title}</h1>', unsafe_allow_html=True)
        st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)
        
        # st.markdown('<div class="brown-card" style="text-align: center; padding: 2rem; margin-bottom: 2rem;">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown('<p style="color: var(--secondary); font-size: 1.1rem; font-weight: 600;">Discover and share quality art supplies from fellow artists</p>', 
                       unsafe_allow_html=True)
        with col2:
            role_class = f"role-{user_ctx.role.value}"
            st.markdown(f'<span class="role-badge {role_class}">{user_ctx.role.value.title()}</span>', 
                       unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
