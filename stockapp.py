import streamlit as st
import pandas as pd
import os
import json
import datetime
from PIL import Image

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Control de Stock y Pedidos - Mayorista", layout="wide")

CSV_FILE = "stock_gorras.csv"
PEDIDOS_FILE = "pedidos.csv"
FOLDER_FOTOS = "fotos"
PASSWORD_ADMIN = "GorrasCba2026"  # Esta es la contraseña única para todo el sistema

# Crear carpetas y archivos si no existen
if not os.path.exists(FOLDER_FOTOS):
    os.makedirs(FOLDER_FOTOS)

if not os.path.exists(CSV_FILE):
    df_init = pd.DataFrame(columns=["ID", "Modelo", "Categoría", "Precio Mayorista", "Stock", "Ruta Foto"])
    df_init.to_csv(CSV_FILE, index=False)

if not os.path.exists(PEDIDOS_FILE):
    df_ped_init = pd.DataFrame(columns=["ID_Pedido", "Fecha", "Cliente", "Localidad", "Productos_JSON", "Total_Unidades", "Total_Pesos", "Estado"])
    df_ped_init.to_csv(PEDIDOS_FILE, index=False)

# Funciones de utilidad para lectura y escritura de datos
def cargar_datos():
    return pd.read_csv(CSV_FILE, dtype={"ID": str})

def guardar_datos(df):
    df.to_csv(CSV_FILE, index=False)

def cargar_pedidos():
    return pd.read_csv(PEDIDOS_FILE, dtype={"ID_Pedido": str})

def guardar_pedidos(df):
    df.to_csv(PEDIDOS_FILE, index=False)

# --- MENÚ LATERAL DE NAVEGACIÓN ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["Ver Catálogo y Stock", "Gestionar Pedidos", "Panel de Administrador"])

# --- VISTA 1: VER CATÁLOGO Y STOCK ---
if opcion == "Ver Catálogo y Stock":
    st.title("📦 Inventario General de Gorras")
    df = cargar_datos()
    
    if df.empty:
        st.info("El inventario está vacío. Podés agregar productos en el 'Panel de Administrador'.")
    else:
        busqueda = st.text_input("🔍 Buscar por ID o Modelo:", "")
        if busqueda:
            df = df[df['ID'].str.contains(busqueda, case=False) | df['Modelo'].str.contains(busqueda, case=False)]

        st.write("---")
        cols_por_fila = 4
        filas = [df[i:i + cols_por_fila] for i in range(0, df.shape[0], cols_por_fila)]
        
        for fila in filas:
            cols = st.columns(cols_por_fila)
            for idx, (index, row) in enumerate(fila.iterrows()):
                with cols[idx]:
                    if pd.notna(row['Ruta Foto']) and os.path.exists(row['Ruta Foto']):
                        st.image(Image.open(row['Ruta Foto']), use_container_width=True)
                    else:
                        st.warning("Sin foto disponible 📸")
                    st.subheader(f"{row['Modelo']}")
                    st.write(f"**ID:** `{row['ID']}`")
                    st.write(f"**Categoría:** {row['Categoría']}")
                    st.write(f"**Precio Mayorista:** ${row['Precio Mayorista']:,}")
                    if row['Stock'] <= 5:
                        st.error(f"⚠️ **Stock bajo:** {row['Stock']} unidades")
                    else:
                        st.success(f"**Stock:** {row['Stock']} unidades")
                    st.write("---")

# --- VISTA 2: GESTIONAR PEDIDOS ---
elif opcion == "Gestionar Pedidos":
    st.title("📝 Control y Validación de Pedidos")
    
    password_pedidos = st.text_input("Ingresá la contraseña de administración:", type="password", key="pass_ped")
    if password_pedidos == PASSWORD_ADMIN:
        df_pedidos = cargar_pedidos()
        
        if df_pedidos.empty:
            st.info("No se ha registrado ningún pedido aún.")
        else:
            estado_filtro = st.selectbox("Filtrar por Estado:", ["Pendientes", "Confirmados", "Cancelados"])
            traducido = {"Pendientes": "Pendiente", "Confirmados": "Confirmado", "Cancelados": "Cancelado"}
            df_filtrado = df_pedidos[df_pedidos['Estado'] == traducido[estado_filtro]]
            
            if df_filtrado.empty:
                st.write(f"No hay pedidos con estado: **{estado_filtro}**")
            else:
                for idx, row in df_filtrado.iterrows():
                    with st.expander(f"🛒 Pedido {row['ID_Pedido']} - {row['Cliente']} ({row['Fecha']})"):
                        st.write(f"**Cliente:** {row['Cliente']} | **Ubicación:** {row['Localidad']}")
                        st.write(f"**Total Unidades:** {row['Total_Unidades']} | **Monto Total:** ${row['Total_Pesos']:,}")
                        st.write("**Detalle de Productos:**")
                        
                        productos_dict = json.loads(row['Productos_JSON'])
                        df_stock_ref = cargar_datos()
                        
                        for p_id, p_cant in productos_dict.items():
                            nombre_prod = df_stock_ref[df_stock_ref['ID'] == p_id]['Modelo'].values
                            nombre_mostrar = nombre_prod[0] if len(nombre_prod) > 0 else "Modelo Eliminado"
                            st.write(f"- Código `{p_id}`: {nombre_mostrar} x {p_cant} unidades.")
                        
                        if row['Estado'] == "Pendiente":
                            st.write("---")
                            col_conf, col_canc = st.columns(2)
                            
                            with col_conf:
                                if st.button("✅ Confirmar Pedido", key=f"conf_{row['ID_Pedido']}"):
                                    df_pedidos.at[idx, 'Estado'] = "Confirmado"
                                    guardar_pedidos(df_pedidos)
                                    st.success(f"Pedido {row['ID_Pedido']} Confirmado correctamente.")
                                    st.rerun()
                                    
                            with col_canc:
                                if st.button("❌ Cancelar y Devolver Stock", key=f"canc_{row['ID_Pedido']}"):
                                    df_stock = cargar_datos()
                                    for prod_id, cant_devolver in productos_dict.items():
                                        if prod_id in df_stock['ID'].values:
                                            df_stock.loc[df_stock['ID'] == prod_id, 'Stock'] += cant_devolver
                                    
                                    df_pedidos.at[idx, 'Estado'] = "Cancelado"
                                    guardar_datos(df_stock)
                                    guardar_pedidos(df_pedidos)
                                    st.error(f"Pedido {row['ID_Pedido']} Cancelado. El stock fue devuelto al inventario.")
                                    st.rerun()
    elif password_pedidos != "":
        st.error("Contraseña incorrecta.")

# --- VISTA 3: PANEL DE ADMINISTRADOR (CRUD PRODUCTOS) ---
elif opcion == "Panel de Administrador":  # <-- ¡ERROR DE TIPEO SOLUCIONADO ACÁ!
    st.title("🛡️ Panel de Configuración de Productos")
    
    password_input = st.text_input("Ingresá la contraseña de administración:", type="password", key="pass_admin_crud")
    
    if password_input == PASSWORD_ADMIN:
        st.success("Acceso concedido al gestor de productos.")
        df = cargar_datos()
        
        accion = st.selectbox("¿Qué acción querés realizar?:", ["Agregar Producto", "Modificar Producto", "Eliminar Producto"])
        st.write("---")
        
        # --- ACCIÓN: AGREGAR ---
        if accion == "Agregar Producto":
            st.header("➕ Añadir Nuevo Modelo al Catálogo")
            with st.form("form_add", clear_on_submit=True):
                nuevo_id = st.text_input("ID Único (ej: G001):").strip()
                nuevo_modelo = st.text_input("Nombre del Modelo (ej: Trucker Premium Black):")
                nueva_cat = st.selectbox("Categoría:", ["Lisas", "Vintage", "Premium", "Piluso", "G5", "Cerradas","Jordan"])
                nuevo_precio = st.number_input("Precio Mayorista ($):", min_value=0, step=100)
                nuevo_stock = st.number_input("Stock Inicial (Unidades):", min_value=0, step=1)
                foto_subida = st.file_uploader("Subir Foto de la Gorra:", type=["jpg", "jpeg", "png"])
                
                if st.form_submit_button("Guardar Producto"):
                    if not nuevo_id or not nuevo_modelo:
                        st.error("El ID y el Nombre son obligatorios.")
                    elif nuevo_id in df['ID'].values:
                        st.error(f"El ID '{nuevo_id}' ya existe en el sistema.")
                    else:
                        ruta_foto = ""
                        if foto_subida:
                            ext = foto_subida.name.split(".")[-1]
                            ruta_foto = os.path.join(FOLDER_FOTOS, f"{nuevo_id}.{ext}")
                            Image.open(foto_subida).save(ruta_foto)
                        
                        nueva_fila = {
                            "ID": nuevo_id, "Modelo": nuevo_modelo, "Categoría": nueva_cat,
                            "Precio Mayorista": nuevo_precio, "Stock": nuevo_stock, "Ruta Foto": ruta_foto
                        }
                        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
                        guardar_datos(df)
                        st.success(f"¡{nuevo_modelo} se agregó con éxito!")
                        st.rerun()

        # --- ACCIÓN: MODIFICAR ---
        elif accion == "Modificar Producto":
            st.header("📝 Modificar Producto Existente")
            if df.empty:
                st.info("No hay productos para modificar.")
            else:
                id_mod = st.selectbox("Seleccioná el ID del producto:", df['ID'].values)
                fila = df[df['ID'] == id_mod].iloc[0]
                
                mod_modelo = st.text_input("Nombre del Modelo:", value=fila['Modelo'])
                mod_cat = st.selectbox("Categoría:", ["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"], index=["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"].index(fila['Categoría']) if fila['Categoría'] in ["Trucker", "Snapback", "Dad Hat", "Piluso", "Urbana", "Otros"] else 0)
                mod_precio = st.number_input("Precio Mayorista ($):", min_value=0, value=int(fila['Precio Mayorista']))
                mod_stock = st.number_input("Stock actual (Unidades):", min_value=0, value=int(fila['Stock']))
                
                st.write("Foto actual:")
                if pd.notna(fila['Ruta Foto']) and os.path.exists(fila['Ruta Foto']):
                    st.image(Image.open(fila['Ruta Foto']), width=150)
                
                nueva_foto_mod = st.file_uploader("Reemplazar foto (opcional):", type=["jpg", "jpeg", "png"])
                
                if st.button("Actualizar Cambios"):
                    idx = df[df['ID'] == id_mod].index[0]
                    ruta_foto_final = fila['Ruta Foto']
                    
                    if nueva_foto_mod:
                        ext = nueva_foto_mod.name.split(".")[-1]
                        ruta_foto_final = os.path.join(FOLDER_FOTOS, f"{id_mod}.{ext}")
                        Image.open(nueva_foto_mod).save(ruta_foto_final)
                    
                    df.at[idx, 'Modelo'] = mod_modelo
                    df.at[idx, 'Categoría'] = mod_cat
                    df.at[idx, 'Precio Mayorista'] = mod_precio
                    df.at[idx, 'Stock'] = mod_stock
                    df.at[idx, 'Ruta Foto'] = ruta_foto_final
                    
                    guardar_datos(df)
                    st.success("¡Producto modificado con éxito!")
                    st.rerun()

        # --- ACCIÓN: ELIMINAR ---
        elif accion == "Eliminar Producto":
            st.header("❌ Eliminar un Producto")
            if df.empty:
                st.info("No hay productos para eliminar.")
            else:
                id_eli = st.selectbox("Seleccioná el ID a borrar:", df['ID'].values)
                fila_eli = df[df['ID'] == id_eli].iloc[0]
                
                st.warning(f"¿Seguro que querés borrar el modelo: {fila_eli['Modelo']} (ID: {id_eli})? Esto no se puede deshacer.")
                
                if st.button("Confirmar Eliminación"):
                    # Borrar archivo físico de la imagen
                    if pd.notna(fila_eli['Ruta Foto']) and os.path.exists(fila_eli['Ruta Foto']):
                        try:
                            os.remove(fila_eli['Ruta Foto'])
                        except:
                            pass
                    
                    df = df[df['ID'] != id_eli]
                    guardar_datos(df)
                    st.success("Producto eliminado del sistema.")
                    st.rerun()
                    
    elif password_input != "":
        st.error("Contraseña incorrecta. Ingresá 'gorras2026' para administrar.")