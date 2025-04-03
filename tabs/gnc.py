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
    st.title("Análisis de Despachos")
    
    try:
        # Read the consolidated CSV file from the data directory
        df = pd.read_csv('data/consolidated_data.csv')
        
        # Filter for GNC products
        df = df[df['Producto'] == 'GNC']
        
        # Create Fecha column from Año, Mes, Día
        df['Fecha'] = pd.to_datetime({
            'year': df['Año'].astype(int),
            'month': df['Mes'].astype(int),
            'day': df['Día'].astype(int)
        })
        
        # Add Hora column (default to 00:00 since we don't have time data)
        df['Hora'] = '00:00'
        
        # Set specific column order
        columns_order = ['Fecha', 'Hora', 'Sucursal', 'Pico', 'Volumen', 'Importe', 'PPU']
        df = df[columns_order]
        
        # Add filters
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range filter
            min_date = df['Fecha'].min().date()
            max_date = df['Fecha'].max().date()
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
                default=None,  # No default selection
                placeholder="Seleccionar picos..."
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        if date_range and len(date_range) == 2:
            try:
                # Convert date_range to datetime.date objects if they aren't already
                start_date = date_range[0]
                end_date = date_range[1]
                
                # Apply date filter only if the selected range is different from the full range
                if start_date > filtered_df['Fecha'].min().date() or end_date < filtered_df['Fecha'].max().date():
                    mask = (filtered_df['Fecha'].dt.date >= start_date) & (filtered_df['Fecha'].dt.date <= end_date)
                    filtered_df = filtered_df[mask]
            except Exception as e:
                st.error(f"Error al aplicar filtro de fecha: {str(e)}")
            
        if pico_selected:  # Only apply filter if picos are selected
            filtered_df = filtered_df[filtered_df['Pico'].isin(pico_selected)]

        # Display data section inside an expander
        with st.expander("📊 Datos de Despachos", expanded=True):
            # Create a copy of the DataFrame for display
            display_df = filtered_df.copy()
            
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
            st.write(f"Cantidad de registros: {len(filtered_df)}")
            
            # Add pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                page_size = st.selectbox(
                    "Registros por página",
                    options=[10, 25, 50, 100],
                    index=1,  # Default to 25
                    key="page_size_gnc"  # Add unique key
                )
            
            # Calculate pagination
            total_pages = (len(display_df) + page_size - 1) // page_size
            current_page = st.session_state.get('current_page_gnc', 1)
            
            with col2:
                st.write(f"Página {current_page} de {total_pages}")
            
            with col3:
                col3_1, col3_2 = st.columns(2)
                with col3_1:
                    if current_page > 1:
                        if st.button("← Anterior", key="prev_gnc"):
                            st.session_state.current_page_gnc = current_page - 1
                with col3_2:
                    if current_page < total_pages:
                        if st.button("Siguiente →", key="next_gnc"):
                            st.session_state.current_page_gnc = current_page + 1
            
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