import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
import traceback

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

def clean_product_name(x):
    """Clean product names by removing nan and standardizing format"""
    if pd.isna(x) or str(x).lower() == 'nan':
        return 'Sin Producto'
    return str(x).strip()

def clean_pico_id(x):
    """Clean pico IDs by removing nan and standardizing format"""
    if pd.isna(x) or str(x).lower() in ['nan', 'none', 'nonenone']:
        return 'Sin Pico'
    return str(x).strip()

def render():
    st.title("Análisis de Despachos")
    
    try:
        # Read the consolidated CSV file from the data directory
        df = pd.read_csv('data/consolidated_data.csv')
        
        # Clean Producto and Pico columns
        df['Producto'] = df['Producto'].apply(clean_product_name)
        df['Pico'] = df['Pico'].apply(clean_pico_id)
        
        # Filter for non-GNC products
        df = df[df['Producto'] != 'GNC']
        
        # Create Fecha column from Año, Mes, Día
        df['Fecha'] = pd.to_datetime({
            'year': df['Año'].astype(int),
            'month': df['Mes'].astype(int),
            'day': df['Día'].astype(int)
        })
        
        # Add Hora column (default to 00:00 since we don't have time data)
        df['Hora'] = '00:00'
        
        # Set specific column order
        columns_order = ['Fecha', 'Hora', 'Sucursal', 'Pico', 'Producto', 'Volumen', 'Importe', 'PPU']
        df = df[columns_order]
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            try:
                min_date = df['Fecha'].min().date()
                max_date = df['Fecha'].max().date()
                date_range = st.date_input(
                    "Período",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
            except Exception as e:
                st.error(f"Error en filtro de fecha: {str(e)}")
                # Fallback to default date range
                date_range = None
        
        with col2:
            # Product filter - exclude 'Sin Producto' from default selection
            productos = sorted([p for p in df['Producto'].unique() if p != 'Sin Producto'])
            producto_selected = st.multiselect(
                "Producto",
                options=productos,
                default=None,  # No default selection
                placeholder="Seleccionar productos..."
            )
            
        with col3:
            # Pico filter - exclude 'Sin Pico' from default selection
            picos = sorted([p for p in df['Pico'].unique() if p != 'Sin Pico'])
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
        
        if producto_selected:  # Only apply filter if products are selected
            filtered_df = filtered_df[filtered_df['Producto'].isin(producto_selected)]
            
        if pico_selected:  # Only apply filter if picos are selected
            filtered_df = filtered_df[filtered_df['Pico'].isin(pico_selected)]

        # Display summary statistics
        with st.expander("📈 Resumen", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_importe = filtered_df['Importe'].sum()
                st.metric("Importe Total", format_argentine_currency(total_importe))
                
            with col2:
                total_volumen = filtered_df['Volumen'].sum()
                st.metric("Volumen Total", format_argentine_number(total_volumen))
                
            with col3:
                total_despachos = len(filtered_df)
                st.metric("Total Despachos", format_argentine_number(total_despachos))
            
            # Summary by product
            st.subheader("Resumen por Producto")
            summary = filtered_df.groupby('Producto').agg({
                'Importe': ['count', 'sum'],
                'Volumen': 'sum'
            }).round(2)
            
            # Format the summary
            summary.columns = ['Cantidad', 'Importe Total', 'Volumen Total']
            summary['Importe Total'] = summary['Importe Total'].apply(format_argentine_currency)
            summary['Volumen Total'] = summary['Volumen Total'].apply(format_argentine_number)
            summary['Cantidad'] = summary['Cantidad'].apply(format_argentine_number)
            
            st.dataframe(summary, use_container_width=True)

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
                    key="page_size_liquidos"  # Add unique key
                )
            
            # Calculate pagination
            total_pages = (len(display_df) + page_size - 1) // page_size
            current_page = st.session_state.get('current_page_liquidos', 1)
            
            with col2:
                st.write(f"Página {current_page} de {total_pages}")
            
            with col3:
                col3_1, col3_2 = st.columns(2)
                with col3_1:
                    if current_page > 1:
                        if st.button("← Anterior", key="prev_liquidos"):
                            st.session_state.current_page_liquidos = current_page - 1
                with col3_2:
                    if current_page < total_pages:
                        if st.button("Siguiente →", key="next_liquidos"):
                            st.session_state.current_page_liquidos = current_page + 1
            
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
        st.error(f"Detalles del error: {traceback.format_exc()}") 