import streamlit as st
import pandas as pd
import os
import urllib.parse
import json
import datetime
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Catálogo & Pedidos Mayoristas", layout="wide")

CSV_FILE = "stock_gorras.csv"
PEDIDOS_FILE = "pedidos.csv"
NUMERO_WHATSAPP = "5493516629349"
MINIMO_UNIDADES = 10  # 🧢 Modificá este número si querés cambiar el mínimo de gorras requerido

def cargar_datos():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE, dtype={"ID": str})
    return pd.DataFrame(columns=["ID", "Modelo", "Categoría", "Precio Mayorista", "Stock", "Ruta Foto"])

# Inicializar estado para controlar si el pedido actual ya fue reservado en esta sesión
if 'pedido_procesado' not in st.session_state:
    st.session_state['pedido_procesado'] = False
if 'id_pedido_actual' not in st.session_state:
    st.session_state['id_pedido_actual'] = ""

st.title("🧢 Distribuidora - Pedidos Mayoristas")
st.write("Armá tu carrito. Al confirmar, tus gorras quedarán reservadas temporalmente hasta validar el pago.")
st.write("---")

df = cargar_datos()
df_disponible = df[df['Stock'] > 0].copy()

if df_disponible.empty:
    st.info("👋 Sin stock disponible momentáneamente.")
else:
    col_busq, col_cat = st.columns([2, 1])
    with col_busq:
        busqueda = st.text_input("🔍 Buscar gorra:", "")
    with col_cat:
        categorias = ["Todas"] + list(df_disponible['Categoría'].unique())
        cat_seleccionada = st.selectbox("Tipo:", categorias)
    
    if busqueda:
        df_disponible = df_disponible[df_disponible['Modelo'].str.contains(busqueda, case=False) | df_disponible['ID'].str.contains(busqueda, case=False)]
    if cat_seleccionada != "Todas":
        df_disponible = df_disponible[df_disponible['Categoría'] == cat_seleccionada]

    # GRILLA DE PRODUCTOS
    pedido_cliente = {}
    cols_por_fila = 4
    filas = [df_disponible[i:i + cols_por_fila] for i in range(0, df_disponible.shape[0], cols_por_fila)]
    
    for fila in filas:
        cols = st.columns(cols_por_fila)
        for idx, (index, row) in enumerate(fila.iterrows()):
            with cols[idx]:
                if pd.notna(row['Ruta Foto']) and os.path.exists(row['Ruta Foto']):
                    st.image(Image.open(row['Ruta Foto']), use_container_width=True)
                else:
                    st.warning("Foto 📸")
                
                st.markdown(f"### {row['Modelo']}")
                st.markdown(f"**Código:** `{row['ID']}` | **Precio:** ${row['Precio Mayorista']:,}")
                st.markdown(f"**Disponibles:** {row['Stock']} u.")
                
                # Deshabilitar inputs si ya procesó el pedido
                cant = st.number_input(
                    f"Cantidad:", min_value=0, max_value=int(row['Stock']), step=1, 
                    key=f"prod_{row['ID']}", 
                    disabled=st.session_state['pedido_procesado']
                )
                
                if cant > 0:
                    pedido_cliente[row['ID']] = {
                        "Modelo": row['Modelo'], "Precio": row['Precio Mayorista'],
                        "Cantidad": cant, "Subtotal": row['Precio Mayorista'] * cant
                    }
                st.write("---")

    # PANEL LATERAL (CARRITO)
    st.sidebar.title("🛒 Tu Pedido")
    
    if not pedido_cliente:
        st.sidebar.info("Carrito vacío.")
        st.session_state['pedido_procesado'] = False
    else:
        total_pedido = 0
        total_items = 0
        for id_prod, info in pedido_cliente.items():
            st.sidebar.write(f"**{info['Modelo']}** (x{info['Cantidad']}) - ${info['Subtotal']:,}")
            total_pedido += info['Subtotal']
            total_items += info['Cantidad']
            
        st.sidebar.markdown(f"### **Total Unidades:** {total_items}")
        st.sidebar.markdown(f"## **Total:** ${total_pedido:,}")
        st.sidebar.write("---")
        
        # --- VALIDACIÓN DE CANTIDAD MÍNIMA ---
        if total_items < MINIMO_UNIDADES:
            faltante = MINIMO_UNIDADES - total_items
            st.sidebar.warning(
                f"⚠️ **Monto Mínimo No Alcanzado**\n\n"
                f"El pedido mínimo para compras mayoristas es de **{MINIMO_UNIDADES} unidades**.\n\n"
                f"Te faltan **{faltante}** gorras en el carrito para poder finalizar tu pedido."
            )
        else:
            # Si supera el mínimo de 10 unidades, se desbloquea el formulario de contacto
            nombre_cliente = st.sidebar.text_input("Tu Nombre:", disabled=st.session_state['pedido_procesado']).strip()
            localidad_cliente = st.sidebar.text_input("Ciudad / Provincia:", disabled=st.session_state['pedido_procesado']).strip()
            
            if nombre_cliente and localidad_cliente:
                
                # PASO 1: RESERVAR EN EL SISTEMA
                if not st.session_state['pedido_procesado']:
                    if st.sidebar.button("🔒 1. Reservar y Procesar Pedido", use_container_width=True):
                        
                        # Cargar stock actual para restar
                        df_stock_actual = pd.read_csv(CSV_FILE, dtype={"ID": str})
                        
                        # Restar stock
                        for p_id, info in pedido_cliente.items():
                            df_stock_actual.loc[df_stock_actual['ID'] == p_id, 'Stock'] -= info['Cantidad']
                        
                        # Guardar pedido en pedidos.csv
                        df_pedidos_actual = pd.read_csv(PEDIDOS_FILE, dtype={"ID_Pedido": str})
                        nuevo_id = f"P{len(df_pedidos_actual) + 1:04d}"
                        
                        dict_simplificado = {k: v['Cantidad'] for k, v in pedido_cliente.items()}
                        json_productos = json.dumps(dict_simplificado)
                        
                        nueva_fila_ped = {
                            "ID_Pedido": nuevo_id,
                            "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Cliente": nombre_cliente,
                            "Localidad": localidad_cliente,
                            "Productos_JSON": json_productos,
                            "Total_Unidades": total_items,
                            "Total_Pesos": total_pedido,
                            "Estado": "Pendiente"
                        }
                        
                        df_pedidos_actual = pd.concat([df_pedidos_actual, pd.DataFrame([nueva_fila_ped])], ignore_index=True)
                        
                        # Guardar ambos archivos
                        df_stock_actual.to_csv(CSV_FILE, index=False)
                        df_pedidos_actual.to_csv(PEDIDOS_FILE, index=False)
                        
                        # Cambiar estados de sesión
                        st.session_state['pedido_procesado'] = True
                        st.session_state['id_pedido_actual'] = nuevo_id
                        st.sidebar.success(f"¡Reserva completada! Código: {nuevo_id}")
                        st.rerun()
                
                # PASO 2: DESCARGAR E IR A WHATSAPP
                else:
                    st.sidebar.info(f"Pedido Guardado (N° {st.session_state['id_pedido_actual']})")
                    
                    # Crear PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("helvetica", "B", 16)
                    pdf.cell(0, 10, f"PEDIDO MAYORISTA Nro: {st.session_state['id_pedido_actual']}", ln=True, align="C")
                    pdf.ln(5)
                    pdf.set_font("helvetica", "", 12)
                    pdf.cell(0, 8, f"Cliente: {nombre_cliente} | Ubicación: {localidad_cliente}", ln=True)
                    pdf.cell(0, 5, "--------------------------------------------------------------------------------------", ln=True)
                    
                    pdf.set_font("helvetica", "B", 11)
                    pdf.cell(30, 8, "Código", border=1)
                    pdf.cell(90, 8, "Modelo", border=1)
                    pdf.cell(20, 8, "Cant", border=1, align="C")
                    pdf.cell(40, 8, "Subtotal", border=1, align="R")
                    pdf.ln()
                    
                    pdf.set_font("helvetica", "", 11)
                    for id_p, inf in pedido_cliente.items():
                        pdf.cell(30, 8, id_p, border=1)
                        pdf.cell(90, 8, inf['Modelo'], border=1)
                        pdf.cell(20, 8, str(inf['Cantidad']), border=1, align="C")
                        pdf.cell(40, 8, f"${inf['Subtotal']:,}", border=1, align="R")
                        pdf.ln()
                    
                    pdf.ln(5)
                    pdf.set_font("helvetica", "B", 12)
                    pdf.cell(0, 8, f"Monto Total: ${total_pedido:,}", ln=True, align="R")
                    
                    pdf_bytes = pdf.output()
                    
                    st.sidebar.download_button(
                        label="📥 2. Descargar Remito PDF",
                        data=bytes(pdf_bytes),
                        file_name=f"Pedido_{st.session_state['id_pedido_actual']}_{nombre_cliente}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    # Link WhatsApp
                    msg = f"¡Hola! Registré mi pedido Nro {st.session_state['id_pedido_actual']} en la app a nombre de {nombre_cliente}. Ahí te adjunto el PDF con el detalle."
                    url_wa = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}"
                    
                    st.sidebar.markdown(
                        f'<a href="{url_wa}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;">📲 3. Enviar por WhatsApp</button></a>',
                        unsafe_allow_html=True
                    )
                    
                    if st.sidebar.button("🔄 Armar Nuevo Pedido"):
                        st.session_state['pedido_procesado'] = False
                        st.session_state['id_pedido_actual'] = ""
                        st.rerun()
            else:
                st.sidebar.warning("Completá Nombre y Localidad para avanzar.")