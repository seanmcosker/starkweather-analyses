import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Set page config
st.set_page_config(page_title="Starkweather Tracker", layout="wide")

# Initialize data storage
DATA_FILE = "starkweather_data.json"

def load_data():
    """Load beer data from JSON file."""
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"beers": [], "available_beers": []}

def save_data(data):
    """Save beer data to JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_beer(beer_name, date=None):
    """Add a beer to the tracking data."""
    data = load_data()
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    data["beers"].append({
        "name": beer_name,
        "date": date,
        "timestamp": datetime.now().isoformat()
    })
    save_data(data)

def fetch_starkweather_beers(url):
    """Fetch beer names from Starkweather website."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find beer names - look for common patterns
        beers = []
        
        # Look for beer names in common containers
        for item in soup.find_all(['h3', 'h4', 'div', 'p']):
            text = item.get_text(strip=True)
            # Filter out empty and very short strings
            if text and len(text) > 3 and len(text) < 100:
                # Check if it looks like a beer name (contains common beer keywords or reasonable length)
                if any(keyword in text.lower() for keyword in ['ipa', 'stout', 'lager', 'pale', 'ale', 'pilsner', 'sour', 'porter', 'wheat', 'cider']) or (5 < len(text) < 60):
                    beers.append(text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_beers = []
        for beer in beers:
            if beer not in seen:
                seen.add(beer)
                unique_beers.append(beer)
        
        return unique_beers[:20]  # Return top 20 results
    
    except Exception as e:
        st.error(f"Error fetching beers: {str(e)}")
        return []

def update_available_beers(new_beers):
    """Update available beers list (cumulative - doesn't remove old ones)."""
    data = load_data()
    current_beers = set(data.get("available_beers", []))
    
    # Add new beers
    for beer in new_beers:
        current_beers.add(beer)
    
    data["available_beers"] = sorted(list(current_beers))
    save_data(data)
    return len(data["available_beers"])

# Title and description
st.title("🍺 Starkweather Brewery Tracker")
st.markdown("Track your beers from Starkweather Brewery")

# Load current data
data = load_data()
beers = data.get("beers", [])
available_beers = data.get("available_beers", [])

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Add Beer", "Refresh Menu", "Upload Receipt"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Summary Statistics")
    
    # Calculate stats from available beers
    if available_beers:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Beers Tracked", len(beers))
        
        with col2:
            st.metric("Available Beers", len(available_beers))
        
        with col3:
            if beers:
                df = pd.DataFrame(beers)
                most_recent = pd.to_datetime(df['date']).max().strftime("%Y-%m-%d")
                st.metric("Most Recent", most_recent)
            else:
                st.metric("Most Recent", "—")
        
        with col4:
            if available_beers:
                st.metric("Tracked Types", len(set([b['name'] for b in beers])))
        
        # Beer breakdown with all available beers
        st.subheader("Beer Inventory")
        
        # Create a dataframe with all available beers and their counts
        beer_counts = {}
        for beer in available_beers:
            beer_counts[beer] = 0
        
        # Add counts from tracked beers
        if beers:
            df_tracked = pd.DataFrame(beers)
            for beer_name in df_tracked['name'].unique():
                count = len(df_tracked[df_tracked['name'] == beer_name])
                if beer_name in beer_counts:
                    beer_counts[beer_name] = count
                else:
                    beer_counts[beer_name] = count  # Include tracked beers not in menu
        
        # Convert to dataframe
        beer_df = pd.DataFrame(list(beer_counts.items()), columns=['Beer Name', 'Count'])
        beer_df = beer_df.sort_values('Count', ascending=False)
        
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            st.bar_chart(beer_df.set_index('Beer Name'))
        
        with col_table:
            st.dataframe(beer_df, hide_index=True, use_container_width=True)
        
        # Timeline
        if beers:
            st.subheader("Recent Activity")
            df = pd.DataFrame(beers)
            df['date'] = pd.to_datetime(df['date'])
            df_recent = df.sort_values('date', ascending=False).head(10)
            st.dataframe(df_recent[['date', 'name']], hide_index=True, use_container_width=True)
    
    else:
        st.info("No available beers yet. Click 'Refresh Menu' to load beers from Starkweather!")

# --- TAB 2: ADD BEER ---
with tab2:
    st.header("Add a Beer")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if available_beers:
            beer_name = st.selectbox("Select Beer", available_beers, key="beer_select")
        else:
            beer_name = st.text_input("Beer Name (no menu loaded yet)", placeholder="e.g., Hazy IPA")
    
    with col2:
        beer_date = st.date_input("Date", datetime.now())
    
    if st.button("Add Beer", use_container_width=True):
        if beer_name:
            add_beer(beer_name, beer_date.strftime("%Y-%m-%d"))
            st.success(f"✅ Added {beer_name}!")
            st.rerun()
        else:
            st.error("Please select or enter a beer name")

# --- TAB 3: REFRESH MENU ---
with tab3:
    st.header("Refresh Beer Menu")
    st.markdown("Load the current beer menu from Starkweather Brewing")
    
    url_input = st.text_input(
        "Menu URL",
        value="https://starkweatherbrewing.com/beer",
        placeholder="https://starkweatherbrewing.com/beer"
    )
    
    if st.button("Fetch Beers", use_container_width=True):
        with st.spinner("Fetching menu..."):
            fetched_beers = fetch_starkweather_beers(url_input)
            
            if fetched_beers:
                total_beers = update_available_beers(fetched_beers)
                st.success(f"✅ Found {len(fetched_beers)} beers! Total available beers: {total_beers}")
                
                with st.expander("View fetched beers"):
                    st.write(fetched_beers)
                
                st.rerun()
            else:
                st.warning("Could not find beers at that URL. The website structure may have changed.")
    
    st.divider()
    st.subheader("Current Menu")
    if available_beers:
        st.write(f"**{len(available_beers)} beers available**")
        cols = st.columns(3)
        for idx, beer in enumerate(sorted(available_beers)):
            with cols[idx % 3]:
                st.write(f"• {beer}")
    else:
        st.info("No beers loaded yet. Click 'Fetch Beers' above to get started.")

# --- TAB 4: UPLOAD RECEIPT ---
with tab4:
    st.header("Upload Receipt")
    st.info("📋 Receipt upload feature coming soon! This will allow you to automatically extract beer information from receipt images.")
    
    uploaded_file = st.file_uploader("Upload receipt image", type=['jpg', 'jpeg', 'png', 'pdf'])
    
    if uploaded_file:
        st.write("File received:", uploaded_file.name)
        st.warning("Receipt parsing is not yet implemented. You can manually add beers in the 'Add Beer' tab for now.")

