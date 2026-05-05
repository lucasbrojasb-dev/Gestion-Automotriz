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
    username = st.text_input("Usuario", value="admin")
    password = st.text_input("Contraseña", type="password", value="admin123")
    
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
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# ==================== MENÚ PRINCIPAL ====================
st.success(f"✅ Bienvenido, {st.session_state.usuario}")

menu = st.sidebar.selectbox("Menú Principal", 
    ["🏠 Dashboard", "🛠️ Nueva Orden", "📖 Historial", "🚙 Vehículos"])

# ==================== DASHBOARD ====================
if menu == "🏠 Dashboard":
    st.subheader("Dashboard")
    st.write("El sistema está funcionando correctamente.")
    st.balloons()

# ==================== NUEVA ORDEN ====================
elif menu == "🛠️ Nueva Orden":
    st.subheader("Nueva Orden de Trabajo")
    ot_id = f"OT-{datetime.now().strftime('%Y%m%d-%H%M')}"
    st.info(f"**Orden:** {ot_id}")

    patente = st.text_input("Patente del vehículo", placeholder="ABCD12").upper()
    mecanico = st.text_input("Mecánico", st.session_state.usuario)

    # Inicializar lista de items de forma segura
    if 'items' not in st.session_state:
        st.session_state.items = []

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo de item", ["Mano de Obra", "Repuesto", "Insumo", "Lubricante"])
        cantidad = st.number_input("Cantidad", min_value=0.1, value=1.0, step=0.5)
    with col2:
        desc = st.text_input("Descripción del item")
        precio = st.number_input("Precio Unitario $", min_value=0, value=15000)

    if st.button("➕ Agregar Item", use_container_width=True):
        if desc.strip():
            st.session_state.items.append({
                "tipo": tipo,
                "descripcion": desc,
                "cantidad": cantidad,
                "precio_unit": precio,
                "subtotal": round(cantidad * precio, 2)
            })
            st.rerun()
        else:
            st.warning("Por favor ingresa una descripción")

    # Mostrar items de forma SEGURA
    if st.session_state.items:
        try:
            df = pd.DataFrame(st.session_state.items)
            st.dataframe(df, use_container_width=True)
            
            subtotal = df['subtotal'].sum()
            st.metric("Total (con IVA 19%)", f"${subtotal * 1.19:,.0f}")
        except:
            st.error("Error al mostrar items")
    else:
        st.info("Agrega items para ver el presupuesto")

    if st.button("💾 Guardar Orden", type="primary", use_container_width=True):
        if st.session_state.items:
            st.success("✅ Orden guardada correctamente (simulado)")
            st.balloons()
        else:
            st.warning("Debes agregar al menos un item")

st.caption("Sistema Taller - Versión estable para Streamlit Cloud")
