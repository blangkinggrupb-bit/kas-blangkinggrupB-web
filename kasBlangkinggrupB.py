from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line
from datetime import datetime
import json
import os
import shutil
import urllib.parse
import webbrowser
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# --- KONFIGURASI LIBRARY TAMBAHAN ---
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

try:
    from plyer import share
except ImportError:
    share = None

# --- KONFIGURASI WARNA PRO ---
WARNA_HEADER = (0.12, 0.58, 0.95, 1)
WARNA_BARIS_A = (1, 1, 1, 1)
WARNA_BARIS_B = (0.94, 0.97, 1, 1)
WARNA_TEKS_HEADER = (1, 1, 1, 1)
WARNA_TEKS_UTAMA = (0.1, 0.1, 0.1, 1)
WARNA_BIRU_CERAH = (0.2, 0.6, 1, 1)

# --- CUSTOM WIDGETS ---
class BorderLabel(Label):
    def __init__(self, border_color=(0.8, 0.8, 0.8, 1), bg_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.border_color = border_color
        self.custom_bg = bg_color
        if 'color' not in kwargs: self.color = WARNA_TEKS_UTAMA
        with self.canvas.before:
            Color(*self.custom_bg)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
            Color(*self.border_color)
            self.rect = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect_bg.pos = self.pos
        self.rect_bg.size = self.size
        self.rect.rectangle = (self.x, self.y, self.width, self.height)

class ClickableLabel(BorderLabel):
    def __init__(self, on_click=None, **kwargs):
        super().__init__(**kwargs)
        self.on_click = on_click
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.on_click:
            self.on_click(self.text)
            return True
        return super().on_touch_down(touch)

# --- SCREEN: LOGIN ---
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1,1,1,1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_rect)
        root = BoxLayout(orientation='vertical', padding=dp(20))
        login_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(280), spacing=dp(15))
        login_box.add_widget(Label(text="[b][color=3399FF]KAS BLANGKING[/color][/b]", markup=True, font_size='40sp', halign="center"))
        login_box.add_widget(Label(text="ADMIN LOGIN", font_size='25sp', color=WARNA_TEKS_UTAMA, halign="center"))
        self.pass_input = TextInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=dp(60), halign="center", font_size='25sp')
        login_box.add_widget(self.pass_input)
        btn = Button(text="MASUK", size_hint_y=None, height=dp(65), background_color=WARNA_BIRU_CERAH, color=(1,1,1,1), bold=True, background_normal='', font_size='25sp')
        btn.bind(on_release=self.cek_login)
        login_box.add_widget(btn)
        root.add_widget(login_box); root.add_widget(Label()); self.add_widget(root)
    def _update_rect(self, instance, value): self.rect.size = instance.size
    def cek_login(self, _):
        if self.pass_input.text == "1234": self.manager.current = 'utama'

# --- SCREEN: MAIN ---
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1,1,1,1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_rect)
        self.file_data = "data_kas_blangking_v9.json"
        self.path_folder = os.getcwd()
        self.folder_backup = os.path.join(self.path_folder, "backups_kas")
        if not os.path.exists(self.folder_backup): os.makedirs(self.folder_backup)
        
        self.anggota = {}; self.transaksi = []; self.p3k = []; self.selected_members = []
        self.config = {"nom_iuran": "10000"}
        now_init = datetime.now()
        self.sel_hari, self.sel_bulan, self.sel_tahun = now_init.strftime("%d"), now_init.strftime("%m"), now_init.strftime("%Y")
        self.tahun_ceklis_aktif = self.sel_tahun 
        self.dropdown = DropDown()
        self.load_data()
        self.setup_ui()

    def _update_rect(self, instance, value): self.rect.size = instance.size

    def setup_ui(self):
        self.clear_widgets()
        now = datetime.now()
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Header
        root.add_widget(Label(text="[b][color=3399FF]KAS BLANGKING GRUP B[/color][/b]", markup=True, size_hint_y=None, height=dp(55), font_size='35sp'))
        
        # Filter Rekap
        rekap_filter = BoxLayout(size_hint_y=None, height=dp(65), spacing=dp(3))
        self.spin_rekap_h = Spinner(text=self.sel_hari, values=[str(i).zfill(2) for i in range(1, 32)], font_size='20sp', size_hint_x=0.15, background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        self.spin_rekap_b = Spinner(text=self.sel_bulan, values=[str(i).zfill(2) for i in range(1, 13)], font_size='20sp', size_hint_x=0.15, background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        self.spin_rekap_t = Spinner(text=self.sel_tahun, values=[str(i) for i in range(2025, 2101)], font_size='20sp', size_hint_x=0.20, background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        self.spin_det_saldo = Spinner(text="SALDO TOTAL", values=[], font_size='20sp', background_color=WARNA_BIRU_CERAH, color=(1,1,1,1), size_hint_x=0.50, background_normal='', bold=True)
        for s in [self.spin_rekap_h, self.spin_rekap_b, self.spin_rekap_t]: s.bind(text=self.update_rekap_trigger)
        rekap_filter.add_widget(self.spin_rekap_h); rekap_filter.add_widget(self.spin_rekap_b); rekap_filter.add_widget(self.spin_rekap_t); rekap_filter.add_widget(self.spin_det_saldo)
        root.add_widget(rekap_filter)

        # Grid Rekap
        self.grid_rekap = GridLayout(cols=3, size_hint_y=None, height=dp(140), spacing=2)
        for h in ["Keterangan", "Tunai", "QRIS"]: self.grid_rekap.add_widget(BorderLabel(text=h, bold=True, font_size='22sp', bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER))
        self.val_in_t = BorderLabel(text="0", font_size='22sp'); self.val_in_q = BorderLabel(text="0", font_size='22sp')
        self.val_out_t = BorderLabel(text="0", font_size='22sp'); self.val_out_q = BorderLabel(text="0", font_size='22sp')
        self.val_tot_t = BorderLabel(text="0", bold=True, color=(0,0.4,1,1), font_size='22sp'); self.val_tot_q = BorderLabel(text="0", bold=True, color=(0,0.4,1,1), font_size='22sp')
        for l, vt, vq in [("Masuk", self.val_in_t, self.val_in_q), ("Keluar", self.val_out_t, self.val_out_q), ("TOTAL", self.val_tot_t, self.val_tot_q)]:
            self.grid_rekap.add_widget(BorderLabel(text=l, font_size='22sp', bg_color=(0.85, 0.92, 1, 1), bold=True)); self.grid_rekap.add_widget(vt); self.grid_rekap.add_widget(vq)
        root.add_widget(self.grid_rekap)

        # Form Input
        input_grid = GridLayout(cols=2, size_hint_y=None, height=dp(250), spacing=dp(8))
        self.in_cari = TextInput(hint_text="Nama Anggota", multiline=False, font_size='25sp', size_hint_y=None, height=dp(60)); self.in_cari.bind(text=self.auto_complete)
        self.spin_nom_quick = Spinner(text="Nominal", values=("10000", "300000", "500000", "Input Sendiri"), font_size='25sp', background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        self.spin_nom_quick.bind(text=self.update_input_nom)
        self.in_nom = TextInput(hint_text="Rp Nominal", input_filter='int', multiline=False, font_size='25sp', size_hint_y=None, height=dp(60))
        self.spin_ket = Spinner(text="Keterangan", values=("Iuran Januari","Iuran Februari","Iuran Maret","Iuran April","Iuran Mei","Iuran Juni","Iuran Juli","Iuran Agustus","Iuran September","Iuran Oktober","Iuran November","Iuran Desember", "Sumbangan Keluarga Sakit","Karyawan Sakit","Keluarga Meninggal","Beli Obat","Pindah Rekening","Setor tunai","Tarik Tunai","Beli Soffel","lainnya"), font_size='25sp', background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        box_tgl_input = BoxLayout(spacing=dp(3))
        self.in_hari = Spinner(text=now.strftime("%d"), values=[str(i).zfill(2) for i in range(1, 32)], font_size='20sp', background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        self.in_bulan = Spinner(text=now.strftime("%m"), values=[str(i).zfill(2) for i in range(1, 13)], font_size='20sp', background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        self.in_tahun = Spinner(text=now.strftime("%Y"), values=[str(i) for i in range(2025, 2101)], font_size='25sp', background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA, background_normal='')
        box_tgl_input.add_widget(self.in_hari); box_tgl_input.add_widget(self.in_bulan); box_tgl_input.add_widget(self.in_tahun)
        input_grid.add_widget(self.in_cari); input_grid.add_widget(self.spin_nom_quick)
        input_grid.add_widget(self.in_nom); input_grid.add_widget(self.spin_ket)
        input_grid.add_widget(Label(text="Tgl Transaksi:", font_size='25sp', color=WARNA_TEKS_UTAMA, bold=True)); input_grid.add_widget(box_tgl_input)
        root.add_widget(input_grid)
        
        self.spin_met = Spinner(text="Tunai", values=("Tunai", "QRIS", "KELUAR TUNAI", "KELUAR QRIS"), font_size='25sp', size_hint_y=None, height=dp(60), background_color=WARNA_BIRU_CERAH, color=(1,1,1,1), bold=True, background_normal='')
        root.add_widget(self.spin_met)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(5))
        b_simpan = Button(text="SIMPAN", background_color=WARNA_BIRU_CERAH, bold=True, color=(1,1,1,1), font_size='25sp', background_normal=''); b_simpan.bind(on_release=lambda x: self.proses_bayar(False))
        b_wa = Button(text="SIMPAN + WA", background_color=WARNA_BIRU_CERAH, bold=True, color=(1,1,1,1), font_size='25sp', background_normal=''); b_wa.bind(on_release=lambda x: self.proses_bayar(True))
        btn_box.add_widget(b_simpan); btn_box.add_widget(b_wa); root.add_widget(btn_box)

        root.add_widget(Label())
        footer = BoxLayout(size_hint_y=None, height=dp(65), spacing=dp(5))
        menu_f = [("AGT", self.buka_db), ("CEK", self.buka_ceklis), ("DASH", self.buka_grafik), ("P3K", self.buka_p3k), ("WA", self.buka_pengingat), ("HIST", self.buka_riwayat_transaksi)]
        for t, f in menu_f:
            b = Button(text=t, background_color=WARNA_BIRU_CERAH, color=(1,1,1,1), bold=True, font_size='25sp', background_normal=''); b.bind(on_release=f); footer.add_widget(b)
        root.add_widget(footer); self.add_widget(root); self.hitung_rekap()

    # --- FITUR BACKUP & DATA ---
    def save_data(self):
        try:
            with open(self.file_data, "w") as f:
                json.dump({"anggota": self.anggota, "transaksi": self.transaksi, "p3k": self.p3k, "config": self.config}, f)
            self.buat_backup_otomatis()
            self.backup_ke_email()
        except Exception as e:
            print(f"Gagal Simpan: {e}")

    def load_data(self):
        if os.path.exists(self.file_data):
            try:
                with open(self.file_data, "r") as f:
                    d = json.load(f)
                    self.anggota = d.get("anggota", {})
                    self.transaksi = d.get("transaksi", [])
                    self.p3k = d.get("p3k", [])
                    self.config = d.get("config", {"nom_iuran": "10000"})
            except: pass

    def backup_ke_email(self):
        threading.Thread(target=self._proses_kirim_email).start()

    def _proses_kirim_email(self):
        email_pengirim = "blangkinggrupb@gmail.com"
        password_app = "frli ubjt aaqh djdx"
        email_penerima = "blangkinggrupb@gmail.com"
        msg = MIMEMultipart()
        msg['From'] = email_pengirim
        msg['To'] = email_penerima
        msg['Subject'] = f"KAS BACKUP: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        try:
            if os.path.exists(self.file_data):
                with open(self.file_data, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {self.file_data}")
                msg.attach(part)
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(email_pengirim, password_app)
                server.send_message(msg)
                server.quit()
        except: pass

    def buat_backup_otomatis(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        f_name = f"backup_{ts}.json"
        dest = os.path.join(self.folder_backup, f_name)
        try:
            shutil.copy2(self.file_data, dest)
            files = [os.path.join(self.folder_backup, f) for f in os.listdir(self.folder_backup) if f.endswith('.json')]
            files.sort(key=os.path.getmtime)
            if len(files) > 10:
                for i in range(len(files) - 10): os.remove(files[i])
        except: pass

    def buka_menu_restore(self, _):
        con = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        con.add_widget(Label(text="PILIH TANGGAL RESTORE", color=WARNA_TEKS_UTAMA, bold=True, size_hint_y=None, height=dp(40)))
        sc = ScrollView(); ly = GridLayout(cols=1, spacing=3, size_hint_y=None); ly.bind(minimum_height=ly.setter('height'))
        files = [f for f in os.listdir(self.folder_backup) if f.endswith('.json')]
        files.sort(reverse=True)
        for f in files:
            btn = Button(text=f, size_hint_y=None, height=dp(50), background_color=(0.9,0.95,1,1), color=WARNA_TEKS_UTAMA)
            btn.bind(on_release=lambda x, fn=f: self.konfirmasi_restore(fn))
            ly.add_widget(btn)
        sc.add_widget(ly); con.add_widget(sc)
        b_cls = Button(text="BATAL", size_hint_y=None, height=dp(50), background_color=(0.8,0,0,1)); b_cls.bind(on_release=lambda x: self.pop_res.dismiss())
        con.add_widget(b_cls); self.pop_res = Popup(title="RESTORE DATA", content=con, size_hint=(0.9, 0.8)); self.pop_res.open()

    def konfirmasi_restore(self, filename):
        box = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        with box.canvas.before: Color(1, 1, 1, 1); Rectangle(pos=box.pos, size=box.size)
        pesan = f"[b][color=FF0000]PERINGATAN![/color][/b]\n\nAnda akan memulihkan data dari file:\n[i]{filename}[/i]\n\nData saat ini akan [b]DITIMPA TOTAL[/b]. Apakah Anda yakin?"
        lbl = Label(text=pesan, markup=True, color=WARNA_TEKS_UTAMA, halign="center")
        box.add_widget(lbl)
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_ya = Button(text="YA, PULIHKAN", background_color=(0.8, 0, 0, 1), bold=True)
        btn_ya.bind(on_release=lambda x: self.eksekusi_restore(filename))
        btn_batal = Button(text="BATAL", background_color=WARNA_BIRU_CERAH, bold=True)
        btn_batal.bind(on_release=lambda x: self.pop_konf.dismiss())
        btn_layout.add_widget(btn_ya); btn_layout.add_widget(btn_batal); box.add_widget(btn_layout)
        self.pop_konf = Popup(title="KONFIRMASI", content=box, size_hint=(0.85, 0.45)); self.pop_konf.open()

    def eksekusi_restore(self, filename):
        path_src = os.path.join(self.folder_backup, filename)
        try:
            shutil.copy2(path_src, self.file_data)
            self.load_data(); self.setup_ui()
            self.pop_konf.dismiss(); self.pop_res.dismiss(); self.pop_m.dismiss()
            Popup(title="Sukses", content=Label(text="Data berhasil dipulihkan!"), size_hint=(0.7,0.3)).open()
        except: pass

    # --- LOGIKA APLIKASI ---
    def update_input_nom(self, s, t):
        if t == "Input Sendiri": self.in_nom.text = ""; self.in_nom.focus = True
        elif t == "10000": 
            self.in_nom.text = "10000"
            lb = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"]
            self.spin_ket.text = f"Iuran {lb[datetime.now().month-1]}"
        elif t in ["300000", "500000"]: 
            self.in_nom.text = t; self.spin_ket.text = "Sumbangan Keluarga " + ("Sakit" if t=="300000" else "Meninggal")

    def update_rekap_trigger(self, s, t):
        self.sel_hari, self.sel_bulan, self.sel_tahun = self.spin_rekap_h.text, self.spin_rekap_b.text, self.spin_rekap_t.text
        self.hitung_rekap()

    def hitung_rekap(self):
        tin_filter, tout_filter, qin_filter, qout_filter = 0, 0, 0, 0
        all_tin, all_tout, all_qin, all_qout = 0, 0, 0, 0
        f_tgl = f"{self.sel_hari}-{self.sel_bulan}-{self.sel_tahun}"
        for tr in self.transaksi:
            v, m = tr.get('jumlah', 0), tr.get('metode', 'Tunai')
            if m == "Tunai": all_tin += v
            elif m == "QRIS": all_qin += v
            elif m == "KELUAR TUNAI": all_tout += v
            elif m == "KELUAR QRIS": all_qout += v
            if tr['tgl'] == f_tgl:
                if m == "Tunai": tin_filter += v
                elif m == "QRIS": qin_filter += v
                elif m == "KELUAR TUNAI": tout_filter += v
                elif m == "KELUAR QRIS": qout_filter += v
        self.val_in_t.text, self.val_out_t.text, self.val_tot_t.text = f"{tin_filter:,}", f"{tout_filter:,}", f"{tin_filter-tout_filter:,}"
        self.val_in_q.text, self.val_out_q.text, self.val_tot_q.text = f"{qin_filter:,}", f"{qout_filter:,}", f"{qin_filter-qout_filter:,}"
        self.spin_det_saldo.text = f"SALDO: Rp{all_tin-all_tout+all_qin-all_qout:,}"
        self.spin_det_saldo.values = [f"Tunai: {all_tin-all_tout:,}", f"QRIS: {all_qin-all_qout:,}"]

    def buka_grafik(self, _):
        con = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        with con.canvas.before: Color(1, 1, 1, 1); self.rect_bg_g = Rectangle(pos=con.pos, size=con.size)
        con.bind(size=lambda inst, val: setattr(self.rect_bg_g, 'size', val), pos=lambda inst, val: setattr(self.rect_bg_g, 'pos', val))
        con.add_widget(Label(text="[b][color=3399FF]VISUALISASI SALDO KAS[/color][/b]", markup=True, size_hint_y=None, height=dp(40), font_size='28sp'))
        all_tin, all_tout, all_qin, all_qout = 0, 0, 0, 0
        for tr in self.transaksi:
            v, m = tr.get('jumlah', 0), tr.get('metode', 'Tunai')
            if m == "Tunai": all_tin += v
            elif m == "QRIS": all_qin += v
            elif m == "KELUAR TUNAI": all_tout += v
            elif m == "KELUAR QRIS": all_qout += v
        s_tunai, s_qris = all_tin - all_tout, all_qin - all_qout
        t_semua = s_tunai + s_qris
        chart_layout = BoxLayout(orientation='horizontal', spacing=dp(40), padding=(dp(20), 0))
        def create_bar(label, value, color):
            bar_con = BoxLayout(orientation='vertical', spacing=dp(5))
            proportion = (value / t_semua) if t_semua > 0 else 0
            bar_h = max(dp(10), dp(200 * proportion))
            bar_con.add_widget(Label(text=f"Rp{value:,}", color=WARNA_TEKS_UTAMA, font_size='14sp', bold=True))
            bar_v = BoxLayout(size_hint_y=None, height=bar_h)
            with bar_v.canvas: Color(*color); Rectangle(pos=bar_v.pos, size=bar_v.size)
            bar_v.bind(pos=lambda inst, val: setattr(inst.canvas.children[-1], 'pos', val), size=lambda inst, val: setattr(inst.canvas.children[-1], 'size', val))
            bar_con.add_widget(bar_v); bar_con.add_widget(Label(text=label, color=WARNA_TEKS_UTAMA, size_hint_y=None, height=dp(30)))
            return bar_con
        chart_layout.add_widget(create_bar("TUNAI", s_tunai, (0.2, 0.6, 1, 1)))
        chart_layout.add_widget(create_bar("QRIS", s_qris, (0, 0.7, 0.3, 1)))
        con.add_widget(chart_layout); con.add_widget(BorderLabel(text=f"TOTAL GABUNGAN: Rp{t_semua:,}", bold=True, bg_color=(0.9, 0.95, 1, 1), size_hint_y=None, height=dp(50)))
        btn_cls = Button(text="TUTUP", size_hint_y=None, height=dp(60), background_color=WARNA_BIRU_CERAH, bold=True, background_normal='')
        btn_cls.bind(on_release=lambda x: self.pop_graph.dismiss()); con.add_widget(btn_cls)
        self.pop_graph = Popup(title="Dashboard Visual", content=con, size_hint=(0.95, 0.8)); self.pop_graph.open()

    def buka_riwayat_transaksi(self, _):
        con = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        self.in_search_hist = TextInput(hint_text="Cari Nama atau Keterangan...", size_hint_y=None, height=dp(55), multiline=False, font_size='18sp')
        self.in_search_hist.bind(text=lambda inst, val: self.update_tabel_riwayat(val))
        con.add_widget(self.in_search_hist)
        f_box = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(5))
        self.fr_h = Spinner(text="Semua", values=["Semua"] + [str(i).zfill(2) for i in range(1, 32)], font_size='16sp'); self.fr_b = Spinner(text="Semua", values=["Semua"] + [str(i).zfill(2) for i in range(1, 13)], font_size='16sp'); self.fr_t = Spinner(text=datetime.now().strftime("%Y"), values=["Semua"] + [str(i) for i in range(2025, 2101)], font_size='16sp')
        for s in [self.fr_h, self.fr_b, self.fr_t]: s.bind(text=lambda *a: self.update_tabel_riwayat(self.in_search_hist.text))
        f_box.add_widget(Label(text="Filter:", color=WARNA_TEKS_UTAMA, size_hint_x=0.15, bold=True)); f_box.add_widget(self.fr_h); f_box.add_widget(self.fr_b); f_box.add_widget(self.fr_t); con.add_widget(f_box)
        h_sc = ScrollView(do_scroll_y=False, size_hint_y=1); self.r_con = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(1720)) 
        h_row = BoxLayout(size_hint_y=None, height=dp(60))
        headers = [("NO",60), ("TANGGAL",150), ("MASUK",160), ("KELUAR",160), ("METODE",170), ("S. TOTAL",210), ("KETERANGAN",650), ("AKSI",130)]
        for t, w in headers: h_row.add_widget(BorderLabel(text=t, bold=True, size_hint_x=None, width=dp(w), font_size='14sp', bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER))
        self.r_con.add_widget(h_row); self.v_sc_r = ScrollView(do_scroll_x=False); self.ly_r = GridLayout(cols=1, spacing=1, size_hint_y=None); self.ly_r.bind(minimum_height=self.ly_r.setter('height'))
        self.v_sc_r.add_widget(self.ly_r); self.r_con.add_widget(self.v_sc_r); h_sc.add_widget(self.r_con); con.add_widget(h_sc)
        btn_f = BoxLayout(size_hint_y=None, height=dp(65), spacing=dp(10))
        b_pdf = Button(text="SIMPAN PDF", background_color=(0,0.6,0.2,1), color=(1,1,1,1), bold=True, font_size='17sp', background_normal=''); b_pdf.bind(on_release=self.ekspor_pdf_spesifik)
        b_sync = Button(text="SINKRON NAMA", background_color=(0.8, 0.4, 0, 1), color=(1,1,1,1), bold=True, font_size='17sp', background_normal=''); b_sync.bind(on_release=self.sinkronkan_keterangan_lama)
        b_cls = Button(text="TUTUP", background_color=WARNA_BIRU_CERAH, color=(1,1,1,1), bold=True, font_size='17sp', background_normal=''); b_cls.bind(on_release=lambda x: self.pop_r.dismiss())
        btn_f.add_widget(b_pdf); btn_f.add_widget(b_sync); btn_f.add_widget(b_cls); con.add_widget(btn_f)
        self.pop_r = Popup(title="RIWAYAT TRANSAKSI LENGKAP", content=con, size_hint=(0.98, 0.95)); self.update_tabel_riwayat(); self.pop_r.open()

    def update_tabel_riwayat(self, search_text=""):
        self.ly_r.clear_widgets(); st, sq, no = 0, 0, 1
        fh, fb, ft = self.fr_h.text, self.fr_b.text, self.fr_t.text
        keyword = search_text.lower()
        for tr in self.transaksi:
            v, m = tr.get('jumlah', 0), tr.get('metode', 'Tunai')
            mi, mo = (v if "KELUAR" not in m else 0), (v if "KELUAR" in m else 0)
            if "Tunai" in m: st += (mi - mo)
            else: sq += (mi - mo)
            dt = tr['tgl'].split('-')
            if (keyword in tr.get('nama','').lower() or keyword in tr.get('keterangan','').lower()):
                if (fh == "Semua" or dt[0] == fh) and (fb == "Semua" or tr['bln'] == fb) and (ft == "Semua" or tr['thn'] == ft):
                    bg_row = WARNA_BARIS_A if no % 2 != 0 else WARNA_BARIS_B
                    row = BoxLayout(size_hint_y=None, height=dp(55))
                    vals = [(str(no),60), (tr['tgl'],150), (f"{mi:,}",160), (f"{mo:,}",160), (m,170), (f"{st+sq:,}",210), (tr['keterangan'],650)]
                    for val, w in vals: row.add_widget(BorderLabel(text=str(val), size_hint_x=None, width=dp(w), font_size='14sp', bg_color=bg_row))
                    btn = Button(text="HAPUS", size_hint_x=None, width=dp(130), background_color=(0.8,0,0,1), font_size='13sp', bold=True, background_normal=''); btn.bind(on_release=lambda x, tid=tr['id']: self.hapus_tr_r(tid)); row.add_widget(btn); self.ly_r.add_widget(row); no += 1

    def ekspor_pdf_spesifik(self, _):
        if not FPDF: return
        p = os.path.join(self.path_folder, "Laporan_Riwayat_Filter.pdf"); pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.add_page(); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, txt="LAPORAN RIWAYAT TRANSAKSI KAS", ln=True, align='C'); pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(30, 144, 255); pdf.set_text_color(255, 255, 255)
        cols = [("No",10), ("Tgl",25), ("Masuk",30), ("Keluar",30), ("Metode",30), ("S. Total",35), ("Keterangan",117)]
        for txt, w in cols: pdf.cell(w, 8, txt, 1, 0, 'C', True)
        pdf.ln(); pdf.set_font("Arial", size=8); pdf.set_text_color(0, 0, 0); st, sq, no = 0, 0, 1; fh, fb, ft = self.fr_h.text, self.fr_b.text, self.fr_t.text
        for tr in self.transaksi:
            v, m = tr.get('jumlah', 0), tr.get('metode', 'Tunai')
            mi, mo = (v if "KELUAR" not in m else 0), (v if "KELUAR" in m else 0)
            if "Tunai" in m: st += (mi - mo)
            else: sq += (mi - mo)
            dt = tr['tgl'].split('-')
            if (fh == "Semua" or dt[0] == fh) and (fb == "Semua" or tr['bln'] == fb) and (ft == "Semua" or tr['thn'] == ft):
                fill = True if no % 2 == 0 else False; pdf.set_fill_color(240, 248, 255)
                pdf.cell(10, 7, str(no), 1, 0, 'C', fill); pdf.cell(25, 7, tr['tgl'], 1, 0, 'C', fill); pdf.cell(30, 7, f"{mi:,}", 1, 0, 'R', fill); pdf.cell(30, 7, f"{mo:,}", 1, 0, 'R', fill); pdf.cell(30, 7, m, 1, 0, 'C', fill); pdf.cell(35, 7, f"{st+sq:,}", 1, 0, 'R', fill); pdf.cell(117, 7, str(tr['keterangan'])[:80], 1, 0, 'L', fill); pdf.ln(); no += 1
        pdf.output(p); self.kirim_lampiran(p)

    def buka_db(self, _):
        con = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        self.in_search_agt = TextInput(hint_text="Cari Nama Anggota...", size_hint_y=None, height=dp(50), multiline=False)
        self.in_search_agt.bind(text=lambda inst, val: self.update_agt_list(val))
        con.add_widget(self.in_search_agt)
        bc = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5)); bc.add_widget(Label(text="Iuran:", color=WARNA_TEKS_UTAMA)); self.in_cfg_nom = TextInput(text=self.config.get("nom_iuran", "10000"), input_filter='int'); bc.add_widget(self.in_cfg_nom); bs = Button(text="SET", background_color=WARNA_BIRU_CERAH, bold=True); bs.bind(on_release=self.simpan_config); bc.add_widget(bs); con.add_widget(bc)
        f = GridLayout(cols=2, size_hint_y=None, height=dp(160), spacing=dp(8)); self.in_n_m = TextInput(hint_text="Nama Anggota"); self.in_w_m = TextInput(hint_text="No WhatsApp"); self.in_bln_gabung = Spinner(text="01", values=[str(i).zfill(2) for i in range(1, 13)], background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA); self.in_thn_gabung = Spinner(text="2025", values=[str(i) for i in range(2025, 2101)], background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA)
        f.add_widget(self.in_n_m); f.add_widget(self.in_w_m); f.add_widget(Label(text="Bulan Gabung:", color=WARNA_TEKS_UTAMA)); f.add_widget(self.in_bln_gabung); f.add_widget(Label(text="Tahun Gabung:", color=WARNA_TEKS_UTAMA)); f.add_widget(self.in_thn_gabung); con.add_widget(f)
        btns = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(10)); b1 = Button(text="SIMPAN", background_color=WARNA_BIRU_CERAH, bold=True); b1.bind(on_release=self.simpan_agt); b2 = Button(text="RESTORE", background_color=(0.8, 0.4, 0, 1), bold=True); b2.bind(on_release=self.buka_menu_restore); btns.add_widget(b1); btns.add_widget(b2); con.add_widget(btns)
        self.agt_list = GridLayout(cols=1, spacing=3, size_hint_y=None); self.agt_list.bind(minimum_height=self.agt_list.setter('height')); sc = ScrollView(); sc.add_widget(self.agt_list); con.add_widget(sc); self.pop_m = Popup(title="DATA ANGGOTA", content=con, size_hint=(0.95, 0.95)); self.update_agt_list(); self.pop_m.open()

    def update_agt_list(self, search_text=""):
        self.agt_list.clear_widgets(); keyword = search_text.lower()
        for n, data in sorted(self.anggota.items()):
            if keyword in n.lower():
                wa = data.get('wa', '') if isinstance(data, dict) else data
                btn = Button(text=f"{n} | {wa}", size_hint_y=None, height=dp(45), background_color=(1,1,1,1), color=WARNA_TEKS_UTAMA); btn.bind(on_release=lambda x, nm=n, d=data: self.isi_form_agt(nm, d)); self.agt_list.add_widget(btn)

    def buka_ceklis(self, search_text=""):
        if not isinstance(search_text, str): search_text = ""
        con = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        self.in_search_cek = TextInput(hint_text="Cari Nama Anggota...", text=search_text, size_hint_y=None, height=dp(50), multiline=False)
        self.in_search_cek.bind(on_text_validate=lambda x: self.update_ceklis_filter(x.text))
        con.add_widget(self.in_search_cek)
        top = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(5)); self.spin_thn_cek = Spinner(text=self.tahun_ceklis_aktif, values=[str(i) for i in range(2025, 2101)], size_hint_x=0.2, background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA); self.spin_thn_cek.bind(text=self.update_thn_ceklis); btn_pdf = Button(text="PDF CEKLIS", background_color=WARNA_BIRU_CERAH, size_hint_x=0.3, bold=True); btn_pdf.bind(on_release=self.ekspor_pdf_ceklis); top.add_widget(Label(text="Thn:", color=WARNA_TEKS_UTAMA, size_hint_x=0.1)); top.add_widget(self.spin_thn_cek); top.add_widget(btn_pdf); con.add_widget(top)
        tl = BoxLayout(orientation='horizontal'); col_n = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(180)); col_n.add_widget(BorderLabel(text="Nama", bold=True, size_hint_y=None, height=dp(45), bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER)); sc_n = ScrollView(do_scroll_x=False); grid_n = GridLayout(cols=1, size_hint_y=None, spacing=1); grid_n.bind(minimum_height=grid_n.setter('height')); sc_n.add_widget(grid_n); col_n.add_widget(sc_n)
        sc_h = ScrollView(do_scroll_y=False); bm = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(1400)); h = BoxLayout(size_hint_y=None, height=dp(45))
        for bln in ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Ags","Sep","Okt","Nov","Des"]: h.add_widget(BorderLabel(text=bln, bold=True, width=dp(90), size_hint_x=None, bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER))
        h.add_widget(BorderLabel(text="Status", bold=True, width=dp(130), size_hint_x=None, bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER)); h.add_widget(BorderLabel(text="Tunggakan", bold=True, width=dp(150), size_hint_x=None, bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER)); bm.add_widget(h); sc_c = ScrollView(do_scroll_x=False); grid_c = GridLayout(cols=14, size_hint_y=None, spacing=1); grid_c.bind(minimum_height=grid_c.setter('height')); sc_c.add_widget(grid_c); bm.add_widget(sc_c); sc_h.add_widget(bm); pt, nd = {}, int(self.config.get("nom_iuran", 10000))
        for tr in self.transaksi:
            if ("iuran" in tr['keterangan'].lower() or "minggu" in tr['keterangan'].lower()) and "KELUAR" not in tr['metode']: pt[tr['nama']] = pt.get(tr['nama'], 0) + (tr['jumlah'] // nd)
        now = datetime.now(); bln_s, thn_s = int(now.strftime("%m")), int(now.strftime("%Y"))
        filtered_members = [n for n in sorted(self.anggota.keys()) if search_text.lower() in n.lower()]
        for idx, nama in enumerate(filtered_members):
            bg_row = WARNA_BARIS_A if idx % 2 == 0 else WARNA_BARIS_B
            d_agt = self.anggota[nama]; bm_m, tm_m = int(d_agt.get("bln_masuk", 1)), int(d_agt.get("thn_masuk", 2025))
            grid_n.add_widget(ClickableLabel(text=nama, size_hint_y=None, height=dp(50), on_click=lambda n: self.kelola_transaksi_anggota(n), bg_color=bg_row))
            tot_b = pt.get(nama, 0); thn_v = int(self.tahun_ceklis_aktif)
            for m in range(1, 13):
                iv, ig = ((thn_v - 2025) * 12) + (m - 1), ((tm_m - 2025) * 12) + (bm_m - 1)
                if iv < ig: grid_c.add_widget(BorderLabel(text="N/A", size=(dp(90),dp(50)), size_hint=(None,None), bg_color=(0.95, 0.95, 0.95, 1)))
                elif tot_b > (iv - ig): grid_c.add_widget(Button(text="V", size=(dp(90),dp(50)), size_hint=(None,None), background_color=(0.2, 0.8, 0.4, 1), color=(1,1,1,1), background_normal=''))
                else: grid_c.add_widget(ClickableLabel(text="-", size=(dp(90),dp(50)), size_hint=(None,None), on_click=lambda x, n=nama, bl=m: self.konf_bayar_cek(n, bl), bg_color=bg_row))
            idx_s = ((thn_s - 2025) * 12) + (bln_s - 1); wajib = max(0, (idx_s - ig) + 1); tb = wajib - tot_b
            if tb < 0:
                grid_c.add_widget(BorderLabel(text="LEBIH", width=dp(130), size_hint_x=None, height=dp(50), color=(0,0.6,0.2,1), bold=True, bg_color=bg_row))
                grid_c.add_widget(BorderLabel(text=f"+{abs(tb) * nd:,}", width=dp(150), size_hint_x=None, height=dp(50), color=(0,0.6,0.2,1), bg_color=bg_row))
            elif tb == 0:
                grid_c.add_widget(BorderLabel(text="LUNAS", width=dp(130), size_hint_x=None, height=dp(50), color=(0,0,1,1), bold=True, bg_color=bg_row))
                grid_c.add_widget(BorderLabel(text="-", width=dp(150), size_hint_x=None, height=dp(50), bg_color=bg_row))
            else:
                grid_c.add_widget(BorderLabel(text="KURANG", width=dp(130), size_hint_x=None, height=dp(50), color=(1,0,0,1), bold=True, bg_color=bg_row))
                grid_c.add_widget(BorderLabel(text=f"{tb * nd:,}", width=dp(150), size_hint_x=None, height=dp(50), color=(1,0,0,1), font_size='13sp', bg_color=bg_row))
        tl.add_widget(col_n); tl.add_widget(sc_h); con.add_widget(tl); con.add_widget(Button(text="TUTUP", size_hint_y=None, height=dp(50), background_color=WARNA_BIRU_CERAH, bold=True, on_release=lambda x: self.pop_cek.dismiss())); self.pop_cek = Popup(title=f"CEKLIS IURAN {self.tahun_ceklis_aktif}", content=con, size_hint=(0.98,0.95)); self.pop_cek.open()

    def ekspor_pdf_ceklis(self, _):
        if not FPDF: return
        thn_v = int(self.tahun_ceklis_aktif); p = os.path.join(self.path_folder, f"Ceklis_{thn_v}.pdf"); pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.add_page(); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, txt=f"CEKLIS IURAN {thn_v}", ln=True, align='C'); pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(30, 144, 255); pdf.set_text_color(255, 255, 255); pdf.cell(40, 8, "Nama", 1, 0, 'C', True)
        for b in ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Ags","Sep","Okt","Nov","Des"]: pdf.cell(15, 8, b, 1, 0, 'C', True)
        pdf.cell(25, 8, "Status", 1, 0, 'C', True); pdf.cell(30, 8, "Tunggak", 1, 0, 'C', True); pdf.ln(); pdf.set_font("Arial", size=8); pdf.set_text_color(0,0,0); pt, nd = {}, int(self.config.get("nom_iuran", 10000))
        for tr in self.transaksi:
            if "iuran" in tr['keterangan'].lower() and "KELUAR" not in tr['metode']: pt[tr['nama']] = pt.get(tr['nama'], 0) + (tr['jumlah'] // nd)
        now = datetime.now(); bln_s, thn_s = int(now.strftime("%m")), int(now.strftime("%Y"))
        for i, nama in enumerate(sorted(self.anggota.keys())):
            fill = True if i % 2 == 1 else False; pdf.set_fill_color(240, 248, 255); d = self.anggota[nama]; bm, tm = int(d.get("bln_masuk", 1)), int(d.get("thn_masuk", 2025)); pdf.cell(40, 7, str(nama)[:20], 1, 0, 'L', fill); tb = pt.get(nama, 0)
            for m in range(1, 13):
                iv, ig = ((thn_v - 2025) * 12) + (m - 1), ((tm - 2025) * 12) + (bm - 1)
                txt = "N/A" if iv < ig else "V" if tb > (iv - ig) else "-"
                if txt == "V": pdf.set_text_color(0, 128, 0)
                pdf.cell(15, 7, txt, 1, 0, 'C', fill); pdf.set_text_color(0, 0, 0)
            is_s = ((thn_s - 2025) * 12) + (bln_s - 1); w = max(0, (is_s - ig) + 1); tun = w - tb
            if tun < 0: pdf.set_text_color(0, 100, 0); pdf.cell(25, 7, "LEBIH", 1, 0, 'C', fill); pdf.cell(30, 7, f"+{abs(tun) * nd:,}", 1, 0, 'C', fill)
            elif tun == 0: pdf.set_text_color(0, 0, 255); pdf.cell(25, 7, "LUNAS", 1, 0, 'C', fill); pdf.cell(30, 7, "-", 1, 0, 'C', fill)
            else: pdf.set_text_color(200, 0, 0); pdf.cell(25, 7, "KURANG", 1, 0, 'C', fill); pdf.cell(30, 7, f"{tun * nd:,}", 1, 0, 'C', fill)
            pdf.ln(); pdf.set_text_color(0, 0, 0)
        pdf.output(p); self.kirim_lampiran(p)

    def buka_p3k(self, _):
        con = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        self.in_search_p3k = TextInput(hint_text="Cari Nama Obat...", size_hint_y=None, height=dp(50), multiline=False)
        self.in_search_p3k.bind(text=lambda inst, val: self.update_tabel_p3k(val)); con.add_widget(self.in_search_p3k)
        input_p3k = GridLayout(cols=3, size_hint_y=None, height=dp(130), spacing=dp(5)); self.p3k_nama = TextInput(hint_text="Nama Obat"); self.p3k_jenis = Spinner(text="Pil", values=("Pil", "Kapsul", "Tablet", "Cair", "Lainnya"), background_color=(0.9, 0.95, 1, 1), color=WARNA_TEKS_UTAMA); self.p3k_exp = TextInput(hint_text="EXP"); self.p3k_in = TextInput(hint_text="IN"); self.p3k_out = TextInput(hint_text="OUT"); btn_s = Button(text="SIMPAN", background_color=WARNA_BIRU_CERAH, bold=True); btn_s.bind(on_release=self.simpan_p3k); input_p3k.add_widget(self.p3k_nama); input_p3k.add_widget(self.p3k_jenis); input_p3k.add_widget(self.p3k_exp); input_p3k.add_widget(self.p3k_in); input_p3k.add_widget(self.p3k_out); input_p3k.add_widget(btn_s); con.add_widget(input_p3k)
        h_sc = ScrollView(do_scroll_y=False, size_hint_y=1); tp = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(1050)); h_row = BoxLayout(size_hint_y=None, height=dp(45))
        for t, w in [("NO",60), ("TGL",110), ("NAMA",200), ("JENIS",110), ("IN",90), ("OUT",90), ("STOK",90), ("EXP",130), ("AKSI",170)]: 
            h_row.add_widget(BorderLabel(text=t, bold=True, size_hint_x=None, width=dp(w), font_size='12sp', bg_color=WARNA_HEADER, color=WARNA_TEKS_HEADER))
        tp.add_widget(h_row); self.ly_p3k = GridLayout(cols=1, spacing=1, size_hint_y=None); self.ly_p3k.bind(minimum_height=self.ly_p3k.setter('height')); vs = ScrollView(do_scroll_x=False); vs.add_widget(self.ly_p3k); tp.add_widget(vs); h_sc.add_widget(tp); con.add_widget(h_sc)
        btn_footer_layout = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(10)); b1 = Button(text="PDF P3K", background_color=(0, 0.7, 0, 1), bold=True); b1.bind(on_release=self.ekspor_pdf_p3k); b2 = Button(text="TUTUP", background_color=WARNA_BIRU_CERAH, bold=True, on_release=lambda x: self.pop_p3k.dismiss()); btn_footer_layout.add_widget(b1); btn_footer_layout.add_widget(b2); con.add_widget(btn_footer_layout)
        self.pop_p3k = Popup(title="STOK P3K", content=con, size_hint=(0.98, 0.95)); self.update_tabel_p3k(); self.pop_p3k.open()

    def update_tabel_p3k(self, search_text=""):
        self.ly_p3k.clear_widgets(); sm, no = {}, 1; keyword = search_text.lower()
        for d in self.p3k:
            stok_val = sm.get(d['nama'], 0) + d['in'] - d['out']; sm[d['nama']] = stok_val
            if keyword in d['nama'].lower():
                bg_baris = WARNA_BARIS_A if no % 2 != 0 else WARNA_BARIS_B
                row = BoxLayout(size_hint_y=None, height=dp(45)); vals = [(str(no),60), (d['tgl'],110), (d['nama'],200), (d['jenis'],110), (str(d['in']),90), (str(d['out']),90), (str(stok_val),90), (d['exp'],130)]
                for v, w in vals: row.add_widget(BorderLabel(text=v, size_hint_x=None, width=dp(w), font_size='12sp', bg_color=bg_baris))
                btn = Button(text="X", size_hint_x=None, width=dp(170), background_color=(0.8,0.2,0.2,1), bold=True); btn.bind(on_release=lambda x, tid=d['id']: self.hapus_p3k(tid)); row.add_widget(btn); self.ly_p3k.add_widget(row); no += 1

    def ekspor_pdf_p3k(self, _):
        if not FPDF: return
        p = os.path.join(self.path_folder, "Laporan_P3K.pdf"); pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.add_page(); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt="STOK P3K", ln=True, align='C'); pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(30, 144, 255); pdf.set_text_color(255, 255, 255)
        for txt, w in [("No",10), ("Tgl",30), ("Nama",60), ("Jenis",30), ("In",20), ("Out",20), ("Stok",20), ("Exp",35)]: pdf.cell(w, 8, txt, 1, 0, 'C', True)
        pdf.ln(); pdf.set_font("Arial", size=8); pdf.set_text_color(0, 0, 0); no, sm = 1, {}
        for d in self.p3k:
            fill = True if no % 2 == 0 else False; pdf.set_fill_color(240, 248, 255)
            sm[d['nama']] = sm.get(d['nama'], 0) + d['in'] - d['out']; pdf.cell(10, 7, str(no), 1, 0, 'C', fill); pdf.cell(30, 7, d['tgl'], 1, 0, 'C', fill); pdf.cell(60, 7, d['nama'], 1, 0, 'L', fill); pdf.cell(30, 7, d['jenis'], 1, 0, 'C', fill); pdf.cell(20, 7, str(d['in']), 1, 0, 'C', fill); pdf.cell(20, 7, str(d['out']), 1, 0, 'C', fill); pdf.cell(20, 7, str(sm[d['nama']]), 1, 0, 'C', fill); pdf.cell(35, 7, d['exp'], 1, 0, 'C', fill); pdf.ln(); no += 1
        pdf.output(p); self.kirim_lampiran(p)

    def kirim_lampiran(self, fp):
        if share: share.share(filepath=fp)
        else: Popup(title="Simpan Ke", content=Label(text=f"File: {fp}"), size_hint=(0.8,0.3)).open()

    def simpan_p3k(self, _):
        n = self.p3k_nama.text.strip()
        if n: 
            self.p3k.append({"id": str(datetime.now().timestamp()), "tgl": datetime.now().strftime("%d-%m-%Y"), "nama": n, "jenis": self.p3k_jenis.text, "in": int(self.p3k_in.text or 0), "out": int(self.p3k_out.text or 0), "exp": self.p3k_exp.text or "-"}); 
            self.save_data(); self.update_tabel_p3k("")

    def hapus_p3k(self, tid): self.p3k = [d for d in self.p3k if d['id'] != tid]; self.save_data(); self.update_tabel_p3k("")

    def simpan_agt(self, _):
        n = self.in_n_m.text.strip()
        if n: self.anggota[n] = {"wa": self.in_w_m.text.strip(), "bln_masuk": self.in_bln_gabung.text, "thn_masuk": self.in_thn_gabung.text}; self.save_data(); self.update_agt_list("")

    def isi_form_agt(self, nm, data):
        self.in_n_m.text = nm
        if isinstance(data, dict): self.in_w_m.text, self.in_bln_gabung.text, self.in_thn_gabung.text = data.get("wa", ""), data.get("bln_masuk", "01"), data.get("thn_masuk", "2025")

    def update_ceklis_filter(self, val): self.pop_cek.dismiss(); self.buka_ceklis(val)
    def update_thn_ceklis(self, s, t): self.tahun_ceklis_aktif = t; self.pop_cek.dismiss(); self.buka_ceklis(None)
    def sinkronkan_keterangan_lama(self, _):
        count = 0
        for tr in self.transaksi:
            n, k = tr.get('nama', ''), tr.get('keterangan', '')
            if n and n.lower() not in k.lower(): tr['keterangan'] = f"{k} - {n}"; count += 1
        if count > 0: self.save_data(); self.update_tabel_riwayat(""); Popup(title="Sukses", content=Label(text=f"{count} data diperbarui."), size_hint=(0.6, 0.3)).open()

    def hapus_tr_r(self, tid): self.transaksi = [t for t in self.transaksi if t['id'] != tid]; self.save_data(); self.update_tabel_riwayat(""); self.hitung_rekap()
    def konf_bayar_cek(self, nama, bulan_idx):
        lb = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"]
        self.in_cari.text, self.in_nom.text, self.spin_ket.text = nama, self.config.get("nom_iuran", "10000"), f"Iuran {lb[bulan_idx-1]}"; self.in_bulan.text, self.in_tahun.text = str(bulan_idx).zfill(2), self.tahun_ceklis_aktif; self.pop_cek.dismiss()
    def auto_complete(self, instance, value):
        if value:
            self.dropdown.dismiss(); self.dropdown = DropDown()
            for n in [x for x in self.anggota if value.lower() in x.lower()][:5]:
                btn = Button(text=n, size_hint_y=None, height=dp(45), background_color=(1,1,1,1), color=WARNA_TEKS_UTAMA); btn.bind(on_release=lambda b: self.set_cari(b.text)); self.dropdown.add_widget(btn)
            if self.dropdown.children: self.dropdown.open(instance)
    def set_cari(self, n): self.in_cari.text = n; self.dropdown.dismiss()
    def simpan_config(self, _): self.config["nom_iuran"] = self.in_cfg_nom.text; self.save_data()

    def format_wa(self, wa):
        wa_str = str(wa).strip()
        if wa_str.startswith('0'): return '62' + wa_str[1:]
        return wa_str

    def proses_bayar(self, sw=False):
        n, nm = self.in_cari.text.strip(), self.in_nom.text.strip()
        if not n or not nm: return
        tgl_m = f"{self.in_hari.text}-{self.in_bulan.text}-{self.in_tahun.text}"; ket_asli = self.spin_ket.text
        ket_lengkap = f"{ket_asli} - {n}" if n.lower() not in ket_asli.lower() else ket_asli
        trx_id = datetime.now().strftime("%Y%m%d") + str(int(datetime.now().timestamp()))[-4:]
        self.transaksi.append({"id": str(datetime.now().timestamp()), "nama": n, "metode": self.spin_met.text, "tgl": tgl_m, "bln": self.in_bulan.text, "thn": self.in_tahun.text, "jumlah": int(nm), "keterangan": ket_lengkap})
        self.save_data(); self.hitung_rekap()
        
        if sw and n in self.anggota:
            wa = self.anggota[n].get('wa','') if isinstance(self.anggota[n], dict) else self.anggota[n]
            wa_f = self.format_wa(wa)
            msg = (
                f"*BUKTI PEMBAYARAN KAS RESMI* ✨\n\n"
                f"Assalamu’alaikum Bapak/Ibu *{n}*.\n\n"
                f"Alhamdulillah, telah kami terima dana iuran Anda dengan rincian sebagai berikut:\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📝 *KETERANGAN PEMBAYARAN*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📅 Tanggal: {tgl_m}\n"
                f"💳 Metode: *{self.spin_met.text}*\n"
                f"💰 Nominal: *Rp{int(nm):,}*\n"
                f"📌 Keperluan: {ket_asli}\n"
                f"🆔 Ref ID: {trx_id}\n\n"
                f"✅ Status: *TERVERIFIKASI & MASUK KAS*\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"Jazakumullah Khairan Katsiran. Semoga iuran ini menjadi berkah. Amin. 🤲\n\n"
                f"Salam takzim,\n*Bendahara Kas Blangking*"
            )
            webbrowser.open(f"https://wa.me/{wa_f}?text={urllib.parse.quote(msg)}")
        self.in_cari.text = ""; self.in_nom.text = ""

    def buka_pengingat(self, _):
        con = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        for t, m, c in [("PILIH SEBAGIAN (MULTI)", "multi", (0, 0.5, 0.8, 1)), ("JADWAL BESOK (SEMUA)", "besok", WARNA_BIRU_CERAH), ("TUNGGAKAN (SEMUA)", "debt", (0.8, 0.4, 0, 1)), ("LUNAS / LEBIH (SEMUA)", "lunas", (0, 0.6, 0.2, 1))]:
            b = Button(text=t, size_hint_y=None, height=dp(65), background_color=c, color=(1,1,1,1), bold=True); b.bind(on_release=self.buka_pilih_sebagian if m == "multi" else lambda x, md=m: self.list_remind(md))
            con.add_widget(b)
        self.pop_remind_root = Popup(title="WHATSAPP REMAINDER", content=con, size_hint=(0.9, 0.7)); self.pop_remind_root.open()

    def buka_pilih_sebagian(self, _):
        self.pop_remind_root.dismiss(); con = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        self.selected_members = []; sc = ScrollView(); ly = GridLayout(cols=1, spacing=dp(5), size_hint_y=None); ly.bind(minimum_height=ly.setter('height'))
        for nama in sorted(self.anggota.keys()):
            btn = ToggleButton(text=nama, size_hint_y=None, height=dp(50), background_color=(0.9, 0.9, 0.9, 1), color=WARNA_TEKS_UTAMA)
            btn.bind(on_release=lambda x, n=nama: self.update_selection(n, x.state)); ly.add_widget(btn)
        sc.add_widget(ly); con.add_widget(sc); self.spin_tipe_part = Spinner(text="Tunggakan", values=("Besok", "Tunggakan", "Lunas"), size_hint_y=None, height=dp(50), background_color=WARNA_BIRU_CERAH)
        con.add_widget(self.spin_tipe_part); b_kirim = Button(text="KIRIM KE YANG DIPILIH", size_hint_y=None, height=dp(60), background_color=(0, 0.6, 0.2, 1), bold=True)
        b_kirim.bind(on_release=self.proses_kirim_sebagian); con.add_widget(b_kirim); self.pop_part = Popup(title="Pilih Anggota", content=con, size_hint=(0.95, 0.9)); self.pop_part.open()

    def update_selection(self, nama, state):
        if state == 'down' and nama not in self.selected_members: self.selected_members.append(nama)
        elif state == 'normal' and nama in self.selected_members: self.selected_members.remove(nama)

    def proses_kirim_sebagian(self, _):
        if not self.selected_members: return
        tipe = self.spin_tipe_part.text.lower(); mode_map = {"besok": "besok", "tunggakan": "debt", "lunas": "lunas"}
        for nama in self.selected_members:
            d = self.anggota[nama]; nd = int(self.config.get("nom_iuran", 10000))
            bt = sum((tr['jumlah'] // nd) for tr in self.transaksi if tr['nama'] == nama and ("iuran" in tr['keterangan'].lower()) and "KELUAR" not in tr['metode'])
            idx_g = ((int(d.get('thn_masuk', 2025)) - 2025) * 12) + (int(d.get('bln_masuk', 1)) - 1); idx_s = ((datetime.now().year - 2025) * 12) + (datetime.now().month - 1); sisa = max(0, (idx_s - idx_g) + 1) - bt
            self.kirim_wa(nama, d.get('wa', ''), sisa, mode_map[tipe])
        self.pop_part.dismiss()

    def list_remind(self, mode):
        self.pop_remind_root.dismiss(); con = BoxLayout(orientation='vertical', padding=dp(10)); sc = ScrollView(); ly = GridLayout(cols=1, spacing=3, size_hint_y=None); ly.bind(minimum_height=ly.setter('height')); nd = int(self.config.get("nom_iuran", 10000))
        for nama, data in sorted(self.anggota.items()):
            bt = sum((tr['jumlah'] // nd) for tr in self.transaksi if tr['nama'] == nama and ("iuran" in tr['keterangan'].lower()) and "KELUAR" not in tr['metode'])
            idx_g = ((int(data.get('thn_masuk', 2025)) - 2025) * 12) + (int(data.get('bln_masuk', 1)) - 1); idx_s = ((datetime.now().year - 2025) * 12) + (datetime.now().month - 1); sisa = max(0, (idx_s - idx_g) + 1) - bt
            if (mode=="debt" and sisa>0) or (mode=="lunas" and sisa<=0) or (mode=="besok"):
                btn = Button(text=f"{nama} ({'Tagih' if sisa>0 else 'Lunas'})", size_hint_y=None, height=dp(55), background_color=(1,1,1,1), color=WARNA_TEKS_UTAMA)
                btn.bind(on_release=lambda x, n=nama, w=data.get('wa',''), s=sisa: self.kirim_wa(n, w, s, mode)); ly.add_widget(btn)
        sc.add_widget(ly); con.add_widget(sc); Popup(title=f"Target: {mode}", content=con, size_hint=(0.95, 0.9)).open()

    def kirim_wa(self, n, w, s, md):
        wa_f = self.format_wa(w); nd = int(self.config.get("nom_iuran", 10000))
        if md == "besok":
            msg = f"Assalamu’alaikum *{n}*. Izin mengingatkan besok jadwal iuran kas *Rp{nd:,}*. Bisa via Tunai/QRIS. Syukron. 🙏"
        elif s > 0:
            msg = f"Assalamu’alaikum *{n}*. Mohon izin iuran kas tertunda *{int(s)} bulan* (Rp{int(s*nd):,}). Semoga dimudahkan rezekinya. Syukron. 🙏"
        else:
            msg = f"Assalamu’alaikum *{n}*. Status kas Anda saat ini *LUNAS*. Terima kasih atas kedisiplinannya. Berkah selalu! 🌟"
        webbrowser.open(f"https://wa.me/{wa_f}?text={urllib.parse.quote(msg)}")

    def kelola_transaksi_anggota(self, nama):
        con = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        with con.canvas.before: Color(1,1,1,1); Rectangle(pos=con.pos, size=con.size)
        ly = GridLayout(cols=1, spacing=2, size_hint_y=None); ly.bind(minimum_height=ly.setter('height'))
        for tr in reversed(self.transaksi):
            if tr['nama'] == nama:
                row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
                row.add_widget(Label(text=f"{tr['tgl']} | Rp{tr['jumlah']:,}", color=WARNA_TEKS_UTAMA))
                btn = Button(text="HAPUS", size_hint_x=None, width=dp(80), background_color=(0.8, 0, 0, 1))
                btn.bind(on_release=lambda x, tid=tr['id']: self.hapus_dari_ceklis(tid)); row.add_widget(btn); ly.add_widget(row)
        sc = ScrollView(); sc.add_widget(ly); con.add_widget(sc); b_cls = Button(text="TUTUP", size_hint_y=None, height=dp(50), background_color=WARNA_BIRU_CERAH); b_cls.bind(on_release=lambda x: self.pop_kelola.dismiss()); con.add_widget(b_cls); self.pop_kelola = Popup(title=f"Riwayat: {nama}", content=con, size_hint=(0.9, 0.7)); self.pop_kelola.open()

    def hapus_dari_ceklis(self, tid):
        self.transaksi = [t for t in self.transaksi if t['id'] != tid]
        self.save_data(); self.hitung_rekap(); self.pop_kelola.dismiss()

# --- APP RUNNER ---
class KasApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='utama'))
        return sm

if __name__ == '__main__':
    KasApp().run()
