import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Blangking v9", layout="wide")

# --- DATABASE SEDERHANA (JSON) ---
FILE_DATA = "data_kas_blangking_v9.json"

def load_data():
    if os.path.exists(FILE_DATA):
        with open(FILE_DATA, "r") as f:
            return json.load(f)
    return {"anggota": {}, "transaksi": [], "p3k": [], "config": {"nom_iuran": "10000"}}

def save_data(data):
    with open(FILE_DATA, "w") as f:
        json.dump(data, f)

# Inisialisasi Data
if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- SISTEM LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None

def login():
    st.title("🔐 Login Kas Blangking")
    user_type = st.radio("Masuk Sebagai:", ["User", "Admin"])
    password = st.text_input("Password", type="password")
    
    if st.button("Masuk"):
        if user_type == "Admin" and password == "1234":
            st.session_state.authenticated = True
            st.session_state.role = "admin"
            st.rerun()
        elif user_type == "User" and password == "user123": # Ganti password user di sini
            st.session_state.authenticated = True
            st.session_state.role = "user"
            st.rerun()
        else:
            st.error("Password Salah!")

if not st.session_state.authenticated:
    login()
    st.stop()

# --- SIDEBAR & NAVIGASI ---
role = st.session_state.role
st.sidebar.title(f"Menu ({role.upper()})")
if role == "admin":
    menu = st.sidebar.selectbox("Pilih Fitur", 
        ["Dashboard", "Input Transaksi", "Ceklis Iuran", "Data Anggota", "Stok P3K", "Riwayat Transaksi"])
else:
    menu = st.sidebar.selectbox("Pilih Fitur", 
        ["Dashboard", "Ceklis Iuran", "Stok P3K"])

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# --- LOGIKA DASHBOARD (SEMUA ROLE) ---
def show_dashboard():
    st.header("📊 Visualisasi Saldo & Kas")
    df_tr = pd.DataFrame(st.session_state.db['transaksi'])
    
    if df_tr.empty:
        st.warning("Belum ada data transaksi.")
        return

    # Hitung Saldo
    tin = df_tr[df_tr['metode'] == "Tunai"]['jumlah'].sum()
    qin = df_tr[df_tr['metode'] == "QRIS"]['jumlah'].sum()
    tout = df_tr[df_tr['metode'] == "KELUAR TUNAI"]['jumlah'].sum()
    qout = df_tr[df_tr['metode'] == "KELUAR QRIS"]['jumlah'].sum()
    
    s_tunai = tin - tout
    s_qris = qin - qout

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tunai", f"Rp {s_tunai:,}")
    col2.metric("Total QRIS", f"Rp {s_qris:,}")
    col3.metric("Total Gabungan", f"Rp {s_tunai + s_qris:,}")

    # Grafik
    chart_data = pd.DataFrame({
        "Metode": ["Tunai", "QRIS"],
        "Saldo": [s_tunai, s_qris]
    })
    fig = px.bar(chart_data, x="Metode", y="Saldo", color="Metode", 
                 color_discrete_map={"Tunai": "#3399FF", "QRIS": "#00B050"})
    st.plotly_chart(fig, use_container_width=True)

# --- LOGIKA CEKLIS IURAN (SEMUA ROLE) ---
def show_ceklis():
    st.header("✅ Ceklis Iuran Anggota")
    thn_pilih = st.selectbox("Pilih Tahun", range(2025, 2031))
    
    # Hitung pembayaran per anggota
    pt = {}
    nd = int(st.session_state.db['config'].get("nom_iuran", 10000))
    for tr in st.session_state.db['transaksi']:
        if "iuran" in tr['keterangan'].lower() and "KELUAR" not in tr['metode']:
            pt[tr['nama']] = pt.get(tr['nama'], 0) + (tr['jumlah'] // nd)

    data_tabel = []
    bulan_list = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]
    
    for nama, info in st.session_state.db['anggota'].items():
        row = {"Nama": nama}
        tot_bayar = pt.get(nama, 0)
        bm, tm = int(info.get("bln_masuk", 1)), int(info.get("thn_masuk", 2025))
        
        for m_idx, m_name in enumerate(bulan_list, 1):
            iv = ((thn_pilih - 2025) * 12) + (m_idx - 1)
            ig = ((tm - 2025) * 12) + (bm - 1)
            
            if iv < ig: row[m_name] = "N/A"
            elif tot_bayar > (iv - ig): row[m_name] = "✔️"
            else: row[m_name] = "❌"
        data_tabel.append(row)
    
    st.table(pd.DataFrame(data_tabel))

# --- LOGIKA STOK P3K (SEMUA ROLE) ---
def show_p3k():
    st.header("💊 Stok Obat P3K")
    if role == "admin":
        with st.expander("Tambah Obat Baru"):
            c1, c2, c3 = st.columns(3)
            n_obat = c1.text_input("Nama Obat")
            j_obat = c2.selectbox("Jenis", ["Pil", "Kapsul", "Cair"])
            e_obat = c3.text_input("Exp Date")
            in_obat = st.number_input("Masuk", min_value=0)
            out_obat = st.number_input("Keluar", min_value=0)
            if st.button("Simpan Obat"):
                st.session_state.db['p3k'].append({
                    "tgl": datetime.now().strftime("%d-%m-%Y"),
                    "nama": n_obat, "jenis": j_obat, "in": in_obat, "out": out_obat, "exp": e_obat
                })
                save_data(st.session_state.db)
                st.success("Data Tersimpan")
                st.rerun()

    if st.session_state.db['p3k']:
        df_p3k = pd.DataFrame(st.session_state.db['p3k'])
        st.dataframe(df_p3k, use_container_width=True)
    else:
        st.info("Belum ada data obat.")

# --- KHUSUS ADMIN: INPUT TRANSAKSI ---
def input_transaksi():
    st.header("📝 Input Transaksi Baru")
    with st.form("form_trx"):
        nama = st.selectbox("Anggota", list(st.session_state.db['anggota'].keys()))
        nom = st.number_input("Nominal (Rp)", min_value=0, step=1000)
        ket = st.text_input("Keterangan", value="Iuran Bulanan")
        metode = st.selectbox("Metode", ["Tunai", "QRIS", "KELUAR TUNAI", "KELUAR QRIS"])
        tgl = st.date_input("Tanggal Transaksi")
        
        if st.form_submit_button("Simpan Transaksi"):
            new_trx = {
                "id": str(datetime.now().timestamp()),
                "nama": nama,
                "metode": metode,
                "tgl": tgl.strftime("%d-%m-%Y"),
                "jumlah": nom,
                "keterangan": f"{ket} - {nama}"
            }
            st.session_state.db['transaksi'].append(new_trx)
            save_data(st.session_state.db)
            st.success("Transaksi Berhasil Dicatat!")

# --- KHUSUS ADMIN: DATA ANGGOTA ---
def kelola_anggota():
    st.header("👥 Manajemen Anggota")
    with st.expander("Tambah Anggota Baru"):
        n_baru = st.text_input("Nama Lengkap")
        w_baru = st.text_input("WhatsApp (Contoh: 0812...)")
        b_masuk = st.selectbox("Bulan Gabung", [str(i).zfill(2) for i in range(1, 13)])
        t_masuk = st.selectbox("Tahun Gabung", [str(i) for i in range(2025, 2030)])
        if st.button("Tambah Anggota"):
            st.session_state.db['anggota'][n_baru] = {"wa": w_baru, "bln_masuk": b_masuk, "thn_masuk": t_masuk}
            save_data(st.session_state.db)
            st.rerun()
    
    st.write("Daftar Anggota Saat Ini:")
    st.json(st.session_state.db['anggota'])

# --- ROUTING MENU ---
if menu == "Dashboard":
    show_dashboard()
elif menu == "Ceklis Iuran":
    show_ceklis()
elif menu == "Stok P3K":
    show_p3k()
elif menu == "Input Transaksi":
    input_transaksi()
elif menu == "Data Anggota":
    kelola_anggota()
elif menu == "Riwayat Transaksi":
    st.header("📜 Riwayat Transaksi Lengkap")
    if st.session_state.db['transaksi']:
        df = pd.DataFrame(st.session_state.db['transaksi'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Tidak ada riwayat.")
