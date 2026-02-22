import streamlit as st
import pandas as pd
import json
import os
import urllib.parse
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Blangking Grup B", layout="wide")

# CSS untuk memperbaiki tampilan Login (Teks Hitam agar terlihat) dan tema cerah
st.markdown("""
    <style>
    .stApp { background-color: #F8FBFF; }
    /* Memastikan teks radio button login berwarna hitam */
    .stRadio div[role="radiogroup"] label { color: #000000 !important; font-weight: bold; }
    .main-card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #1E88E5; color: white; }
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
    return f"https://wa.me/{no_wa}?text={pesan_enc}"

# --- LOGIN SYSTEM ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏦 KAS BLANGKING GRUP B</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        # Perbaikan: Menambahkan label yang jelas agar terlihat
        st.write("### Pilih Hak Akses:")
        role_type = st.radio("Akses sebagai:", ["User", "Admin"], label_visibility="collapsed")
        st.write(f"Akses Terpilih: **{role_type}**")
        pwd = st.text_input("Password", type="password", placeholder="Masukkan Password...")
        
        if st.button("MASUK", use_container_width=True):
            if role_type == "Admin" and pwd == "1234":
                st.session_state.auth, st.session_state.role = True, "admin"
                st.rerun()
            elif role_type == "User" and pwd == "user":
                st.session_state.auth, st.session_state.role = True, "user"
                st.rerun()
            else: st.error("❌ Password Salah!")
    st.stop()

# --- LOGIKA HITUNG SALDO & STATUS (DIPERBAIKI AGAR TIDAK ERROR) ---
nom_iuran = st.session_state.db['config'].get('nom_iuran', 10000)
status_anggota = {}

for nama, info in st.session_state.db['anggota'].items():
    # Menghitung total iuran yang sudah dibayar
    total_bayar = sum(t['jumlah'] for t in st.session_state.db['transaksi'] if t.get('nama') == nama and "iuran" in t.get('keterangan', '').lower())
    
    # Penanganan Error: Jika thn_masuk atau bln_masuk kosong, beri nilai default
    try:
        thn_m = int(info.get('thn_masuk', 2025))
        bln_m = int(info.get('bln_masuk', 1))
        tgl_masuk = datetime(thn_m, bln_m, 1)
    except:
        tgl_masuk = datetime(2025, 1, 1) # Default jika data rusak
        
    tgl_skrg = datetime.now()
    selisih_bln = (tgl_skrg.year - tgl_masuk.year) * 12 + tgl_skrg.month - tgl_masuk.month + 1
    
    bln_terbayar = total_bayar // nom_iuran
    selisih = bln_terbayar - selisih_bln
    
    status_anggota[nama] = {
        "wa": info.get('wa', ''),
        "selisih": selisih,
        "total_bayar": total_bayar
    }

# --- SIDEBAR & MENU ---
with st.sidebar:
    st.title("🛡️ Menu Utama")
    # Menu khusus Admin diperluas
    options = ["📊 Dashboard", "✅ Ceklis Iuran", "💊 Stok P3K", "👥 Data Anggota"]
    if st.session_state.role == "admin":
        options.append("📢 Panel Broadcast (Admin)")
    
    menu = st.sidebar.radio("Navigasi:", options)
    if st.sidebar.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Kondisi Kas Saat Ini")
    df_tr = pd.DataFrame(st.session_state.db['transaksi'])
    if not df_tr.empty:
        # Menghitung saldo dengan pengecekan kolom 'metode'
        s_tunai = df_tr[df_tr.get('metode') == "Tunai"]['jumlah'].sum() - df_tr[df_tr.get('metode') == "KELUAR TUNAI"]['jumlah'].sum()
        s_qris = df_tr[df_tr.get('metode') == "QRIS"]['jumlah'].sum() - df_tr[df_tr.get('metode') == "KELUAR QRIS"]['jumlah'].sum()
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
                nama_list = list(st.session_state.db['anggota'].keys())
                if not nama_list:
                    st.warning("Tambahkan anggota terlebih dahulu di menu Data Anggota!")
                    st.form_submit_button("Simpan", disabled=True)
                else:
                    nama_p = c1.selectbox("Nama Anggota", nama_list)
                    nominal_p = c2.number_input("Nominal Pembayaran", value=nom_iuran, step=5000)
                    ket_p = st.text_input("Keperluan", value=f"Iuran Kas")
                    metode_p = st.selectbox("Metode", ["Tunai", "QRIS"])
                    
                    if st.form_submit_button("SIMPAN & KIRIM BUKTI WA"):
                        ref_id = datetime.now().strftime("%Y%m%d%H%M%S")[:12]
                        tgl_s = datetime.now().strftime("%d-%m-%Y")
                        st.session_state.db['transaksi'].append({
                            "id": ref_id, "nama": nama_p, "jumlah": int(nominal_p), 
                            "metode": metode_p, "tgl": tgl_s, "keterangan": ket_p
                        })
                        save_data(st.session_state.db)
                        
                        pesan_bukti = (
                            f"*BUKTI PEMBAYARAN KAS RESMI* ✨\n\n"
                            f"Assalamu’alaikum Bapak/Ibu *{nama_p}*.\n\n"
                            f"Alhamdulillah, telah kami terima dana iuran Anda dengan rincian sebagai berikut:\n\n"
                            f"━━━━━━━━━━━━━━━━━━\n📝 *KETERANGAN PEMBAYARAN*\n━━━━━━━━━━━━━━━━━━\n"
                            f"📅 Tanggal: {tgl_s}\n💳 Metode: *{metode_p}*\n💰 Nominal: *Rp{int(nominal_p):,}*\n"
                            f"📌 Keperluan: {ket_p}\n🆔 Ref ID: {ref_id}\n\n"
                            f"✅ Status: *TERVERIFIKASI & MASUK KAS*\n━━━━━━━━━━━━━━━━━━\n\n"
                            f"Jazakumullah Khairan Katsiran. Semoga sedekah iuran ini menjadi wasilah pembersih harta...\n\n"
                            f"Salam takzim,\n*Bendahara Kas Blangking*"
                        )
                        st.success("Data Tersimpan!")
                        st.markdown(f'<a href="{buka_wa(st.session_state.db["anggota"][nama_p]["wa"], pesan_bukti)}" target="_blank">Kirim WA Ke Anggota</a>', unsafe_allow_html=True)

# --- 3. PANEL BROADCAST (ADMIN ONLY) ---
elif menu == "📢 Panel Broadcast (Admin)":
    st.header("📢 Kirim Pesan Massal")
    kategori = st.selectbox("Pilih Kelompok Penerima:", ["Pengingat Besok", "Status Lunas", "Status Lebih Bayar", "Status Tunggakan"])
    
    penerima = []
    if kategori == "Pengingat Besok":
        penerima = list(st.session_state.db['anggota'].keys())
        template = "Assalamu’alaikum Bapak/Ibu *{nama}*. ✨\n\nSemoga cahaya keberkahan senantiasa menyertai keluarga. Menjelang hari esok, izin mengingatkan jadwal iuran kas rutin kita sebesar *Rp{nom:,}*..."
    elif kategori == "Status Lunas":
        penerima = [n for n, s in status_anggota.items() if s['selisih'] == 0]
        template = "Assalamu’alaikum Bapak/Ibu *{nama}*. ✨\n\nAlhamdulillah, administrasi kas Anda saat ini dalam status *LUNAS*..."
    elif kategori == "Status Lebih Bayar":
        penerima = [n for n, s in status_anggota.items() if s['selisih'] > 0]
        template = "Masya Allah, Tabarakallah Bapak/Ibu *{nama}*. 🌟\n\nJazakumullah khairan katsiran atas kedisiplinannya. Status kas Anda saat ini *LUNAS* (Bahkan ada lebih bayar *{bln} bulan*)..."
    elif kategori == "Status Tunggakan":
        penerima = [n for n, s in status_anggota.items() if s['selisih'] < 0]
        template = "Assalamu’alaikum Bapak/Ibu *{nama}*. 🌸\n\nMohon izin menyampaikan amanah catatan kas yang masih tertunda selama *{bln} bulan* (Total *Rp{total:,}*)..."

    st.subheader(f"Daftar Anggota: {kategori}")
    for t_nama in penerima:
        info_s = status_anggota[t_nama]
        # Penyesuaian isi template
        if kategori == "Status Lebih Bayar": msg = template.format(nama=t_nama, bln=info_s['selisih'])
        elif kategori == "Status Tunggakan": msg = template.format(nama=t_nama, bln=abs(info_s['selisih']), total=abs(info_s['selisih']*nom_iuran))
        else: msg = template.format(nama=t_nama, nom=nom_iuran)
        
        c1, c2 = st.columns([3, 1])
        c1.write(f"**{t_nama}**")
        c2.markdown(f'[Kirim WA]({buka_wa(info_s["wa"], msg)})')

# --- 4. DATA ANGGOTA ---
elif menu == "👥 Data Anggota":
    st.header("👥 Manajemen Anggota")
    with st.expander("➕ Tambah Anggota Baru"):
        with st.form("form_tambah_agt"):
            n_baru = st.text_input("Nama Lengkap")
            w_baru = st.text_input("WhatsApp (Contoh: 0812345678)")
            c1, c2 = st.columns(2)
            b_baru = c1.selectbox("Bulan Gabung", [str(i).zfill(2) for i in range(1, 13)])
            t_baru = c2.selectbox("Tahun Gabung", [str(i) for i in range(2024, 2030)])
            if st.form_submit_button("Simpan Anggota"):
                if n_baru and w_baru:
                    st.session_state.db['anggota'][n_baru] = {"wa": w_baru, "bln_masuk": b_baru, "thn_masuk": t_baru}
                    save_data(st.session_state.db)
                    st.success("Anggota ditambahkan!")
                    st.rerun()
                else: st.warning("Nama dan WA wajib diisi!")
    
    # Menampilkan daftar untuk hapus data
    if st.session_state.role == "admin" and st.session_state.db['anggota']:
        st.subheader("Daftar Anggota Saat Ini")
        for agt in list(st.session_state.db['anggota'].keys()):
            c1, c2 = st.columns([4, 1])
            c1.write(f"👤 {agt}")
            if c2.button("Hapus", key=f"del_{agt}"):
                del st.session_state.db['anggota'][agt]
                save_data(st.session_state.db)
                st.rerun()
