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


# FIXED Search Component with View Button Styling
class UniversalSearchComponent(BaseUIComponent):
    """Universal search component with corrected view button UI"""
    
    def __init__(self, artworks: List[Artwork]):
        self.artworks = artworks
        self._initialize_session_state()
        self._init_database_connection()
    
    def _init_database_connection(self):
        """Initialize database connection"""
        try:
            from utils import (
                get_all_artworks, get_all_materials, get_all_blogs, 
                get_all_tutorials, get_artists_with_content
            )
            self.get_all_artworks = get_all_artworks
            self.get_all_materials = get_all_materials
            self.get_all_blogs = get_all_blogs
            self.get_all_tutorials = get_all_tutorials
            self.get_artists_with_content = get_artists_with_content
            self.db_available = True
        except ImportError as e:
            st.warning(f"Database connection not available: {e}")
            self.db_available = False
            # Set dummy functions to prevent errors
            self.get_all_artworks = lambda: []
            self.get_all_materials = lambda: []
            self.get_all_blogs = lambda: []
            self.get_all_tutorials = lambda: []
            self.get_artists_with_content = lambda: []
    
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
                title = str(artwork.get('title', '')).lower()
                description = str(artwork.get('description', '')).lower()
                materials = str(artwork.get('materials', '')).lower()
                style = str(artwork.get('style', '')).lower()
                state = str(artwork.get('state', '')).lower()
                
                artist_name = (artwork.get('artist') or 
                             artwork.get('username') or 
                             artwork.get('creator') or 
                             artwork.get('author') or 
                             'Unknown Artist')
                artist = str(artist_name).lower()
                
                if (query_lower in title or 
                    query_lower in artist or 
                    query_lower in description or
                    query_lower in materials or
                    query_lower in style or
                    query_lower in state):
                    
                    results.append(SearchResult(
                        category="🎨 Artwork",
                        title=artwork.get('title', 'Unknown'),
                        subtitle=f"by {artist_name}",
                        description=f"{str(artwork.get('description', ''))[:100]}... | {artwork.get('style', '')} from {artwork.get('state', '')} | ₹{artwork.get('price', '0')}",
                        image_path=artwork.get('image_path', artwork.get('image', '')),
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
                
                seller_name = (material.get('seller') or 
                             material.get('username') or 
                             material.get('creator') or 
                             material.get('author') or 
                             'Unknown Seller')
                seller = str(seller_name).lower()
                
                if (query_lower in name or 
                    query_lower in description or
                    query_lower in category or
                    query_lower in seller):
                    
                    results.append(SearchResult(
                        category="🛒 Materials",
                        title=material.get('name', 'Unknown Material'),
                        subtitle=f"by {seller_name} | Category: {material.get('category', 'Unknown')}",
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
                content = str(blog.get('content', '')).lower()
                
                author_name = (blog.get('author') or 
                             blog.get('username') or 
                             blog.get('creator') or 
                             'Unknown Author')
                author = str(author_name).lower()
                
                if (query_lower in title or 
                    query_lower in author or
                    query_lower in content):
                    
                    results.append(SearchResult(
                        category="📝 Blog",
                        title=blog.get('title', 'Unknown Blog'),
                        subtitle=f"by {author_name}",
                        description=f"{str(blog.get('content', ''))[:100]}... | Posted: {blog.get('created_date', blog.get('timestamp', ''))}",
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
            artists = self.get_artists_with_content()
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
                content = str(tutorial.get('content', '')).lower()
                
                creator_name = (tutorial.get('creator') or 
                              tutorial.get('author') or 
                              tutorial.get('username') or 
                              'Unknown Creator')
                creator = str(creator_name).lower()
                
                if (query_lower in title or 
                    query_lower in creator or
                    query_lower in content):
                    
                    results.append(SearchResult(
                        category="🎓 Tutorial",
                        title=tutorial.get('title', 'Unknown Tutorial'),
                        subtitle=f"by {creator_name}",
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
            all_results.extend(self._search_artworks(query))
            all_results.extend(self._search_materials(query))  
            all_results.extend(self._search_blogs(query))
            all_results.extend(self._search_portfolios(query))
            all_results.extend(self._search_tutorials(query))
        except Exception as e:
            st.error(f"Error performing search: {e}")
        
        return all_results
    
    def _render_search_results(self, results: List[SearchResult]) -> None:
        """Render search results with corrected view button styling"""
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
        
        # Display results by category with corrected view buttons
        for category, items in categories.items():
            st.markdown(f"#### {category} ({len(items)} items)")
            
            for i, item in enumerate(items):
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
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                st.image(item.image_path, width=150)
                            with col2:
                                # View button with CSS wrapper for styling
                                st.markdown('<div class="view-button-container">', unsafe_allow_html=True)
                                
                                button_labels = {
                                    "🎨 Artwork": "View Artwork",
                                    "🛒 Materials": "View Materials", 
                                    "📝 Blog": "View Blog",
                                    "👤 Portfolio": "View Portfolio",
                                    "🎓 Tutorial": "View Tutorial"
                                }
                                
                                button_label = button_labels.get(item.category, "View Details")
                                unique_key = f"view_btn_{item.category.replace(' ', '_')}_{i}_{hash(item.title + item.subtitle)}"
                                
                                if st.button(
                                    f"🔍 {button_label}", 
                                    key=unique_key,
                                    help=f"Navigate to {button_label.lower()}"
                                ):
                                    with st.spinner(f"Opening {button_label.lower()}..."):
                                        st.switch_page(item.link)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                        except:
                            # Fallback without image
                            st.markdown('<div class="view-button-container">', unsafe_allow_html=True)
                            
                            button_labels = {
                                "🎨 Artwork": "View Artwork",
                                "🛒 Materials": "View Materials", 
                                "📝 Blog": "View Blog",
                                "👤 Portfolio": "View Portfolio",
                                "🎓 Tutorial": "View Tutorial"
                            }
                            
                            button_label = button_labels.get(item.category, "View Details")
                            unique_key = f"view_btn_fallback_{item.category.replace(' ', '_')}_{i}_{hash(item.title)}"
                            
                            if st.button(
                                f"🔍 {button_label}", 
                                key=unique_key,
                                help=f"Navigate to {button_label.lower()}"
                            ):
                                with st.spinner(f"Opening {button_label.lower()}..."):
                                    st.switch_page(item.link)
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        # No image case
                        st.markdown('<div class="view-button-container">', unsafe_allow_html=True)
                        
                        button_labels = {
                            "🎨 Artwork": "View Artwork",
                            "🛒 Materials": "View Materials", 
                            "📝 Blog": "View Blog",
                            "👤 Portfolio": "View Portfolio", 
                            "🎓 Tutorial": "View Tutorial"
                        }
                        
                        button_label = button_labels.get(item.category, "View Details")
                        unique_key = f"view_btn_no_img_{item.category.replace(' ', '_')}_{i}_{hash(item.title + str(i))}"
                        
                        if st.button(
                            f"🔍 {button_label}", 
                            key=unique_key,
                            help=f"Navigate to {button_label.lower()}"
                        ):
                            with st.spinner(f"Opening {button_label.lower()}..."):
                                st.switch_page(item.link)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown("---")
    
    def render(self) -> None:
        """Render the search component"""
        st.markdown("### 🔍 Universal Search")
        st.markdown("*Search for artists, artworks, materials, blogs, portfolios, and tutorials*")
        
        # Search input with clean styling
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_query = st.text_input(
                "Search artworks, materials, blogs, portfolios, and tutorials...",
                placeholder="Try: artist name, artwork title, material type...",
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


# Enhanced Theme Provider with Corrected View Button Styling
class ModernThemeProvider(BaseThemeProvider):
    """Modern theme provider with corrected view button styling matching image 2"""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def get_css(self) -> str:
        """Generate CSS styling with corrected view button colors matching image 2"""
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
            
            /* View button colors matching image 2 */
            --view-button-bg: #007BFF;
            --view-button-hover: #0056b3;
            --view-button-active: #004085;
        }}

        /* Global App Styling */
        .stApp {{
            background: linear-gradient(160deg, #f5f1e8 0%, #e8e0d0 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }}

        /* CORRECTED VIEW BUTTONS - Matching Image 2 Style */
        .view-button-container .stButton > button {{
            background: var(--view-button-bg) !important;
            color: white !important;
            border: 1px solid var(--view-button-bg) !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            padding: 8px 16px !important;
            margin: 6px 0 !important;
            transition: all 0.2s ease !important;
            box-shadow: 
                0 2px 4px rgba(0, 123, 255, 0.2),
                0 1px 2px rgba(0, 123, 255, 0.3) !important;
            text-transform: none !important;
            letter-spacing: normal !important;
            position: relative !important;
            overflow: hidden !important;
            min-width: 120px !important;
            height: 36px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        .view-button-container .stButton > button:hover {{
            background: var(--view-button-hover) !important;
            border-color: var(--view-button-hover) !important;
            transform: translateY(-1px) !important;
            box-shadow: 
                0 4px 8px rgba(0, 123, 255, 0.3),
                0 2px 4px rgba(0, 123, 255, 0.4) !important;
        }}

        .view-button-container .stButton > button:active {{
            background: var(--view-button-active) !important;
            border-color: var(--view-button-active) !important;
            transform: translateY(0px) !important;
            box-shadow: 
                0 1px 2px rgba(0, 123, 255, 0.3) !important;
        }}

        /* EXTREMELY FIXED: Force Single Line Navigation */
        .stColumns {{
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 3px !important;
            justify-content: space-around !important;
            align-items: stretch !important;
            width: 100% !important;
            overflow-x: auto !important;
            overflow-y: visible !important;
        }}

        .stColumns > div {{
            flex: 1 1 0px !important;
            min-width: 0 !important;
            max-width: 12.5% !important;
            padding: 0 2px !important;
            display: flex !important;
            align-items: stretch !important;
        }}

        /* Navigation buttons - keep original styling */
        .stColumns .stButton > button {{
            background: var(--gradient-primary) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.7rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.2px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 
                0 2px 4px rgba(139, 69, 19, 0.2),
                0 1px 2px rgba(139, 69, 19, 0.3) !important;
            position: relative !important;
            overflow: hidden !important;
            width: 100% !important;
            height: 40px !important;
            min-width: 50px !important;
            max-width: 100px !important;
            padding: 8px 4px !important;
            white-space: nowrap !important;
            text-overflow: ellipsis !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        .stColumns .stButton > button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 
                0 4px 8px rgba(139, 69, 19, 0.3),
                0 2px 4px rgba(139, 69, 19, 0.4) !important;
            background: linear-gradient(145deg, {self.config.SECONDARY_COLOR}, {self.config.ACCENT_COLOR}) !important;
        }}

        /* Search button - keep original styling */
        .stButton > button:not(.view-button-container .stButton > button):not(.stColumns .stButton > button) {{
            background: var(--gradient-primary) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 10px 16px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 
                0 3px 6px rgba(139, 69, 19, 0.2),
                0 1px 3px rgba(139, 69, 19, 0.3) !important;
        }}

        .stButton > button:not(.view-button-container .stButton > button):not(.stColumns .stButton > button):hover {{
            transform: translateY(-2px) !important;
            box-shadow: 
                0 6px 12px rgba(139, 69, 19, 0.3),
                0 3px 6px rgba(139, 69, 19, 0.4) !important;
        }}

        /* Enhanced 3D Cards */
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
            padding: 1.5rem;
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
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(248, 244, 232, 0.95));
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
            padding: 0.75rem 1rem !important;
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

        /* Footer Enhancement */
        .footer-container {{
            background: var(--glass-bg);
            border-radius: 16px;
            margin-top: 3rem;
            text-align: center;
            border: 1px solid rgba(139, 69, 19, 0.1);
            backdrop-filter: blur(10px);
            padding: 2rem;
        }}

        /* Loading States */
        .stSpinner > div {{
            border-color: var(--primary) transparent var(--primary) transparent !important;
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .search-result-card {{
                margin: 0.5rem 0;
                padding: 1rem;
            }}
            
            h1 {{ 
                font-size: 2.2rem; 
            }}
            
            .card-3d {{
                margin: 10px 0;
                padding: 1rem;
            }}
            
            .view-button-container .stButton > button {{
                font-size: 0.8rem !important;
                padding: 6px 12px !important;
                min-width: 100px !important;
            }}

            .stColumns .stButton > button {{
                font-size: 0.65rem !important;
                padding: 6px 3px !important;
                height: 36px !important;
            }}
        }}

        @media (max-width: 480px) {{
            h1 {{ 
                font-size: 1.8rem; 
            }}
            
            .subtitle {{
                font-size: 1.1rem;
            }}
            
            .view-button-container .stButton > button {{
                font-size: 0.75rem !important;
                padding: 5px 10px !important;
                min-width: 90px !important;
            }}

            .stColumns .stButton > button {{
                font-size: 0.6rem !important;
                padding: 5px 2px !important;
                height: 32px !important;
            }}
        }}
        </style>
        """


# Navigation Component
class NavigationComponent(BaseUIComponent):
    """Navigation bar component with single-line layout"""
    
    def __init__(self, navigation_items: List[NavigationItem]):
        self.navigation_items = navigation_items
    
    def render(self) -> None:
        """Render navigation bar with single-line layout"""
        # Create exactly 8 columns for 8 buttons
        nav_cols = st.columns(8)
        
        # Short button labels
        ultra_short_labels = {
            "Artwork": "Art",
            "Blog": "Blog", 
            "Material": "Materials",
            "Tutorial": "Learn",
            "Portfolio": "Portfolio",
            "Order": "Cart",
            "Register": "Register",
            "Login": "Login"
        }
        
        for i, (col, nav_item) in enumerate(zip(nav_cols, self.navigation_items)):
            with col:
                button_key = f"nav_{nav_item.label}_{i}"
                button_text = ultra_short_labels.get(nav_item.label, nav_item.label[:4])
                
                if st.button(button_text, key=button_key, use_container_width=True):
                    st.switch_page(nav_item.page_path)


class ArtworkGalleryComponent(BaseUIComponent):
    """Artwork gallery component"""
    
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
            try:
                st.image(artwork.img_path, use_container_width=True)
            except:
                st.write("🖼️ Image not found")
            
            if st.button("View Details", key=f"view_{artwork.key}"):
                self._toggle_artwork_detail(artwork.key)
            
            if st.session_state['show_artwork_detail'][artwork.key]:
                self._render_artwork_details(artwork)
    
    def _render_artwork_details(self, artwork: Artwork) -> None:
        """Render artwork details"""
        details = artwork.to_display_dict()
        detail_text = "  \n".join([f"**{key}:** {value}" for key, value in details.items()])
        st.markdown(detail_text, unsafe_allow_html=False)
    
    def render(self) -> None:
        """Render artwork gallery"""
        if self.artworks:
            cols = st.columns(min(len(self.artworks), 3))
            for i, artwork in enumerate(self.artworks):
                col_index = i % len(cols)
                self._render_artwork_card(artwork, cols[col_index])


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
                "price": "₹3,000",
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
        """Create main navigation items"""
        nav_data = [
            ("Artwork", "pages/05_Artworks.py"),
            ("Blog", "pages/06_Blogs.py"),
            ("Material", "pages/07_Materials.py"),
            ("Tutorial", "pages/08_Tutorials.py"),
            ("Portfolio", "pages/09_Portfolio.py"),
            ("Order", "pages/10_Cart.py"),
            ("Register", "pages/Register.py"),
            ("Login", "pages/Login.py")
        ]
        
        return [NavigationItem(label, page) for label, page in nav_data]


# Main Application Class
class BrushAndSoulApp:
    """Enhanced main application with corrected view button UI"""
    
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
        
        # Search component with corrected view buttons
        self.search_component = UniversalSearchComponent(
            self.artwork_factory.create_featured_artworks()
        )
        
        # Feature sections
        self.feature_sections = [
            FeatureSection(
                "For Art Lovers",
                [
                    "Search by artist name for complete portfolios",
                    "Discover authentic folk art with complete provenance",
                    "Secure purchasing with multiple payment options",
                    "Artist profiles and detailed portfolios",
                    "Educational resources and step-by-step tutorials"
                ]
            ),
            FeatureSection(
                "For Artists",
                [
                    "Showcase your complete portfolio to global audience",
                    "Direct connection with art collectors worldwide",
                    "Fair compensation and transparent pricing",
                    "Artist community support and networking",
                    "Professional tools for portfolio management"
                ]
            )
        ]
        
        self.features_component = FeatureSectionComponent(self.feature_sections)
    
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
        
        self.features_component.render()
        
        st.subheader("Platform Features:")
        st.write("""
        - **Artist Name Search**: Find complete portfolios by searching artist names
        - **Comprehensive Results**: Search across artworks, materials, blogs, tutorials, and portfolios
        - **Curated Collections**: Authentic traditional artworks from verified artists
        - **Interactive Learning**: Comprehensive tutorials and educational resources
        - **Cultural Preservation**: Digital archiving of traditional art forms
        - **Community Building**: Connect with fellow art enthusiasts and professionals
        """)
    
    def _render_footer(self) -> None:
        """Render footer section"""
        st.divider()
        st.markdown(
            """
            <div class="footer-container">
                <p><strong>Brush and Soul</strong> - Bridging Traditional Indian Art with Contemporary Audiences</p>
                <p style="font-size: 0.9rem; color: var(--dark);">
                    Enhanced artist search • Cultural preservation • Artist empowerment
                </p>
                <p style="font-size: 0.8rem; color: var(--secondary);">
                    🔍 Search Artists • 🎨 Discover Art • 🛒 Purchase • 📚 Learn • 🤝 Connect
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    def run(self) -> None:
        """Main application entry point with corrected view button UI"""
        # Setup
        self._setup_page_config()
        self._apply_theme()
        
        # Check if there are active search results
        has_search_results = (
            hasattr(st.session_state, 'search_results') and 
            st.session_state.search_results and
            hasattr(st.session_state, 'last_search_query') and
            st.session_state.last_search_query
        )
        
        # Only render navigation when there are NO search results
        if not has_search_results:
            self.navigation.render()
        
        # Always render search component with corrected view buttons
        self.search_component.render()
        
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
    """Application entry point with corrected view button UI"""
    app = BrushAndSoulApp()
    app.run()


if __name__ == "__main__":
    main()
