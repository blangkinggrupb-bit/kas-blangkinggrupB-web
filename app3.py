import streamlit as st
import pandas as pd
import json
import os
import urllib.parse
from datetime import datetime

# --- KONFIGURASI ---
st.set_page_config(page_title="Kas Blangking v9 Pro", layout="wide")

# Custom CSS untuk tampilan cerah
st.markdown("""
    <style>
    .stApp { background-color: #F8FBFF; }
    .main-card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
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

# --- FUNGSI KIRIM WA ---
def buka_wa(no_wa, pesan):
    no_wa = str(no_wa).strip()
    if no_wa.startswith('0'): no_wa = '62' + no_wa[1:]
    pesan_enc = urllib.parse.quote(pesan)
    url = f"https://wa.me/{no_wa}?text={pesan_enc}"
    return url

# --- LOGIN SYSTEM ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏦 KAS BLANGKING V9</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        role = st.radio("Akses:", ["User", "Admin"])
        pwd = st.text_input("Password", type="password")
        if st.button("MASUK", use_container_width=True):
            if role == "Admin" and pwd == "1234":
                st.session_state.auth, st.session_state.role = True, "admin"
                st.rerun()
            elif role == "User" and pwd == "user123":
                st.session_state.auth, st.session_state.role = True, "user"
                st.rerun()
            else: st.error("❌ Password Salah!")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Menu Utama")
    menu = st.radio("Pindah ke:", ["📊 Dashboard", "✅ Ceklis Iuran", "💊 Stok P3K", "📢 Panel Broadcast (Admin)", "👥 Data Anggota"])
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA HITUNG SALDO & STATUS ---
df_tr = pd.DataFrame(st.session_state.db['transaksi'])
nom_iuran = st.session_state.db['config'].get('nom_iuran', 10000)
status_anggota = {}

for nama, info in st.session_state.db['anggota'].items():
    total_bayar = sum(t['jumlah'] for t in st.session_state.db['transaksi'] if t['nama'] == nama and "iuran" in t['keterangan'].lower())
    # Hitung selisih bulan dari awal gabung sampai sekarang
    tgl_skrg = datetime.now()
    tgl_masuk = datetime(int(info['thn_masuk']), int(info['bln_masuk']), 1)
    selisih_bln = (tgl_skrg.year - tgl_masuk.year) * 12 + tgl_skrg.month - tgl_masuk.month + 1
    
    bln_terbayar = total_bayar // nom_iuran
    selisih = bln_terbayar - selisih_bln
    
    status_anggota[nama] = {
        "wa": info['wa'],
        "selisih": selisih, # 0=lunas, >0=lebih, <0=tunggakan
        "total_bayar": total_bayar
    }

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Kondisi Kas Saat Ini")
    if not df_tr.empty:
        s_tunai = df_tr[df_tr['metode'] == "Tunai"]['jumlah'].sum() - df_tr[df_tr['metode'] == "KELUAR TUNAI"]['jumlah'].sum()
        s_qris = df_tr[df_tr['metode'] == "QRIS"]['jumlah'].sum() - df_tr[df_tr['metode'] == "KELUAR QRIS"]['jumlah'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Tunai", f"Rp {s_tunai:,}")
        c2.metric("Saldo QRIS", f"Rp {s_qris:,}")
        c3.metric("Total Kas", f"Rp {s_tunai+s_qris:,}")

# --- 2. CEKLIS & PEMBAYARAN ---
elif menu == "✅ Ceklis Iuran":
    st.header("✅ Pembayaran Iuran")
    if st.session_state.role == "admin":
        with st.expander("📥 Input Transaksi Baru", expanded=True):
            with st.form("input_form"):
                c1, c2 = st.columns(2)
                nama_p = c1.selectbox("Nama Anggota", list(st.session_state.db['anggota'].keys()))
                nominal_p = c2.number_input("Nominal Pembayaran", value=nom_iuran, step=5000)
                ket_p = st.text_input("Keperluan", value=f"Iuran Kas")
                metode_p = st.selectbox("Metode", ["Tunai", "QRIS"])
                
                if st.form_submit_button("SIMPAN & KIRIM BUKTI WA"):
                    ref_id = datetime.now().strftime("%Y%m%d%f")[:12]
                    tgl_s = datetime.now().strftime("%d-%m-%Y")
                    st.session_state.db['transaksi'].append({
                        "id": ref_id, "nama": nama_p, "jumlah": int(nominal_p), 
                        "metode": metode_p, "tgl": tgl_s, "keterangan": ket_p
                    })
                    save_data(st.session_state.db)
                    
                    # Template Pesan Bukti Pembayaran
                    pesan_bukti = (
                        f"*BUKTI PEMBAYARAN KAS RESMI* ✨\n\n"
                        f"Assalamu’alaikum Bapak/Ibu *{nama_p}*.\n\n"
                        f"Alhamdulillah, telah kami terima dana iuran Anda dengan rincian sebagai berikut:\n\n"
                        f"━━━━━━━━━━━━━━━━━━\n📝 *KETERANGAN PEMBAYARAN*\n━━━━━━━━━━━━━━━━━━\n"
                        f"📅 Tanggal: {tgl_s}\n💳 Metode: *{metode_p}*\n💰 Nominal: *Rp{int(nominal_p):,}*\n"
                        f"📌 Keperluan: {ket_p}\n🆔 Ref ID: {ref_id}\n\n"
                        f"✅ Status: *TERVERIFIKASI & MASUK KAS*\n━━━━━━━━━━━━━━━━━━\n\n"
                        f"Jazakumullah Khairan Katsiran. Semoga sedekah iuran ini menjadi wasilah pembersih harta, "
                        f"pembuka pintu rezeki, dan pemberi keberkahan bagi keluarga Bapak/Ibu di dunia maupun akhirat. Amin ya Rabbal 'Alamin. 🤲 🕋\n\n"
                        f"Salam takzim,\n*Bendahara Kas Blangking*"
                    )
                    st.success("Data Tersimpan!")
                    st.markdown(f'<a href="{buka_wa(st.session_state.db["anggota"][nama_p]["wa"], pesan_bukti)}" target="_blank">Klik Disini Untuk Kirim WA ke {nama_p}</a>', unsafe_allow_html=True)

# --- 3. PANEL BROADCAST (ADMIN ONLY) ---
elif menu == "📢 Panel Broadcast (Admin)":
    if st.session_state.role != "admin":
        st.warning("Akses Terbatas!")
    else:
        st.header("📢 Kirim Pesan Massal")
        kategori = st.selectbox("Pilih Kelompok Penerima:", ["Pengingat Besok", "Status Lunas", "Status Lebih Bayar", "Status Tunggakan"])
        
        # Filter Data berdasarkan kategori
        penerima = []
        if kategori == "Pengingat Besok":
            penerima = list(st.session_state.db['anggota'].keys())
            msg_template = "Assalamu’alaikum Bapak/Ibu *{nama}*. ✨\n\nSemoga cahaya keberkahan senantiasa menyertai keluarga. Menjelang hari esok, izin mengingatkan jadwal iuran kas rutin kita sebesar *Rp{nom:,}*.\n\nPembayaran bisa melalui *Tunai* atau *Scan QRIS*.\n\nSemoga setiap rupiahnya menjadi wasilah pembersih harta dan pengetuk pintu langit. Amin. 🤲✨"
        elif kategori == "Status Lunas":
            penerima = [n for n, s in status_anggota.items() if s['selisih'] == 0]
            msg_template = "Assalamu’alaikum Bapak/Ibu *{nama}*. ✨\n\nAlhamdulillah, administrasi kas Anda saat ini dalam status *LUNAS*.\n\nTerima kasih atas kerja samanya dalam menjaga amanah grup ini. Semoga Allah senantiasa melimpahkan rezeki dan berkah-Nya. Syukron jazilan. 🙏🤲"
        elif kategori == "Status Lebih Bayar":
            penerima = [n for n, s in status_anggota.items() if s['selisih'] > 0]
            msg_template = "Masya Allah, Tabarakallah Bapak/Ibu *{nama}*. 🌟\n\nJazakumullah khairan katsiran atas kedisiplinannya. Status kas Anda saat ini *LUNAS* (Bahkan ada lebih bayar *{bln} bulan*).\n\nSemoga Allah menggantinya dengan kesehatan, kebahagiaan, dan keberkahan yang berlipat ganda untuk keluarga. Amin. 🤲🕋"
        elif kategori == "Status Tunggakan":
            penerima = [n for n, s in status_anggota.items() if s['selisih'] < 0]
            msg_template = "Assalamu’alaikum Bapak/Ibu *{nama}*. 🌸\n\nMohon izin menyampaikan amanah catatan kas yang masih tertunda selama *{bln} bulan* (Total *Rp{total:,}*).\n\nKami mendoakan semoga Allah membukakan pintu rezeki dari arah yang tak disangka-sangka agar Bapak/Ibu dapat menunaikannya via *Tunai/QRIS*.\n\nJazakumullah khairan atas perhatiannya. 😊🙏"

        st.subheader(f"Daftar Anggota ({kategori})")
        target = st.multiselect("Pilih Nama (Kosongkan jika ingin kirim satu per satu):", penerima, default=penerima)
        
        for t_nama in target:
            info_s = status_anggota[t_nama]
            # Custom formatting per pesan
            if kategori == "Pengingat Besok": text = msg_template.format(nama=t_nama, nom=nom_iuran)
            elif kategori == "Status Lebih Bayar": text = msg_template.format(nama=t_nama, bln=abs(info_s['selisih']))
            elif kategori == "Status Tunggakan": text = msg_template.format(nama=t_nama, bln=abs(info_s['selisih']), total=abs(info_s['selisih']*nom_iuran))
            else: text = msg_template.format(nama=t_nama)
            
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{t_nama}** ({info_s['wa']})")
                c2.markdown(f'[:green[Kirim WA]]({buka_wa(info_s["wa"], text)})')

# --- 4. DATA ANGGOTA ---
elif menu == "👥 Data Anggota":
    st.header("👥 Manajemen Anggota")
    # Bagian Input Anggota dan Daftar Anggota seperti sebelumnya
    # ... (Gunakan kode yang sudah ada untuk list anggota)
    st.info("Halaman ini untuk mengelola data nama dan nomor WhatsApp anggota.")

