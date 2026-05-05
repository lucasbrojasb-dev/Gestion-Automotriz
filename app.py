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

# ==================== INICIALIZAR ITEMS ====================
if 'items' not in st.session_state:
    st.session_state.items = []

# ==================== PDF FUNCTION ====================
def generar_pdf(tipo, ot_id, patente, mecanico, items, descripcion="", detalles_cliente=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MI TALLER AUTOMOTRIZ", ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "Concepción - Chile", ln=1, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "PRESUPUESTO" if tipo == "presupuesto" else "ORDEN DE TRABAJO", ln=1, align="C")
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Orden: {ot_id}   Patente: {patente}", ln=1)
    pdf.cell(0, 8, f"Mecánico: {mecanico}   Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1)
    pdf.ln(5)

    # Tabla
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
    pdf.cell(35, 8, f"${subtotal:,.0f}", 1, ln=1, align="R")
    pdf.cell(135, 8, "IVA 19%", 1)
    pdf.cell(35, 8, f"${iva:,.0f}", 1, ln=1, align="R")
    pdf.cell(135, 10, "TOTAL", 1)
    pdf.cell(35, 10, f"${total:,.0f}", 1, ln=1, align="R")

    filename = f"{tipo}_{ot_id}.pdf"
    pdf.output(filename)
    return filename

# ==================== NUEVA ORDEN (CORREGIDO) ====================
if menu == "🛠️ Nueva Orden":
    st.subheader("Nueva Orden")
    ot_id = f"OT-{datetime.now().strftime('%Y%m%d-%H%M')}"
    st.info(f"**Orden:** {ot_id}")

    patente = st.text_input("Patente del vehículo").upper()
    mecanico = st.text_input("Mecánico", st.session_state.usuario)
    descripcion = st.text_area("Descripción general")
    detalles_cliente = st.text_area("Detalles indicados por el cliente")

    col1, col2 = st.columns(2)
    with col1:
        tipo_item = st.selectbox("Tipo", ["Mano de Obra", "Repuesto", "Insumo", "Lubricante"])
        cantidad = st.number_input("Cantidad", min_value=0.1, value=1.0, step=0.5)
    with col2:
        desc_item = st.text_input("Descripción del item")
        precio = st.number_input("Precio Unitario $", min_value=0, value=15000)

    if st.button("➕ Agregar Item", use_container_width=True):
        st.session_state.items.append({
            "tipo": tipo_item,
            "descripcion": desc_item,
            "cantidad": cantidad,
            "precio_unit": precio,
            "subtotal": round(cantidad * precio, 2)
        })
        st.rerun()

    # === Mostrar items de forma segura ===
    if st.session_state.items:
        df_items = pd.DataFrame(st.session_state.items)
        st.dataframe(df_items, use_container_width=True)
        
        subtotal = df_items['subtotal'].sum()
        st.metric("Total con IVA", f"${subtotal * 1.19:,.0f}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Guardar Orden", type="primary", use_container_width=True):
            if st.session_state.items:
                conn = get_db_connection()
                subtotal = sum(item['subtotal'] for item in st.session_state.items)
                conn.execute("""INSERT INTO ordenes 
                             (ot_id, fecha, patente, estado, mecanico, descripcion, subtotal, iva, total)
                             VALUES (?,?,?,?,?,?,?,?,?)""",
                            (ot_id, datetime.now().strftime("%Y-%m-%d %H:%M"), patente, 
                             "Pendiente", mecanico, descripcion, subtotal, subtotal*0.19, subtotal*1.19))
                for item in st.session_state.items:
                    conn.execute("INSERT INTO items_ot VALUES (NULL,?,?,?,?,?,?)",
                                (ot_id, item['tipo'], item['descripcion'], item['cantidad'], item['precio_unit'], item['subtotal']))
                conn.commit()
                conn.close()
                st.success("✅ Orden guardada correctamente")
                st.session_state.items = []  # Limpiar
                st.rerun()
            else:
                st.warning("Agrega al menos un item")

    with col2:
        if st.button("📄 Generar Presupuesto", use_container_width=True) and st.session_state.items:
            filename = generar_pdf("presupuesto", ot_id, patente, mecanico, st.session_state.items, descripcion, detalles_cliente)
            with open(filename, "rb") as f:
                st.download_button("⬇️ Descargar PDF", f, file_name=filename, use_container_width=True)

st.caption("Sistema Taller v2.6 - Error corregido")
