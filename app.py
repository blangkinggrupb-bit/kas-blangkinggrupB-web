import streamlit as st
import pandas as pd
import json
import os
import shutil
from datetime import datetime
import urllib.parse
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Blangking Web", layout="wide")

# --- STYLE CSS CUSTOM ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1e88e5; color: white; }
    .header-kas { text-align: center; color: #1e88e5; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI DATA ---
FILE_DATA = "data_kas_blangking_v9.json"

def load_data():
    if os.path.exists(FILE_DATA):
        with open(FILE_DATA, "r") as f:
            return json.load(f)
    return {"anggota": {}, "transaksi": [], "p3k": [], "config": {"nom_iuran": "10000"}}

def save_data(data):
    with open(FILE_DATA, "w") as f:
        json.dump(data, f)
    # Trigger backup email di sini jika perlu

# --- SESSION STATE (DB) ---
if 'db' not in st.session_state:
    st.session_state.db = load_data()

db = st.session_state.db

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 class='header-kas'>KAS BLANGKING</h1>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pw = st.text_input("Admin Password", type="password")
            if st.button("Masuk"):
                if pw == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Password Salah")
    st.stop()

# --- SIDEBAR NAVIGASI ---
menu = st.sidebar.selectbox("MENU UTAMA", ["Dashboard", "Input Transaksi", "Ceklis Iuran", "Data Anggota", "Riwayat", "Stok P3K"])

# --- LOGIKA DASHBOARD ---
if menu == "Dashboard":
    st.markdown("<h2 class='header-kas'>DASHBOARD KAS</h2>", unsafe_allow_html=True)
    
    df_tr = pd.DataFrame(db['transaksi'])
    if not df_tr.empty:
        # Hitung Saldo
        tin = df_tr[df_tr['metode'] == 'Tunai']['jumlah'].sum()
        qin = df_tr[df_tr['metode'] == 'QRIS']['jumlah'].sum()
        tout = df_tr[df_tr['metode'] == 'KELUAR TUNAI']['jumlah'].sum()
        qout = df_tr[df_tr['metode'] == 'KELUAR QRIS']['jumlah'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("SALDO TUNAI", f"Rp {tin-tout:,}")
        c2.metric("SALDO QRIS", f"Rp {qin-qout:,}")
        c3.metric("TOTAL SALDO", f"Rp {(tin+qin)-(tout+qout):,}")
        
        st.bar_chart({"Tunai": tin-tout, "QRIS": qin-qout})
    else:
        st.info("Belum ada data transaksi.")

# --- INPUT TRANSAKSI ---
elif menu == "Input Transaksi":
    st.subheader("Tambah Transaksi Baru")
    with st.form("form_transaksi"):
        col1, col2 = st.columns(2)
        nama = col1.selectbox("Nama Anggota", list(db['anggota'].keys()))
        nom = col2.number_input("Nominal (Rp)", min_value=0, step=5000)
        ket = col1.text_input("Keterangan")
        met = col2.selectbox("Metode", ["Tunai", "QRIS", "KELUAR TUNAI", "KELUAR QRIS"])
        tgl = col1.date_input("Tanggal")
        
        submit = st.form_submit_button("SIMPAN")
        wa_submit = st.form_submit_button("SIMPAN & KIRIM WA")

        if submit or wa_submit:
            new_id = str(datetime.now().timestamp())
            tgl_str = tgl.strftime("%d-%m-%Y")
            entry = {
                "id": new_id, "nama": nama, "metode": met, "tgl": tgl_str,
                "bln": tgl.strftime("%m"), "thn": tgl.strftime("%Y"),
                "jumlah": int(nom), "keterangan": f"{ket} - {nama}"
            }
            db['transaksi'].append(entry)
            save_data(db)
            st.success("Data Tersimpan!")
            
            if wa_submit:
                msg = f"*BUKTI KAS BLANGKING*\n\nTerima kasih *{nama}*.\nDana Rp{nom:,} telah kami terima ({met})\nKeperluan: {ket}\nTgl: {tgl_str}"
                wa_no = db['anggota'][nama]['wa']
                if wa_no.startswith('0'): wa_no = '62' + wa_no[1:]
                url = f"https://wa.me/{wa_no}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<meta http-equiv="refresh" content="0;URL=\'{url}\'"/>', unsafe_allow_html=True)

# --- CEKLIS IURAN ---
elif menu == "Ceklis Iuran":
    st.subheader("Tabel Ceklis Iuran")
    thn_view = st.selectbox("Pilih Tahun", [str(i) for i in range(2025, 2031)])
    
    # Logika hitung iuran (Disederhanakan untuk web)
    data_ceklis = []
    nom_iuran = int(db['config']['nom_iuran'])
    
    for nama, info in db['anggota'].items():
        # Hitung total iuran masuk untuk nama tersebut
        total_bayar = sum(t['jumlah'] for t in db['transaksi'] if t['nama'] == nama and "iuran" in t['keterangan'].lower())
        bulan_lunas = total_bayar // nom_iuran
        data_ceklis.append({"Nama": nama, "Total Bulan Lunas": bulan_lunas, "Sisa Saldo": total_bayar % nom_iuran})
    
    st.table(data_ceklis)

# --- RIWAYAT ---
elif menu == "Riwayat":
    st.subheader("Riwayat Transaksi Lengkap")
    df_hist = pd.DataFrame(db['transaksi'])
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
        if st.button("Hapus Transaksi Terakhir"):
            db['transaksi'].pop()
            save_data(db)
            st.rerun()
    else:
        st.write("Belum ada riwayat.")

# --- DATA ANGGOTA ---
elif menu == "Data Anggota":
    st.subheader("Manajemen Anggota")
    with st.expander("Tambah Anggota Baru"):
        n_m = st.text_input("Nama Lengkap")
        w_m = st.text_input("No WhatsApp (Contoh: 0812...)")
        if st.button("Simpan Anggota"):
            db['anggota'][n_m] = {"wa": w_m, "bln_masuk": "01", "thn_masuk": "2025"}
            save_data(db)
            st.rerun()
    
    st.write("Daftar Anggota Saat Ini:")
    st.json(db['anggota'])

# --- FOOTER ---
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()
