from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
import uuid

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  PAYMENT SYSTEM ENHANCEMENTS
# ─────────────────────────────────────────────────────────────────────────────
class PaymentMethod(Enum):
    """Available payment methods"""
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    UPI = "UPI (PhonePe/GPay/Paytm)"
    NET_BANKING = "Net Banking"
    CASH_ON_DELIVERY = "Cash on Delivery"
    DIGITAL_WALLET = "Digital Wallet"

@dataclass
class PaymentInfo:
    """Payment information structure"""
    method: PaymentMethod
    amount: float
    transaction_id: str = ""
    status: str = "pending"
    timestamp: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

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

# ─────────────────────────────────────────────────────────────────────────────
#  TYPE DEFINITIONS & PROTOCOLS
# ─────────────────────────────────────────────────────────────────────────────
class CartOpsProtocol(Protocol):
    """Database-side operations required by this page."""
    def get_cart(self, username: str) -> List[Dict[str, Any]]: ...
    def remove_from_cart(self, username: str, item_id: int) -> bool: ...
    def clear_cart(self, username: str) -> bool: ...
    def place_order(self, username: str, items: List[Dict[str, Any]], 
                   payment_info: PaymentInfo, shipping_info: ShippingInfo) -> Dict[str, Any]: ...

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
    page_title: str = "Shopping Cart"
    layout: str = "wide"
    max_width: str = "900px"
    currency_symbol: str = "₹"
    # Payment settings
    min_order_amount: float = 100.0
    shipping_charge: float = 50.0
    free_shipping_threshold: float = 1000.0
    tax_rate: float = 0.18  # 18% GST

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
class CartItem:
    """Enhanced cart item representation"""
    id: int
    username: str
    item_type: str
    item_id: int
    item_name: str
    price: float
    quantity: int = 1
    added_at: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CartItem":
        return cls(
            id=d.get('id', 0),
            username=d.get('username', ''),
            item_type=d.get('item_type', 'unknown'),
            item_id=d.get('item_id', 0),
            item_name=d.get('item_name', 'Unknown Item'),
            price=float(d.get('price', 0)),
            quantity=d.get('quantity', 1),
            added_at=d.get('added_at', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'item_name': self.item_name,
            'price': self.price,
            'quantity': self.quantity,
            'added_at': self.added_at
        }

    @property
    def total_price(self) -> float:
        """Calculate total price for this cart item"""
        return self.price * self.quantity

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """Enhanced database operations manager with payment support"""
    
    def __init__(self):
        self.operations_available = True
        try:
            from utils import (
                get_cart_items,
                remove_from_cart,
                clear_cart,
                place_order,
            )
            
            self.get_cart_items = get_cart_items
            self.remove_from_cart = remove_from_cart
            self.clear_cart = clear_cart
            self.place_order = place_order
            
            logger.info("Database operations initialized successfully")
            
        except ImportError as e:
            logger.error(f"Database utilities not available: {e}")
            self.operations_available = False
            st.error(f"Database operations not available: {e}")

    def fetch_cart_items(self, username: str) -> List[CartItem]:
        """Fetch cart items for user with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return []
        
        try:
            cart_data = self.get_cart_items(username)
            logger.info(f"Fetched {len(cart_data)} cart items for user {username}")
            return [CartItem.from_dict(item) for item in cart_data]
        except Exception as e:
            logger.error(f"Error fetching cart items for {username}: {e}")
            st.error(f"Error loading cart: {e}")
            return []

    def remove_cart_item(self, username: str, cart_item_id: int) -> bool:
        """Remove item from cart with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            result = self.remove_from_cart(username, cart_item_id)
            if result:
                logger.info(f"Cart item {cart_item_id} removed for user {username}")
            return result
        except Exception as e:
            logger.error(f"Error removing cart item: {e}")
            st.error(f"Error removing item: {e}")
            return False

    def clear_user_cart(self, username: str) -> bool:
        """Clear all items from user's cart with proper error handling"""
        if not self.operations_available:
            st.error("Database operations not available")
            return False
        
        try:
            result = self.clear_cart(username)
            if result:
                logger.info(f"Cart cleared for user {username}")
            return result
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            st.error(f"Error clearing cart: {e}")
            return False

    def create_order_with_payment(self, username: str, cart_items: List[CartItem], 
                                 payment_info: PaymentInfo, 
                                 shipping_info: ShippingInfo) -> Dict[str, Any]:
        """Create order with payment and shipping information"""
        if not self.operations_available:
            st.error("Database operations not available")
            return {'status': 'error', 'message': 'Database not available'}
        
        try:
            # Convert cart items to the format expected by place_order
            order_items = []
            for cart_item in cart_items:
                order_items.append({
                    'item_type': cart_item.item_type,
                    'item_id': cart_item.item_id,
                    'item_name': cart_item.item_name,
                    'price': cart_item.price,
                    'quantity': cart_item.quantity
                })
            
            logger.info(f"Attempting to place order for {username} with {len(order_items)} items")
            result = self.place_order(username, order_items, payment_info, shipping_info)
            
            if result.get('status') == 'success':
                logger.info(f"Order placed successfully for {username}, Order ID: {result.get('order_id')}")
                return result
            else:
                logger.error(f"Order failed for {username}: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {'status': 'error', 'message': str(e)}

# ─────────────────────────────────────────────────────────────────────────────
#  UI COMPONENT BASE CLASS
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

# ─────────────────────────────────────────────────────────────────────────────
#  PAYMENT PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────
class PaymentProcessor(UIComponent):
    """Enhanced payment processing component"""
    
    def __init__(self, cfg: UIConfig, db: DatabaseManager):
        super().__init__(cfg, db)
        self.current_step = "cart"
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render payment step-by-step process"""
        pass
    
    def render_shipping_form(self) -> Optional[ShippingInfo]:
        """Render shipping address form"""
        st.markdown("### 🚚 Shipping Information")
        
        with st.form("shipping_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("Full Name *", placeholder="Enter your full name")
                address_line1 = st.text_input("Address Line 1 *", placeholder="Street address")
                city = st.text_input("City *", placeholder="City")
                phone = st.text_input("Phone Number *", placeholder="+91 9876543210")
            
            with col2:
                email = st.text_input("Email *", placeholder="email@example.com")
                address_line2 = st.text_input("Address Line 2", placeholder="Apartment, suite, etc.")
                col_state, col_pin = st.columns(2)
                with col_state:
                    state = st.text_input("State *", placeholder="State")
                with col_pin:
                    pincode = st.text_input("PIN Code *", placeholder="123456")
            
            submitted = st.form_submit_button("💾 Save Shipping Address", use_container_width=True)
            
            if submitted:
                # Validation
                if not all([full_name, address_line1, city, state, pincode, phone, email]):
                    st.error("❌ Please fill all required fields marked with *")
                    return None
                
                if len(pincode) != 6 or not pincode.isdigit():
                    st.error("❌ PIN code must be 6 digits")
                    return None
                
                shipping_info = ShippingInfo(
                    full_name=full_name,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city,
                    state=state,
                    pincode=pincode,
                    phone=phone,
                    email=email
                )
                
                st.success("✅ Shipping address saved!")
                return shipping_info
        
        return None
    
    def render_payment_methods(self, total_amount: float) -> Optional[PaymentInfo]:
        """Render payment methods selection"""
        st.markdown("### 💳 Payment Method")
        
        # Payment method selection
        payment_method = st.selectbox(
            "Choose Payment Method",
            options=[method.value for method in PaymentMethod],
            format_func=lambda x: f"{self._get_payment_icon(x)} {x}"
        )
        
        selected_method = PaymentMethod(payment_method)
        
        # Render specific payment form based on selection
        payment_info = self._render_payment_form(selected_method, total_amount)
        
        return payment_info
    
    def _get_payment_icon(self, method_name: str) -> str:
        """Get icon for payment method"""
        icons = {
            "Credit Card": "💳",
            "Debit Card": "💳",
            "UPI (PhonePe/GPay/Paytm)": "📱",
            "Net Banking": "🏦",
            "Cash on Delivery": "💵",
            "Digital Wallet": "💰"
        }
        return icons.get(method_name, "💳")
    
    def _render_payment_form(self, method: PaymentMethod, amount: float) -> Optional[PaymentInfo]:
        """Render payment form based on selected method"""
        
        if method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
            return self._render_card_payment(method, amount)
        elif method == PaymentMethod.UPI:
            return self._render_upi_payment(method, amount)
        elif method == PaymentMethod.NET_BANKING:
            return self._render_netbanking_payment(method, amount)
        elif method == PaymentMethod.CASH_ON_DELIVERY:
            return self._render_cod_payment(method, amount)
        elif method == PaymentMethod.DIGITAL_WALLET:
            return self._render_wallet_payment(method, amount)
        
        return None
    
    def _render_card_payment(self, method: PaymentMethod, amount: float) -> Optional[PaymentInfo]:
        """Render card payment form"""
        with st.form("card_payment"):
            st.markdown("#### 💳 Card Details")
            
            col1, col2 = st.columns(2)
            with col1:
                card_number = st.text_input("Card Number", placeholder="1234 5678 9012 3456", max_chars=19)
                card_holder = st.text_input("Card Holder Name", placeholder="JOHN DOE")
            
            with col2:
                col_exp, col_cvv = st.columns(2)
                with col_exp:
                    expiry = st.text_input("MM/YY", placeholder="12/25", max_chars=5)
                with col_cvv:
                    cvv = st.text_input("CVV", placeholder="123", max_chars=3, type="password")
            
            st.markdown("---")
            st.markdown(f"**Amount to pay: {self.cfg.currency_symbol}{amount:.2f}**")
            
            pay_button = st.form_submit_button(f"💳 Pay {self.cfg.currency_symbol}{amount:.2f}", use_container_width=True)
            
            if pay_button:
                if self._validate_card_details(card_number, expiry, cvv, card_holder):
                    # Simulate payment processing
                    with st.spinner("Processing payment..."):
                        time.sleep(2)
                        
                    transaction_id = f"TXN{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
                    
                    return PaymentInfo(
                        method=method,
                        amount=amount,
                        transaction_id=transaction_id,
                        status="success",
                        timestamp=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                        details={
                            "card_last4": card_number[-4:] if len(card_number) >= 4 else "****",
                            "card_type": method.value
                        }
                    )
        
        return None
    
    def _render_upi_payment(self, method: PaymentMethod, amount: float) -> Optional[PaymentInfo]:
        """Render UPI payment form"""
        with st.form("upi_payment"):
            st.markdown("#### 📱 UPI Payment")
            
            col1, col2 = st.columns(2)
            with col1:
                upi_id = st.text_input("UPI ID", placeholder="yourname@paytm")
                upi_app = st.selectbox("UPI App", ["PhonePe", "Google Pay", "Paytm", "BHIM", "Other"])
            
            with col2:
                st.markdown("**QR Code Payment**")
                st.markdown("📱 Scan QR code with your UPI app")
                st.code(f"upi://pay?pa=merchant@upi&am={amount}&cu=INR")
            
            st.markdown("---")
            st.markdown(f"**Amount to pay: {self.cfg.currency_symbol}{amount:.2f}**")
            
            pay_button = st.form_submit_button(f"📱 Pay with UPI {self.cfg.currency_symbol}{amount:.2f}", use_container_width=True)
            
            if pay_button and upi_id:
                with st.spinner("Processing UPI payment..."):
                    time.sleep(3)
                
                transaction_id = f"UPI{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
                
                return PaymentInfo(
                    method=method,
                    amount=amount,
                    transaction_id=transaction_id,
                    status="success",
                    timestamp=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    details={
                        "upi_id": upi_id,
                        "app": upi_app
                    }
                )
        
        return None
    
    def _render_netbanking_payment(self, method: PaymentMethod, amount: float) -> Optional[PaymentInfo]:
        """Render net banking payment form"""
        with st.form("netbanking_payment"):
            st.markdown("#### 🏦 Net Banking")
            
            bank = st.selectbox("Select Your Bank", [
                "State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank",
                "Punjab National Bank", "Bank of Baroda", "Canara Bank", "Other"
            ])
            
            st.markdown("---")
            st.markdown(f"**Amount to pay: {self.cfg.currency_symbol}{amount:.2f}**")
            st.info("🔒 You will be redirected to your bank's secure login page")
            
            pay_button = st.form_submit_button(f"🏦 Pay via {bank}", use_container_width=True)
            
            if pay_button:
                with st.spinner("Redirecting to bank portal..."):
                    time.sleep(2)
                
                transaction_id = f"NB{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
                
                return PaymentInfo(
                    method=method,
                    amount=amount,
                    transaction_id=transaction_id,
                    status="success",
                    timestamp=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    details={"bank": bank}
                )
        
        return None
    
    def _render_cod_payment(self, method: PaymentMethod, amount: float) -> Optional[PaymentInfo]:
        """Render cash on delivery option"""
        with st.form("cod_payment"):
            st.markdown("#### 💵 Cash on Delivery")
            
            st.info("💡 Pay cash when your order is delivered to your doorstep")
            st.warning("⚠️ Additional COD charges may apply")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Order Amount:** {self.cfg.currency_symbol}{amount:.2f}")
                st.markdown(f"**COD Charges:** {self.cfg.currency_symbol}25.00")
            
            with col2:
                total_cod = amount + 25  # COD charges
                st.markdown(f"**Total Amount:** {self.cfg.currency_symbol}{total_cod:.2f}")
            
            st.markdown("---")
            confirm_cod = st.checkbox("I confirm to pay cash on delivery")
            
            place_order = st.form_submit_button("📦 Place COD Order", use_container_width=True)
            
            if place_order and confirm_cod:
                transaction_id = f"COD{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
                
                return PaymentInfo(
                    method=method,
                    amount=total_cod,
                    transaction_id=transaction_id,
                    status="pending",
                    timestamp=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    details={"cod_charges": 25.0}
                )
        
        return None
    
    def _render_wallet_payment(self, method: PaymentMethod, amount: float) -> Optional[PaymentInfo]:
        """Render digital wallet payment"""
        with st.form("wallet_payment"):
            st.markdown("#### 💰 Digital Wallet")
            
            wallet_type = st.selectbox("Select Wallet", [
                "Paytm Wallet", "Amazon Pay", "Mobikwik", "Freecharge", "Ola Money"
            ])
            
            wallet_balance = st.number_input("Available Balance", value=5000.0, disabled=True)
            
            if amount > wallet_balance:
                st.error(f"❌ Insufficient balance. Required: {self.cfg.currency_symbol}{amount:.2f}")
                st.stop()
            
            st.markdown("---")
            st.markdown(f"**Amount to pay: {self.cfg.currency_symbol}{amount:.2f}**")
            
            pay_button = st.form_submit_button(f"💰 Pay from {wallet_type}", use_container_width=True)
            
            if pay_button:
                with st.spinner("Processing wallet payment..."):
                    time.sleep(2)
                
                transaction_id = f"WAL{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
                
                return PaymentInfo(
                    method=method,
                    amount=amount,
                    transaction_id=transaction_id,
                    status="success",
                    timestamp=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    details={"wallet": wallet_type}
                )
        
        return None
    
    def _validate_card_details(self, card_number: str, expiry: str, cvv: str, holder: str) -> bool:
        """Validate card details"""
        if not all([card_number, expiry, cvv, holder]):
            st.error("❌ Please fill all card details")
            return False
        
        # Remove spaces from card number
        card_number = card_number.replace(" ", "")
        
        if len(card_number) < 13 or not card_number.isdigit():
            st.error("❌ Invalid card number")
            return False
        
        if len(cvv) != 3 or not cvv.isdigit():
            st.error("❌ CVV must be 3 digits")
            return False
        
        if "/" not in expiry or len(expiry) != 5:
            st.error("❌ Expiry must be in MM/YY format")
            return False
        
        return True

# ─────────────────────────────────────────────────────────────────────────────
#  STYLE MANAGER - CORRECTED CSS
# ─────────────────────────────────────────────────────────────────────────────
class StyleManager(UIComponent):
    """Enhanced CSS styling with CORRECTED step indicator"""
    
    def render(self, user_ctx: UserCtx) -> None:
        """Apply enhanced CSS styling with CORRECTED step indicator"""
        st.markdown(f"""
        <style>
            :root {{
                --primary: #8B4513;
                --secondary: #A0522D;
                --accent: #5C4033;
                --light: #F8F4E8;
                --dark: #343434;
                --success: #4CAF50;
                --warning: #FF9800;
                --error: #F44336;
                --glass-bg: rgba(255, 255, 255, 0.95);
                --shadow: 0 8px 32px rgba(139, 69, 19, 0.1);
                --shadow-hover: 0 12px 40px rgba(139, 69, 19, 0.15);
            }}

            .stApp {{
                background: linear-gradient(160deg, #f5f1e8 0%, #e8e0d0 100%);
                font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            }}
            
            .cart-container {{
                max-width: {self.cfg.max_width};
                margin: 0 auto;
                padding: 1rem;
            }}
            
            /* CORRECTED Step Indicator Styles */
            .step-indicator {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin: 2rem auto;
                background: var(--glass-bg);
                border-radius: 20px;
                padding: 2rem 1rem;
                box-shadow: var(--shadow);
                max-width: 700px;
                position: relative;
                backdrop-filter: blur(15px);
            }}
            
            .step {{
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                color: #888;
                font-weight: 600;
                font-size: 0.9rem;
                transition: all 0.3s ease;
                position: relative;
                min-width: 120px;
                z-index: 1;
            }}
            
            .step.active {{
                color: var(--primary);
            }}
            
            .step.completed {{
                color: var(--success);
            }}
            
            .step-number {{
                width: 45px;
                height: 45px;
                border-radius: 50%;
                background: #ddd;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
                font-weight: bold;
                margin-bottom: 0.75rem;
                transition: all 0.3s ease;
                border: 3px solid transparent;
                position: relative;
                z-index: 2;
            }}
            
            .step.active .step-number {{
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                border-color: var(--primary);
                transform: scale(1.15);
                box-shadow: 0 6px 20px rgba(139, 69, 19, 0.4);
            }}
            
            .step.completed .step-number {{
                background: linear-gradient(135deg, var(--success), #45a049);
                border-color: var(--success);
            }}
            
            .step.completed .step-number::before {{
                content: "✓";
                font-size: 1rem;
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 3;
            }}
            
            .step-text {{
                font-size: 0.85rem;
                font-weight: 600;
                margin-top: 0.25rem;
                text-align: center;
                line-height: 1.2;
            }}
            
            .step-connector {{
                flex: 1;
                height: 3px;
                background: #ddd;
                margin: 0 1rem;
                margin-top: -22px;
                position: relative;
                z-index: 0;
            }}
            
            .step.completed + .step-connector,
            .step.active + .step-connector {{
                background: linear-gradient(90deg, var(--success), var(--primary));
            }}
            
            /* Cart Items */
            .cart-item {{
                background: var(--glass-bg);
                border-radius: 16px;
                margin: 1.5rem 0;
                box-shadow: var(--shadow);
                border-left: 5px solid var(--primary);
                transition: all 0.3s ease;
                padding: 1.5rem;
                backdrop-filter: blur(10px);
            }}
            
            .cart-item:hover {{
                transform: translateY(-3px);
                box-shadow: var(--shadow-hover);
                border-left-width: 8px;
            }}
            
            .item-title {{
                color: var(--accent);
                font-size: 1.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, var(--accent), var(--primary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .item-price {{
                color: var(--primary);
                font-weight: bold;
                font-size: 1.3rem;
            }}
            
            .item-details {{
                color: var(--dark);
                margin: 0.5rem 0;
                font-size: 0.95rem;
            }}
            
            .total-section {{
                background: var(--glass-bg);
                border-radius: 16px;
                margin: 2rem 0;
                padding: 1.5rem;
                border-top: 4px solid var(--primary);
                box-shadow: var(--shadow);
                backdrop-filter: blur(10px);
            }}
            
            .total-amount {{
                color: var(--accent);
                font-size: 2rem;
                font-weight: bold;
                background: linear-gradient(135deg, var(--accent), var(--primary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .empty-cart {{
                color: var(--secondary);
                text-align: center;
                font-size: 1.3rem;
                padding: 4rem;
                background: var(--glass-bg);
                border-radius: 16px;
                border: 2px dashed var(--secondary);
                backdrop-filter: blur(10px);
            }}
            
            .empty-cart::before {{
                content: "🛒";
                display: block;
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            
            .order-summary {{
                background: var(--glass-bg);
                border-radius: 16px;
                padding: 1.5rem;
                margin: 1rem 0;
                border-left: 4px solid var(--success);
                box-shadow: var(--shadow);
            }}
            
            .price-breakdown {{
                border-top: 2px solid var(--primary);
                padding-top: 1rem;
                margin-top: 1rem;
            }}
            
            .order-confirmation {{
                background: linear-gradient(135deg, rgba(76, 175, 80, 0.1), rgba(129, 199, 132, 0.1));
                border: 2px solid var(--success);
                border-radius: 20px;
                padding: 2rem;
                margin: 2rem 0;
                text-align: center;
                box-shadow: var(--shadow);
            }}
            
            .confirmation-icon {{
                font-size: 4rem;
                color: var(--success);
                margin-bottom: 1rem;
            }}
            
            .stButton>button {{
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                color: white !important;
                border-radius: 12px;
                padding: 0.8rem 2rem;
                border: none;
                font-weight: 600;
                font-size: 1rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(139, 69, 19, 0.25);
                min-height: 48px;
            }}
            
            .stButton>button:hover {{
                background: linear-gradient(135deg, var(--accent), var(--primary));
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(139, 69, 19, 0.35);
            }}
            
            .page-title {{
                color: var(--accent);
                text-align: center;
                margin-bottom: 2rem;
                font-size: 2.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, var(--accent), var(--primary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: -0.3px;
            }}
            
            .page-title:after {{
                content: "";
                display: block;
                width: 150px;
                height: 4px;
                background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent));
                margin: 1rem auto;
                border-radius: 2px;
            }}
            
            /* Mobile Responsiveness */
            @media (max-width: 768px) {{
                .cart-container {{
                    max-width: 100%;
                    padding: 0.5rem;
                }}
                
                .step-indicator {{
                    flex-direction: column;
                    gap: 1.5rem;
                    padding: 1rem;
                }}
                
                .step {{
                    flex-direction: row;
                    justify-content: flex-start;
                    width: 100%;
                    text-align: left;
                    min-width: auto;
                }}
                
                .step-number {{
                    margin-right: 1rem;
                    margin-bottom: 0;
                }}
                
                .step-text {{
                    margin-top: 0;
                    text-align: left;
                }}
                
                .step-connector {{
                    display: none;
                }}
                
                .cart-item, .total-section {{
                    padding: 1rem;
                    margin: 1rem 0;
                }}
                
                .total-amount {{
                    font-size: 1.5rem;
                }}
                
                .page-title {{
                    font-size: 2rem;
                }}
            }}
            
            @media (max-width: 480px) {{
                .page-title {{
                    font-size: 1.8rem;
                }}
                
                .cart-item {{
                    padding: 1rem;
                    border-radius: 12px;
                }}
            }}
            
            .security-badge {{
                display: inline-flex;
                align-items: center;
                background: rgba(76, 175, 80, 0.1);
                color: var(--success);
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.9rem;
                margin: 0.25rem;
                border: 1px solid rgba(76, 175, 80, 0.3);
            }}
            
            /* Form Enhancements */
            .stTextInput > div > div > input,
            .stSelectbox > div > div,
            .stNumberInput > div > div > input {{
                border-radius: 12px !important;
                border: 2px solid rgba(139, 69, 19, 0.2) !important;
                background: white !important;
                padding: 0.8rem 1rem !important;
                font-size: 1rem !important;
            }}
            
            .stTextInput > div > div > input:focus,
            .stSelectbox > div > div:focus-within,
            .stNumberInput > div > div > input:focus {{
                border-color: var(--primary) !important;
                box-shadow: 0 0 0 3px rgba(139, 69, 19, 0.15) !important;
            }}
            
            /* Animation Classes */
            @keyframes slideInUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .slide-in {{
                animation: slideInUp 0.5s ease-out;
            }}
            
            @keyframes fadeInUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .cart-item {{
                animation: fadeInUp 0.6s ease-out;
            }}
        </style>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  CHECKOUT FLOW - CORRECTED STEP INDICATOR
# ─────────────────────────────────────────────────────────────────────────────
class CheckoutFlow(UIComponent):
    """Enhanced checkout flow with CORRECTED step indicator"""
    
    def __init__(self, cfg: UIConfig, db: DatabaseManager):
        super().__init__(cfg, db)
        self.payment_processor = PaymentProcessor(cfg, db)
        
        # Initialize session state for checkout flow
        if 'checkout_step' not in st.session_state:
            st.session_state.checkout_step = 'cart'
        if 'shipping_info' not in st.session_state:
            st.session_state.shipping_info = None
        if 'payment_info' not in st.session_state:
            st.session_state.payment_info = None
    
    def render(self, user_ctx: UserCtx) -> None:
        """Render the complete checkout flow"""
        
        # Fetch cart items
        cart_items = self.db.fetch_cart_items(user_ctx.username)
        
        if not cart_items:
            self._render_empty_cart()
            return
        
        # Calculate totals
        subtotal = sum(item.total_price for item in cart_items)
        shipping = self._calculate_shipping(subtotal)
        tax = subtotal * self.cfg.tax_rate
        total = subtotal + shipping + tax
        
        # Render step indicator - CORRECTED
        self._render_step_indicator()
        
        # Render current step content
        if st.session_state.checkout_step == 'cart':
            self._render_cart_review(cart_items, subtotal, shipping, tax, total, user_ctx)
        elif st.session_state.checkout_step == 'shipping':
            self._render_shipping_step(cart_items, total)
        elif st.session_state.checkout_step == 'payment':
            self._render_payment_step(cart_items, total, user_ctx)
        elif st.session_state.checkout_step == 'confirmation':
            self._render_confirmation_step()
    
    def _render_step_indicator(self) -> None:
        """Render checkout step indicator - CORRECTED HTML structure"""
        steps = [
            ('cart', '1', '🛒 Review Cart'),
            ('shipping', '2', '🚚 Shipping'),
            ('payment', '3', '💳 Payment'),
            ('confirmation', '4', '✅ Confirmation')
        ]
        
        current_step = st.session_state.checkout_step
        
        # Build properly structured HTML
        step_html = '<div class="step-indicator">'
        
        for i, (step_key, number, label) in enumerate(steps):
            # Determine step status
            if step_key == current_step:
                step_class = 'step active'
            elif self._is_step_completed(step_key):
                step_class = 'step completed'
            else:
                step_class = 'step'
            
            # Add connector line (except before first step)
            if i > 0:
                step_html += '<div class="step-connector"></div>'
            
            # Add step with proper structure
            step_html += f'''
            <div class="{step_class}">
                <div class="step-number">{number}</div>
                <span class="step-text">{label}</span>
            </div>'''
        
        # Close the main container
        step_html += '</div>'
        
        # Render the HTML
        st.markdown(step_html, unsafe_allow_html=True)
    
    def _is_step_completed(self, step: str) -> bool:
        """Check if a step is completed - CORRECTED logic"""
        steps_order = ['cart', 'shipping', 'payment', 'confirmation']
        
        try:
            current_index = steps_order.index(st.session_state.checkout_step)
            step_index = steps_order.index(step)
            return step_index < current_index
        except ValueError:
            return False
    
    def _render_cart_review(self, cart_items: List[CartItem], subtotal: float, 
                           shipping: float, tax: float, total: float, user_ctx: UserCtx) -> None:
        """Render cart review step"""
        st.markdown("### 🛒 Review Your Order")
        
        # Cart items
        for item in cart_items:
            with st.container():
                st.markdown("<div class='cart-item'>", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"<div class='item-title'>{item.item_name}</div>", unsafe_allow_html=True)
                    st.markdown(f"*{item.item_type.title()}*")
                
                with col2:
                    st.markdown(f"**Qty:** {item.quantity}")
                    st.markdown(f"<div class='item-price'>{self.cfg.currency_symbol}{item.price:.2f}</div>", 
                               unsafe_allow_html=True)
                
                with col3:
                    if st.button("🗑️ Remove", key=f"remove_{item.id}", use_container_width=True):
                        if self.db.remove_cart_item(user_ctx.username, item.id):
                            st.success("Item removed!")
                            time.sleep(0.5)
                            st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Order summary
        self._render_order_summary(subtotal, shipping, tax, total)
        
        # Continue button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Continue Shopping", use_container_width=True):
                st.switch_page("pages/3_Gallery.py")
        
        with col2:
            if st.button("➡️ Proceed to Shipping", use_container_width=True):
                st.session_state.checkout_step = 'shipping'
                st.rerun()
    
    def _render_shipping_step(self, cart_items: List[CartItem], total: float) -> None:
        """Render shipping information step"""
        shipping_info = self.payment_processor.render_shipping_form()
        
        if shipping_info:
            st.session_state.shipping_info = shipping_info
            st.session_state.checkout_step = 'payment'
            st.rerun()
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Back to Cart", use_container_width=True):
                st.session_state.checkout_step = 'cart'
                st.rerun()
    
    def _render_payment_step(self, cart_items: List[CartItem], total: float, user_ctx: UserCtx) -> None:
        """Render payment step"""
        # Show order summary
        self._render_order_summary_compact(total)
        
        # Payment form
        payment_info = self.payment_processor.render_payment_methods(total)
        
        if payment_info:
            # Process the order
            result = self.db.create_order_with_payment(
                user_ctx.username, 
                cart_items, 
                payment_info, 
                st.session_state.shipping_info
            )
            
            if result.get('status') == 'success':
                st.session_state.payment_info = payment_info
                st.session_state.order_result = result
                st.session_state.checkout_step = 'confirmation'
                
                # Clear cart
                self.db.clear_user_cart(user_ctx.username)
                st.rerun()
            else:
                st.error(f"❌ Payment failed: {result.get('message', 'Unknown error')}")
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 Back to Shipping", use_container_width=True):
                st.session_state.checkout_step = 'shipping'
                st.rerun()
    
    def _render_confirmation_step(self) -> None:
        """Render order confirmation step"""
        st.markdown(
            '''
            <div class="order-confirmation slide-in">
                <div class="confirmation-icon">🎉</div>
                <h2>Order Placed Successfully!</h2>
                <p>Thank you for your purchase. Your order has been confirmed.</p>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        
        if 'order_result' in st.session_state and 'payment_info' in st.session_state:
            order_result = st.session_state.order_result
            payment_info = st.session_state.payment_info
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📄 Order Details")
                st.markdown(f"**Order ID:** #{order_result.get('order_id', 'N/A')}")
                st.markdown(f"**Amount Paid:** {self.cfg.currency_symbol}{payment_info.amount:.2f}")
                st.markdown(f"**Payment Method:** {payment_info.method.value}")
                st.markdown(f"**Transaction ID:** {payment_info.transaction_id}")
                st.markdown(f"**Date:** {payment_info.timestamp}")
            
            with col2:
                st.markdown("### 🚚 Delivery Information")
                if st.session_state.shipping_info:
                    shipping = st.session_state.shipping_info
                    st.markdown(f"**Name:** {shipping.full_name}")
                    st.markdown(f"**Address:** {shipping.address_line1}")
                    if shipping.address_line2:
                        st.markdown(f"**Address 2:** {shipping.address_line2}")
                    st.markdown(f"**City:** {shipping.city}, {shipping.state}")
                    st.markdown(f"**PIN:** {shipping.pincode}")
        
        # Security badges
        st.markdown(
            '''
            <div style="text-align: center; margin: 2rem 0;">
                <span class="security-badge">🔒 Secure Payment</span>
                <span class="security-badge">📱 SMS Updates</span>
                <span class="security-badge">🚚 Tracked Delivery</span>
                <span class="security-badge">💯 100% Genuine</span>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📧 Email Receipt", use_container_width=True):
                st.success("✅ Receipt sent to your email!")
        
        with col2:
            if st.button("📦 Track Order", use_container_width=True):
                st.info("🚚 Tracking information will be available within 24 hours")
        
        with col3:
            if st.button("🛒 Continue Shopping", use_container_width=True):
                # Reset checkout flow
                st.session_state.checkout_step = 'cart'
                st.session_state.shipping_info = None
                st.session_state.payment_info = None
                if 'order_result' in st.session_state:
                    del st.session_state.order_result
                st.switch_page("pages/05_Artworks.py")
    
    def _calculate_shipping(self, subtotal: float) -> float:
        """Calculate shipping charges"""
        if subtotal >= self.cfg.free_shipping_threshold:
            return 0.0
        return self.cfg.shipping_charge
    
    def _render_order_summary(self, subtotal: float, shipping: float, tax: float, total: float) -> None:
        """Render detailed order summary"""
        st.markdown(
            f'''
            <div class="order-summary">
                <h3>💰 Order Summary</h3>
                <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
                    <span>Subtotal:</span>
                    <span>{self.cfg.currency_symbol}{subtotal:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
                    <span>Shipping:</span>
                    <span>{self.cfg.currency_symbol}{shipping:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
                    <span>Tax (GST 18%):</span>
                    <span>{self.cfg.currency_symbol}{tax:.2f}</span>
                </div>
                <div class="price-breakdown">
                    <div style="display: flex; justify-content: space-between;">
                        <span class="total-amount">Total:</span>
                        <span class="total-amount">{self.cfg.currency_symbol}{total:.2f}</span>
                    </div>
                </div>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        
        if shipping == 0:
            st.success(f"🚚 FREE SHIPPING! (Orders above {self.cfg.currency_symbol}{self.cfg.free_shipping_threshold})")
    
    def _render_order_summary_compact(self, total: float) -> None:
        """Render compact order summary for payment step"""
        st.markdown(
            f'''
            <div class="order-summary">
                <h4>💰 Total Amount</h4>
                <div class="total-amount">{self.cfg.currency_symbol}{total:.2f}</div>
            </div>
            ''', 
            unsafe_allow_html=True
        )
    
    def _render_empty_cart(self) -> None:
        """Render empty cart message"""
        st.markdown(
            '''
            <div class="empty-cart">
                <strong>Your Cart is Empty</strong><br><br>
                Browse our amazing collection and add items to your cart!
            </div>
            ''', 
            unsafe_allow_html=True
        )
        
        if st.button("🎨 Browse Gallery", use_container_width=True):
            st.switch_page("pages/05_Artworks.py")

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class CartApplication:
    """Enhanced cart application with corrected components"""
    
    def __init__(self):
        self.cfg = UIConfig()
        self.db = DatabaseManager()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.style_manager = StyleManager(self.cfg, self.db)
        self.checkout_flow = CheckoutFlow(self.cfg, self.db)
    
    def run(self) -> None:
        """Main application entry point"""
        try:
            # Page configuration
            st.set_page_config(
                page_title=self.cfg.page_title,
                page_icon="🛒",
                layout=self.cfg.layout,
                initial_sidebar_state="collapsed"
            )
            
            # Apply styling
            self.style_manager.render(None)
            
            # Authentication check
            user_ctx = UserCtx.from_session()
            if not user_ctx:
                st.warning("🔐 Please login to view your cart.")
                st.stop()
            
            # Main container
            st.markdown("<div class='cart-container'>", unsafe_allow_html=True)
            
            # Page header
            st.markdown("<h1 class='page-title'>🛒 Shopping Cart & Checkout</h1>", unsafe_allow_html=True)
            
            # Render checkout flow
            self.checkout_flow.render(user_ctx)
            
            # Footer
            st.markdown("---")
            st.markdown(
                '''
                <div style="text-align: center; color: var(--secondary); margin: 2rem 0;">
                    <span class="security-badge">🔒 256-bit SSL Encryption</span>
                    <span class="security-badge">🛡️ PCI DSS Compliant</span>
                    <span class="security-badge">📞 24/7 Support</span>
                    <span class="security-badge">🚚 Secure Delivery</span>
                </div>
                ''', 
                unsafe_allow_html=True
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"❌ Application error: {e}")

def main() -> None:
    """Application main function"""
    try:
        app = CartApplication()
        app.run()
    except Exception as e:
        logger.error(f"Main application error: {e}")
        st.error("❌ Application failed to load. Please try again.")

if __name__ == "__main__":
    main()
