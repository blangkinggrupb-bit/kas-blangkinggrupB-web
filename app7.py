import streamlit as st
import pandas as pd
import json
import os
import urllib.parse
from datetime import datetime
import plotly.express as px

# --- 1. CONFIG & THEME BIRU CERAH ---
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
        width: 100%;
    }
    .stMetric {
        background-color: #E1F5FE !important;
        border-radius: 10px !important;
        padding: 10px !important;
        border-left: 5px solid #03A9F4 !important;
    }
    /* Memperjelas Tabel */
    .styled-table { width:100%; border-collapse: collapse; margin: 25px 0; font-size: 0.9em; min-width: 400px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE LOGIC ---
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
        pilihan = st.radio("Akses Sebagai:", ["User", "Admin"])
        pwd = st.text_input("Password", type="password")
        if st.button("MASUK"):
            if pilihan == "Admin" and pwd == "1234":
                st.session_state.auth, st.session_state.role = True, "admin"
                st.rerun()
            elif pilihan == "User" and pwd == "user123":
                st.session_state.auth, st.session_state.role = True, "user"
                st.rerun()
            else: st.error("❌ Password Salah!")
    st.stop()

# --- 5. LOGIKA STATUS ANGGOTA ---
nom_iuran = st.session_state.db['config'].get('nom_iuran', 10000)
status_summary = {}

if st.session_state.db['anggota']:
    for nama, info in st.session_state.db['anggota'].items():
        total_bayar = sum(t['jumlah'] for t in st.session_state.db['transaksi'] if t.get('nama') == nama and "iuran" in t.get('keterangan','').lower())
        
        # Ambil bulan & tahun gabung (default Jan 2025 jika tidak ada)
        bln_m = int(info.get('bln_masuk', 1))
        thn_m = int(info.get('thn_masuk', 2025))
        tgl_skrg = datetime.now()
        
        # Hitung berapa bulan kewajiban sejak gabung sampai sekarang
        total_bln_wajib = (tgl_skrg.year - thn_m) * 12 + tgl_skrg.month - bln_m + 1
        if total_bln_wajib < 1: total_bln_wajib = 1
        
        bln_lunas = total_bayar // nom_iuran
        selisih = bln_lunas - total_bln_wajib
        
        status_summary[nama] = {
            "wa": info.get('wa', ''),
            "selisih": selisih,
            "total_rp": total_bayar,
            "tunggakan_rp": abs(selisih * nom_iuran) if selisih < 0 else 0
        }

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 🛡️ Role: {st.session_state.role.upper()}")
    menu = st.radio("MENU UTAMA", ["📊 Dashboard", "✅ Ceklis & Input", "📢 Broadcast WA", "💊 Stok P3K", "👥 Data Anggota"])
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 7. MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Ringkasan Kas")
    df = pd.DataFrame(st.session_state.db['transaksi'])
    if not df.empty:
        m = df[df['metode'].isin(['Tunai', 'QRIS'])]['jumlah'].sum()
        k = df[df['metode'].str.contains('KELUAR', na=False)]['jumlah'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Bersih", f"Rp {m-k:,}")
        c2.metric("Total Masuk", f"Rp {m:,}")
        c3.metric("Total Keluar", f"Rp {k:,}")
        fig = px.pie(names=['Masuk', 'Keluar'], values=[m, k], color_discrete_sequence=['#03A9F4', '#FF5252'])
        st.plotly_chart(fig)
    else:
        st.info("Belum ada data transaksi untuk ditampilkan.")

# --- 8. MENU: CEKLIS & INPUT ---
elif menu == "✅ Ceklis & Input":
    st.header("✅ Ceklis Iuran")
    
    if st.session_state.role == "admin":
        with st.expander("📥 INPUT PEMBAYARAN BARU", expanded=True):
            with st.form("f_bayar"):
                if not st.session_state.db['anggota']:
                    st.error("Silakan tambah anggota dulu di menu 'Data Anggota'")
                else:
                    nama_p = st.selectbox("Nama Anggota", list(st.session_state.db['anggota'].keys()))
                    nominal_p = st.number_input("Nominal", value=nom_iuran)
                    metode_p = st.selectbox("Metode", ["Tunai", "QRIS"])
                    ket_p = st.text_input("Keterangan", "Iuran Kas")
                    if st.form_submit_button("SIMPAN & KIRIM BUKTI WA"):
                        ref = datetime.now().strftime("%Y%m%d%H%M")
                        tgl_s = datetime.now().strftime("%d-%m-%Y")
                        st.session_state.db['transaksi'].append({"id":ref, "nama":nama_p, "jumlah":int(nominal_p), "metode":metode_p, "tgl":tgl_s, "keterangan":ket_p})
                        save_data(st.session_state.db)
                        
                        # BUKTI BAYAR TEMPLATE
                        pesan = f"*BUKTI PEMBAYARAN KAS RESMI* ✨\n\nAssalamu’alaikum Bapak/Ibu *{nama_p}*.\n\nAlhamdulillah, telah kami terima dana iuran Anda dengan rincian sebagai berikut:\n\n━━━━━━━━━━━━━━━━━━\n📝 *KETERANGAN PEMBAYARAN*\n━━━━━━━━━━━━━━━━━━\n📅 Tanggal: {tgl_s}\n💳 Metode: *{metode_p}*\n💰 Nominal: *Rp{int(nominal_p):,}*\n📌 Keperluan: {ket_p}\n🆔 Ref ID: {ref}\n\n✅ Status: *TERVERIFIKASI & MASUK KAS*\n━━━━━━━━━━━━━━━━━━\n\nJazakumullah Khairan Katsiran. Semoga sedekah iuran ini menjadi wasilah pembersih harta, pembuka pintu rezeki, dan pemberi keberkahan bagi keluarga Bapak/Ibu di dunia maupun akhirat. Amin ya Rabbal 'Alamin. 🤲 🕋\n\nSalam takzim,\n*Bendahara Kas Blangking*"
                        st.markdown(f'<a href="{kirim_wa(st.session_state.db["anggota"][nama_p]["wa"], pesan)}" target="_blank" style="background-color:#25D366; color:white; padding:10px; border-radius:5px; text-decoration:none;">📲 KIRIM BUKTI KE WA</a>', unsafe_allow_html=True)
                        st.rerun()

    if status_summary:
        st.write("### Daftar Status Iuran")
        df_cek = pd.DataFrame([{"Nama": k, "Status": "LUNAS ✅" if v['selisih'] >= 0 else f"TUNGGAK {abs(v['selisih'])} BLN ❌", "Total Bayar": f"Rp {v['total_rp']:,}"} for k, v in status_summary.items()])
        st.table(df_cek)
    else:
        st.info("Daftar iuran akan muncul setelah ada data anggota.")

# --- 9. MENU: BROADCAST WA ---
elif menu == "📢 Broadcast WA":
    st.header("📢 Kirim Pesan Masal")
    if st.session_state.role != "admin":
        st.warning("Hanya untuk Admin.")
    elif not status_summary:
        st.info("Belum ada data anggota.")
    else:
        tipe = st.selectbox("Pilih Kategori Pesan:", ["Pengingat Besok", "Status Lunas", "Status Lebih Bayar", "Status Tunggakan"])
        
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

# --- 10. MENU: STOK P3K ---
elif menu == "💊 Stok P3K":
    st.header("💊 Manajemen Obat")
    if st.session_state.role == "admin":
        with st.form("f_p3k"):
            n_o = st.text_input("Nama Obat")
            j_o = st.number_input("Jumlah", min_value=0)
            if st.form_submit_button("Tambah"):
                st.session_state.db['p3k'].append({"Nama Obat": n_o, "Stok": j_o})
                save_data(st.session_state.db)
                st.rerun()
    if st.session_state.db['p3k']: st.table(pd.DataFrame(st.session_state.db['p3k']))

# --- 11. MENU: DATA ANGGOTA ---
elif menu == "👥 Data Anggota":
    st.header("👥 Pengaturan Anggota")
    if st.session_state.role == "admin":
        with st.expander("➕ TAMBAH ANGGOTA BARU", expanded=True):
            with st.form("f_agt"):
                n_b = st.text_input("Nama Lengkap")
                w_b = st.text_input("WhatsApp (628...)")
                c1, c2 = st.columns(2)
                bln_b = c1.selectbox("Bulan Gabung", range(1, 13), index=0)
                thn_b = c2.selectbox("Tahun Gabung", [2024, 2025, 2026], index=1)
                if st.form_submit_button("SIMPAN DATA"):
                    if n_b and w_b:
                        st.session_state.db['anggota'][n_b] = {"wa":w_b, "bln_masuk":bln_b, "thn_masuk":thn_b}
                        save_data(st.session_state.db)
                        st.success(f"Berhasil menambah {n_b}")
                        st.rerun()
                    else: st.warning("Nama & WA wajib diisi.")
    
    st.write("### Daftar Nama Anggota")
    for n, i in st.session_state.db['anggota'].items():
        st.write(f"🔹 {n} (Gabung: {i['bln_masuk']}/{i['thn_masuk']})")
