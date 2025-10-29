import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Shopify Product Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
    .positive {
        color: green;
        font-weight: bold;
    }
    .negative {
        color: red;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class Dashboard:
    def __init__(self):
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.SUPABASE_URL, self.SUPABASE_KEY)
        self.table_name = "inventorypacer"  # your Supabase table
    
    def get_table_data(self, date=None, limit=None):
        """
        Fetch data from Supabase table.
        - date: string in 'dd-mm-yyyy', fetches that day
        - limit: int, fetches last n records
        """
        query = self.supabase.table(self.table_name).select(
            "Date, rings, pendants, earrings, bracelets"
        )
        if date:
            query = query.filter("Date", "eq", date)
        else:
            if limit:
                query = query.order("Date", desc=True).limit(limit)
            else:
                query = query.order("Date", desc=True)
        try:
            response = query.execute()
            if response.data:
                df = pd.DataFrame(response.data)
                df.rename(columns={"Date": "date"}, inplace=True)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error fetching data: {e}")
            return pd.DataFrame()
    
    def get_latest_data(self):
        df = self.get_table_data(limit=1)
        return df
    
    def get_ratio_analysis(self, data_df):
        """Calculate current ratios vs target ratios"""
        if data_df.empty:
            return None
        
        target_ratios = {
            'rings': 40,
            'pendants': 25, 
            'earrings': 20,
            'bracelets': 15
        }
        
        analysis = []
        total_products = data_df['total_products'].iloc[0]
        
        for product_type, target_percent in target_ratios.items():
            current_count = data_df[product_type].iloc[0]
            current_percent = (current_count / total_products * 100) if total_products > 0 else 0
            target_count = (target_percent / 100) * total_products
            difference = target_count - current_count
            
            analysis.append({
                'Product Type': product_type.title(),
                'Current Count': current_count,
                'Current %': round(current_percent, 1),
                'Target %': target_percent,
                'Target Count': round(target_count, 1),
                'Difference': round(difference, 1),
                'Status': 'Above Target' if difference < 0 else 'Below Target'
            })
        
        return pd.DataFrame(analysis)

def main():
    dashboard = Dashboard()
    
    st.markdown('<h1 class="main-header">🏪 Shopify Product Dashboard</h1>', unsafe_allow_html=True)

        # Fetch the latest date data
    all_data = dashboard.get_table_data()
    if all_data.empty:
        st.warning("⚠️ No data available in Supabase database.")
        return

    # Get all available dates sorted (latest first)
    available_dates = sorted(all_data['date'].unique(), reverse=True)
    latest_date_str = available_dates[0]

    # --- Add date selector ---
    selected_date = st.selectbox(
        "📅 Select Date",
        options=available_dates,
        index=0,  # default to the latest date
        help="Select a date to view product distribution and ratio analysis."
    )

    # --- Determine which date's data to load ---
    if "selected_date" not in st.session_state:
        # On first load → show latest data
        st.session_state.selected_date = latest_date_str

    # If user changes selection, update state
    if selected_date != st.session_state.selected_date:
        st.session_state.selected_date = selected_date

    # --- Fetch data for the selected date ---
    data_df = dashboard.get_table_data(date=st.session_state.selected_date)

    if data_df.empty:
        st.error(f"❌ No data found for **{st.session_state.selected_date}**. Please choose another date.")
        return

    # --- Show date info ---
    st.info(f"Showing data for **{st.session_state.selected_date}**")
    # Convert columns to integers
    for col in ['rings', 'pendants', 'earrings', 'bracelets']:
        data_df[col] = pd.to_numeric(data_df[col], errors='coerce').fillna(0).astype(int)

    data_df['total_products'] = data_df[['rings', 'pendants', 'earrings', 'bracelets']].sum(axis=1)

    # Latest snapshot section
    st.subheader("📅 Data Snapshot")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Date", data_df['date'].iloc[0])
    with col2:
        st.metric("Total Products", data_df['total_products'].iloc[0])
    with col3:
        st.metric("Rings", data_df['rings'].iloc[0])
    with col4:
        st.metric("Pendants", data_df['pendants'].iloc[0])
    with col5:
        st.metric("Earrings", data_df['earrings'].iloc[0])
    with col6:
        st.metric("Bracelets", data_df['bracelets'].iloc[0])
    
    # Current Distribution
    st.subheader("📊 Current Product Distribution")
    col1, col2 = st.columns(2)
    product_types = ['rings', 'pendants', 'earrings', 'bracelets']
    counts = [data_df[pt].iloc[0] for pt in product_types]
    labels = [pt.title() for pt in product_types]
    
    with col1:
        fig_pie = px.pie(values=counts, names=labels, title="Product Type Distribution",
                         color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        fig_bar = px.bar(x=labels, y=counts, title="Product Counts by Type",
                         labels={'x': 'Product Type', 'y': 'Count'},
                         color=labels, color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Ratio Analysis
    st.subheader("🎯 Ratio Analysis vs Targets")
    ratio_df = dashboard.get_ratio_analysis(data_df)
    if ratio_df is not None:
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(
                ratio_df.style.format({
                    'Current %': '{:.1f}%',
                    'Target %': '{:.1f}%',
                    'Target Count': '{:.1f}',
                    'Difference': '{:+.1f}'
                }),
                use_container_width=True
            )
        with col2:
            fig_ratio = go.Figure()
            fig_ratio.add_trace(go.Bar(
                name='Current %', x=ratio_df['Product Type'], y=ratio_df['Current %'], marker_color='lightblue'
            ))
            fig_ratio.add_trace(go.Bar(
                name='Target %', x=ratio_df['Product Type'], y=ratio_df['Target %'], marker_color='orange'
            ))
            fig_ratio.update_layout(title="Current vs Target Ratios", barmode='group',
                                    xaxis_title="Product Type", yaxis_title="Percentage (%)")
            st.plotly_chart(fig_ratio, use_container_width=True)
    
    # Recommendations
    st.subheader("💡 Recommendations")
    if ratio_df is not None:
        recommendations = []
        for _, row in ratio_df.iterrows():
            if row['Difference'] > 0:
                recommendations.append(
                    f"📌 Upload **{abs(row['Difference']):.0f}** more **{row['Product Type']}** "
                    f"(currently {row['Current Count']}, target {row['Target Count']:.0f})"
                )
            elif row['Difference'] < 0:
                recommendations.append(
                    f"✅ **{row['Product Type']}** is above target by {abs(row['Difference']):.0f} units"
                )
        if recommendations:
            for rec in recommendations:
                st.write(rec)
        else:
            st.success("🎉 All product categories are meeting or exceeding their targets!")
    
    st.markdown("---")
    st.markdown(
        "**Dashboard Updates**: Automatically showing data for the most recent date available in Supabase."
    )

if __name__ == "__main__":
    main()