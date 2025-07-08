import streamlit as st
import requests
import time
import math
import pandas as pd
from typing import Tuple, Optional, List, Dict
import io

# Page configuration
st.set_page_config(
    page_title="Address Distance Calculator",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        color: #e0e0e0;
        font-size: 1.1rem;
        margin: 0;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #667eea;
    }
    
    .input-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    
    .results-section {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .stSelectbox > div > div {
        border-radius: 10px;
    }
    
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    
    .stTextArea > div > div > textarea {
        border-radius: 10px;
    }
    
    .success-badge {
        background: #d4edda;
        color: #155724;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .error-badge {
        background: #f8d7da;
        color: #721c24;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

class AddressDistanceCalculator:
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.routing_url = "https://router.project-osrm.org/route/v1/driving"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'StreamlitDistanceCalculator/1.0'
        })
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode an address using OpenStreetMap Nominatim API"""
        try:
            params = {
                'format': 'json',
                'q': address,
                'limit': 1,
                'addressdetails': 1
            }
            
            response = self.session.get(self.nominatim_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                return float(data[0]['lat']), float(data[0]['lon'])
            return None
            
        except Exception as e:
            return None
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate straight-line distance using Haversine formula"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c  # Earth's radius in km
    
    def get_routing_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
        """Get actual driving distance using OSRM routing"""
        try:
            url = f"{self.routing_url}/{lon1},{lat1};{lon2},{lat2}"
            params = {
                'overview': 'false',
                'geometries': 'geojson'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 'Ok' and data.get('routes'):
                distance_m = data['routes'][0]['distance']
                return distance_m / 1000  # Convert to km
            return None
            
        except Exception:
            return None
    
    def calculate_distances(self, fixed_address: str, destination_addresses: List[str], distance_type: str) -> List[Dict]:
        """Calculate distances from fixed address to destinations"""
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        # Geocode fixed address
        status_placeholder.info(f"🔍 Finding location for: {fixed_address}")
        fixed_coords = self.geocode_address(fixed_address)
        
        if not fixed_coords:
            st.error(f"❌ Could not find location for fixed address: {fixed_address}")
            return []
        
        st.success(f"✅ Fixed address located: {fixed_coords[0]:.6f}, {fixed_coords[1]:.6f}")
        
        results = []
        total_addresses = len(destination_addresses)
        
        for i, dest_address in enumerate(destination_addresses):
            # Update progress
            progress = (i + 1) / total_addresses
            progress_bar.progress(progress)
            status_placeholder.info(f"🔍 Processing {i+1}/{total_addresses}: {dest_address}")
            
            # Add delay to respect API rate limits
            if i > 0:
                time.sleep(1)
            
            # Geocode destination
            dest_coords = self.geocode_address(dest_address)
            
            if not dest_coords:
                results.append({
                    'Address': dest_address,
                    'Distance (km)': None,
                    'Distance Type': distance_type,
                    'Status': 'Address not found',
                    'Latitude': None,
                    'Longitude': None
                })
                continue
            
            # Calculate distance based on type
            if distance_type == "Straight Line (Haversine)":
                distance = self.haversine_distance(
                    fixed_coords[0], fixed_coords[1],
                    dest_coords[0], dest_coords[1]
                )
                status = 'Success'
            else:  # Actual Route Distance
                distance = self.get_routing_distance(
                    fixed_coords[0], fixed_coords[1],
                    dest_coords[0], dest_coords[1]
                )
                status = 'Success' if distance else 'Route not found'
            
            results.append({
                'Address': dest_address,
                'Distance (km)': round(distance, 2) if distance else None,
                'Distance Type': distance_type,
                'Status': status,
                'Latitude': dest_coords[0],
                'Longitude': dest_coords[1]
            })
        
        status_placeholder.success(f"✅ Completed processing {total_addresses} addresses!")
        progress_bar.empty()
        
        return results

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📍 Address Distance Calculator</h1>
        <p>Calculate distances between addresses using OpenStreetMap - Choose between straight-line or actual route distances</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize calculator
    if 'calculator' not in st.session_state:
        st.session_state.calculator = AddressDistanceCalculator()
    
    # Input section
    st.markdown('<div class="input-section">', unsafe_allow_html=True)
    
    # Configuration row
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎯 Configuration")
        fixed_address = st.text_input(
            "Fixed Address (Origin Point)",
            placeholder="e.g., Mumbai Central Station, Mumbai, India",
            help="This address will be used as the starting point for all distance calculations"
        )
    
    with col2:
        st.subheader("📏 Distance Type")
        distance_type = st.selectbox(
            "Choose calculation method:",
            ["Straight Line (Haversine)", "Actual Route Distance"],
            help="Straight Line: Direct distance 'as the crow flies'\nActual Route: Real driving/routing distance"
        )
    
    st.markdown("---")
    
    # Input method selection
    st.subheader("📝 Destination Addresses")
    
    # Tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["✏️ Manual Entry", "📄 Upload Excel", "📋 Paste Text"])
    
    destination_addresses = []
    
    with tab1:
        st.markdown("**Add destination addresses one by one:**")
        
        # Initialize session state
        if 'addresses' not in st.session_state:
            st.session_state.addresses = [""]
        
        # Address management buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("➕ Add Address", use_container_width=True):
                st.session_state.addresses.append("")
        with col2:
            if st.button("➖ Remove Last", use_container_width=True) and len(st.session_state.addresses) > 1:
                st.session_state.addresses.pop()
        with col3:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.addresses = [""]
        
        # Address inputs
        for i in range(len(st.session_state.addresses)):
            st.session_state.addresses[i] = st.text_input(
                f"Destination {i+1}",
                value=st.session_state.addresses[i],
                placeholder=f"Enter destination address {i+1}",
                key=f"manual_addr_{i}"
            )
        
        destination_addresses = [addr.strip() for addr in st.session_state.addresses if addr.strip()]
    
    with tab2:
        st.markdown("**Upload an Excel file with addresses:**")
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="First column should contain addresses"
        )
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                if not df.empty:
                    addresses_column = df.iloc[:, 0].dropna().astype(str).tolist()
                    destination_addresses = [addr.strip() for addr in addresses_column if addr.strip()]
                    
                    st.success(f"✅ Loaded {len(destination_addresses)} addresses")
                    
                    # Preview
                    if destination_addresses:
                        with st.expander("🔍 Preview addresses"):
                            for i, addr in enumerate(destination_addresses[:10]):
                                st.write(f"{i+1}. {addr}")
                            if len(destination_addresses) > 10:
                                st.info(f"... and {len(destination_addresses) - 10} more addresses")
                                
            except Exception as e:
                st.error(f"❌ Error reading Excel file: {str(e)}")
    
    with tab3:
        st.markdown("**Paste multiple addresses (one per line):**")
        text_input = st.text_area(
            "Paste addresses here",
            height=150,
            placeholder="Address 1\nAddress 2\nAddress 3\n...",
            help="Enter one address per line"
        )
        
        if text_input:
            destination_addresses = [addr.strip() for addr in text_input.split('\n') if addr.strip()]
            st.success(f"✅ Parsed {len(destination_addresses)} addresses")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Status and calculation section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏠 Fixed Address</h3>
            <p>{'✅ Set' if fixed_address else '❌ Not Set'}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎯 Destinations</h3>
            <p>{len(destination_addresses)} addresses</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📏 Method</h3>
            <p>{distance_type}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate button
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        calculate_button = st.button(
            "🚀 Calculate Distances",
            use_container_width=True,
            disabled=not (fixed_address and destination_addresses),
            type="primary"
        )
    
    # Calculation and results
    if calculate_button:
        if not fixed_address:
            st.error("❌ Please enter a fixed address")
        elif not destination_addresses:
            st.error("❌ Please add at least one destination address")
        else:
            with st.spinner("Calculating distances..."):
                results = st.session_state.calculator.calculate_distances(
                    fixed_address, destination_addresses, distance_type
                )
                
                if results:
                    st.session_state.results = results
                    st.session_state.fixed_address = fixed_address
                    st.session_state.distance_type = distance_type
    
    # Display results
    if 'results' in st.session_state:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="results-section">', unsafe_allow_html=True)
        
        st.subheader("📊 Results")
        
        results_df = pd.DataFrame(st.session_state.results)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📍 Total Addresses", len(results_df))
        
        with col2:
            successful = len(results_df[results_df['Status'] == 'Success'])
            st.metric("✅ Successful", successful)
        
        with col3:
            failed = len(results_df[results_df['Status'] != 'Success'])
            st.metric("❌ Failed", failed)
        
        with col4:
            if successful > 0:
                avg_distance = results_df[results_df['Status'] == 'Success']['Distance (km)'].mean()
                st.metric("📏 Avg Distance", f"{avg_distance:.1f} km")
            else:
                st.metric("📏 Avg Distance", "N/A")
        
        # Results table
        st.markdown("### 📋 Detailed Results")
        
        # Format the dataframe for display
        display_df = results_df[['Address', 'Distance (km)', 'Status']].copy()
        
        # Color code the status
        def highlight_status(row):
            if row['Status'] == 'Success':
                return ['background-color: #d4edda'] * len(row)
            else:
                return ['background-color: #f8d7da'] * len(row)
        
        styled_df = display_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        # Download section
        st.markdown("### 💾 Download Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                results_df.to_excel(writer, sheet_name='Distance Results', index=False)
            output.seek(0)
            
            st.download_button(
                label="📥 Download Excel",
                data=output.getvalue(),
                file_name=f"distance_results_{int(time.time())}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # CSV download
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"distance_results_{int(time.time())}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
