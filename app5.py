import streamlit as st
import pandas as pd
import json
import os
import urllib.parse
from datetime import datetime

# --- 1. SETTING DASAR ---
st.set_page_config(page_title="KAS BLANGKING", layout="wide")

# CSS UNTUK TAMPILAN (Memaksa teks terlihat jelas)
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3, p, label { color: #000000 !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .status-box { padding: 10px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

FILE_DATA = "data_kas_blangking_v9.json"

def load_data():
    if os.path.exists(FILE_DATA):
        try:
            with open(FILE_DATA, "r") as f: return json.load(f)
        except: pass
    return {"anggota": {}, "transaksi": [], "p3k": [], "config": {"nom_iuran": 10000}}

def save_data(data):
    with open(FILE_DATA, "w") as f: json.dump(data, f, indent=4)

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# --- 2. SISTEM LOGIN (DIBUAT SANGAT JELAS) ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🏦 LOGIN KAS BLANGKING</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("### Pilih Akses Anda:")
        pilihan = st.radio("SANGAT PENTING: Pilih salah satu", ["USER (Lihat Data)", "ADMIN (Input Data)"])
        pwd = st.text_input("Masukkan Password", type="password")
        
        if st.button("MASUK SEKARANG"):
            if "ADMIN" in pilihan and pwd == "1234":
                st.session_state.auth, st.session_state.role = True, "admin"
                st.rerun()
            elif "USER" in pilihan and pwd == "user123":
                st.session_state.auth, st.session_state.role = True, "user"
                st.rerun()
            else:
                st.error("❌ Password Salah atau Pilihan Salah!")
    st.stop()

# --- 3. LOGIKA HITUNGAN (SEDERHANA - ANTI ERROR) ---
def get_status_summary():
    summary = {}
    nom = st.session_state.db['config'].get('nom_iuran', 10000)
    for nama, info in st.session_state.db['anggota'].items():
        # Hitung total bayar iuran saja
        total = sum(t['jumlah'] for t in st.session_state.db['transaksi'] if t.get('nama') == nama and "iuran" in t.get('keterangan','').lower())
        
        # Hitung kewajiban (Sederhana: dari Jan 2025 sampai sekarang)
        skrg = datetime.now()
        mulai = datetime(2025, 1, 1)
        wajib_bln = (skrg.year - mulai.year) * 12 + skrg.month - mulai.month + 1
        
        bayar_bln = total // nom
        selisih = bayar_bln - wajib_bln
        
        summary[nama] = {
            "wa": info.get('wa', ''),
            "selisih": selisih,
            "total_rp": total,
            "tunggakan_rp": abs(selisih * nom) if selisih < 0 else 0
        }
    return summary

# --- 4. SIDEBAR MENU ---
with st.sidebar:
    st.write(f"Selamat Datang, **{st.session_state.role.upper()}**")
    menu = st.radio("Navigasi", ["Dashboard", "Ceklis & Input", "Broadcast WA", "Manajemen Anggota"])
    if st.button("Keluar/Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 5. FITUR: DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Dashboard")
    df = pd.DataFrame(st.session_state.db['transaksi'])
    if not df.empty:
        total_masuk = df[df['metode'].isin(['Tunai', 'QRIS'])]['jumlah'].sum()
        total_keluar = df[df['metode'].str.contains('KELUAR', na=False)]['jumlah'].sum()
        st.metric("Saldo Kas Bersih", f"Rp {total_masuk - total_keluar:,}")
    else:
        st.write("Belum ada data transaksi.")

# --- 6. FITUR: CEKLIS & INPUT ---
elif menu == "Ceklis & Input":
    st.title("✅ Ceklis & Input")
    
    if st.session_state.role == "admin":
        with st.expander("➕ INPUT PEMBAYARAN BARU", expanded=True):
            with st.form("form_bayar"):
                n_p = st.selectbox("Pilih Anggota", list(st.session_state.db['anggota'].keys()))
                j_p = st.number_input("Nominal", value=10000)
                m_p = st.selectbox("Metode", ["Tunai", "QRIS"])
                k_p = st.text_input("Keterangan", "Iuran Kas")
                if st.form_submit_button("SIMPAN"):
                    ref = datetime.now().strftime("%Y%m%d%H%M")
                    st.session_state.db['transaksi'].append({
                        "id": ref, "nama": n_p, "jumlah": int(j_p), "metode": m_p, 
                        "tgl": datetime.now().strftime("%d-%m-%Y"), "keterangan": k_p
                    })
                    save_data(st.session_state.db)
                    st.success("Tersimpan!")
                    st.rerun()

    st.write("### Data Iuran Anggota")
    stat = get_status_summary()
    for n, s in stat.items():
        color = "green" if s['selisih'] >= 0 else "red"
        st.markdown(f"""<div class='status-box'>
            <b>{n}</b><br>
            Status: <span style='color:{color}'>{'LUNAS' if s['selisih'] >= 0 else 'MENUNGGAK'}</span><br>
            Total Bayar: Rp {s['total_rp']:,}
            </div>""", unsafe_allow_html=True)

# --- 7. FITUR: BROADCAST ---
elif menu == "Broadcast WA":
    if st.session_state.role != "admin":
        st.warning("Hanya untuk Admin")
    else:
        st.title("📢 Kirim Pesan WA")
        stat = get_status_summary()
        
        tipe = st.selectbox("Jenis Pesan", ["Kwitansi Terakhir", "Pengingat Iuran", "Tunggakan"])
        
        for n, s in stat.items():
            pesan = ""
            if tipe == "Kwitansi Terakhir":
                pesan = f"Terima Kasih Bapak/Ibu {n}, iuran telah kami terima. Status: LUNAS."
            elif tipe == "Pengingat Iuran":
                pesan = f"Assalamu’alaikum {n}, jangan lupa iuran kas rutin Rp10.000 ya."
            elif tipe == "Tunggakan" and s['selisih'] < 0:
                pesan = f"Mohon maaf {n}, ada tunggakan kas sebesar Rp{s['tunggakan_rp']:,}. Mohon segera dilunasi."
            
            if pesan:
                c1, c2 = st.columns([3,1])
                c1.write(f"Kirim ke: **{n}**")
                url = f"https://wa.me/{s['wa']}?text={urllib.parse.quote(pesan)}"
                c2.markdown(f"[KIRIM WA]({url})")

# --- 8. MANAJEMEN ANGGOTA ---
elif menu == "Manajemen Anggota":
    st.title("👥 Anggota")
    if st.session_state.role == "admin":
        with st.form("tambah_agt"):
            nama_b = st.text_input("Nama")
            wa_b = st.text_input("WhatsApp (Awali 62)")
            if st.form_submit_button("Tambah Anggota"):
                st.session_state.db['anggota'][nama_b] = {"wa": wa_b, "bln_masuk": "01", "thn_masuk": "2025"}
                save_data(st.session_state.db)
                st.rerun()
    
    for n in list(st.session_state.db['anggota'].keys()):
        st.write(f"👤 {n}")
