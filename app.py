import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os
import uuid
import hashlib
import shutil

# ================= CONFIG =================
st.set_page_config(page_title="ENAM Taller", layout="centered")
st.title("🚗 ENAM Servicio Automotriz")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ================= SEGURIDAD =================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= DB =================
def db():
    return sqlite3.connect('taller.db')

def init_db():
    conn = db()
    c = conn.cursor()

    # RESET CONTROLADO (solo si hay error de estructura)
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios 
        (username TEXT PRIMARY KEY, password TEXT, nombre TEXT, rol TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS vehiculos 
        (patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, ano INTEGER, km INTEGER)""")

    c.execute("""CREATE TABLE IF NOT EXISTS ordenes 
        (ot_id TEXT PRIMARY KEY, fecha TEXT, patente TEXT, estado TEXT,
         mecanico TEXT, descripcion TEXT, subtotal REAL, iva REAL, total REAL, pagado REAL DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS items_ot 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, ot_id TEXT, tipo TEXT, descripcion TEXT,
         cantidad REAL, precio_unit REAL, subtotal REAL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS fotos_vehiculo 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, patente TEXT, filename TEXT, fecha TEXT)""")

    # usuarios seguros
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin', ?, 'Administrador', 'admin')",
              (hash_pass('admin123'),))
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('mecanico', ?, 'Mecánico', 'mecanico')",
              (hash_pass('1234'),))

    conn.commit()
    conn.close()

init_db()

# ================= BACKUP =================
def backup():
    try:
        shutil.copy("taller.db", f"backup_{datetime.now().strftime('%Y%m%d')}.db")
    except:
        pass

# ================= LOGIN =================
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
            st.error("Usuario o clave incorrectos")

    st.stop()

st.sidebar.success(f"👤 {st.session_state.user}")

menu = st.sidebar.selectbox("Menú", ["Dashboard","Vehículos","Nueva Orden","Historial"])

# ================= DASHBOARD =================
if menu == "Dashboard":
    conn = db()
    df = pd.read_sql_query("SELECT * FROM ordenes", conn)
    conn.close()

    if not df.empty:
        total = df['total'].sum()
        pagado = df['pagado'].sum()

        st.metric("💰 Total", f"${total:,.0f}")
        st.metric("💵 Pagado", f"${pagado:,.0f}")
        st.metric("⏳ Pendiente", f"${total-pagado:,.0f}")

# ================= VEHICULOS =================
elif menu == "Vehículos":
    st.subheader("Vehículos")

    patente = st.text_input("Patente").upper()
    marca = st.text_input("Marca")
    modelo = st.text_input("Modelo")
    ano = st.number_input("Año", 1950, 2030)
    km = st.number_input("KM")

    if st.button("Guardar Vehículo"):
        conn = db()
        conn.execute("INSERT OR REPLACE INTO vehiculos VALUES (?,?,?,?,?)",
                     (patente,marca,modelo,ano,km))
        conn.commit()
        conn.close()
        st.success("Vehículo guardado")

# ================= NUEVA ORDEN =================
elif menu == "Nueva Orden":

    if "items" not in st.session_state or not isinstance(st.session_state.items, list):
        st.session_state.items = []

    ot_id = f"OT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    st.info(f"Orden: {ot_id}")

    patente = st.text_input("Patente").upper()

    conn = db()
    veh = conn.execute("SELECT * FROM vehiculos WHERE patente=?", (patente,)).fetchone()
    conn.close()

    if veh:
        st.success(f"{veh[1]} {veh[2]} - KM {veh[4]}")

    desc = st.text_area("Descripción")

    fotos = st.file_uploader("Fotos del vehículo", accept_multiple_files=True)

    tipo = st.selectbox("Tipo", ["MO","Repuesto","Insumo"])
    item_desc = st.text_input("Descripción item")
    cant = st.number_input("Cantidad", 1.0)
    precio = st.number_input("Precio FINAL (IVA incluido)", 1000)

    if st.button("Agregar Item"):
        if item_desc:
            st.session_state.items.append({
                "tipo": tipo,
                "descripcion": item_desc,
                "cantidad": cant,
                "precio_unit": precio,
                "subtotal": cant * precio
            })

    # mostrar items seguro
    if len(st.session_state.items) > 0:
        try:
            df_items = pd.DataFrame(st.session_state.items)

            if "subtotal" in df_items.columns:
                st.dataframe(df_items, use_container_width=True)
                st.metric("Total", f"${df_items['subtotal'].sum():,.0f}")
        except:
            st.session_state.items = []

    # guardar orden
    if st.button("Guardar Orden"):
        if not st.session_state.items:
            st.error("Debes agregar items")
        else:
            conn = db()

            total = sum(i['subtotal'] for i in st.session_state.items)
            neto = total / 1.19
            iva = total - neto

            conn.execute("INSERT INTO ordenes VALUES (?,?,?,?,?,?,?,?,?,0)",
                         (ot_id,
                          datetime.now().strftime("%Y-%m-%d %H:%M"),
                          patente,
                          "Pendiente",
                          st.session_state.user,
                          desc,
                          neto,
                          iva,
                          total))

            for i in st.session_state.items:
                conn.execute("""INSERT INTO items_ot 
                    (ot_id, tipo, descripcion, cantidad, precio_unit, subtotal)
                    VALUES (?,?,?,?,?,?)""",
                    (ot_id, i['tipo'], i['descripcion'], i['cantidad'], i['precio_unit'], i['subtotal']))

            # fotos
            if fotos:
                for f in fotos:
                    name = f"{uuid.uuid4()}_{f.name}"
                    path = os.path.join("uploads", name)

                    with open(path, "wb") as out:
                        out.write(f.read())

                    conn.execute("""INSERT INTO fotos_vehiculo 
                        (patente, filename, fecha)
                        VALUES (?,?,?)""",
                        (patente, name, datetime.now()))

            conn.commit()
            conn.close()

            backup()

            st.success("Orden guardada")
            st.session_state.items = []

# ================= HISTORIAL =================
elif menu == "Historial":
    st.subheader("Historial")

    patente = st.text_input("Patente buscar").upper()

    if patente:
        conn = db()
        df = pd.read_sql_query("SELECT * FROM ordenes WHERE patente=? ORDER BY fecha DESC",
                               conn, params=(patente,))
        conn.close()

        if df.empty:
            st.warning("Sin registros")
        else:
            for _, row in df.iterrows():

                st.markdown(f"### {row['ot_id']} - {row['estado']}")
                st.write(f"💰 ${row['total']:,.0f}")
                st.write(f"💵 Pagado: ${row['pagado']:,.0f}")

                col1, col2 = st.columns(2)

                # finalizar
                with col1:
                    if row['estado'] != "Terminado":
                        if st.button(f"Finalizar {row['ot_id']}", key=f"fin{row['ot_id']}"):
                            conn = db()
                            conn.execute("UPDATE ordenes SET estado='Terminado' WHERE ot_id=?",
                                         (row['ot_id'],))
                            conn.commit()
                            conn.close()
                            st.rerun()

                # pago
                with col2:
                    pago = st.number_input(f"Pago {row['ot_id']}", 0, key=f"pay{row['ot_id']}")

                    if st.button(f"Pagar {row['ot_id']}", key=f"btn{row['ot_id']}"):
                        conn = db()
                        conn.execute("UPDATE ordenes SET pagado=? WHERE ot_id=?",
                                     (pago, row['ot_id']))
                        conn.commit()
                        conn.close()
                        st.rerun()
