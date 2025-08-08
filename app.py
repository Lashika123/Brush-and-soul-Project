import streamlit as st
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


# Configuration using dataclass
@dataclass(frozen=True)
class AppConfig:
    """Application configuration with immutable settings"""
    PAGE_TITLE: str = "Brush and Soul"
    PAGE_ICON: str = "🎨"
    LAYOUT: str = "wide"
    PRIMARY_COLOR: str = "#8B4513"
    SECONDARY_COLOR: str = "#A0522D"
    ACCENT_COLOR: str = "#5C4033"
    LIGHT_COLOR: str = "#F8F4E8"
    DARK_COLOR: str = "#343434"


# Data models using dataclasses
@dataclass
class Artwork:
    """Artwork model with comprehensive details"""
    img_path: str
    title: str
    artist: str
    description: str
    materials: str
    state: str
    style: str
    price: str
    key: str
    
    def to_display_dict(self) -> Dict[str, str]:
        """Convert artwork to display dictionary"""
        return {
            "Artist": self.artist,
            "Title": self.title,
            "Description": self.description,
            "Materials": self.materials,
            "State": self.state,
            "Style": self.style,
            "Price": self.price
        }


@dataclass
class NavigationItem:
    """Navigation item model"""
    label: str
    page_path: str


@dataclass
class FeatureSection:
    """Feature section model"""
    title: str
    features: List[str]
    expanded: bool = True


@dataclass
class SearchResult:
    """Search result model for unified display"""
    category: str
    title: str
    subtitle: str
    description: str
    link: str = ""
    image_path: str = ""


# Abstract base classes
class BaseUIComponent(ABC):
    """Abstract base class for UI components"""
    
    @abstractmethod
    def render(self) -> None:
        """Render the component"""
        pass


class BaseThemeProvider(ABC):
    """Abstract base class for theme providers"""
    
    @abstractmethod
    def get_css(self) -> str:
        """Get CSS styling"""
        pass


# Search Component Implementation with Real Database Integration
class UniversalSearchComponent(BaseUIComponent):
    """Universal search component for all content types with real database integration"""
    
    def __init__(self, artworks: List[Artwork]):
        self.artworks = artworks
        self._initialize_session_state()
        self._init_database_connection()
    
    def _init_database_connection(self):
        """Initialize database connection"""
        try:
            from utils import (
                get_all_artworks, get_all_materials, get_all_blogs, 
                get_all_tutorials
            )
            self.get_all_artworks = get_all_artworks
            self.get_all_materials = get_all_materials
            self.get_all_blogs = get_all_blogs
            self.get_all_tutorials = get_all_tutorials
            self.db_available = True
        except ImportError as e:
            st.warning(f"Database connection not available: {e}")
            self.db_available = False
            # Set dummy functions to prevent errors
            self.get_all_artworks = lambda: []
            self.get_all_materials = lambda: []
            self.get_all_blogs = lambda: []
            self.get_all_tutorials = lambda: []
    
    def _initialize_session_state(self) -> None:
        """Initialize session state for search"""
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
    
    def _search_artworks(self, query: str) -> List[SearchResult]:
        """Search artworks from database"""
        results = []
        if not self.db_available:
            return results
        
        try:
            artworks = self.get_all_artworks()
            query_lower = query.lower()
            
            for artwork in artworks:
                # Handle None values and ensure safe string conversion
                title = str(artwork.get('title', '')).lower()
                username = str(artwork.get('username', '')).lower()
                description = str(artwork.get('description', '')).lower()
                materials = str(artwork.get('materials', '')).lower()
                style = str(artwork.get('style', '')).lower()
                state = str(artwork.get('state', '')).lower()
                
                if (query_lower in title or 
                    query_lower in username or 
                    query_lower in description or
                    query_lower in materials or
                    query_lower in style or
                    query_lower in state):
                    
                    results.append(SearchResult(
                        category="🎨 Artwork",
                        title=artwork.get('title', 'Unknown'),
                        subtitle=f"by {artwork.get('username', 'Unknown Artist')}",
                        description=f"{str(artwork.get('description', ''))[:100]}... | {artwork.get('style', '')} from {artwork.get('state', '')} | ₹{artwork.get('price', '0')}",
                        image_path=artwork.get('image_path', ''),
                        link="pages/05_Artworks.py"
                    ))
        except Exception as e:
            st.error(f"Error searching artworks: {e}")
        
        return results
    
    def _search_materials(self, query: str) -> List[SearchResult]:
        """Search materials from database"""
        results = []
        if not self.db_available:
            return results
        
        try:
            materials = self.get_all_materials()
            query_lower = query.lower()
            
            for material in materials:
                name = str(material.get('name', '')).lower()
                description = str(material.get('description', '')).lower()
                category = str(material.get('category', '')).lower()
                
                if (query_lower in name or 
                    query_lower in description or
                    query_lower in category):
                    
                    results.append(SearchResult(
                        category="🛒 Materials",
                        title=material.get('name', 'Unknown Material'),
                        subtitle=f"Category: {material.get('category', 'Unknown')}",
                        description=f"{str(material.get('description', ''))[:100]}... | Category: {material.get('category', '')} | ₹{material.get('price', '0')}",
                        image_path=material.get('image_path', ''),
                        link="pages/07_Materials.py"
                    ))
        except Exception as e:
            st.error(f"Error searching materials: {e}")
        
        return results
    
    def _search_blogs(self, query: str) -> List[SearchResult]:
        """Search blogs from database"""
        results = []
        if not self.db_available:
            return results
        
        try:
            blogs = self.get_all_blogs()
            query_lower = query.lower()
            
            for blog in blogs:
                title = str(blog.get('title', '')).lower()
                username = str(blog.get('username', '')).lower()
                content = str(blog.get('content', '')).lower()
                
                if (query_lower in title or 
                    query_lower in username or
                    query_lower in content):
                    
                    results.append(SearchResult(
                        category="📝 Blog",
                        title=blog.get('title', 'Unknown Blog'),
                        subtitle=f"by {blog.get('username', 'Unknown Author')}",
                        description=f"{str(blog.get('content', ''))[:100]}... | Posted: {blog.get('created_date', '')}",
                        image_path=blog.get('image_path', ''),
                        link="pages/06_Blogs.py"
                    ))
        except Exception as e:
            st.error(f"Error searching blogs: {e}")
        
        return results
    
    def _search_portfolios(self, query: str) -> List[SearchResult]:
        """Search artist portfolios from database"""
        results = []
        if not self.db_available:
            return results
        
        try:
            # Get unique artists/users from different sources
            artists = set()
            
            # From artworks
            artworks = self.get_all_artworks()
            for artwork in artworks:
                if artwork.get('username'):
                    artists.add(artwork.get('username'))
            
            # From blogs
            blogs = self.get_all_blogs()
            for blog in blogs:
                if blog.get('username'):
                    artists.add(blog.get('username'))
            
            query_lower = query.lower()
            
            for artist in artists:
                if query_lower in artist.lower():
                    results.append(SearchResult(
                        category="👤 Portfolio",
                        title=artist,
                        subtitle="Artist Portfolio",
                        description=f"View the complete portfolio and works by {artist}",
                        link="pages/09_Portfolio.py"
                    ))
                        
        except Exception as e:
            st.error(f"Error searching portfolios: {e}")
        
        return results
    
    def _search_tutorials(self, query: str) -> List[SearchResult]:
        """Search tutorials from database"""
        results = []
        if not self.db_available:
            return results
        
        try:
            tutorials = self.get_all_tutorials()
            query_lower = query.lower()
            
            for tutorial in tutorials:
                title = str(tutorial.get('title', '')).lower()
                username = str(tutorial.get('username', '')).lower()
                content = str(tutorial.get('content', '')).lower()
                
                if (query_lower in title or 
                    query_lower in username or
                    query_lower in content):
                    
                    results.append(SearchResult(
                        category="🎓 Tutorial",
                        title=tutorial.get('title', 'Unknown Tutorial'),
                        subtitle=f"by {tutorial.get('username', 'Unknown Creator')}",
                        description=f"{str(tutorial.get('content', ''))[:100]}... | Created: {tutorial.get('created_date', '')}",
                        image_path="",
                        link="pages/08_Tutorials.py"
                    ))
        except Exception as e:
            st.error(f"Error searching tutorials: {e}")
        
        return results
    
    def _perform_search(self, query: str) -> List[SearchResult]:
        """Perform comprehensive search across all categories"""
        if not query or len(query.strip()) < 2:
            return []
        
        if not self.db_available:
            st.warning("Database connection not available. Please check your utils.py configuration.")
            return []
        
        all_results = []
        
        try:
            # Search each category
            all_results.extend(self._search_artworks(query))
            all_results.extend(self._search_materials(query))
            all_results.extend(self._search_blogs(query))
            all_results.extend(self._search_portfolios(query))
            all_results.extend(self._search_tutorials(query))
        except Exception as e:
            st.error(f"Error performing search: {e}")
        
        return all_results
    
    def _render_search_results(self, results: List[SearchResult]) -> None:
        """Render search results in a structured format"""
        if not results:
            st.info("🔍 No results found. Try searching for artist names, artwork titles, materials, or techniques.")
            return
        
        st.markdown(f"### 🔍 Search Results ({len(results)} found)")
        
        # Group results by category
        categories = {}
        for result in results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        # Display results by category
        for category, items in categories.items():
            st.markdown(f"#### {category} ({len(items)} items)")
            
            for item in items:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="search-result-card">
                            <h4 style="color: var(--accent); margin-bottom: 5px;">{item.title}</h4>
                            <p style="color: var(--primary); font-weight: 600; margin-bottom: 8px;">{item.subtitle}</p>
                            <p style="color: var(--dark); margin-bottom: 10px;">{item.description}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    if item.image_path and item.image_path.strip():
                        try:
                            st.image(item.image_path, width=200)
                        except:
                            pass  # Skip if image can't be loaded
                    
                    if st.button(f"View {category.split()[1]}", key=f"view_{item.category}_{item.title}_{hash(item.description)}"):
                        st.switch_page(item.link)
                
                st.markdown("---")
    
    def render(self) -> None:
        """Render the search component"""
        # Search input with enhanced styling
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_query = st.text_input(
                "Search artworks, materials, blogs, portfolios, and tutorials...",
                label_visibility="collapsed"
            )
        
        with col2:
            search_button = st.button("🔍 Search", use_container_width=True)
        
        # Show database status
        if not self.db_available:
            st.error("⚠️ Database connection not available. Search functionality is limited.")
        
        # Perform search on input change or button click
        if search_query or search_button:
            if search_query != st.session_state.get('last_search_query', ''):
                st.session_state.last_search_query = search_query
                st.session_state.search_results = self._perform_search(search_query)
            
            # Display results
            self._render_search_results(st.session_state.search_results)


# Enhanced Theme Provider with Corrected CSS
class ModernThemeProvider(BaseThemeProvider):
    """Modern theme provider with corrected 3D effects and search styling"""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def get_css(self) -> str:
        """Generate CSS styling with corrections and enhancements"""
        return f"""
        <style>
        :root {{
            --primary: {self.config.PRIMARY_COLOR};
            --secondary: {self.config.SECONDARY_COLOR};
            --accent: {self.config.ACCENT_COLOR};
            --light: {self.config.LIGHT_COLOR};
            --dark: {self.config.DARK_COLOR};
            --glass-bg: rgba(255, 255, 255, 0.95);
            --shadow: 0 6px 12px rgba(139, 69, 19, 0.15);
            --hover-shadow: 0 8px 16px rgba(139, 69, 19, 0.25);
            --gradient-primary: linear-gradient(145deg, {self.config.PRIMARY_COLOR}, {self.config.SECONDARY_COLOR});
            --gradient-accent: linear-gradient(135deg, {self.config.ACCENT_COLOR}, {self.config.PRIMARY_COLOR});
        }}

        /* Global App Styling */
        .stApp {{
            background: linear-gradient(160deg, #f5f1e8 0%, #e8e0d0 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }}

        /* Enhanced 3D Cards with Fixed Hover Effects */
        .card-3d {{
            background: linear-gradient(145deg, #ffffff, #f8f8f8);
            border-radius: 16px;
            margin: 15px 0;
            box-shadow: 
                0 6px 12px rgba(139, 69, 19, 0.15), 
                0 10px 24px rgba(139, 69, 19, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.6);
            transform-style: preserve-3d;
            transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}

        .card-3d:hover {{
            transform: translateY(-8px) rotateX(2deg);
            box-shadow: 
                0 15px 30px rgba(139, 69, 19, 0.2), 
                0 20px 40px rgba(139, 69, 19, 0.15),
                inset 0 1px 0 rgba(255, 255, 255, 0.8);
        }}

        .card-3d::before {{
            content: '';
            position: absolute;
            top: 0; 
            left: 0; 
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
            border-radius: 16px 16px 0 0;
        }}

        /* Enhanced Search Result Cards */
        .search-result-card {{
            background: var(--glass-bg);
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: var(--shadow);
            border-left: 4px solid var(--primary);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            backdrop-filter: blur(10px);
        }}

        .search-result-card:hover {{
            transform: translateX(8px) translateY(-2px);
            box-shadow: var(--hover-shadow);
            border-left-width: 6px;
        }}

        /* Fixed Navigation Button Styling */
        .stButton > button {{
            background: var(--gradient-primary) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 
                0 4px 8px rgba(139, 69, 19, 0.2),
                0 1px 3px rgba(139, 69, 19, 0.3) !important;
            position: relative !important;
            overflow: hidden !important;
            width: 100% !important;
        }}

        .stButton > button:before {{
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent) !important;
            transition: left 0.5s !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 
                0 8px 16px rgba(139, 69, 19, 0.3),
                0 4px 8px rgba(139, 69, 19, 0.4) !important;
            background: linear-gradient(145deg, {self.config.SECONDARY_COLOR}, {self.config.ACCENT_COLOR}) !important;
        }}

        .stButton > button:hover:before {{
            left: 100% !important;
        }}

        .stButton > button:active {{
            transform: translateY(-1px) scale(0.98) !important;
        }}

        /* Enhanced Text Input Styling */
        .stTextInput > div > div > input {{
            border-radius: 12px !important;
            border: 2px solid rgba(139, 69, 19, 0.3) !important;
            font-size: 1rem !important;
            background: rgba(255, 255, 255, 0.95) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06) !important;
            backdrop-filter: blur(5px) !important;
        }}

        .stTextInput > div > div > input:focus {{
            border-color: var(--primary) !important;
            box-shadow: 
                inset 0 2px 4px rgba(0, 0, 0, 0.06),
                0 0 0 3px rgba(139, 69, 19, 0.15) !important;
            background: white !important;
        }}

        .stTextInput > div > div > input::placeholder {{
            color: rgba(139, 69, 19, 0.6) !important;
            font-style: italic !important;
        }}

        /* Enhanced Typography */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--accent);
            font-family: 'Georgia', 'Times New Roman', serif;
            font-weight: 600;
            line-height: 1.3;
        }}

        h1 {{ 
            font-size: 2.8rem; 
            text-align: center; 
            margin-bottom: 1rem;
            background: var(--gradient-accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 2px 4px rgba(139, 69, 19, 0.1);
        }}

        h2 {{
            font-size: 2.2rem;
            margin: 1.5rem 0 1rem 0;
        }}

        h3 {{
            font-size: 1.8rem;
            margin: 1.2rem 0 0.8rem 0;
        }}

        .subtitle {{
            font-size: 1.3rem;
            text-align: center;
            color: var(--accent);
            margin-bottom: 2.5rem;
            font-weight: 400;
            font-style: italic;
            opacity: 0.9;
        }}

        /* Enhanced Container Styling */
        .main > div {{
            padding: 1rem 0;
        }}

        /* Improved Expander Styling */
        .streamlit-expanderHeader {{
            background-color: var(--glass-bg) !important;
            border-radius: 8px !important;
            border: 1px solid rgba(139, 69, 19, 0.2) !important;
        }}

        /* Enhanced Divider */
        hr {{
            border: none !important;
            height: 2px !important;
            background: var(--gradient-primary) !important;
            margin: 2rem 0 !important;
            border-radius: 1px !important;
        }}

        /* Image Enhancement */
        .stImage > img {{
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(139, 69, 19, 0.15);
            transition: transform 0.3s ease;
        }}

        .stImage > img:hover {{
            transform: scale(1.02);
        }}

        /* Sidebar Styling */
        .css-1d391kg {{
            background-color: var(--light);
        }}

        /* Footer Enhancement */
        .footer-container {{
            background: var(--glass-bg);
            border-radius: 16px;
            margin-top: 3rem;
            text-align: center;
            border: 1px solid rgba(139, 69, 19, 0.1);
            backdrop-filter: blur(10px);
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .search-result-card {{
                margin: 0.5rem 0;
            }}
            
            h1 {{ 
                font-size: 2.2rem; 
            }}
            
            .card-3d {{
                margin: 10px 0;
                padding: 1rem;
            }}
            
            .stButton > button {{
                padding: 10px 16px !important;
                font-size: 0.9rem !important;
            }}
        }}

        @media (max-width: 480px) {{
            h1 {{ 
                font-size: 1.8rem; 
            }}
            
            .subtitle {{
                font-size: 1.1rem;
            }}
        }}

        /* Animation Classes */
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

        .fade-in-up {{
            animation: fadeInUp 0.6s ease-out;
        }}

        /* Loading States */
        .stSpinner > div {{
            border-color: var(--primary) transparent var(--primary) transparent !important;
        }}
        </style>
        """


# Navigation Component with Orders Button
class NavigationComponent(BaseUIComponent):
    """Navigation bar component with improved layout"""
    
    def __init__(self, navigation_items: List[NavigationItem]):
        self.navigation_items = navigation_items
    
    def render(self) -> None:
        """Render navigation bar with better spacing"""
        # Create columns for navigation items
        nav_cols = st.columns(len(self.navigation_items))
        
        for col, nav_item in zip(nav_cols, self.navigation_items):
            with col:
                # Add special styling for Orders button
                button_key = f"nav_{nav_item.label}"
                if nav_item.label == "Orders":
                    # Special styling for Orders button
                    if st.button(f" {nav_item.label}", key=button_key):
                        st.switch_page(nav_item.page_path)
                else:
                    if st.button(nav_item.label, key=button_key):
                        st.switch_page(nav_item.page_path)


class ArtworkGalleryComponent(BaseUIComponent):
    """Artwork gallery component with state management"""
    
    def __init__(self, artworks: List[Artwork]):
        self.artworks = artworks
        self._initialize_session_state()
    
    def _initialize_session_state(self) -> None:
        """Initialize session state for artwork details"""
        if 'show_artwork_detail' not in st.session_state:
            st.session_state['show_artwork_detail'] = {
                artwork.key: False for artwork in self.artworks
            }
    
    def _toggle_artwork_detail(self, artwork_key: str) -> None:
        """Toggle artwork detail visibility"""
        current_state = st.session_state['show_artwork_detail'].get(artwork_key, False)
        st.session_state['show_artwork_detail'][artwork_key] = not current_state
    
    def _render_artwork_card(self, artwork: Artwork, column) -> None:
        """Render individual artwork card"""
        with column:
            st.image(artwork.img_path, use_container_width=True)
            
            if st.button("View Details", key=f"view_{artwork.key}"):
                self._toggle_artwork_detail(artwork.key)
            
            # Show details if toggled
            if st.session_state['show_artwork_detail'][artwork.key]:
                self._render_artwork_details(artwork)
    
    def _render_artwork_details(self, artwork: Artwork) -> None:
        """Render artwork details with proper line breaks"""
        details = artwork.to_display_dict()
        detail_text = "  \n".join([f"**{key}:** {value}" for key, value in details.items()])
        st.markdown(detail_text, unsafe_allow_html=False)
    
    def render(self) -> None:
        """Render artwork gallery"""
        cols = st.columns(len(self.artworks))
        for col, artwork in zip(cols, self.artworks):
            self._render_artwork_card(artwork, col)


class FeatureSectionComponent(BaseUIComponent):
    """Feature section component"""
    
    def __init__(self, sections: List[FeatureSection]):
        self.sections = sections
    
    def render(self) -> None:
        """Render feature sections"""
        feat_cols = st.columns(len(self.sections))
        
        for col, section in zip(feat_cols, self.sections):
            with col:
                with st.expander(f"**{section.title}**", expanded=section.expanded):
                    for feature in section.features:
                        st.write(f"- {feature}")


class ActionButtonsComponent(BaseUIComponent):
    """Action buttons component"""
    
    def __init__(self, buttons: List[tuple]):
        self.buttons = buttons
    
    def render(self) -> None:
        """Render action buttons"""
        action_cols = st.columns([1, 1, 2])
        
        for i, (label, key, page_path) in enumerate(self.buttons):
            if i < len(action_cols):
                with action_cols[i]:
                    if st.button(label, key=key):
                        st.switch_page(page_path)


# Factory classes
class ArtworkFactory:
    """Factory for creating artwork instances"""
    
    @staticmethod
    def create_featured_artworks() -> List[Artwork]:
        """Create featured artworks collection"""
        artworks_data = [
            {
                "img_path": "D:/Brush and soul/uploads/Madhubani.jpg",
                "title": "Madhubani Painting",
                "artist": "Priya Sharma",
                "description": "Classic folk painting from Bihar using natural colors.",
                "materials": "Natural dyes, Handmade paper",
                "state": "Bihar",
                "style": "Madhubani",
                "price": "₹4,000",
                "key": "details1"
            },
            {
                "img_path": "D:/Brush and soul/uploads/warli1.jpg",
                "title": "Warli Art",
                "artist": "Rajesh Patil",
                "description": "Tribal geometric paintings representing daily life.",
                "materials": "White pigment, MUD background",
                "state": "Maharashtra",
                "style": "Warli",
                "price": "₹2,800",
                "key": "details2"
            },
            {
                "img_path": "D:/Brush and soul/uploads/kalamkari.jpg",
                "title": "Kalamkari",
                "artist": "Sunita Reddy",
                "description": "Narrative textile painting with hand-drawn motifs.",
                "materials": "Natural dyes, Cotton cloth",
                "state": "Andhra Pradesh",
                "style": "Kalamkari",
                "price": "₹4,200",
                "key": "details3"
            }
        ]
        
        return [Artwork(**artwork_data) for artwork_data in artworks_data]


class NavigationFactory:
    
    @staticmethod
    def create_main_navigation() -> List[NavigationItem]:
        """Create main navigation items without Home button, with Orders button"""
        nav_data = [
            ("Artwork", "pages/05_Artworks.py"),
            ("Blog", "pages/06_Blogs.py"),
            ("Material", "pages/07_Materials.py"),
            ("Tutorial", "pages/08_Tutorials.py"),
            ("Portfolio", "pages/09_Portfolio.py"),
            ("Order", "pages/10_Cart.py"),  # Orders button that opens Cart page
            ("Register", "pages/Register.py"),
            ("Login", "pages/Login.py")
        ]
        
        return [NavigationItem(label, page) for label, page in nav_data]


# Enhanced Main Application Class
class BrushAndSoulApp:
    """Enhanced main application class with real database search"""
    
    def __init__(self):
        self.config = AppConfig()
        self.theme_provider = ModernThemeProvider(self.config)
        self.artwork_factory = ArtworkFactory()
        self.navigation_factory = NavigationFactory()
        
        # Initialize components
        self.navigation = NavigationComponent(
            self.navigation_factory.create_main_navigation()
        )
        self.artwork_gallery = ArtworkGalleryComponent(
            self.artwork_factory.create_featured_artworks()
        )
        
        # Initialize search component with real database
        self.search_component = UniversalSearchComponent(
            self.artwork_factory.create_featured_artworks()
        )
        
        # Feature sections
        self.feature_sections = [
            FeatureSection(
                "For Art Lovers",
                [
                    "Discover genuine folk art with complete provenance",
                    "Secure purchasing experience with multiple payment options",
                    "Detailed artist profiles and portfolios",
                    "Real-time search across all content types",
                    "Educational resources and tutorials"
                ]
            ),
            FeatureSection(
                "For Artists",
                [
                    "Dedicated platform to showcase your work",
                    "Direct access to collectors worldwide",
                    "Fair compensation for your craft",
                    "Artist community support and networking",
                    "Tools to manage your portfolio and materials"
                ]
            )
        ]
        
        self.features_component = FeatureSectionComponent(self.feature_sections)
        
        # Action buttons
        self.action_buttons = ActionButtonsComponent([
            ("Explore Artworks", "explore", "pages/05_Artworks.py"),
            ("Artist Portal", "portal", "pages/09_Portfolio.py")
        ])
    
    def _setup_page_config(self) -> None:
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title=self.config.PAGE_TITLE,
            layout=self.config.LAYOUT,
            page_icon=self.config.PAGE_ICON
        )
    
    def _apply_theme(self) -> None:
        """Apply theme styling"""
        st.markdown(self.theme_provider.get_css(), unsafe_allow_html=True)
    
    def _render_header(self) -> None:
        """Render main header section"""
        st.markdown('<div class="card-3d">', unsafe_allow_html=True)
        st.markdown('<h1>Welcome To Brush and Soul</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Preserving India\'s Artistic Heritage Through Technology</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_about_section(self) -> None:
        """Render about us section"""
        st.header("Digital Home for Indian Folk Art")
        st.write("""
        Our platform serves as a vibrant online marketplace and educational hub dedicated to 
        India's traditional folk arts. We connect art lovers with authentic regional artisans 
        while preserving cultural heritage through modern technology.
        """)
        
        # Render feature sections
        self.features_component.render()
        
        st.subheader("Platform Features:")
        st.write("""
        - **Real-time Search**: Find artworks, materials, blogs, portfolios, and tutorials from live database
        - **Curated Collections**: Authentic traditional artworks from verified artists
        - **Interactive Learning**: Comprehensive tutorials and educational resources
        - **Cultural Preservation**: Digital archiving of traditional art forms
        - **Artist Support**: Tools and platform for creators to showcase and sell their work
        - **Community Building**: Connect with fellow art enthusiasts and professionals
        """)
        
        # Render action buttons
        self.action_buttons.render()
    
    def _render_footer(self) -> None:
        """Render footer section"""
        st.divider()
        st.markdown(
            """
            <div class="footer-container">
                <p><strong>Brush and Soul</strong> - Bridging Traditional Indian Art with Contemporary Audiences</p>
                <p style="font-size: 0.9rem; color: var(--dark);">
                    Real-time database search • Cultural preservation • Artist empowerment
                </p>
                <p style="font-size: 0.8rem; color: var(--secondary);">
                    🔍 Search • 🎨 Discover • 🛒 Purchase • 📚 Learn • 🤝 Connect
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    def run(self) -> None:
        """Enhanced main application entry point with real database search"""
        # Setup
        self._setup_page_config()
        self._apply_theme()
        
        # Render navigation
        self.navigation.render()
        
        # Render search component (prominently placed)
        self.search_component.render()
        
        # Check if there are active search results
        has_search_results = (
            hasattr(st.session_state, 'search_results') and 
            st.session_state.search_results and
            hasattr(st.session_state, 'last_search_query') and
            st.session_state.last_search_query
        )
        
        # If no active search, show main content
        if not has_search_results:
            self._render_header()
            
            # Featured artworks section
            st.markdown("## Featured Artworks")
            self.artwork_gallery.render()
            
            self._render_about_section()
        
        # Always render footer
        self._render_footer()


# Application entry point
def main():
    """Application entry point with real database integration"""
    app = BrushAndSoulApp()
    app.run()


if __name__ == "__main__":
    main()
