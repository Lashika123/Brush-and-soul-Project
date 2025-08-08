"""
pages/04_Dashboard.py
--------------------
Advanced Python dashboard with database backend integration.
Maintains exact UI and logic from the original file.
FIXED: Duplicate key error by ensuring all Streamlit element keys are unique.
"""

from __future__ import annotations

import datetime
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Advanced Type Definitions and Protocols                                   #
# --------------------------------------------------------------------------- #
class DatabaseOperationProtocol(Protocol):
    """Protocol for database operations"""
    def get_orders(self, username: str) -> List[Dict[str, Any]]: ...
    def remove_order_by_id(self, order_id: Union[str, int]) -> bool: ...
    def get_artist_artworks(self, username: str) -> List[Dict[str, Any]]: ...
    def update_artwork(self, artwork_id: int, updates: Dict[str, Any]) -> bool: ...
    def remove_artwork(self, artwork_id: int) -> bool: ...

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
    page_title: str = "Dashboard"
    layout: str = "wide"
    description_limit: int = 100
    currency_symbol: str = "₹"

@dataclass
class UserContext:
    """User context information"""
    username: str
    role: UserRole
    email: Optional[str] = None
    
    @classmethod
    def from_session_state(cls, user_data: Dict[str, Any]) -> 'UserContext':
        """Create UserContext from session state data"""
        return cls(
            username=user_data.get("username", "User").title(),
            role=UserRole.from_string(user_data.get("user_type", "customer")),
            email=user_data.get("email")
        )

@dataclass
class ArtworkData:
    """Artwork data structure"""
    title: str
    artist: str
    price: float
    description: str
    artwork_id: Optional[int] = None
    image_path: Optional[str] = None
    status: str = "active"
    upload_date: Optional[str] = None

@dataclass
class OrderItemData:
    """Order item data structure"""
    title: str
    price: float
    quantity: int = 1

@dataclass
class OrderData:
    """Order data structure"""
    order_id: Union[str, int]
    username: str
    total_amount: float
    order_date: str
    items: List[OrderItemData] = field(default_factory=list)

# --------------------------------------------------------------------------- #
#  Advanced Database Manager with Error Handling                             #
# --------------------------------------------------------------------------- #
class DatabaseManager:
    """Advanced database operations manager with comprehensive error handling"""
    
    def __init__(self):
        self._operations = self._initialize_database_operations()
    
    def _initialize_database_operations(self) -> DatabaseOperationProtocol:
        """Initialize database operations with error handling"""
        try:
            from utils import get_orders, remove_order_by_id, get_artist_artworks, update_artwork, remove_artwork
            
            # Create a wrapper class to satisfy the protocol
            class DatabaseOperations:
                def __init__(self):
                    self.get_orders = get_orders
                    self.remove_order_by_id = remove_order_by_id
                    self.get_artist_artworks = get_artist_artworks
                    self.update_artwork = update_artwork
                    self.remove_artwork = remove_artwork
            
            logger.info("Database operations initialized successfully")
            return DatabaseOperations()
            
        except ImportError as e:
            logger.error(f"Failed to import database utilities: {e}")
            st.error("Database connection error. Please check system configuration.")
            raise

    @contextmanager
    def error_handler(self, operation_name: str):
        """Context manager for database operation error handling"""
        try:
            yield
        except Exception as e:
            logger.error(f"Database operation '{operation_name}' failed: {e}")
            st.error(f"Database operation failed: {operation_name}")
            raise

    def fetch_user_orders(self, username: str) -> List[OrderData]:
        """Fetch and parse user orders with error handling"""
        with self.error_handler("fetch_user_orders"):
            raw_orders = self._operations.get_orders(username)
            return [self._parse_order_data(order) for order in raw_orders]

    def fetch_artist_artworks(self, username: str) -> List[ArtworkData]:
        """Fetch and parse artist artworks with error handling"""
        with self.error_handler("fetch_artist_artworks"):
            raw_artworks = self._operations.get_artist_artworks(username)
            return [self._parse_artwork_data(artwork) for artwork in raw_artworks]

    def update_artwork_data(self, artwork_id: int, updates: Dict[str, Any]) -> bool:
        """Update artwork with validation and error handling"""
        with self.error_handler("update_artwork"):
            return self._operations.update_artwork(artwork_id, updates)

    def delete_artwork_data(self, artwork_id: int) -> bool:
        """Delete artwork with error handling"""
        with self.error_handler("delete_artwork"):
            return self._operations.remove_artwork(artwork_id)

    def delete_order_data(self, order_id: Union[str, int]) -> bool:
        """Delete order with error handling"""
        with self.error_handler("delete_order"):
            return self._operations.remove_order_by_id(order_id)

    def _parse_order_data(self, raw_order: Dict[str, Any]) -> OrderData:
        """Parse raw order data into structured format"""
        items = []
        for item_data in raw_order.get('items', []):
            items.append(OrderItemData(
                title=item_data.get('title', 'Untitled'),
                price=float(item_data.get('price', 0)),
                quantity=item_data.get('quantity', 1)
            ))

        # Parse date exactly as in original
        raw_date = raw_order.get('date') or raw_order.get('order_date')
        formatted_date = self._format_order_date(raw_date)

        return OrderData(
            order_id=raw_order.get('order_id', f"unknown_{hash(str(raw_order))}"),
            username=raw_order.get('username', ''),
            total_amount=float(raw_order.get('total_amount') or raw_order.get('total', 0)),
            order_date=formatted_date,
            items=items
        )

    def _parse_artwork_data(self, raw_artwork: Dict[str, Any]) -> ArtworkData:
        """Parse raw artwork data into structured format"""
        return ArtworkData(
            artwork_id=raw_artwork.get('id'),
            title=raw_artwork.get('title', 'Untitled'),
            artist=raw_artwork.get('artist', ''),
            price=float(raw_artwork.get('price', 0)),
            description=raw_artwork.get('description', ''),
            status=raw_artwork.get('status', 'active'),
            upload_date=raw_artwork.get('upload_date')
        )

    def _format_order_date(self, raw_date: Optional[str]) -> str:
        """Format order date exactly as in original"""
        if raw_date:
            try:
                parsed_date = datetime.datetime.fromisoformat(raw_date)
                return parsed_date.strftime("%d-%m-%Y")
            except Exception:
                return raw_date
        return "Date Unknown"

# --------------------------------------------------------------------------- #
#  Advanced Session Management                                                #
# --------------------------------------------------------------------------- #
class SessionManager:
    """Advanced session state management with validation"""
    
    @staticmethod
    def validate_authentication() -> UserContext:
        """Validate user authentication and return user context"""
        if "user" not in st.session_state or not st.session_state.logged_in:
            st.warning("Please login to access the dashboard.")
            st.stop()
        
        return UserContext.from_session_state(st.session_state.user)

    @staticmethod
    def initialize_cache() -> None:
        """Initialize session cache for performance optimization"""
        cache_keys = ['orders_cache']
        for key in cache_keys:
            if key not in st.session_state:
                st.session_state[key] = []

# --------------------------------------------------------------------------- #
#  Abstract UI Component System                                               #
# --------------------------------------------------------------------------- #
class UIComponent(ABC):
    """Abstract base class for UI components"""
    
    def __init__(self, config: UIConfiguration, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
    
    @abstractmethod
    def render(self, user_context: UserContext) -> None:
        """Render the UI component"""
        pass

class WelcomeSection(UIComponent):
    """Welcome section component"""
    
    def render(self, user_context: UserContext) -> None:
        """Render welcome section exactly as original"""
        st.markdown(f"""
            <div class="welcome-section">
                <h2 style='color: var(--accent); font-family: "Playfair Display", serif;'>Welcome, {user_context.username}! 👋</h2>
                <div class="divider"></div>
            </div>
        """, unsafe_allow_html=True)

class ArtistDashboardSection(UIComponent):
    """Artist dashboard section component"""
    
    def render(self, user_context: UserContext) -> None:
        """Render artist dashboard exactly as original"""
        spacer1, main_col, spacer2 = st.columns([1, 3, 1])

        with main_col:
            st.markdown("<h2 class='header'>🎨 Artist's Hub</h2>", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom:30px;'></div>", unsafe_allow_html=True)

            self._render_action_cards()
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            self._render_artwork_collection(user_context)

    def _render_action_cards(self) -> None:
        """Render artist action cards with unique keys"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="action-card">
                <h4>🆕 Upload New Artwork</h4>
                <p>Add your new artwork to the gallery</p>
            """, unsafe_allow_html=True)
            if st.button("➕ Add Artwork", key="artist_dashboard_upload_artwork_btn"):
                st.switch_page("pages/05_Artworks.py")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="action-card">
                <h4>📝 Manage Your Blogs</h4>
                <p>Create or edit your art blogs</p>
            """, unsafe_allow_html=True)
            if st.button("📝 Open Blog Manager", key="artist_dashboard_manage_blogs_btn"):
                st.switch_page("pages/06_Blogs.py")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="action-card">
                <h4>🖼️ View Portfolio</h4>
                <p>See your complete portfolio</p>
            """, unsafe_allow_html=True)
            if st.button("🎨 View My Portfolio", key="artist_dashboard_view_portfolio_btn"):
                st.switch_page("pages/09_Portfolio.py")
            st.markdown("</div>", unsafe_allow_html=True)

    def _render_artwork_collection(self, user_context: UserContext) -> None:
        """Render artwork collection exactly as original"""
        st.markdown("<h3 class='header'>🗂 Your Artwork Collection</h3>", unsafe_allow_html=True)
        
        try:
            artworks = self.db_manager.fetch_artist_artworks(user_context.username)
        except Exception:
            artworks = []

        if artworks:
            self._render_artwork_list(artworks)
        else:
            self._render_empty_artwork_state()

    def _render_artwork_list(self, artworks: List[ArtworkData]) -> None:
        """Render artwork list with edit/delete functionality"""
        for idx, art in enumerate(artworks):
            with st.container():
                # Truncate description exactly as original
                description = art.description[:self.config.description_limit] + "..." if len(art.description) > self.config.description_limit else art.description
                
                st.markdown(f"""
                    <div class="card-3d artwork-card">
                        <h4>🎨 {art.title}</h4>
                        <p><strong>Price:</strong> {self.config.currency_symbol}{art.price}</p>
                        <p>{description}</p>
                    </div>
                """, unsafe_allow_html=True)

                self._render_artwork_editor(art, idx)

    def _render_artwork_editor(self, artwork: ArtworkData, idx: int) -> None:
        """Render artwork edit controls exactly as original"""
        with st.expander("✏️ Edit Artwork Details", expanded=False):
            new_title = st.text_input("Title", value=artwork.title, key=f"artist_dashboard_title-{idx}")
            new_price = st.number_input(
                "Price (INR)",
                value=float(artwork.price),
                key=f"artist_dashboard_price-{idx}",
                min_value=0.0,
                step=100.0
            )
            new_description = st.text_area("Description", value=artwork.description, key=f"artist_dashboard_desc-{idx}")

            col_edit, col_delete = st.columns(2)
            
            with col_edit:
                if st.button("💾 Save Changes", key=f"artist_dashboard_save-{idx}"):
                    self._handle_artwork_update(artwork, new_title, new_price, new_description)
            
            with col_delete:
                if st.button("🗑️ Delete Artwork", key=f"artist_dashboard_delete-{idx}"):
                    self._handle_artwork_deletion(artwork, idx)

    def _handle_artwork_update(self, artwork: ArtworkData, new_title: str, new_price: float, new_description: str) -> None:
        """Handle artwork update exactly as original"""
        updates = {
            'title': new_title,
            'price': new_price,
            'description': new_description
        }
        
        try:
            if self.db_manager.update_artwork_data(artwork.artwork_id, updates):
                st.success(f"Artwork '{new_title}' updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update artwork.")
        except Exception:
            st.error("Failed to update artwork.")

    def _handle_artwork_deletion(self, artwork: ArtworkData, idx: int) -> None:
        """Handle artwork deletion exactly as original"""
        confirm = st.checkbox(
            f"Are you sure you want to delete '{artwork.title}'?", 
            key=f"artist_dashboard_confirm-{idx}"
        )
        
        if confirm:
            try:
                if self.db_manager.delete_artwork_data(artwork.artwork_id):
                    st.success(f"Artwork '{artwork.title}' deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete artwork.")
            except Exception:
                st.error("Failed to delete artwork.")

    def _render_empty_artwork_state(self) -> None:
        """Render empty artwork state exactly as original"""
        st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">✨</div>
                <h4 style="color: var(--accent);">No Artworks Yet</h4>
                <p>You haven't uploaded any artworks yet.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("➕ Add Artwork", key="artist_dashboard_empty_state_upload_artwork_btn"):
            st.switch_page("pages/05_Artworks.py")

class CustomerDashboardSection(UIComponent):
    """Customer dashboard section component"""
    
    def render(self, user_context: UserContext) -> None:
        """Render customer dashboard exactly as original"""
        st.markdown("<h2 class='header'>🛍️ Customer's Corner</h2>", unsafe_allow_html=True)
        
        self._render_customer_action_cards()
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    def _render_customer_action_cards(self) -> None:
        """Render customer action cards with unique keys"""
        col1, col2, col3, col4 = st.columns(4)

        action_cards = [
            ("🎨 Browse Art", "Explore beautiful artworks", "customer_dashboard_browse_art_btn", "pages/05_Artworks.py"),
            ("🛒 Shop Supplies", "Find art materials", "customer_dashboard_shop_supplies_btn", "pages/07_Materials.py"),
            ("📚 Learn", "Access tutorials", "customer_dashboard_learn_btn", "pages/08_Tutorials.py"),
            ("🛍️ View Cart", "Check your cart", "customer_dashboard_view_cart_btn", "pages/10_Cart.py")
        ]

        columns = [col1, col2, col3, col4]
        
        for i, (title, description, key, page) in enumerate(action_cards):
            with columns[i]:
                st.markdown(f"""
                    <div class="action-card" style="pointer-events:none;">
                        <h4>{title}</h4>
                        <p>{description}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(title, key=key):
                    st.switch_page(page)

class OrderHistorySection(UIComponent):
    """Order history section component"""
    
    def render(self, user_context: UserContext) -> None:
        """Render order history exactly as original"""
        try:
            orders = self.db_manager.fetch_user_orders(user_context.username)
        except Exception:
            orders = []

        st.markdown("<h3 class='header'>📦 Your Order History</h3>", unsafe_allow_html=True)

        if orders:
            self._render_order_list(orders, user_context.username)
        else:
            self._render_empty_orders_state()

    def _render_order_list(self, orders: List[OrderData], username: str) -> None:
        """Render order list exactly as original"""
        # Cache orders in session state for smooth UI updates
        if 'orders_cache' not in st.session_state:
            st.session_state.orders_cache = orders.copy()

        orders_to_show = st.session_state.orders_cache
        deleted_any = False

        for order in orders_to_show:
            with st.container():
                st.markdown(f"""
                    <div class="card-3d">
                        <h4>📅 Order Date: {order.order_date}</h4>
                        <h5>🧑 Username: {username}</h5>
                        <p><strong>Total: {self.config.currency_symbol}{order.total_amount}</strong></p>
                        <div style='margin-top: 10px;'>
                """, unsafe_allow_html=True)

                # Render order items exactly as original
                for item in order.items:
                    st.markdown(f"""
                        <div class="order-item">
                            <p><strong>{item.title}</strong> ({self.config.currency_symbol}{item.price})</p>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                # Delete Order button exactly as original with unique key
                delete_key = f"order_history_delete_order_{order.order_id}"
                if st.button("🗑️ Delete Order", key=delete_key):
                    if self._handle_order_deletion(order.order_id):
                        deleted_any = True

                st.markdown("</div>", unsafe_allow_html=True)

        if deleted_any:
            st.rerun()

    def _handle_order_deletion(self, order_id: Union[str, int]) -> bool:
        """Handle order deletion exactly as original"""
        # Remove from visual cache
        st.session_state.orders_cache = [
            o for o in st.session_state.orders_cache if o.order_id != order_id
        ]
        
        # Remove from backend persistent store
        try:
            if self.db_manager.delete_order_data(order_id):
                st.success(f"Order {order_id} deleted successfully!")
                return True
            else:
                st.error(f"Failed to delete order {order_id}")
                return False
        except Exception as e:
            st.error(f"Failed to delete order {order_id}: {e}")
            return False

    def _render_empty_orders_state(self) -> None:
        """Render empty orders state exactly as original"""
        st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">🛒</div>
                <h4 style="color: var(--accent);">No Orders Yet</h4>
                <p>You haven't placed any orders yet.</p>
            </div>
        """, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Main Dashboard Application with Advanced Architecture                      #
# --------------------------------------------------------------------------- #
class DashboardApplication:
    """Main dashboard application with component-based architecture"""
    
    def __init__(self):
        self.config = UIConfiguration()
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager()
        
        # Initialize UI components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize all UI components"""
        self.welcome_section = WelcomeSection(self.config, self.db_manager)
        self.artist_dashboard = ArtistDashboardSection(self.config, self.db_manager)
        self.customer_dashboard = CustomerDashboardSection(self.config, self.db_manager)
        self.order_history = OrderHistorySection(self.config, self.db_manager)

    def run(self) -> None:
        """Main application entry point"""
        # --- Page config ---
        st.set_page_config(page_title=self.config.page_title, layout=self.config.layout)

        # --- Custom CSS Styling --- (exactly as original)
        self._apply_custom_styling()

        # Hide Streamlit page name pill
        st.markdown("""
        <style>
            /* Hide Streamlit's default page-name pill in the main toolbar */
            header[data-testid="stHeader"] div:first-child {visibility:hidden;}
        </style>
        """, unsafe_allow_html=True)

        # --- Authentication check ---
        user_context = self.session_manager.validate_authentication()

        # --- Welcome Section ---
        self.welcome_section.render(user_context)

        # ---- SHOW ONLY THE DASHBOARD FOR THE LOGGED-IN USER TYPE ----
        if user_context.role == UserRole.ARTIST:
            self.artist_dashboard.render(user_context)
        elif user_context.role == UserRole.CUSTOMER:
            self.customer_dashboard.render(user_context)

        # --- Order History (common for both user types) ---
        self.order_history.render(user_context)

    def _apply_custom_styling(self) -> None:
        """Apply custom CSS styling exactly as original"""
        st.markdown("""
        <style>
            :root {
                --primary: #8B4513;
                --secondary: #A0522D;
                --accent: #5C4033;
                --light: #F8F4E8;
                --dark: #343434;
            }
            .stApp {
                background: linear-gradient(160deg, #f5f1e8 0%, #e8e0d0 100%);
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            .card-3d {
                background: white;
                border-radius: 16px;
                padding: 25px;
                margin: 15px 0;
                box-shadow: 0 6px 12px rgba(139, 69, 19, 0.15), 0 10px 24px rgba(139, 69, 19, 0.1);
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            .card-3d:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 24px rgba(139, 69, 19, 0.2), 0 16px 32px rgba(139, 69, 19, 0.15);
            }
            .card-3d::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--primary), var(--secondary));
            }
            h1, h2, h3 {
                color: var(--accent);
                font-family: 'Playfair Display', serif;
                font-weight: 600;
            }
            .stButton>button {
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 500;
                transition: all 0.3s ease;
                border: none;
                background: linear-gradient(145deg, var(--primary), var(--secondary));
                color: white;
            }
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(139, 69, 19, 0.2);
            }
            .danger-btn {
                background: linear-gradient(145deg, #a52a2a, #8b0000);
            }
            .header {
                color: var(--accent);
                margin-bottom: 16px;
                font-family: 'Playfair Display', serif;
                position: relative;
            }
            .header:after {
                content: '';
                position: absolute;
                width: 100%; height: 3px;
                bottom: -5px; left: 0;
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                border-radius: 3px;
            }
            .divider {
                height: 1px;
                margin: 24px 0;
                background: linear-gradient(90deg, transparent, rgba(139, 69, 19, 0.5), transparent);
            }
            .artwork-card {
                border-left: 4px solid var(--primary);
                padding-left: 20px;
                margin-bottom: 20px;
                background: rgba(139, 69, 19, 0.05);
            }
            .order-item {
                background: rgba(248, 244, 232, 0.7);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                border-left: 3px solid var(--primary);
                transition: all 0.3s ease;
            }
            .order-item:hover {
                transform: translateX(5px);
                background: rgba(139, 69, 19, 0.05);
            }
            .action-card {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 16px;
                padding: 20px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 4px 8px rgba(139, 69, 19, 0.1);
                margin-bottom: 20px;
            }
            .action-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 16px rgba(139, 69, 19, 0.2);
            }
            .action-card h4 {
                color: var(--accent);
                margin-bottom: 8px;
                font-family: 'Playfair Display', serif;
            }
            .action-card p {
                color: #666;
                font-size: 0.9em;
            }
            .welcome-section {
                background: linear-gradient(135deg, rgba(139, 69, 19, 0.1), rgba(160, 82, 45, 0.1));
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 40px;
                text-align: center;
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            .empty-state {
                text-align: center;
                padding: 40px 20px;
                border-radius: 16px;
                background: rgba(255, 255, 255, 0.8);
                margin: 20px 0;
                box-shadow: 0 4px 8px rgba(139, 69, 19, 0.1);
            }
            .empty-state-icon {
                font-size: 48px;
                margin-bottom: 16px;
                color: var(--primary);
            }
        </style>
        """, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Application Entry Point                                                    #
# --------------------------------------------------------------------------- #
def main() -> None:
    """Application main function with error handling"""
    try:
        app = DashboardApplication()
        app.run()
    except Exception as e:
        logger.error(f"Critical application error: {e}")
        st.error("Dashboard failed to load. Please contact support.")

if __name__ == "__main__":
    main()
