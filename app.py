import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Mi Taller", layout="centered")

st.title("🚗 Mi Taller Automotriz")

# ==================== BASE DE DATOS ====================
def init_db():
    conn = sqlite3.connect('taller.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT)''')
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin', 'admin123', 'Administrador', 'admin')")
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('taller.db')

# ==================== LOGIN ====================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader("🔐 Iniciar Sesión")
    col1, col2 = st.columns([1,1])
    with col1:
        username = st.text_input("Usuario", placeholder="admin")
    with col2:
        password = st.text_input("Contraseña", type="password", placeholder="admin123")
    
    if st.button("Ingresar", use_container_width=True):
        conn = get_db()
        user = conn.execute("SELECT * FROM usuarios WHERE username=? AND password=?", 
                           (username, password)).fetchone()
        conn.close()
        if user:
            st.session_state.logged_in = True
            st.session_state.usuario = user[2]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrecta")
    st.stop()

# ==================== SI YA INICIÓ SESIÓN ====================
st.success(f"✅ Bienvenido, {st.session_state.usuario}")

menu = st.sidebar.selectbox("Menú Principal", 
    ["🏠 Dashboard", "🛠️ Nueva Orden", "📖 Historial", "🚙 Vehículos"])

st.divider()

# ==================== DASHBOARD ====================
if menu == "🏠 Dashboard":
    st.subheader("Dashboard")
    st.write("Sistema funcionando correctamente ✅")
    st.info("Prueba las otras opciones del menú lateral")

# ==================== NUEVA ORDEN (SIMPLIFICADA) ====================
elif menu == "🛠️ Nueva Orden":
    st.subheader("Nueva Orden")
    ot_id = f"OT-{datetime.now().strftime('%Y%m%d-%H%M')}"
    st.info(f"Orden: **{ot_id}**")

    patente = st.text_input("Patente del vehículo").upper()
    mecanico = st.text_input("Mecánico", st.session_state.usuario)
    
    if 'items' not in st.session_state:
        st.session_state.items = []

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo", ["Mano de Obra", "Repuesto", "Insumo", "Lubricante"])
        cantidad = st.number_input("Cantidad", 0.1, value=1.0)
    with col2:
        descripcion = st.text_input("Descripción")
        precio = st.number_input("Precio $", value=15000)

    if st.button("➕ Agregar Item", use_container_width=True):
        if descripcion.strip():
            st.session_state.items.append({
                "tipo": tipo,
                "descripcion": descripcion,
                "cantidad": cantidad,
                "precio_unit": precio,
                "subtotal": cantidad * precio
            })
            st.rerun()

    if st.session_state.items:
        df = pd.DataFrame(st.session_state.items)
        st.dataframe(df, use_container_width=True)

    if st.button("💾 Guardar Orden", type="primary", use_container_width=True):
        st.success("Orden guardada (simulado)")

# ==================== OTRAS SECCIONES ====================
elif menu == "📖 Historial":
    st.subheader("Historial")
    patente = st.text_input("Buscar por Patente")
    if patente:
        st.info("Aquí aparecerán las órdenes de esa patente")

elif menu == "🚙 Vehículos":
    st.subheader("Vehículos")
    st.write("Sección de vehículos (en desarrollo)")

st.caption("Versión de prueba simplificada")
