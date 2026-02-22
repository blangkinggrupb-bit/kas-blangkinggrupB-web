import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import urllib.parse
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Blangking Web", layout="wide")

# --- DATABASE LOGIC ---
FILE_DATA = "data_kas_blangking_v9.json"

def load_data():
    if os.path.exists(FILE_DATA):
        try:
            with open(FILE_DATA, "r") as f:
                return json.load(f)
        except:
            pass
    return {"anggota": {}, "transaksi": [], "p3k": [], "config": {"nom_iuran": "10000"}}

def save_data(data):
    with open(FILE_DATA, "w") as f:
        json.dump(data, f)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

# --- SESSION STATE UNTUK LOGIN ---
if 'role' not in st.session_state:
    st.session_state.role = None

# --- FUNGSI LOGIN ---
def login_ui():
    st.title("🔐 Akses Kas Blangking")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Admin Login")
        pw = st.text_input("Masukkan Password Admin", type="password")
        if st.button("Masuk sebagai Admin"):
            if pw == "1234":
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Password Admin Salah")
                
    with col2:
        st.subheader("User Access")
        st.write("Akses terbatas untuk melihat laporan saja.")
        if st.button("Masuk sebagai User (View Only)"):
            st.session_state.role = "user"
            st.rerun()

if st.session_state.role is None:
    login_ui()
    st.stop()

# --- HITUNG SALDO (GLOBAL) ---
st_in = sum(t['jumlah'] for t in data['transaksi'] if t['metode'] == "Tunai")
sq_in = sum(t['jumlah'] for t in data['transaksi'] if t['metode'] == "QRIS")
st_out = sum(t['jumlah'] for t in data['transaksi'] if t['metode'] == "KELUAR TUNAI")
sq_out = sum(t['jumlah'] for t in data['transaksi'] if t['metode'] == "KELUAR QRIS")
saldo_tunai = st_in - st_out
saldo_qris = sq_in - sq_out
total_saldo = saldo_tunai + saldo_qris

# --- SIDEBAR ---
st.sidebar.title(f"👤 Role: {st.session_state.role.upper()}")
st.sidebar.metric("Total Saldo", f"Rp {total_saldo:,}")
st.sidebar.write(f"Tunai: Rp {saldo_tunai:,}")
st.sidebar.write(f"QRIS: Rp {saldo_qris:,}")
if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

# --- MAIN APP ---
st.title("🟦 KAS BLANGKING GRUP B")

# Definisi Tab berdasarkan Role
if st.session_state.role == "admin":
    tabs = st.tabs(["📝 Input Transaksi", "✅ Ceklis Iuran", "📊 Riwayat & Grafik", "💊 P3K", "👥 Anggota"])
else:
    tabs = st.tabs(["✅ Ceklis Iuran", "📊 Riwayat & Grafik", "💊 P3K"])

# --- TAB CEKLIS IURAN (Akses: Admin & User) ---
idx_tab_ceklis = 1 if st.session_state.role == "admin" else 0
with tabs[idx_tab_ceklis]:
    st.subheader("📋 Status Iuran Anggota")
    thn_view = st.selectbox("Tahun", [str(i) for i in range(2025, 2030)])
    nom_iuran = int(data['config'].get("nom_iuran", 10000))
    
    pembayaran_iuran = {}
    for tr in data['transaksi']:
        if "iuran" in tr['keterangan'].lower() and "KELUAR" not in tr['metode']:
            pembayaran_iuran[tr['nama']] = pembayaran_iuran.get(tr['nama'], 0) + (tr['jumlah'] // nom_iuran)

    rows = []
    now = datetime.now()
    idx_now = ((now.year - 2025) * 12) + (now.month - 1)
    
    for nama in sorted(data['anggota'].keys()):
        detail = data['anggota'][nama]
        idx_gabung = ((int(detail.get("thn_masuk", 2025)) - 2025) * 12) + (int(detail.get("bln_masuk", 1)) - 1)
        total_bayar = pembayaran_iuran.get(nama, 0)
        
        row = {"Nama": nama}
        for m_idx, m_name in enumerate(["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"]):
            idx_cek = ((int(thn_view) - 2025) * 12) + m_idx
            if idx_cek < idx_gabung: row[m_name] = "⚪"
            elif total_bayar > (idx_cek - idx_gabung): row[m_name] = "✅"
            else: row[m_name] = "❌"
        
        wajib = max(0, (idx_now - idx_gabung) + 1)
        tunggakan = wajib - total_bayar
        row["Tunggakan"] = f"Rp {tunggakan * nom_iuran:,}" if tunggakan > 0 else "LUNAS"
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# --- TAB RIWAYAT & GRAFIK (Akses: Admin & User) ---
idx_tab_hist = 2 if st.session_state.role == "admin" else 1
with tabs[idx_tab_hist]:
    st.subheader("📈 Grafik Saldo")
    fig = go.Figure(data=[
        go.Bar(name='Tunai', x=['Saldo'], y=[saldo_tunai], marker_color='#1E90FF'),
        go.Bar(name='QRIS', x=['Saldo'], y=[saldo_qris], marker_color='#32CD32')
    ])
    fig.update_layout(barmode='group', height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📜 Riwayat Transaksi")
    if data['transaksi']:
        df_hist = pd.DataFrame(data['transaksi']).sort_index(ascending=False)
        st.dataframe(df_hist[['tgl', 'nama', 'jumlah', 'metode', 'keterangan']], use_container_width=True)

# --- TAB P3K (Akses: Admin & User) ---
idx_tab_p3k = 3 if st.session_state.role == "admin" else 2
with tabs[idx_tab_p3k]:
    st.subheader("💊 Stok Obat P3K")
    if st.session_state.role == "admin":
        with st.expander("Update Stok P3K"):
            p_nama = st.text_input("Nama Obat")
            p_stok = st.number_input("Jumlah Stok", min_value=0)
            if st.button("Simpan Obat"):
                data['p3k'].append({"nama": p_nama, "stok": p_stok, "tgl": datetime.now().strftime("%d-%m-%Y")})
                save_data(data); st.rerun()
    
    if data['p3k']:
        st.table(data['p3k'])

# --- KHUSUS TAB ADMIN: INPUT TRANSAKSI & ANGGOTA ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.subheader("📥 Input Transaksi")
        c1, c2 = st.columns(2)
        with c1:
            n_in = st.selectbox("Pilih Anggota", sorted(data['anggota'].keys()))
            m_in = st.selectbox("Metode", ["Tunai", "QRIS", "KELUAR TUNAI", "KELUAR QRIS"])
        with c2:
            nom_in = st.number_input("Nominal", min_value=0, step=5000)
            ket_in = st.text_input("Keterangan")
        
        if st.button("Simpan Transaksi"):
            data['transaksi'].append({
                "id": str(datetime.now().timestamp()), "nama": n_in, "metode": m_in,
                "tgl": datetime.now().strftime("%d-%m-%Y"), "jumlah": int(nom_in), "keterangan": ket_in
            })
            save_data(data); st.success("Tersimpan!"); st.rerun()

    with tabs[4]:
        st.subheader("👥 Manajemen Anggota")
        with st.expander("Tambah Anggota Baru"):
            n_agt = st.text_input("Nama Anggota")
            w_agt = st.text_input("WhatsApp (628...)")
            if st.button("Simpan Anggota"):
                data['anggota'][n_agt] = {"wa": w_agt, "bln_masuk": datetime.now().strftime("%m"), "thn_masuk": "2025"}
                save_data(data); st.rerun()
        st.write(data['anggota'])
