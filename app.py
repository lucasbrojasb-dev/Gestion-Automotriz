import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os
import uuid
import hashlib
import shutil

# ==================== CONFIG ====================
st.set_page_config(page_title="ENAM Taller", layout="centered")
st.title("🚗 ENAM Servicio Automotriz")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ==================== SEGURIDAD ====================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ==================== DB ====================
def init_db():
    conn = sqlite3.connect('taller.db')
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS usuarios 
        (username TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS vehiculos 
        (patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, ano INTEGER, km INTEGER)""")

    c.execute("""CREATE TABLE IF NOT EXISTS ordenes 
        (ot_id TEXT PRIMARY KEY, fecha TEXT, patente TEXT, estado TEXT,
         mecanico TEXT, descripcion TEXT, subtotal REAL, iva REAL, total REAL, pagado REAL DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS items_ot 
        (id INTEGER PRIMARY KEY, ot_id TEXT, tipo TEXT, descripcion TEXT,
         cantidad REAL, precio_unit REAL, subtotal REAL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS fotos_vehiculo 
        (id INTEGER PRIMARY KEY, patente TEXT, filename TEXT, fecha TEXT)""")

    # usuarios
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin', ?, 'Administrador', 'admin')",
              (hash_pass('admin123'),))
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('mecanico', ?, 'Mecánico', 'mecanico')",
              (hash_pass('1234'),))

    conn.commit()
    conn.close()

init_db()

def db():
    return sqlite3.connect('taller.db')

# ==================== BACKUP ====================
def backup():
    shutil.copy("taller.db", f"backup_{datetime.now().strftime('%Y%m%d')}.db")

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.subheader("🔐 Login")
    u = st.text_input("Usuario")
    p = st.text_input("Clave", type="password")

    if st.button("Ingresar"):
        conn = db()
        user = conn.execute("SELECT * FROM usuarios WHERE username=? AND password=?",
                            (u, hash_pass(p))).fetchone()
        conn.close()
        if user:
            st.session_state.login = True
            st.session_state.user = user[2]
            st.rerun()
        else:
            st.error("Error login")
    st.stop()

st.sidebar.success(st.session_state.user)

menu = st.sidebar.selectbox("Menú", ["Dashboard","Vehículos","Nueva Orden","Historial"])

# ==================== PDF ====================
def generar_pdf(tipo, ot, items):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)

    pdf.cell(0,10,"ENAM Servicio Automotriz",ln=1)
    pdf.cell(0,10,f"Orden: {ot['ot_id']}",ln=1)

    subtotal = sum(i['subtotal'] for i in items)
    total = subtotal
    neto = total / 1.19
    iva = total - neto

    pdf.cell(0,10,f"Total: ${int(total):,}",ln=1)

    if tipo == "presupuesto":
        pdf.set_text_color(255,0,0)
        pdf.multi_cell(0,10,"VALOR ESTIMADO - SUJETO A CAMBIOS")
        pdf.set_text_color(0,0,0)

    file = f"{tipo}_{ot['ot_id']}.pdf"
    pdf.output(file)
    return file

# ==================== DASHBOARD ====================
if menu == "Dashboard":
    conn = db()
    df = pd.read_sql_query("SELECT * FROM ordenes", conn)
    conn.close()

    if not df.empty:
        pagado = df['pagado'].sum()
        total = df['total'].sum()

        st.metric("💰 Total", f"${total:,.0f}")
        st.metric("💵 Pagado", f"${pagado:,.0f}")
        st.metric("⏳ Pendiente", f"${total-pagado:,.0f}")

# ==================== VEHICULOS ====================
elif menu == "Vehículos":
    patente = st.text_input("Patente").upper()
    marca = st.text_input("Marca")
    modelo = st.text_input("Modelo")
    ano = st.number_input("Año", 1950, 2030)
    km = st.number_input("KM")

    if st.button("Guardar"):
        conn = db()
        conn.execute("INSERT OR REPLACE INTO vehiculos VALUES (?,?,?,?,?)",
                     (patente,marca,modelo,ano,km))
        conn.commit()
        conn.close()
        st.success("Guardado")

# ==================== ORDEN ====================
elif menu == "Nueva Orden":
    ot_id = f"OT-{datetime.now().strftime('%H%M%S')}"
    patente = st.text_input("Patente").upper()

    conn = db()
    veh = conn.execute("SELECT * FROM vehiculos WHERE patente=?", (patente,)).fetchone()
    conn.close()

    if veh:
        st.info(f"{veh[1]} {veh[2]} - KM {veh[4]}")

    desc = st.text_area("Descripción")

    # fotos
    fotos = st.file_uploader("Fotos", accept_multiple_files=True)

    if "items" not in st.session_state:
        st.session_state.items = []

    tipo = st.selectbox("Tipo", ["MO","Repuesto","Insumo"])
    d = st.text_input("Item")
    cant = st.number_input("Cantidad",1.0)
    precio = st.number_input("Precio FINAL (con IVA)",1000)

    if st.button("Agregar"):
        st.session_state.items.append({
            "descripcion": d,
            "cantidad": cant,
            "precio_unit": precio,
            "subtotal": cant*precio
        })

    if st.session_state.items:
        df = pd.DataFrame(st.session_state.items)
        st.dataframe(df)
        st.metric("Total", f"${df['subtotal'].sum():,.0f}")

    if st.button("Guardar Orden"):
        if not st.session_state.items:
            st.error("Sin items")
        else:
            conn = db()
            subtotal = sum(i['subtotal'] for i in st.session_state.items)
            neto = subtotal/1.19
            iva = subtotal-neto

            conn.execute("INSERT INTO ordenes VALUES (?,?,?,?,?,?,?,?,?,0)",
                         (ot_id,datetime.now(),patente,"Pendiente",
                          st.session_state.user,desc,neto,iva,subtotal))

            for i in st.session_state.items:
                conn.execute("INSERT INTO items_ot VALUES (NULL,?,?,?,?,?,?)",
                             (ot_id,"",i['descripcion'],i['cantidad'],i['precio_unit'],i['subtotal']))

            if fotos:
                for f in fotos:
                    name = f"{uuid.uuid4()}_{f.name}"
                    with open(os.path.join("uploads",name),"wb") as out:
                        out.write(f.read())
                    conn.execute("INSERT INTO fotos_vehiculo VALUES (NULL,?,?,?)",
                                 (patente,name,datetime.now()))

            conn.commit()
            conn.close()

            backup()

            st.success("Orden guardada")
            st.session_state.items = []

# ==================== HISTORIAL ====================
elif menu == "Historial":
    patente = st.text_input("Patente").upper()

    if patente:
        conn = db()
        df = pd.read_sql_query("SELECT * FROM ordenes WHERE patente=?", conn, params=(patente,))
        conn.close()

        for _, row in df.iterrows():
            st.write(f"### {row['ot_id']} - {row['estado']}")
            st.write(f"Total: ${row['total']:,.0f}")

            pago = st.number_input(f"Pago {row['ot_id']}",0,key=row['ot_id'])

            if st.button(f"Pagar {row['ot_id']}"):
                conn = db()
                conn.execute("UPDATE ordenes SET pagado=? WHERE ot_id=?",
                             (pago,row['ot_id']))
                conn.commit()
                conn.close()
                st.success("Pago registrado")
