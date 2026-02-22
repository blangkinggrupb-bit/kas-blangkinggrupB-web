import streamlit as st
import pandas as pd
import json
import os
import urllib.parse
from datetime import datetime
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Blangking v9 Pro", layout="wide")

# --- DATABASE SEDERHANA (JSON) ---
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

# Inisialisasi Data ke Session State
if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- FUNGSI PEMBANTU ---
def format_wa(wa):
    wa_str = str(wa).strip()
    if wa_str.startswith('0'):
        return '62' + wa_str[1:]
    return wa_str

# --- SISTEM LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None

def login():
    st.markdown("<h1 style='text-align: center; color: #3399FF;'>KAS BLANGKING V9</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Silakan pilih akses untuk masuk</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_type = st.radio("Masuk Sebagai:", ["User (Lihat Data)", "Admin (Kelola)"])
        password = st.text_input("Password", type="password")
        
        if st.button("MASUK SEKARANG", use_container_width=True):
            if user_type == "Admin (Kelola)" and password == "1234":
                st.session_state.authenticated = True
                st.session_state.role = "admin"
                st.rerun()
            elif user_type == "User (Lihat Data)" and password == "user123":
                st.session_state.authenticated = True
                st.session_state.role = "user"
                st.rerun()
            else:
                st.error("❌ Password Salah!")

if not st.session_state.authenticated:
    login()
    st.stop()

# --- SIDEBAR NAVIGASI ---
role = st.session_state.role
st.sidebar.markdown(f"### 🛡️ Akses: {role.upper()}")

if role == "admin":
    menu = st.sidebar.radio("NAVIGASI MENU", 
        ["📊 Dashboard", "📝 Input Transaksi", "✅ Ceklis Iuran", "💊 Stok P3K", "👥 Data Anggota", "📜 Riwayat Transaksi"])
else:
    menu = st.sidebar.radio("NAVIGASI MENU", 
        ["📊 Dashboard", "✅ Ceklis Iuran", "💊 Stok P3K"])

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Visualisasi Saldo Kas")
    df_tr = pd.DataFrame(st.session_state.db['transaksi'])
    
    if not df_tr.empty:
        # Hitung Saldo
        tin = df_tr[df_tr['metode'] == "Tunai"]['jumlah'].sum()
        qin = df_tr[df_tr['metode'] == "QRIS"]['jumlah'].sum()
        tout = df_tr[df_tr['metode'] == "KELUAR TUNAI"]['jumlah'].sum()
        qout = df_tr[df_tr['metode'] == "KELUAR QRIS"]['jumlah'].sum()
        
        s_tunai = tin - tout
        s_qris = qin - qout

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Saldo Tunai", f"Rp {s_tunai:,}")
        c2.metric("📱 Saldo QRIS", f"Rp {s_qris:,}")
        c3.metric("🏦 Total Gabungan", f"Rp {s_tunai + s_qris:,}")

        fig = px.bar(
            x=["Tunai", "QRIS"], 
            y=[s_tunai, s_qris],
            color=["Tunai", "QRIS"],
            labels={'x': 'Metode', 'y': 'Saldo (Rp)'},
            color_discrete_map={"Tunai": "#3399FF", "QRIS": "#00B050"},
            title="Perbandingan Saldo Kas"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data transaksi untuk dihitung.")

# --- 2. INPUT TRANSAKSI (ADMIN ONLY) ---
elif menu == "📝 Input Transaksi":
    st.header("📝 Catat Transaksi Baru")
    with st.form("form_trx"):
        col_f1, col_f2 = st.columns(2)
        nama = col_f1.selectbox("Pilih Anggota", sorted(list(st.session_state.db['anggota'].keys())))
        nom = col_f2.number_input("Nominal (Rp)", min_value=0, step=1000)
        
        col_f3, col_f4 = st.columns(2)
        ket = col_f3.selectbox("Keterangan", ["Iuran Januari", "Iuran Februari", "Iuran Maret", "Iuran April", "Iuran Mei", "Iuran Juni", "Iuran Juli", "Iuran Agustus", "Iuran September", "Iuran Oktober", "Iuran November", "Iuran Desember", "Sumbangan Keluarga Sakit", "Keluarga Meninggal", "Lainnya"])
        metode = col_f4.selectbox("Metode Pembayaran", ["Tunai", "QRIS", "KELUAR TUNAI", "KELUAR QRIS"])
        
        tgl = st.date_input("Tanggal Transaksi", datetime.now())
        
        submit = st.form_submit_button("SIMPAN TRANSAKSI")
        if submit:
            new_trx = {
                "id": str(datetime.now().timestamp()),
                "nama": nama,
                "metode": metode,
                "tgl": tgl.strftime("%d-%m-%Y"),
                "jumlah": int(nom),
                "keterangan": f"{ket} - {nama}"
            }
            st.session_state.db['transaksi'].append(new_trx)
            save_data(st.session_state.db)
            st.success(f"✅ Berhasil mencatat {ket} untuk {nama}")

# --- 3. CEKLIS IURAN ---
elif menu == "✅ Ceklis Iuran":
    st.header("✅ Tabel Ceklis Iuran")
    thn_pilih = st.selectbox("Pilih Tahun Pantauan", range(2025, 2031))
    
    pt = {}
    nd = int(st.session_state.db['config'].get("nom_iuran", 10000))
    for tr in st.session_state.db['transaksi']:
        if "iuran" in tr['keterangan'].lower() and "KELUAR" not in tr['metode']:
            pt[tr['nama']] = pt.get(tr['nama'], 0) + (tr['jumlah'] // nd)

    data_tabel = []
    bulan_list = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]
    
    for nama, info in sorted(st.session_state.db['anggota'].items()):
        row = {"Nama Anggota": nama}
        tot_bayar = pt.get(nama, 0)
        bm, tm = int(info.get("bln_masuk", 1)), int(info.get("thn_masuk", 2025))
        
        for m_idx, m_name in enumerate(bulan_list, 1):
            iv = ((thn_pilih - 2025) * 12) + (m_idx - 1)
            ig = ((tm - 2025) * 12) + (bm - 1)
            
            if iv < ig: row[m_name] = "N/A"
            elif tot_bayar > (iv - ig): row[m_name] = "LUNAS"
            else: row[m_name] = "BELUM"
        data_tabel.append(row)
    
    df_cek = pd.DataFrame(data_tabel)

    def color_status(val):
        if val == "LUNAS": color = '#d4edda'; txt = '#155724'
        elif val == "BELUM": color = '#f8d7da'; txt = '#721c24'
        else: color = '#e2e3e5'; txt = '#383d41'
        return f'background-color: {color}; color: {txt}; font-weight: bold; text-align: center'

    st.dataframe(df_cek.style.applymap(color_status, subset=bulan_list), use_container_width=True, height=500)

# --- 4. STOK P3K ---
elif menu == "💊 Stok P3K":
    st.header("💊 Manajemen Stok Obat")
    
    if role == "admin":
        with st.expander("➕ Tambah/Update Stok Obat"):
            with st.form("p3k_form"):
                c1, c2, c3 = st.columns(3)
                n_obat = c1.text_input("Nama Obat")
                j_obat = c2.selectbox("Jenis", ["Pil", "Kapsul", "Cair", "Tablet", "Salep"])
                e_obat = c3.text_input("Exp Date (Bulan/Tahun)")
                c4, c5 = st.columns(2)
                stok_in = c4.number_input("Stok Masuk", min_value=0)
                stok_out = c5.number_input("Stok Keluar", min_value=0)
                if st.form_submit_button("SIMPAN DATA OBAT"):
                    st.session_state.db['p3k'].append({
                        "id": str(datetime.now().timestamp()), "tgl": datetime.now().strftime("%d-%m-%Y"),
                        "nama": n_obat, "jenis": j_obat, "in": int(stok_in), "out": int(stok_out), "exp": e_obat
                    })
                    save_data(st.session_state.db)
                    st.rerun()

    if st.session_state.db['p3k']:
        df_p3k = pd.DataFrame(st.session_state.db['p3k'])
        # Hitung Stok Akhir per Obat
        df_sum = df_p3k.groupby('nama').agg({'in': 'sum', 'out': 'sum'}).reset_index()
        df_sum['Stok Akhir'] = df_sum['in'] - df_sum['out']
        
        st.subheader("📦 Sisa Stok Saat Ini")
        st.table(df_sum[['nama', 'Stok Akhir']])
        
        st.subheader("📜 Detail Mutasi Obat")
        st.dataframe(df_p3k[['tgl', 'nama', 'jenis', 'in', 'out', 'exp']], use_container_width=True)
    else:
        st.info("Data obat masih kosong.")

# --- 5. DATA ANGGOTA ---
elif menu == "👥 Data Anggota":
    st.header("👥 Daftar Anggota Grup")
    
    if role == "admin":
        with st.expander("➕ Tambah Anggota Baru"):
            with st.form("agt_form"):
                nama_b = st.text_input("Nama Lengkap")
                wa_b = st.text_input("No WhatsApp (Contoh: 0812345678)")
                c1, c2 = st.columns(2)
                b_m = c1.selectbox("Bulan Gabung", [str(i).zfill(2) for i in range(1, 13)])
                t_m = c2.selectbox("Tahun Gabung", [str(i) for i in range(2025, 2030)])
                if st.form_submit_button("TAMBAHKAN"):
                    st.session_state.db['anggota'][nama_b] = {"wa": wa_b, "bln_masuk": b_m, "thn_masuk": t_m}
                    save_data(st.session_state.db)
                    st.success(f"Anggota {nama_b} berhasil didaftarkan.")
                    st.rerun()

    st.markdown("---")
    for nama, info in sorted(st.session_state.db['anggota'].items()):
        with st.container():
            col_n, col_w, col_btn = st.columns([3, 2, 2])
            col_n.markdown(f"**👤 {nama}**")
            col_w.text(f"📞 {info.get('wa', '-')}")
            
            # Tombol WhatsApp
            wa_link = f"https://wa.me/{format_wa(info.get('wa',''))}?text=Assalamu’alaikum%20Bapak/Ibu%20{nama}"
            col_btn.markdown(f"[![WA](https://img.shields.io/badge/Chat-WhatsApp-25D366?style=flat&logo=whatsapp)]({wa_link})")
            
            if role == "admin":
                if col_btn.button("🗑️ Hapus", key=f"del_{nama}"):
                    del st.session_state.db['anggota'][nama]
                    save_data(st.session_state.db)
                    st.rerun()
            st.markdown("<hr style='margin:0; border-color:#f0f2f6;'>", unsafe_allow_html=True)

# --- 6. RIWAYAT TRANSAKSI (ADMIN ONLY) ---
elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Semua Riwayat Transaksi")
    if st.session_state.db['transaksi']:
        df_h = pd.DataFrame(st.session_state.db['transaksi'])
        # Sortir terbaru di atas
        df_h = df_h.sort_values(by='id', ascending=False)
        st.dataframe(df_h[['tgl', 'nama', 'jumlah', 'metode', 'keterangan']], use_container_width=True)
        
        if st.button("🗑️ Kosongkan Semua Data (Hati-hati!)"):
            if st.checkbox("Saya yakin ingin menghapus semua riwayat"):
                st.session_state.db['transaksi'] = []
                save_data(st.session_state.db)
                st.rerun()
    else:
        st.info("Belum ada riwayat transaksi.")
