"""
utils.py
--------
Complete utility functions for Brush and Soul art platform with Payment Integration.
Uses PyMySQL for database operations - Bio and Website in Portfolio ONLY.
ENHANCED: Date formatting in dd-mm-yyyy format throughout the application
"""

from __future__ import annotations

import hashlib
import logging
import os
import pymysql
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration - FIXED for data storage
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',  # Update this with your MySQL password
    'database': 'brush_and_soul',
    'charset': 'utf8mb4',
    'autocommit': True  # Enable autocommit for automatic data storage
}

UPLOADS_DIR = "uploads"

# --------------------------------------------------------------------------- #
#  Enhanced User and Data Models - Bio and Website in Portfolio Only         #
# --------------------------------------------------------------------------- #
class UserType(Enum):
    """User type enumeration"""
    ARTIST = "artist"
    CUSTOMER = "customer"

class PaymentMethod(Enum):
    """Payment methods enumeration - ENHANCED"""
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    UPI = "UPI (PhonePe/GPay/Paytm)"
    NET_BANKING = "Net Banking"
    CASH_ON_DELIVERY = "Cash on Delivery"
    DIGITAL_WALLET = "Digital Wallet"

@dataclass
class User:
    """User data model - Bio and Website NOT included here"""
    user_id: int
    username: str
    email: str
    password_hash: str
    user_type: UserType
    created_at: Optional[datetime] = None

@dataclass
class PaymentInfo:
    """Payment information structure - ENHANCED to handle PaymentMethod enum"""
    method: Union[str, PaymentMethod]  # Accept both string and PaymentMethod enum
    amount: float
    transaction_id: str = ""
    status: str = "pending"
    timestamp: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        
        # Convert PaymentMethod enum to string if needed for database storage
        if isinstance(self.method, PaymentMethod):
            self.method = self.method.value

@dataclass
class ShippingInfo:
    """Shipping address information"""
    full_name: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    phone: str = ""
    email: str = ""

# --------------------------------------------------------------------------- #
#  Enhanced Date Formatting Functions - NEW                                  #
# --------------------------------------------------------------------------- #
def format_date_to_ddmmyyyy(date_input: Union[str, datetime, None]) -> str:
    """
    Convert various date formats to dd-mm-yyyy format
    Handles: YYYYMMDDHHMMSS, datetime objects, ISO dates, etc.
    """
    try:
        if not date_input:
            return ""
        
        # If it's already a string in dd-mm-yyyy format, return as is
        if isinstance(date_input, str) and re.match(r'^\d{2}-\d{2}-\d{4}$', date_input):
            return date_input
        
        # Handle YYYYMMDDHHMMSS format (from your original question)
        if isinstance(date_input, str) and len(date_input) >= 8:
            # Extract date part from YYYYMMDDHHMMSS
            if len(date_input) >= 14:  # Full timestamp
                date_part = date_input[:8]  # Get YYYYMMDD
            else:
                date_part = date_input
            
            # Parse YYYYMMDD format
            if len(date_part) == 8 and date_part.isdigit():
                dt = datetime.strptime(date_part, "%Y%m%d")
                return dt.strftime("%d-%m-%Y")
        
        # Handle datetime objects
        if isinstance(date_input, datetime):
            return date_input.strftime("%d-%m-%Y")
        
        # Handle date objects
        if hasattr(date_input, 'strftime'):
            return date_input.strftime("%d-%m-%Y")
        
        # Handle ISO date strings (YYYY-MM-DD)
        if isinstance(date_input, str):
            try:
                dt = datetime.fromisoformat(str(date_input).replace('Z', '+00:00'))
                return dt.strftime("%d-%m-%Y")
            except:
                pass
        
        # Try to parse common date formats
        common_formats = [
            "%Y-%m-%d",          # 2025-08-06
            "%Y/%m/%d",          # 2025/08/06
            "%d/%m/%Y",          # 06/08/2025
            "%d-%m-%Y",          # 06-08-2025
            "%Y%m%d",            # 20250806
            "%d.%m.%Y",          # 06.08.2025
            "%Y-%m-%d %H:%M:%S", # 2025-08-06 22:00:00
            "%d/%m/%Y %H:%M:%S"  # 06/08/2025 22:00:00
        ]
        
        for fmt in common_formats:
            try:
                dt = datetime.strptime(str(date_input), fmt)
                return dt.strftime("%d-%m-%Y")
            except:
                continue
        
        return str(date_input)  # Return as string if all parsing fails
        
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return str(date_input) if date_input else ""

def get_current_date_ddmmyyyy() -> str:
    """Get current date in dd-mm-yyyy format"""
    return datetime.now().strftime("%d-%m-%Y")

def get_current_datetime_ddmmyyyy() -> str:
    """Get current datetime in dd-mm-yyyy HH:MM format"""
    return datetime.now().strftime("%d-%m-%Y %H:%M")

def format_order_date(order_date: Any) -> str:
    """Format order date specifically for display"""
    return format_date_to_ddmmyyyy(order_date)

def format_timestamp_to_ddmmyyyy(timestamp: str) -> str:
    """Convert YYYYMMDDHHMMSS timestamp to dd-mm-yyyy format"""
    try:
        if not timestamp or len(timestamp) < 8:
            return ""
        
        # Extract date part (YYYYMMDD) from timestamp
        date_part = timestamp[:8]
        
        if len(date_part) == 8 and date_part.isdigit():
            year = date_part[:4]
            month = date_part[4:6]
            day = date_part[6:8]
            return f"{day}-{month}-{year}"
        
        return timestamp
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}")
        return str(timestamp) if timestamp else ""

# --------------------------------------------------------------------------- #
#  Database Connection Manager                                                #
# --------------------------------------------------------------------------- #
class DatabaseManager:
    """Advanced MySQL database connection manager with payment support"""
    
    def __init__(self, config: Dict = None):
        self.config = config or DB_CONFIG
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic closing and commit"""
        conn = None
        try:
            conn = pymysql.connect(**self.config)
            if not self.config.get('autocommit', False):
                conn.autocommit(True)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """Initialize database with all required tables including payment support"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create database if not exists
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
                cursor.execute(f"USE {self.config['database']}")
                
                # Users table 
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INT PRIMARY KEY AUTO_INCREMENT,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        user_type ENUM('artist', 'customer') NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Artworks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS artworks (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        artist VARCHAR(255) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        materials VARCHAR(255),
                        state VARCHAR(255),
                        style VARCHAR(255),
                        price DECIMAL(10,2) NOT NULL,
                        image VARCHAR(500),
                        upload_date DATE,
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Blog posts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS blogs (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        author VARCHAR(255) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        image VARCHAR(500),
                        timestamp VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Materials table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS materials (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        price DECIMAL(10,2) NOT NULL,
                        category VARCHAR(255),
                        image_path VARCHAR(500),
                        listed_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tutorials table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tutorials (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        creator VARCHAR(255) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        content TEXT,
                        video_path VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Portfolios table (bio and website INCLUDED here)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolios (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        bio TEXT,
                        website VARCHAR(500),
                        last_updated DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Enhanced Orders table with payment and shipping
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INT PRIMARY KEY AUTO_INCREMENT,
                        username VARCHAR(255) NOT NULL,
                        total_amount DECIMAL(10,2) NOT NULL,
                        subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                        shipping_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                        tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                        order_date DATE NOT NULL,
                        order_status ENUM('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
                        payment_method VARCHAR(100),
                        payment_status ENUM('pending', 'success', 'failed', 'refunded') DEFAULT 'pending',
                        transaction_id VARCHAR(255),
                        payment_details JSON,
                        shipping_full_name VARCHAR(255),
                        shipping_address_line1 VARCHAR(500),
                        shipping_address_line2 VARCHAR(500),
                        shipping_city VARCHAR(255),
                        shipping_state VARCHAR(255),
                        shipping_pincode VARCHAR(10),
                        shipping_phone VARCHAR(20),
                        shipping_email VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
                # Order items table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS order_items (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        order_id INT NOT NULL,
                        item_type VARCHAR(50) NOT NULL,
                        item_id INT NOT NULL,
                        item_name VARCHAR(255) NOT NULL,
                        quantity INT DEFAULT 1,
                        price DECIMAL(10,2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
                    )
                """)
                
                # Cart table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cart (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        username VARCHAR(255) NOT NULL,
                        item_type VARCHAR(50) NOT NULL,
                        item_id INT NOT NULL,
                        item_name VARCHAR(255) NOT NULL,
                        price DECIMAL(10,2) NOT NULL,
                        quantity INT DEFAULT 1,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Payment transactions table for detailed tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payment_transactions (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        order_id INT NOT NULL,
                        transaction_id VARCHAR(255) UNIQUE NOT NULL,
                        payment_method VARCHAR(100) NOT NULL,
                        amount DECIMAL(10,2) NOT NULL,
                        status ENUM('pending', 'success', 'failed', 'refunded') DEFAULT 'pending',
                        gateway_response JSON,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
                    )
                """)
                
                logger.info("Database initialized successfully with payment support - Bio and Website in Portfolio only")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

# --------------------------------------------------------------------------- #
#  Core Utility Functions                                                     #
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Password is valid"

def generate_transaction_id(prefix: str = "TXN") -> str:
    """Generate unique transaction ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
    return f"{prefix}{timestamp}{unique_id}"

def save_uploaded_file(uploaded_file, subdirectory: str = "") -> Optional[str]:
    """Save uploaded file and return path"""
    try:
        if not uploaded_file:
            return None
        
        # Create upload directory
        upload_dir = Path(UPLOADS_DIR)
        if subdirectory:
            upload_dir = upload_dir / subdirectory
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return str(file_path)
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        return None

def delete_file(filepath: str) -> bool:
    """Delete file if it exists"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {filepath}: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Authentication Functions - Bio and Website NOT in Users                   #
# --------------------------------------------------------------------------- #
def register_user(username: str, email: str, password: str, user_type: str) -> tuple[bool, str]:
    """Register new user - Bio and Website NOT included in registration"""
    try:
        # Enhanced validation
        if not all([username, email, password, user_type]):
            return False, "Missing required fields for registration"
        
        if user_type not in ['artist', 'customer']:
            return False, f"Invalid user type: {user_type}"
        
        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, f"Invalid email format: {email}"
        
        is_valid, msg = is_valid_password(password)
        if not is_valid:
            return False, msg
        
        instance = _instance()
        if not instance or not instance.db_manager:
            return False, "Database not available"
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for existing username
            cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, f"Username '{username}' already exists"
            
            # Check for existing email
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return False, f"Email '{email}' already exists"
            
            # Create new user (bio and website NOT included)
            password_hash = hash_password(password)
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, user_type) 
                   VALUES (%s, %s, %s, %s)""",
                (username, email, password_hash, user_type)
            )
            
            logger.info(f"User {username} registered successfully")
            return True, "Registration successful"
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return False, f"Registration failed: {str(e)}"

def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user - Bio and Website NOT included in response"""
    try:
        # Clean inputs
        username = username.strip()
        password = password.strip()
        
        logger.info(f"Authentication attempt for username: '{username}'")
        
        if not username or not password:
            logger.warning("Empty username or password provided")
            return None
        
        instance = _instance()
        if not instance or not instance.db_manager:
            logger.error("Database not available")
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Find user (case-insensitive)
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
            user = cursor.fetchone()
            
            if user:
                # Check password
                password_hash = hash_password(password)
                if user['password_hash'] == password_hash:
                    logger.info(f"Authentication successful for user: {username}")
                    return {
                        "user_id": user['user_id'],
                        "username": user['username'],
                        "email": user['email'],
                        "user_type": user['user_type']
                        # bio and website NOT included in auth response
                    }
                else:
                    logger.warning(f"Password mismatch for user: {username}")
            else:
                logger.warning(f"User '{username}' not found in database")
            
            return None
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

def update_password(email: str, new_password: str) -> bool:
    """Update user password by email"""
    try:
        is_valid, _ = is_valid_password(new_password)
        if not is_valid:
            return False
        
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            password_hash = hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (password_hash, email)
            )
            return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Password update error: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Enhanced Cart and Order Functions with Payment Support and Date Formatting #
# --------------------------------------------------------------------------- #
def add_to_cart(username: str, item: Dict[str, Any]) -> bool:
    """Add item to user's cart"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Determine item type and extract relevant info
            item_type = 'artwork' if 'artist' in item else 'material'
            item_id = item.get('id', 0)
            item_name = item.get('title') or item.get('name', 'Unknown Item')
            price = float(item.get('price', 0))
            
            cursor.execute(
                """INSERT INTO cart (username, item_type, item_id, item_name, price, quantity) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (username, item_type, item_id, item_name, price, 1)
            )
            
            logger.info(f"Item added to cart: {item_name} for user {username}")
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return False

def get_cart_items(username: str) -> List[Dict[str, Any]]:
    """Get user's cart items with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM cart WHERE username = %s ORDER BY added_at DESC", (username,))
            cart_items = list(cursor.fetchall())
            
            # Format dates in cart items
            for item in cart_items:
                if item.get('added_at'):
                    item['added_at'] = format_date_to_ddmmyyyy(item['added_at'])
            
            return cart_items
    except Exception as e:
        logger.error(f"Error fetching cart items: {e}")
        return []

def get_cart(username: str) -> List[Dict[str, Any]]:
    """Get user's cart (alias for compatibility)"""
    return get_cart_items(username)

def remove_from_cart(username: str, item_id: int) -> bool:
    """Remove item from cart"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cart WHERE username = %s AND id = %s", (username, item_id))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        return False

def clear_cart(username: str) -> bool:
    """Clear user's cart"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cart WHERE username = %s", (username,))
            return True
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        return False

def place_order(username: str, items: List[Dict[str, Any]], 
                payment_info: PaymentInfo = None, 
                shipping_info: ShippingInfo = None) -> Dict[str, Any]:
    """Enhanced place order with payment and shipping support and formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return {'status': 'error', 'message': 'Database not available'}
        
        # Calculate amounts
        subtotal = sum(float(item.get('price', 0)) * item.get('quantity', 1) for item in items)
        shipping_amount = 50.0 if subtotal < 1000.0 else 0.0  # Free shipping over ₹1000
        tax_amount = subtotal * 0.18  # 18% GST
        total_amount = subtotal + shipping_amount + tax_amount
        
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # ENHANCED: Handle PaymentMethod enum and string properly
            payment_method = 'Unknown'
            payment_status = 'pending'
            transaction_id = None
            payment_details_str = None
            
            if payment_info:
                # Handle both PaymentMethod enum and string
                if isinstance(payment_info.method, PaymentMethod):
                    payment_method = payment_info.method.value
                else:
                    payment_method = str(payment_info.method)
                
                payment_status = payment_info.status
                transaction_id = payment_info.transaction_id
                
                # Create enhanced payment details
                payment_details = {
                    'method': payment_method,
                    'transaction_id': payment_info.transaction_id,
                    'status': payment_info.status,
                    'timestamp': payment_info.timestamp or get_current_datetime_ddmmyyyy(),
                    'details': payment_info.details
                }
                payment_details_str = str(payment_details)
            
            # Use current date in proper format for database
            current_date = datetime.now().strftime("%Y-%m-%d")  # Database format
            
            cursor.execute(
                """INSERT INTO orders (
                    username, total_amount, subtotal, shipping_amount, tax_amount, order_date,
                    payment_method, payment_status, transaction_id, payment_details,
                    shipping_full_name, shipping_address_line1, shipping_address_line2,
                    shipping_city, shipping_state, shipping_pincode, shipping_phone, shipping_email
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    username, total_amount, subtotal, shipping_amount, tax_amount,
                    current_date,  # Store in database format
                    payment_method,
                    payment_status,
                    transaction_id,
                    payment_details_str,
                    shipping_info.full_name if shipping_info else '',
                    shipping_info.address_line1 if shipping_info else '',
                    shipping_info.address_line2 if shipping_info else '',
                    shipping_info.city if shipping_info else '',
                    shipping_info.state if shipping_info else '',
                    shipping_info.pincode if shipping_info else '',
                    shipping_info.phone if shipping_info else '',
                    shipping_info.email if shipping_info else ''
                )
            )
            order_id = cursor.lastrowid
            
            # Add order items
            for item in items:
                cursor.execute(
                    """INSERT INTO order_items (order_id, item_type, item_id, item_name, quantity, price) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        order_id,
                        item.get('item_type', 'unknown'),
                        item.get('item_id', 0),
                        item.get('item_name', 'Unknown'),
                        item.get('quantity', 1),
                        item.get('price', 0)
                    )
                )
            
            # Record payment transaction if payment info provided
            if payment_info and payment_info.transaction_id:
                cursor.execute(
                    """INSERT INTO payment_transactions (order_id, transaction_id, payment_method, amount, status) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (order_id, payment_info.transaction_id, payment_method, total_amount, payment_info.status)
                )
            
            # Clear cart after placing order
            clear_cart(username)
            
            logger.info(f"Enhanced order placed successfully - ID: {order_id}, Total: ₹{total_amount}")
            return {
                'status': 'success',
                'order_id': order_id,
                'total_amount': total_amount,
                'subtotal': subtotal,
                'shipping_amount': shipping_amount,
                'tax_amount': tax_amount,
                'transaction_id': payment_info.transaction_id if payment_info else None,
                'order_date': get_current_date_ddmmyyyy()  # Return in dd-mm-yyyy format
            }
            
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return {'status': 'error', 'message': str(e)}

def get_orders(username: str) -> List[Dict[str, Any]]:
    """Get user's orders with enhanced details and formatted dates in dd-mm-yyyy"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Get orders with items and enhanced details
            cursor.execute("""
                SELECT o.order_id, o.username, o.total_amount, o.subtotal, o.shipping_amount, o.tax_amount,
                       o.order_date, o.order_status, o.payment_method, o.payment_status, o.transaction_id,
                       o.shipping_full_name, o.shipping_address_line1, o.shipping_city, o.shipping_state, o.shipping_pincode,
                       o.created_at, o.updated_at,
                       GROUP_CONCAT(CONCAT(oi.item_name, ':', oi.quantity, ':', oi.price) SEPARATOR '|') as items_data
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.username = %s
                GROUP BY o.order_id
                ORDER BY o.created_at DESC
            """, (username,))
            
            orders = []
            for row in cursor.fetchall():
                # Parse items data
                items = []
                if row['items_data']:
                    for item_str in row['items_data'].split('|'):
                        parts = item_str.split(':')
                        if len(parts) >= 3:
                            items.append({
                                'title': parts[0],
                                'quantity': int(parts[1]),
                                'price': float(parts[2])
                            })
                
                # Format dates properly to dd-mm-yyyy
                formatted_order_date = format_date_to_ddmmyyyy(row['order_date'])
                formatted_created_at = format_date_to_ddmmyyyy(row['created_at'])
                formatted_updated_at = format_date_to_ddmmyyyy(row['updated_at'])
                
                orders.append({
                    'order_id': row['order_id'],
                    'username': row['username'],
                    'total_amount': float(row['total_amount']),
                    'total': float(row['total_amount']),  # Alias for compatibility
                    'subtotal': float(row['subtotal']) if row['subtotal'] else 0.0,
                    'shipping_amount': float(row['shipping_amount']) if row['shipping_amount'] else 0.0,
                    'tax_amount': float(row['tax_amount']) if row['tax_amount'] else 0.0,
                    'order_date': formatted_order_date,  # dd-mm-yyyy format
                    'date': formatted_order_date,  # Alias in dd-mm-yyyy format
                    'created_date': formatted_created_at,  # dd-mm-yyyy format
                    'updated_date': formatted_updated_at,  # dd-mm-yyyy format
                    'order_status': row['order_status'],
                    'payment_method': row['payment_method'],
                    'payment_status': row['payment_status'],
                    'transaction_id': row['transaction_id'],
                    'shipping_address': {
                        'full_name': row['shipping_full_name'],
                        'address_line1': row['shipping_address_line1'],
                        'city': row['shipping_city'],
                        'state': row['shipping_state'],
                        'pincode': row['shipping_pincode']
                    },
                    'items': items
                })
            
            return orders
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return []

def update_order_status(order_id: int, status: str) -> bool:
    """Update order status"""
    try:
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
        if status not in valid_statuses:
            return False
            
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET order_status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                (status, order_id)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return False

def update_payment_status(order_id: int, status: str, transaction_id: str = None) -> bool:
    """Update payment status"""
    try:
        valid_statuses = ['pending', 'success', 'failed', 'refunded']
        if status not in valid_statuses:
            return False
            
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            if transaction_id:
                cursor.execute(
                    "UPDATE orders SET payment_status = %s, transaction_id = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                    (status, transaction_id, order_id)
                )
            else:
                cursor.execute(
                    "UPDATE orders SET payment_status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                    (status, order_id)
                )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating payment status: {e}")
        return False

def remove_order_by_id(order_id: Union[str, int]) -> bool:
    """Remove order by ID"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete payment transactions first
            cursor.execute("DELETE FROM payment_transactions WHERE order_id = %s", (int(order_id),))
            
            # Delete order items (foreign key constraint will handle this automatically)
            cursor.execute("DELETE FROM order_items WHERE order_id = %s", (int(order_id),))
            
            # Delete order
            cursor.execute("DELETE FROM orders WHERE order_id = %s", (int(order_id),))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing order: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Artwork Functions with Date Formatting                                    #
# --------------------------------------------------------------------------- #
def get_new_artwork_id() -> int:
    """Get next available artwork ID"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return 1
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM artworks")
            result = cursor.fetchone()
            return (result[0] or 0) + 1
    except Exception as e:
        logger.error(f"Error getting new artwork ID: {e}")
        return 1

def save_artwork(artwork_data: Dict[str, Any]) -> Optional[int]:
    """Save artwork to database with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Format upload_date if provided
            upload_date = artwork_data.get('upload_date')
            if upload_date:
                # Convert to database format (YYYY-MM-DD)
                if isinstance(upload_date, str):
                    try:
                        # If it's in dd-mm-yyyy format, convert to YYYY-MM-DD
                        if re.match(r'^\d{2}-\d{2}-\d{4}$', upload_date):
                            day, month, year = upload_date.split('-')
                            upload_date = f"{year}-{month}-{day}"
                    except:
                        upload_date = datetime.now().strftime("%Y-%m-%d")
            else:
                upload_date = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute(
                """INSERT INTO artworks (artist, title, description, materials, state, style, price, image, upload_date, status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    artwork_data.get('artist'),
                    artwork_data.get('title'),
                    artwork_data.get('description', ''),
                    artwork_data.get('materials', ''),
                    artwork_data.get('state', ''),
                    artwork_data.get('style', ''),
                    artwork_data.get('price'),
                    artwork_data.get('image'),
                    upload_date,
                    artwork_data.get('status', 'active')
                )
            )
            
            artwork_id = cursor.lastrowid
            logger.info(f"Artwork saved with ID: {artwork_id}")
            return artwork_id
    except Exception as e:
        logger.error(f"Error saving artwork: {e}")
        return None

def get_artist_artworks(username: str) -> List[Dict[str, Any]]:
    """Get all artworks by artist with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM artworks WHERE artist = %s AND status = 'active' ORDER BY created_at DESC",
                (username,)
            )
            artworks = list(cursor.fetchall())
            
            # Format dates in artworks
            for artwork in artworks:
                if artwork.get('upload_date'):
                    artwork['upload_date'] = format_date_to_ddmmyyyy(artwork['upload_date'])
                if artwork.get('created_at'):
                    artwork['created_at'] = format_date_to_ddmmyyyy(artwork['created_at'])
            
            return artworks
    except Exception as e:
        logger.error(f"Error fetching artist artworks: {e}")
        return []

def get_all_artworks() -> List[Dict[str, Any]]:
    """Get all active artworks with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM artworks WHERE status = 'active' ORDER BY created_at DESC")
            artworks = list(cursor.fetchall())
            
            # Format dates in artworks
            for artwork in artworks:
                if artwork.get('upload_date'):
                    artwork['upload_date'] = format_date_to_ddmmyyyy(artwork['upload_date'])
                if artwork.get('created_at'):
                    artwork['created_at'] = format_date_to_ddmmyyyy(artwork['created_at'])
            
            return artworks
    except Exception as e:
        logger.error(f"Error fetching all artworks: {e}")
        return []

def update_artwork(artwork_id: int, updates: Dict[str, Any]) -> bool:
    """Update artwork"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        # Build update query dynamically
        update_fields = []
        values = []
        
        allowed_fields = ['title', 'description', 'materials', 'state', 'style', 'price', 'image']
        for key, value in updates.items():
            if key in allowed_fields:
                update_fields.append(f"{key} = %s")
                values.append(value)
        
        if not update_fields:
            return False
        
        values.append(artwork_id)
        query = f"UPDATE artworks SET {', '.join(update_fields)} WHERE id = %s"
        
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            return cursor.rowcount > 0
            
    except Exception as e:
        logger.error(f"Error updating artwork: {e}")
        return False

def remove_artwork(artwork_id: int) -> bool:
    """Remove artwork (soft delete)"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE artworks SET status = 'deleted' WHERE id = %s",
                (artwork_id,)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing artwork: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Blog Functions with Date Formatting                                       #
# --------------------------------------------------------------------------- #
def save_blog_entry(blog_data: Dict[str, Any]) -> Optional[int]:
    """Save blog entry to database with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Format timestamp
            timestamp = blog_data.get('date')
            if not timestamp:
                timestamp = get_current_datetime_ddmmyyyy()
            
            cursor.execute(
                """INSERT INTO blogs (author, title, content, image, timestamp) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    blog_data.get('author'),
                    blog_data.get('title'),
                    blog_data.get('content'),
                    blog_data.get('image_path'),
                    timestamp
                )
            )
            
            blog_id = cursor.lastrowid
            logger.info(f"Blog saved with ID: {blog_id}")
            return blog_id
    except Exception as e:
        logger.error(f"Error saving blog: {e}")
        return None

def get_all_blogs() -> List[Dict[str, Any]]:
    """Get all blog posts with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM blogs ORDER BY created_at DESC")
            blogs = list(cursor.fetchall())
            
            # Format dates in blogs
            for blog in blogs:
                if blog.get('timestamp'):
                    # Handle timestamp conversion if it's in YYYYMMDDHHMMSS format
                    blog['timestamp'] = format_timestamp_to_ddmmyyyy(blog['timestamp'])
                if blog.get('created_at'):
                    blog['created_at'] = format_date_to_ddmmyyyy(blog['created_at'])
            
            return blogs
    except Exception as e:
        logger.error(f"Error fetching blogs: {e}")
        return []

def get_user_blogs(username: str) -> List[Dict[str, Any]]:
    """Get blogs by specific user with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM blogs WHERE author = %s ORDER BY created_at DESC", (username,))
            blogs = list(cursor.fetchall())
            
            # Format dates in blogs
            for blog in blogs:
                if blog.get('timestamp'):
                    blog['timestamp'] = format_timestamp_to_ddmmyyyy(blog['timestamp'])
                if blog.get('created_at'):
                    blog['created_at'] = format_date_to_ddmmyyyy(blog['created_at'])
            
            return blogs
    except Exception as e:
        logger.error(f"Error fetching user blogs: {e}")
        return []

def update_blog(blog_id: int, data: Dict[str, Any]) -> bool:
    """Update blog post"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE blogs SET title = %s, content = %s, image = %s WHERE id = %s""",
                (data.get('title'), data.get('content'), data.get('image_path'), blog_id)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating blog: {e}")
        return False

def delete_blog(blog_id: int) -> bool:
    """Delete blog post"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blogs WHERE id = %s", (blog_id,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting blog: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Materials Functions with Date Formatting                                  #
# --------------------------------------------------------------------------- #
def save_material(material_data: Dict[str, Any]) -> Optional[int]:
    """Save material to database with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Format listed_date
            listed_date = material_data.get('listed_date')
            if not listed_date:
                listed_date = datetime.now().strftime("%Y-%m-%d")
            elif isinstance(listed_date, str) and re.match(r'^\d{2}-\d{2}-\d{4}$', listed_date):
                # Convert dd-mm-yyyy to YYYY-MM-DD for database
                day, month, year = listed_date.split('-')
                listed_date = f"{year}-{month}-{day}"
            
            cursor.execute(
                """INSERT INTO materials (seller, name, description, price, category, image_path, listed_date) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    material_data.get('seller'),
                    material_data.get('name'),
                    material_data.get('description', ''),
                    material_data.get('price'),
                    material_data.get('category', ''),
                    material_data.get('image_path'),
                    listed_date
                )
            )
            
            material_id = cursor.lastrowid
            logger.info(f"Material saved with ID: {material_id}")
            return material_id
    except Exception as e:
        logger.error(f"Error saving material: {e}")
        return None

def get_all_materials() -> List[Dict[str, Any]]:
    """Get all materials with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM materials ORDER BY created_at DESC")
            materials = list(cursor.fetchall())
            
            # Format dates in materials
            for material in materials:
                if material.get('listed_date'):
                    material['listed_date'] = format_date_to_ddmmyyyy(material['listed_date'])
                if material.get('created_at'):
                    material['created_at'] = format_date_to_ddmmyyyy(material['created_at'])
            
            return materials
    except Exception as e:
        logger.error(f"Error fetching materials: {e}")
        return []

def get_user_materials(username: str) -> List[Dict[str, Any]]:
    """Get materials by seller with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM materials WHERE seller = %s ORDER BY created_at DESC", (username,))
            materials = list(cursor.fetchall())
            
            # Format dates in materials
            for material in materials:
                if material.get('listed_date'):
                    material['listed_date'] = format_date_to_ddmmyyyy(material['listed_date'])
                if material.get('created_at'):
                    material['created_at'] = format_date_to_ddmmyyyy(material['created_at'])
            
            return materials
    except Exception as e:
        logger.error(f"Error fetching user materials: {e}")
        return []

def update_material(material_id: int, updates: Dict[str, Any]) -> bool:
    """Update material"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        update_fields = []
        values = []
        
        allowed_fields = ['name', 'description', 'price', 'category', 'image_path']
        for key, value in updates.items():
            if key in allowed_fields:
                update_fields.append(f"{key} = %s")
                values.append(value)
        
        if not update_fields:
            return False
        
        values.append(material_id)
        query = f"UPDATE materials SET {', '.join(update_fields)} WHERE id = %s"
        
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating material: {e}")
        return False

def delete_material(material_id: int) -> bool:
    """Delete material"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = %s", (material_id,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting material: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Tutorial Functions with Date Formatting                                   #
# --------------------------------------------------------------------------- #
def save_tutorial(tutorial_data: Dict[str, Any]) -> Optional[int]:
    """Save tutorial to database"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO tutorials (creator, title, content, video_path) 
                   VALUES (%s, %s, %s, %s)""",
                (
                    tutorial_data.get('author') or tutorial_data.get('creator'),
                    tutorial_data.get('title'),
                    tutorial_data.get('content'),
                    tutorial_data.get('video_path')
                )
            )
            
            tutorial_id = cursor.lastrowid
            logger.info(f"Tutorial saved with ID: {tutorial_id}")
            return tutorial_id
    except Exception as e:
        logger.error(f"Error saving tutorial: {e}")
        return None

def get_all_tutorials() -> List[Dict[str, Any]]:
    """Get all tutorials with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT *, creator as author FROM tutorials ORDER BY created_at DESC")
            tutorials = list(cursor.fetchall())
            
            # Format dates in tutorials
            for tutorial in tutorials:
                if tutorial.get('created_at'):
                    tutorial['created_at'] = format_date_to_ddmmyyyy(tutorial['created_at'])
            
            return tutorials
    except Exception as e:
        logger.error(f"Error fetching tutorials: {e}")
        return []

def get_user_tutorials(username: str) -> List[Dict[str, Any]]:
    """Get tutorials by creator with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return []
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT *, creator as author FROM tutorials WHERE creator = %s ORDER BY created_at DESC", (username,))
            tutorials = list(cursor.fetchall())
            
            # Format dates in tutorials
            for tutorial in tutorials:
                if tutorial.get('created_at'):
                    tutorial['created_at'] = format_date_to_ddmmyyyy(tutorial['created_at'])
            
            return tutorials
    except Exception as e:
        logger.error(f"Error fetching user tutorials: {e}")
        return []

def update_tutorial(tutorial_id: int, data: Dict[str, Any]) -> bool:
    """Update tutorial"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tutorials SET title = %s, content = %s, video_path = %s WHERE id = %s""",
                (data.get('title'), data.get('content'), data.get('video_path'), tutorial_id)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating tutorial: {e}")
        return False

def delete_tutorial(tutorial_id: int) -> bool:
    """Delete tutorial"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tutorials WHERE id = %s", (tutorial_id,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting tutorial: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Portfolio Functions - Bio and Website INCLUDED here with Date Formatting  #
# --------------------------------------------------------------------------- #
def get_portfolio(username: str) -> Optional[Dict[str, Any]]:
    """Get user portfolio - Bio and Website INCLUDED with formatted dates"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM portfolios WHERE username = %s", (username,))
            portfolio = cursor.fetchone()
            
            if portfolio:
                return {
                    'id': portfolio['id'],
                    'username': portfolio['username'],
                    'bio': portfolio['bio'] or '',
                    'website': portfolio['website'] or '',
                    'last_updated': format_date_to_ddmmyyyy(portfolio['last_updated']),
                    'created_at': format_date_to_ddmmyyyy(portfolio['created_at'])
                }
            return None
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        return None

def save_portfolio(portfolio_data: Dict[str, Any]) -> Optional[int]:
    """Save portfolio data - Bio and Website INCLUDED"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            return None
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Use current date for last_updated
            last_updated = datetime.now().strftime("%Y-%m-%d")
            
            # Try to update first
            cursor.execute(
                """UPDATE portfolios SET bio = %s, website = %s, last_updated = %s WHERE username = %s""",
                (
                    portfolio_data.get('bio', ''),
                    portfolio_data.get('website', ''),
                    last_updated,
                    portfolio_data.get('username')
                )
            )
            
            if cursor.rowcount == 0:
                # Insert new portfolio
                cursor.execute(
                    """INSERT INTO portfolios (username, bio, website, last_updated) 
                       VALUES (%s, %s, %s, %s)""",
                    (
                        portfolio_data.get('username'),
                        portfolio_data.get('bio', ''),
                        portfolio_data.get('website', ''),
                        last_updated
                    )
                )
                portfolio_id = cursor.lastrowid
                logger.info(f"Portfolio created for user: {portfolio_data.get('username')}")
                return portfolio_id
            else:
                logger.info(f"Portfolio updated for user: {portfolio_data.get('username')}")
                return 1  # Updated successfully
                
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")
        return None

def update_portfolio(portfolio_data: Dict[str, Any]) -> bool:
    """Update portfolio data - Bio and Website INCLUDED"""
    try:
        result = save_portfolio(portfolio_data)
        return result is not None
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}")
        return False

def update_portfolio_field(username: str, field: str, value: str) -> bool:
    """Update specific portfolio field - Bio and Website allowed"""
    try:
        allowed_fields = ['bio', 'website']  # Bio and Website allowed in portfolio
        if field not in allowed_fields:
            return False
        
        instance = _instance()
        if not instance or not instance.db_manager:
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # First check if portfolio exists
            cursor.execute("SELECT id FROM portfolios WHERE username = %s", (username,))
            if not cursor.fetchone():
                # Create portfolio if doesn't exist
                cursor.execute(
                    "INSERT INTO portfolios (username, bio, website, last_updated) VALUES (%s, '', '', %s)",
                    (username, datetime.now().strftime("%Y-%m-%d"))
                )
            
            # Update the field
            query = f"UPDATE portfolios SET {field} = %s, last_updated = %s WHERE username = %s"
            cursor.execute(query, (value, datetime.now().strftime("%Y-%m-%d"), username))
            return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Portfolio field update error: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Database Reset Functions                                                   #
# --------------------------------------------------------------------------- #
def reset_all_users() -> bool:
    """Remove all users from database - USE WITH CAUTION"""
    try:
        instance = _instance()
        if not instance or not instance.db_manager:
            logger.error("Database not available")
            return False
            
        with instance.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Disable foreign key checks temporarily
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # Clear all tables in correct order (considering foreign keys)
            tables = [
                'payment_transactions', 'order_items', 'orders', 'cart', 'portfolios', 
                'blogs', 'tutorials', 'materials', 'artworks', 'users'
            ]
            
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            logger.info("All users and related data deleted successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error resetting users: {e}")
        return False

# --------------------------------------------------------------------------- #
#  Singleton Pattern for Global Access                                       #
# --------------------------------------------------------------------------- #
class UtilsManager:
    """Singleton manager for all utilities"""
    
    def __init__(self):
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            self.db_manager = None

_utils_instance = None

def _instance() -> Optional[UtilsManager]:
    """Get or create singleton instance"""
    global _utils_instance
    if _utils_instance is None:
        try:
            _utils_instance = UtilsManager()
        except Exception as e:
            logger.error(f"Failed to create utils instance: {e}")
            return None
    return _utils_instance

# Initialize on import with error handling
try:
    instance = _instance()
    if instance and instance.db_manager:
        logger.info("Utils initialized successfully with ENHANCED date formatting in dd-mm-yyyy - Bio and Website in Portfolio only")
    else:
        logger.warning("Utils initialized but database not available")
except Exception as e:
    logger.error(f"Failed to initialize utils: {e}")

# --------------------------------------------------------------------------- #
#  Export Functions                                                           #
# --------------------------------------------------------------------------- #
__all__ = [
    # Authentication
    'register_user', 'authenticate', 'hash_password', 'is_valid_password', 'update_password',
    # Portfolio (with bio and website)
    'get_portfolio', 'save_portfolio', 'update_portfolio', 'update_portfolio_field',
    # Artwork
    'save_artwork', 'get_artist_artworks', 'get_all_artworks', 'update_artwork', 
    'remove_artwork', 'get_new_artwork_id',
    # Blog
    'save_blog_entry', 'get_all_blogs', 'get_user_blogs', 'update_blog', 'delete_blog',
    # Materials
    'save_material', 'get_all_materials', 'get_user_materials', 'update_material', 'delete_material',
    # Tutorials
    'save_tutorial', 'get_all_tutorials', 'get_user_tutorials', 'update_tutorial', 'delete_tutorial',
    # Enhanced Cart & Orders with PaymentMethod enum support and Date Formatting
    'add_to_cart', 'get_cart_items', 'get_cart', 'remove_from_cart', 'clear_cart', 
    'place_order', 'get_orders', 'remove_order_by_id', 'update_order_status', 'update_payment_status',
    # Payment utilities - ENHANCED
    'generate_transaction_id', 'PaymentInfo', 'ShippingInfo', 'PaymentMethod',
    # Date formatting utilities - NEW
    'format_date_to_ddmmyyyy', 'get_current_date_ddmmyyyy', 'get_current_datetime_ddmmyyyy',
    'format_order_date', 'format_timestamp_to_ddmmyyyy',
    # File operations
    'save_uploaded_file', 'delete_file',
    # Database management
    'reset_all_users'
]
