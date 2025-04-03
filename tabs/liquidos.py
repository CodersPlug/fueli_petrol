import streamlit as st
import pandas as pd
from datetime import datetime
from auth import get_current_organization
from database import get_despachos

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
        # Get current organization
        organization = get_current_organization()
        
        # Get non-GNC data from database
        df = get_despachos(organization=organization)
        df = df[df['producto'] != 'GNC']  # Filter out GNC
        
        # Check if we have any data
        if len(df) == 0:
            st.warning(f"No se encontraron datos para la organización {organization}")
            return
        
        # Clean product and pico columns
        df['producto'] = df['producto'].apply(clean_product_name)
        df['pico'] = df['pico'].apply(clean_pico_id)
        
        # Convert fecha to datetime if it's not already
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Add filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Date range filter
            min_date = df['fecha'].min().date()
            max_date = df['fecha'].max().date()
            date_range = st.date_input(
                "Período",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="date_range_liquidos"
            )
        
        with col2:
            # Sucursal filter
            sucursales = sorted(df['sucursal'].unique())
            sucursal_selected = st.multiselect(
                "Sucursal",
                options=sucursales,
                default=None,  # No default selection
                placeholder="Seleccionar sucursales...",
                key="sucursal_multiselect_liquidos"
            )

        with col3:
            # Product filter - exclude 'Sin Producto' from default selection
            productos = sorted([p for p in df['producto'].unique() if p != 'Sin Producto'])
            producto_selected = st.multiselect(
                "Producto",
                options=productos,
                default=None,  # No default selection
                placeholder="Seleccionar productos...",
                key="producto_multiselect_liquidos"
            )
            
        with col4:
            # Pico filter - exclude 'Sin Pico' from default selection
            picos = sorted([p for p in df['pico'].unique() if p != 'Sin Pico'])
            pico_selected = st.multiselect(
                "Pico",
                options=picos,
                default=None,  # No default selection
                placeholder="Seleccionar picos...",
                key="pico_multiselect_liquidos"
            )
        
        # Apply filters
        if date_range and len(date_range) == 2:
            df = get_despachos(
                organization=organization,
                producto=producto_selected if producto_selected else None,
                start_date=date_range[0],
                end_date=date_range[1],
                pico=pico_selected if pico_selected else None
            )
            # Filter out GNC after getting data
            df = df[df['producto'] != 'GNC']
            # Apply sucursal filter after getting data (since get_despachos doesn't support it directly)
            if sucursal_selected:
                df = df[df['sucursal'].isin(sucursal_selected)]

        # Display summary statistics
        with st.expander("📈 Resumen", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_importe = df['importe'].sum()
                st.metric("Importe Total", format_argentine_currency(total_importe))
                
            with col2:
                total_volumen = df['volumen'].sum()
                st.metric("Volumen Total", format_argentine_number(total_volumen))
                
            with col3:
                total_despachos = len(df)
                st.metric("Total Despachos", format_argentine_number(total_despachos))
            
            # Summary by product
            st.subheader("Resumen por Producto")
            summary = df.groupby('producto').agg({
                'importe': ['count', 'sum'],
                'volumen': 'sum'
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
            display_df = df.copy()
            
            # Select only the columns we want to display, with sucursal as the third column
            display_columns = ['fecha', 'hora', 'sucursal', 'pico', 'producto', 'volumen', 'importe', 'ppu']
            display_df = display_df[display_columns]
            
            # Format the fecha column to show only the date
            display_df['fecha'] = display_df['fecha'].dt.strftime('%d/%m/%Y')
            
            # Format numeric columns
            display_df['volumen'] = display_df['volumen'].apply(format_argentine_number)
            display_df['importe'] = display_df['importe'].apply(format_argentine_currency)
            display_df['ppu'] = display_df['ppu'].apply(format_argentine_number)
            
            # Rename columns for display
            display_df = display_df.rename(columns={
                'fecha': 'Fecha',
                'hora': 'Hora',
                'sucursal': 'Sucursal',
                'pico': 'Pico',
                'producto': 'Producto',
                'volumen': 'Volumen',
                'importe': 'Importe',
                'ppu': 'PPU'
            })
            
            # Display total records
            st.write(f"Cantidad de registros: {len(df)}")
            
            # Add pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                page_size = st.selectbox(
                    "Registros por página",
                    options=[10, 25, 50, 100],
                    index=1,  # Default to 25
                    key="page_size_liquidos"
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
        st.error(f"Error al cargar los datos: {str(e)}") 