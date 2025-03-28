import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

def format_argentine_number(x):
    """Format number in Argentine style (comma as decimal, period as thousands)"""
    try:
        num = float(x)
        # Format with 2 decimal places and thousands separator
        return f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return x

def format_argentine_currency(x):
    """Format currency in Argentine style"""
    try:
        num = float(x)
        # Format with 2 decimal places and thousands separator
        return f"${num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return x

def render():
    st.title("Análisis de Despachos GNC")
    
    try:
        # Read the CSV file from the data directory
        df = pd.read_csv('data/gnc.csv')
        
        # Convert Fecha to datetime with dayfirst=True for DD/MM/YYYY format
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
        
        # Convert Importe to numeric, removing currency symbols and thousands separators
        df['Importe'] = pd.to_numeric(df['Importe'].str.replace('[\$,]', '', regex=True), errors='coerce')
        
        # Add Hora column from Fecha
        df['Hora'] = df['Fecha'].dt.strftime('%H:%M')
        
        # Combine Surtidor and Manguera into Pico with space
        def format_manguera(x):
            try:
                # If it's a number, convert to letter (1->a, 2->b, etc.)
                return chr(96 + int(x))
            except ValueError:
                # If it's already a letter, return as is
                return str(x).lower()
        
        df['Pico'] = df['Surtidor'].astype(str) + ' ' + df['Manguera'].astype(str).map(format_manguera)
        
        # Set specific column order
        columns_order = ['Fecha', 'Hora', 'Sucursal', 'Pico', 'Volumen', 'Importe', 'PPU']
        df = df[columns_order]
        
        # Add filters
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range filter
            min_date = df['Fecha'].min()
            max_date = df['Fecha'].max()
            date_range = st.date_input(
                "Período",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
        with col2:
            # Pico filter
            picos = sorted(df['Pico'].unique())
            pico_selected = st.multiselect(
                "Pico",
                options=picos,
                default=picos
            )
        
        # Apply filters
        if len(date_range) == 2:
            mask = (df['Fecha'].dt.date >= date_range[0]) & (df['Fecha'].dt.date <= date_range[1])
            df = df[mask]
        
        if pico_selected:
            df = df[df['Pico'].isin(pico_selected)]

        # Display data section inside an expander
        with st.expander("📊 Datos de Despachos", expanded=True):
            # Create a copy of the DataFrame for display
            display_df = df.copy()
            
            # Format the Fecha column to show only the date
            if 'Fecha' in display_df.columns:
                display_df['Fecha'] = display_df['Fecha'].dt.strftime('%d/%m/%Y')
            
            # Format numeric columns
            if 'Volumen' in display_df.columns:
                display_df['Volumen'] = display_df['Volumen'].apply(format_argentine_number)
            
            if 'Importe' in display_df.columns:
                display_df['Importe'] = display_df['Importe'].apply(format_argentine_currency)
            
            if 'PPU' in display_df.columns:
                display_df['PPU'] = display_df['PPU'].apply(format_argentine_number)
            
            # Display total records
            st.write(f"Cantidad de registros: {len(df)}")
            
            # Add pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                page_size = st.selectbox(
                    "Registros por página",
                    options=[10, 25, 50, 100],
                    index=1  # Default to 25
                )
            
            # Calculate pagination
            total_pages = (len(display_df) + page_size - 1) // page_size
            current_page = st.session_state.get('current_page', 1)
            
            with col2:
                st.write(f"Página {current_page} de {total_pages}")
            
            with col3:
                if current_page > 1:
                    if st.button("← Anterior"):
                        st.session_state.current_page = current_page - 1
                if current_page < total_pages:
                    if st.button("Siguiente →"):
                        st.session_state.current_page = current_page + 1
            
            # Slice the dataframe for the current page
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            page_df = display_df.iloc[start_idx:end_idx]
            
            # Display the paginated dataframe
            st.dataframe(
                page_df,
                use_container_width=True,
                hide_index=True
            )
        
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}") 