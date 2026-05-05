import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Mi Taller", layout="centered", initial_sidebar_state="collapsed")
st.title("🚗 Mi Taller Automotriz")

# ==================== BASE DE DATOS ====================
def init_db():
    conn = sqlite3.connect('taller.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (rut TEXT PRIMARY KEY, nombre TEXT, telefono TEXT, email TEXT, direccion TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS vehiculos 
                 (patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, ano INTEGER, 
                  km_actual INTEGER, cliente_rut TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ordenes 
                 (ot_id TEXT PRIMARY KEY, fecha TEXT, patente TEXT, estado TEXT, 
                  mecanico TEXT, descripcion TEXT, subtotal REAL, iva REAL, total REAL, pagado REAL DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS items_ot 
                 (id INTEGER PRIMARY KEY, ot_id TEXT, tipo TEXT, descripcion TEXT, 
                  cantidad REAL, precio_unit REAL, subtotal REAL)''')

    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin', 'admin123', 'Administrador', 'admin')")
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('mecanico', '1234', 'Mecánico', 'mecanico')")
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect('taller.db')

# ==================== LOGIN ====================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario = None

if not st.session_state.logged_in:
    st.subheader("🔐 Iniciar Sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar", use_container_width=True):
        conn = get_db_connection()
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

st.sidebar.success(f"👤 {st.session_state.usuario}")

menu = st.sidebar.selectbox("Menú", 
    ["🏠 Dashboard", "🚙 Vehículos", "🛠️ Nueva Orden", "📖 Historial", "📊 Reportes"])

# ==================== INICIALIZACIÓN SEGURA ====================
if 'items' not in st.session_state:
    st.session_state.items = []

# ==================== FUNCIÓN PDF ====================
def generar_pdf(tipo, ot_id, patente, mecanico, items, descripcion="", detalles_cliente=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MI TALLER AUTOMOTRIZ", ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "Concepción - Chile", ln=1, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "PRESUPUESTO", ln=1, align="C")
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Orden: {ot_id}   Patente: {patente}   Mecánico: {mecanico}", ln=1)
    pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(80, 8, "Descripción", 1)
    pdf.cell(20, 8, "Cant", 1, align="C")
    pdf.cell(35, 8, "P. Unit", 1, align="R")
    pdf.cell(35, 8, "Subtotal", 1, align="R", ln=1)

    subtotal = 0
    pdf.set_font("Arial", "", 10)
    for item in items:
        pdf.cell(80, 8, str(item.get('descripcion', ''))[:40], 1)
        pdf.cell(20, 8, str(item.get('cantidad', '')), 1, align="C")
        pdf.cell(35, 8, f"${item.get('precio_unit', 0):,.0f}", 1, align="R")
        pdf.cell(35, 8, f"${item.get('subtotal', 0):,.0f}", 1, align="R", ln=1)
        subtotal += item.get('subtotal', 0)

    iva = subtotal * 0.19
    total = subtotal + iva

    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(135, 8, "Subtotal", 1)
    pdf.cell
