import streamlit as st
import pandas as pd
import os
import urllib.parse
import json
import datetime
from fpdf import FPDF
from PIL import Image

# --- ESTO TIENE QUE ESTAR ARRIBA DE TODO ---
if 'pedido_procesado' not in st.session_state:
    st.session_state['pedido_procesado'] = False

if 'id_pedido_actual' not in st.session_state:
    st.session_state['id_pedido_actual'] = ""

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Sistema Integral - Gorras Mayorista", layout="wide")

CSV_FILE = "stock_gorras.csv"
PEDIDOS_FILE = "pedidos.csv"
FOLDER_FOTOS = "fotos"
NUMERO_WHATSAPP = "5493516629349"
PASSWORD_ADMIN = "GorrasCba2026"
MINIMO_UNIDADES = 10  # Mínimo de gorras para el cliente

# Crear carpetas y archivos base si no existen
if not os.path.exists(FOLDER_FOTOS):
    os.makedirs(FOLDER_FOTOS)

if not os.path.exists(CSV_FILE):
    df_init = pd.DataFrame(columns=["ID", "Modelo", "Categoría", "Precio Mayorista", "Stock", "Ruta Foto"])
    df_init.to_csv(CSV_FILE, index=False)

if not os.path.exists(PEDIDOS_FILE):
    df_ped_init = pd.DataFrame(columns=["ID_Pedido", "Fecha", "Cliente", "Localidad", "Productos_JSON", "Total_Unidades", "Total_Pesos", "Estado"])
    df_ped_init.to_csv(PEDIDOS_FILE, index=False)

# Funciones de lectura y escritura
def cargar_datos():
    return pd.read_csv(CSV_FILE, dtype={"ID": str})

def guardar_datos(df):
    df.to_csv(CSV_FILE, index=False)

def cargar_pedidos():
    return pd.read_csv(PEDIDOS_FILE, dtype={"ID_Pedido": str})

def guardar_pedidos(df):
    df.to_csv(PEDIDOS_FILE, index=False)

# Inicializar estados de sesión para el carrito del cliente
if 'pedido_procesado' not in st.session_state:
    st.session_state['pedido_procesado'] = False
if 'id_pedido_actual' not in st.session_state:
    st.session_state['id_pedido_actual'] = ""

# --- MENÚ LATERAL DE NAVEGACIÓN ---
st.sidebar.title("Menú Principal")
CON_ACCESO = ["🛍️ Catálogo de Clientes", "📝 Gestionar Pedidos (Privado)", "🛡️ Panel de Administrador (Privado)"]
opcion = st.sidebar.radio("Ir a:", CON_ACCESO)

# ==========================================
# VISTA 1: CATÁLOGO DE CLIENTES (PÚBLICO)
# ==========================================
if opcion == "🛍️ Catálogo de Clientes":
    st.title("🧢 Distribuidora - Pedidos Mayoristas")
    st.write("Armá tu carrito. Al confirmar, tus gorras quedarán reservadas temporalmente.")
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

        # Grilla de productos
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
                    
                    cant = st.number_input(
                        f"Cantidad:", min_value=0, max_value=int(row['Stock']), step=1, 
                        key=f"prod_{row['ID']}", disabled=st.session_state['pedido_procesado']
                    )
                    
                    if cant > 0:
                        pedido_cliente[row['ID']] = {
                            "Modelo": row['Modelo'], "Precio": row['Precio Mayorista'],
                            "Cantidad": cant, "Subtotal": row['Precio Mayorista'] * cant
                        }
                    st.write("---")

        # Carrito en barra lateral
        st.sidebar.write("---")
        st.sidebar.subheader("🛒 Tu Carrito")
        
        if not pedido_cliente:
            st.sidebar.info("Carrito vacío.")
            st.session_state['pedido_procesado'] = False
        else:
            total_pedido = 0
            total_items = 0
            for id_prod, info in pedido_cliente.items():
                st.sidebar.write(f"• **{info['Modelo']}** (x{info['Cantidad']})")
                total_pedido += info['Subtotal']
                total_items += info['Cantidad']
                
            st.sidebar.markdown(f"**Total Unidades:** {total_items}")
            st.sidebar.markdown(f"### **Total: ${total_pedido:,}**")
            
            # Validación mínimo 10 prendas
            if total_items < MINIMO_UNIDADES:
                faltante = MINIMO_UNIDADES - total_items
                st.sidebar.warning(f"⚠️ **Mínimo no alcanzado:** Te faltan **{faltante}** gorras para poder pedir.")
            else:
                nombre_cliente = st.sidebar.text_input("Tu Nombre:", disabled=st.session_state['pedido_procesado']).strip()
                localidad_cliente = st.sidebar.text_input("Ciudad / Provincia:", disabled=st.session_state['pedido_procesado']).strip()
                
                if nombre_cliente and localidad_cliente:
                    if not st.session_state['pedido_procesado']:
                        if st.sidebar.button("🔒 1. Reservar Pedido", use_container_width=True):
                            df_stock_actual = cargar_datos()
                            for p_id, info in pedido_cliente.items():
                                df_stock_actual.loc[df_stock_actual['ID'] == p_id, 'Stock'] -= info['Cantidad']
                            
                            df_pedidos_actual = cargar_pedidos()
                            nuevo_id = f"P{len(df_pedidos_actual) + 1:04d}"
                            json_productos = json.dumps({k: v['Cantidad'] for k, v in pedido_cliente.items()})
                            
                            nueva_fila_ped = {
                                "ID_Pedido": nuevo_id, "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "Cliente": nombre_cliente, "Localidad": localidad_cliente, "Productos_JSON": json_productos,
                                "Total_Unidades": total_items, "Total_Pesos": total_pedido, "Estado": "Pendiente"
                            }
                            df_pedidos_actual = pd.concat([df_pedidos_actual, pd.DataFrame([nueva_fila_ped])], ignore_index=True)
                            
                            guardar_datos(df_stock_actual)
                            guardar_pedidos(df_pedidos_actual)
                            
                            st.session_state['pedido_procesado'] = True
                            st.session_state['id_pedido_actual'] = nuevo_id
                            st.sidebar.success(f"¡Reserva N° {nuevo_id} exitosa!")
                            st.rerun()
                    else:
                        st.sidebar.info(f"Pedido Guardado (N° {st.session_state['id_pedido_actual']})")
                        
                        # Generar PDF
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("helvetica", "B", 16)
                        pdf.cell(0, 10, f"PEDIDO MAYORISTA Nro: {st.session_state['id_pedido_actual']}", ln=True, align="C")
                        pdf.ln(5)
                        pdf.set_font("helvetica", "", 12)
                        pdf.cell(0, 8, f"Cliente: {nombre_cliente} | Ubicación: {localidad_cliente}", ln=True)
                        pdf.ln(5)
                        
                        for id_p, inf in pedido_cliente.items():
                            pdf.cell(0, 8, f"- {inf['Modelo']} (Cod: {id_p}) x {inf['Cantidad']} u. --- Subtotal: ${inf['Subtotal']:,}", ln=True)
                        pdf.ln(5)
                        pdf.cell(0, 8, f"Monto Total: ${total_pedido:,}", ln=True)
                        
                        pdf_bytes = pdf.output()
                        st.sidebar.download_button(label="📥 2. Descargar PDF", data=bytes(pdf_bytes), file_name=f"Pedido_{st.session_state['id_pedido_actual']}.pdf", mime="application/pdf", use_container_width=True)
                        
                        msg = f"¡Hola! Registré mi pedido Nro {st.session_state['id_pedido_actual']} por {total_items} gorras a nombre de {nombre_cliente}."
                        url_wa = f"https://wa.me/{NUMERO_WHATSAPP}?text={urllib.parse.quote(msg)}"
                        st.sidebar.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;">📲 3. Enviar WhatsApp</button></a>', unsafe_allow_html=True)
                        
                        if st.sidebar.button("🔄 Armar Nuevo Pedido"):
                            st.session_state['pedido_procesado'] = False
                            st.session_state['id_pedido_actual'] = ""
                            st.rerun()
                else:
                    st.sidebar.warning("Ingresá tu Nombre y Localidad.")

# ==========================================
# VISTA 2: GESTIONAR PEDIDOS (PRIVADO)
# ==========================================
elif opcion == "📝 Gestionar Pedidos (Privado)":
    st.title("📝 Control y Validación de Pedidos")
    password = st.text_input("Contraseña de acceso:", type="password")
    
    if password == PASSWORD_ADMIN:
        df_pedidos = cargar_pedidos()
        if df_pedidos.empty:
            st.info("No hay pedidos registrados.")
        else:
            estado_filtro = st.selectbox("Filtrar:", ["Pendientes", "Confirmados", "Cancelados"])
            trad = {"Pendientes": "Pendiente", "Confirmados": "Confirmado", "Cancelados": "Cancelado"}
            df_filtrado = df_pedidos[df_pedidos['Estado'] == trad[estado_filtro]]
            
            for idx, row in df_filtrado.iterrows():
                with st.expander(f"🛒 Pedido {row['ID_Pedido']} - {row['Cliente']}"):
                    st.write(f"**Ubicación:** {row['Localidad']} | **Total:** ${row['Total_Pesos']:,} ({row['Total_Unidades']} u.)")
                    productos_dict = json.loads(row['Productos_JSON'])
                    df_stock_ref = cargar_datos()
                    
                    for p_id, p_cant in productos_dict.items():
                        nom = df_stock_ref[df_stock_ref['ID'] == p_id]['Modelo'].values
                        st.write(f"- {nom[0] if len(nom)>0 else 'Eliminado'} x {p_cant} u.")
                    
                    if row['Estado'] == "Pendiente":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Confirmar", key=f"c_{row['ID_Pedido']}"):
                                df_pedidos.at[idx, 'Estado'] = "Confirmado"
                                guardar_pedidos(df_pedidos)
                                st.rerun()
                        with c2:
                            if st.button("❌ Cancelar (Devuelve Stock)", key=f"x_{row['ID_Pedido']}"):
                                df_stock = cargar_datos()
                                for prod_id, cant in productos_dict.items():
                                    if prod_id in df_stock['ID'].values:
                                        df_stock.loc[df_stock['ID'] == prod_id, 'Stock'] += cant
                                df_pedidos.at[idx, 'Estado'] = "Cancelado"
                                guardar_datos(df_stock)
                                guardar_pedidos(df_pedidos)
                                st.rerun()
    elif password != "":
        st.error("Clave incorrecta.")

# ==========================================
# VISTA 3: PANEL DE ADMINISTRADOR (PRIVADO)
# ==========================================
elif opcion == "🛡️ Panel de Administrador (Privado)":
    st.title("🛡️ Panel de Configuración de Productos")
    password = st.text_input("Contraseña de acceso:", type="password", key="crud_pass")
    
    if password == PASSWORD_ADMIN:
        df = cargar_datos()
        accion = st.selectbox("Acción:", ["Agregar Producto", "Modificar Producto", "Eliminar Producto"])
        
        if accion == "Agregar Producto":
            with st.form("add_f", clear_on_submit=True):
                n_id = st.text_input("ID (ej: G001):").strip()
                n_mod = st.text_input("Nombre:")
                n_cat = st.selectbox("Categoría:", ["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"])
                n_pre = st.number_input("Precio ($):", min_value=0, step=100)
                n_stk = st.number_input("Stock:", min_value=0, step=1)
                foto = st.file_uploader("Foto:", type=["jpg", "png", "jpeg"])
                
                if st.form_submit_button("Guardar"):
                    if n_id and n_mod and n_id not in df['ID'].values:
                        r_foto = ""
                        if foto:
                            ext = foto.name.split(".")[-1]
                            r_foto = os.path.join(FOLDER_FOTOS, f"{n_id}.{ext}")
                            Image.open(foto).save(r_foto)
                        df = pd.concat([df, pd.DataFrame([{"ID":n_id, "Modelo":n_mod, "Categoría":n_cat, "Precio Mayorista":n_pre, "Stock":n_stk, "Ruta Foto":r_foto}])], ignore_index=True)
                        guardar_datos(df)
                        st.success("¡Agregado!")
                        st.rerun()
                    else:
                        st.error("ID inválido o ya existente.")

        elif accion == "Modificar Producto" and not df.empty:
            id_m = st.selectbox("ID a modificar:", df['ID'].values)
            fila = df[df['ID'] == id_m].iloc[0]
            m_mod = st.text_input("Nombre:", value=fila['Modelo'])
            m_cat = st.selectbox("Categoría:", ["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"], index=["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"].index(fila['Categoría']) if fila['Categoría'] in ["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"] else 0)
            m_pre = st.number_input("Precio ($):", value=int(fila['Precio Mayorista']))
            m_stk = st.number_input("Stock:", value=int(fila['Stock']))
            
            if st.button("Actualizar"):
                idx = df[df['ID'] == id_m].index[0]
                df.at[idx, 'Modelo'] = m_mod
                df.at[idx, 'Categoría'] = m_cat
                df.at[idx, 'Precio Mayorista'] = m_pre
                df.at[idx, 'Stock'] = m_stk
                guardar_datos(df)
                st.success("¡Modificado!")
                st.rerun()

        elif accion == "Eliminar Producto" and not df.empty:
            id_e = st.selectbox("ID a borrar:", df['ID'].values)
            if st.button("Confirmar Eliminación"):
                df = df[df['ID'] != id_e]
                guardar_datos(df)
                st.success("¡Eliminado!")
                st.rerun()
    elif password != "":
        st.error("Clave incorrecta.")