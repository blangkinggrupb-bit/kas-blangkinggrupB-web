import streamlit as st
import pandas as pd
import json
import os
import urllib.parse
from datetime import datetime
import plotly.express as px

# --- 1. CONFIG & FULL BLUE THEME ---
st.set_page_config(page_title="KAS BLANGKING V9", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, h4, p, label { color: #01579B !important; }
    [data-testid="stSidebar"] { background-color: #E3F2FD !important; }
    .stButton>button {
        background-color: #03A9F4 !important;
        color: white !important;
        border-radius: 15px !important;
        font-weight: bold !important;
    }
    .stMetric {
        background-color: #E1F5FE !important;
        border-radius: 10px !important;
        padding: 10px !important;
        border-left: 5px solid #03A9F4 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
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

# --- 3. FUNGSI WHATSAPP ---
def kirim_wa(nomor, pesan):
    clean_no = str(nomor).replace(" ", "").replace("+", "").replace("-", "")
    if clean_no.startswith("0"): clean_no = "62" + clean_no[1:]
    pesan_url = urllib.parse.quote(pesan)
    return f"https://api.whatsapp.com/send?phone={clean_no}&text={pesan_url}"

# --- 4. LOGIN SYSTEM ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🏦 KAS BLANGKING V9</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        pilihan = st.radio("Akses:", ["User", "Admin"])
        pwd = st.text_input("Password", type="password")
        if st.button("MASUK"):
            if pilihan == "Admin" and pwd == "1234":
                st.session_state.auth, st.session_state.role = True, "admin"
                st.rerun()
            elif pilihan == "User" and pwd == "user123":
                st.session_state.auth, st.session_state.role = True, "user"
                st.rerun()
            else: st.error("Sandi Salah!")
    st.stop()

# --- 5. LOGIKA STATUS (BERDASARKAN TGL GABUNG) ---
nom_iuran = st.session_state.db['config'].get('nom_iuran', 10000)
status_summary = {}

for nama, info in st.session_state.db['anggota'].items():
    total_bayar = sum(t['jumlah'] for t in st.session_state.db['transaksi'] if t.get('nama') == nama and "iuran" in t.get('keterangan','').lower())
    
    # Hitung kewajiban dari bulan gabung
    bln_m = int(info.get('bln_masuk', 1))
    thn_m = int(info.get('thn_masuk', 2025))
    tgl_skrg = datetime.now()
    total_bln_wajib = (tgl_skrg.year - thn_m) * 12 + tgl_skrg.month - bln_m + 1
    
    bln_lunas = total_bayar // nom_iuran
    selisih = bln_lunas - total_bln_wajib
    
    status_summary[nama] = {
        "wa": info.get('wa', ''),
        "selisih": selisih,
        "total_rp": total_bayar,
        "tunggakan_rp": abs(selisih * nom_iuran) if selisih < 0 else 0
    }

# --- 6. MENU SIDEBAR ---
with st.sidebar:
    st.title("💠 MENU")
    menu = st.radio("Pilih:", ["Dashboard", "Ceklis & Input", "Broadcast WA", "P3K", "Data Anggota"])
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 7. DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Dashboard Kas")
    df = pd.DataFrame(st.session_state.db['transaksi'])
    if not df.empty:
        c1, c2 = st.columns(2)
        masuk = df[df['metode'].isin(['Tunai', 'QRIS'])]['jumlah'].sum()
        keluar = df[df['metode'].str.contains('KELUAR', na=False)]['jumlah'].sum()
        c1.metric("Total Saldo", f"Rp {masuk-keluar:,}")
        fig = px.pie(names=['Masuk', 'Keluar'], values=[masuk, keluar], color_discrete_sequence=['#03A9F4', '#F44336'])
        st.plotly_chart(fig)

# --- 8. CEKLIS & INPUT ---
elif menu == "Ceklis & Input":
    st.header("✅ Ceklis Iuran")
    if st.session_state.role == "admin":
        with st.expander("➕ Input Bayar"):
            with st.form("f_bayar"):
                nama_p = st.selectbox("Nama", list(st.session_state.db['anggota'].keys()))
                nominal_p = st.number_input("Nominal", value=nom_iuran)
                metode_p = st.selectbox("Metode", ["Tunai", "QRIS"])
                ket_p = st.text_input("Keperluan", "Iuran Kas")
                if st.form_submit_button("Simpan & Bukti WA"):
                    ref = datetime.now().strftime("%Y%m%d%H%M")
                    tgl_s = datetime.now().strftime("%d-%m-%Y")
                    st.session_state.db['transaksi'].append({"id":ref, "nama":nama_p, "jumlah":int(nominal_p), "metode":metode_p, "tgl":tgl_s, "keterangan":ket_p})
                    save_data(st.session_state.db)
                    
                    # PESAN BUKTI PEMBAYARAN
                    pesan = f"*BUKTI PEMBAYARAN KAS RESMI* ✨\n\nAssalamu’alaikum Bapak/Ibu *{nama_p}*.\n\nAlhamdulillah, telah kami terima dana iuran Anda dengan rincian sebagai berikut:\n\n━━━━━━━━━━━━━━━━━━\n📝 *KETERANGAN PEMBAYARAN*\n━━━━━━━━━━━━━━━━━━\n📅 Tanggal: {tgl_s}\n💳 Metode: *{metode_p}*\n💰 Nominal: *Rp{int(nominal_p):,}*\n📌 Keperluan: {ket_p}\n🆔 Ref ID: {ref}\n\n✅ Status: *TERVERIFIKASI & MASUK KAS*\n━━━━━━━━━━━━━━━━━━\n\nJazakumullah Khairan Katsiran. Semoga sedekah iuran ini menjadi wasilah pembersih harta, pembuka pintu rezeki, dan pemberi keberkahan bagi keluarga Bapak/Ibu di dunia maupun akhirat. Amin ya Rabbal 'Alamin. 🤲 🕋\n\nSalam takzim,\n*Bendahara Kas Blangking*"
                    st.markdown(f'<a href="{kirim_wa(st.session_state.db["anggota"][nama_p]["wa"], pesan)}" target="_blank">KLIK KIRIM BUKTI WA</a>', unsafe_allow_html=True)

    # Tabel Tampilan
    data_tabel = []
    for n, s in status_summary.items():
        st_text = "LUNAS" if s['selisih'] >= 0 else f"TUNGGAK {abs(s['selisih'])} BLN"
        data_tabel.append({"Nama": n, "Total Bayar": f"Rp {s['total_rp']:,}", "Status": st_text})
    st.table(pd.DataFrame(data_tabel))

# --- 9. BROADCAST WA ---
elif menu == "Broadcast WA":
    if st.session_state.role != "admin": st.warning("Khusus Admin")
    else:
        st.header("📢 Panel Broadcast")
        tipe = st.selectbox("Pilih Pesan:", ["Pengingat Besok", "Status Lunas", "Status Lebih Bayar", "Status Tunggakan"])
        
        for n, s in status_summary.items():
            pesan = ""
            if tipe == "Pengingat Besok":
                pesan = f"Assalamu’alaikum Bapak/Ibu *{n}*. ✨\n\nSemoga cahaya keberkahan senantiasa menyertai keluarga. Menjelang hari esok, izin mengingatkan jadwal iuran kas rutin kita sebesar *Rp{nom_iuran:,}*.\n\nPembayaran bisa melalui *Tunai* atau *Scan QRIS*.\n\nSemoga setiap rupiahnya menjadi wasilah pembersih harta dan pengetuk pintu langit. Amin. 🤲✨"
            elif tipe == "Status Lunas" and s['selisih'] == 0:
                pesan = f"Assalamu’alaikum Bapak/Ibu *{n}*. ✨\n\nAlhamdulillah, administrasi kas Anda saat ini dalam status *LUNAS*.\n\nTerima kasih atas kerja samanya dalam menjaga amanah grup ini. Semoga Allah senantiasa melimpahkan rezeki dan berkah-Nya. Syukron jazilan. 🙏🤲"
            elif tipe == "Status Lebih Bayar" and s['selisih'] > 0:
                pesan = f"Masya Allah, Tabarakallah Bapak/Ibu *{n}*. 🌟\n\nJazakumullah khairan katsiran atas kedisiplinannya. Status kas Anda saat ini *LUNAS* (Bahkan ada lebih bayar *{s['selisih']} bulan*).\n\nSemoga Allah menggantinya dengan kesehatan, kebahagiaan, dan keberkahan yang berlipat ganda untuk keluarga. Amin. 🤲🕋"
            elif tipe == "Status Tunggakan" and s['selisih'] < 0:
                pesan = f"Assalamu’alaikum Bapak/Ibu *{n}*. 🌸\n\nMohon izin menyampaikan amanah catatan kas yang masih tertunda selama *{abs(s['selisih'])} bulan* (Total *Rp{s['tunggakan_rp']:,}*).\n\nKami mendoakan semoga Allah membukakan pintu rezeki dari arah yang tak disangka-sangka agar Bapak/Ibu dapat menunaikannya via *Tunai/QRIS*.\n\nJazakumullah khairan atas perhatiannya. 😊🙏"
            
            if pesan:
                c1, c2 = st.columns([3,1])
                c1.write(f"📲 {n}")
                c2.markdown(f'[Kirim WA]({kirim_wa(s["wa"], pesan)})')

# --- 10. P3K ---
elif menu == "P3K":
    st.header("💊 Inventaris P3K")
    if st.session_state.role == "admin":
        with st.form("f_p3k"):
            n_o = st.text_input("Nama Obat")
            j_o = st.number_input("Stok", min_value=0)
            if st.form_submit_button("Tambah"):
                st.session_state.db['p3k'].append({"Barang": n_o, "Stok": j_o})
                save_data(st.session_state.db)
                st.rerun()
    if st.session_state.db['p3k']: st.table(pd.DataFrame(st.session_state.db['p3k']))

# --- 11. DATA ANGGOTA ---
elif menu == "Data Anggota":
    st.header("👥 Manajemen Anggota")
    if st.session_state.role == "admin":
        with st.expander("➕ Tambah Anggota (Dengan Tanggal Gabung)"):
            with st.form("f_add"):
                n_b = st.text_input("Nama")
                w_b = st.text_input("WA (628...)")
                col1, col2 = st.columns(2)
                bln_b = col1.selectbox("Bulan Gabung", range(1,13), index=0)
                thn_b = col2.selectbox("Tahun Gabung", [2024, 2025, 2026], index=1)
                if st.form_submit_button("Simpan"):
                    st.session_state.db['anggota'][n_b] = {"wa":w_b, "bln_masuk":bln_b, "thn_masuk":thn_b}
                    save_data(st.session_state.db)
                    st.rerun()
    
    st.write("### Daftar Anggota")
    for n, i in st.session_state.db['anggota'].items():
        st.write(f"🔹 {n} (Gabung: {i['bln_masuk']}-{i['thn_masuk']})")
