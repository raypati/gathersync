import customtkinter as ctk
import tkinter as tk
import sqlite3
import tkinter.messagebox as messagebox
import datetime
import hashlib
from tkcalendar import Calendar

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==========================================
# 0. DESIGN SYSTEM & STRUKTUR TIM GATHERSYNC KEL.5 RPL
# ==========================================
COLOR = {
    "bg_root":        "#0f1115",
    "bg_sidebar":     "#0a0c0f",
    "bg_card":        "#1b1e22",
    "bg_card_alt":    "#22262b",
    "bg_input":       "#1b1e22",
    "border":         "#2a2e34",
    "primary":        "#4f7cff",
    "primary_hover":  "#3d63d6",
    "accent":         "#a855f7",
    "success":        "#22c55e",
    "success_hover":  "#1aa34e",
    "danger":         "#ef4444",
    "danger_hover":   "#c9342f",
    "warning":        "#f59e0b",
    "info":           "#38bdf8",
    "text_main":      "#eef1f5",
    "text_sub":       "#9aa3af",
    "text_faint":     "#6b7280",
}

FONT_H1 = ("Segoe UI", 22, "bold")
FONT_H2 = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_BODY_BOLD = ("Segoe UI", 12, "bold")
FONT_SMALL = ("Segoe UI", 10)

MENU_ITEMS = [
    ("dash",     "🏠", "Dashboard Trip"),
    ("kas",      "💳", "Registrasi & Kas"),
    ("plot",     "🚌", "Plotting Kursi & Multi-Unit"),
    ("itin",     "🗓️", "Itinerary"),
    ("manifest", "📄", "Manifest & Audit PDF"),
]

LEADER_DAN_TIM = {
    "Budi Santoso": ["Bayu", "Bunga", "Angga"],
    "Siti Rahma": ["Rian", "Dewi", "Fajar", "Siti"],
    "Andi Pratama": ["Doni", "Putri", "Reza"],
    "Rina Melati": ["Siska", "Yoga", "Tina", "Dimas"],
    "Joko Anwar": ["Hendra", "Lestari", "Roni"],
    "Dewi Lestari": ["Maya", "Agung", "Citra", "Eko"]
}
LIST_LEADER = list(LEADER_DAN_TIM.keys())

RULE_DP_MIN_PERSEN = 30
RULE_RISIKO_H_MINUS = 3
RULE_SELANG_HARI = 2  # selisih minimal antar trip untuk leader yang sama

STATUS_STYLE = {
    "Belum Bayar": {"color": "danger",  "icon": "○"},
    "DP Diterima": {"color": "warning", "icon": "◐"},
    "Cicilan":     {"color": "info",    "icon": "◕"},
    "Lunas":       {"color": "success", "icon": "●"},
}

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def hitung_rekomendasi_armada(jumlah_peserta):
    if jumlah_peserta <= 9:
        return "Private Car / Transport Kecil (<10 org)"
    elif jumlah_peserta <= 16:
        return "Microbus / HiAce (Kapasitas 16 Kursi)"
    elif jumlah_peserta <= 30:
        return "Medium Bus (Kapasitas 30 Kursi)"
    else:
        jumlah_unit = (jumlah_peserta // 45) + (1 if jumlah_peserta % 45 > 0 else 0)
        return f"Big Bus (Multi-Unit: {jumlah_unit} Unit Kendaraan)"

def hitung_kategori(total, dibayar):
    total = total or 0
    dibayar = dibayar or 0
    persen = (dibayar / total * 100) if total > 0 else 0
    persen = max(0, min(persen, 100))
    if persen <= 0:
        kategori = "Belum Bayar"
    elif persen < RULE_DP_MIN_PERSEN:
        kategori = "DP Diterima"
    elif persen < 100:
        kategori = "Cicilan"
    else:
        kategori = "Lunas"
    return kategori, persen

def hitung_status_risiko(tanggal_keberangkatan_str):
    if not tanggal_keberangkatan_str:
        return None
    try:
        tgl = datetime.datetime.strptime(tanggal_keberangkatan_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (tgl - datetime.date.today()).days

def cek_bentrok_jadwal(conn, leader_dipilih, tgl_baru_str, exclude_trip_id=None):
    # bentrok kalau leader yang sama punya trip dengan selisih < RULE_SELANG_HARI hari
    if not tgl_baru_str or not leader_dipilih or leader_dipilih == "Pilih Leader":
        return False, ""
    try:
        tgl_baru = datetime.datetime.strptime(tgl_baru_str, "%Y-%m-%d").date()
    except ValueError:
        return False, ""

    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, nama_trip, leader, tanggal_keberangkatan FROM trip WHERE tanggal_keberangkatan IS NOT NULL").fetchall()
    for t_id, t_nama, t_ldr, t_tgl_str in rows:
        if exclude_trip_id and t_id == exclude_trip_id:
            continue
        if not t_ldr:
            continue
        try:
            tgl_ada = datetime.datetime.strptime(t_tgl_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        selisih = abs((tgl_baru - tgl_ada).days)
        if selisih < RULE_SELANG_HARI and t_ldr == leader_dipilih:
            return True, f"Leader '{leader_dipilih}' sudah bertugas di trip '{t_nama}' pada tanggal {t_tgl_str} (selisih {selisih} hari, minimal {RULE_SELANG_HARI} hari)."
    return False, ""

# ==========================================
# 1. KONFIGURASI DATABASE & LOGIKA INTI
# ==========================================
def setup_database():
    conn = sqlite3.connect("gathersync.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ("admin", hash_password("123")))
    else:
        # password lama (teks biasa) diubah jadi hash
        for a_id, a_pass in cursor.execute("SELECT id, password FROM admin").fetchall():
            if a_pass is not None and len(a_pass) != 64:
                cursor.execute("UPDATE admin SET password=? WHERE id=?", (hash_password(a_pass), a_id))

    cursor.execute('''CREATE TABLE IF NOT EXISTS trip (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nama_trip TEXT, leader TEXT, tim TEXT,
                        tanggal_keberangkatan TEXT, harga_trip REAL DEFAULT 0)''')

    try:
        cursor.execute("ALTER TABLE trip ADD COLUMN harga_trip REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS peserta (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, id_trip INTEGER,
                        nama TEXT, total_tagihan REAL, nominal_bayar REAL,
                        sisa_tagihan REAL, status TEXT, kursi_bus TEXT, unit_bus TEXT DEFAULT 'Unit 1')''')

    try:
        cursor.execute("ALTER TABLE peserta ADD COLUMN unit_bus TEXT DEFAULT 'Unit 1'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS itinerary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, id_trip INTEGER,
                        hari TEXT, jam TEXT, kegiatan TEXT,
                        titik_kumpul TEXT, dresscode TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, id_trip INTEGER,
                        nama TEXT, aksi TEXT, keterangan TEXT, waktu TEXT)''')
    conn.commit()
    return conn

def catat_audit(conn, id_trip, nama, aksi, keterangan):
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.cursor().execute("INSERT INTO audit_log (id_trip, nama, aksi, keterangan, waktu) VALUES (?, ?, ?, ?, ?)", (id_trip, nama, aksi, keterangan, waktu))
    conn.commit()

# ==========================================
# 2. ANTARMUKA APLIKASI
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def draw_gradient(canvas, width, height, color_from, color_to, vertical=True):
    canvas.delete("gradient")
    r1, g1, b1 = canvas.winfo_rgb(color_from)
    r2, g2, b2 = canvas.winfo_rgb(color_to)
    steps = height if vertical else width
    steps = max(steps, 1)
    for i in range(steps):
        ratio = i / steps
        nr = int(r1 + (r2 - r1) * ratio) >> 8
        ng = int(g1 + (g2 - g1) * ratio) >> 8
        nb = int(b1 + (b2 - b1) * ratio) >> 8
        color = f"#{nr:02x}{ng:02x}{nb:02x}"
        if vertical:
            canvas.create_line(0, i, width, i, tags=("gradient",), fill=color)
        else:
            canvas.create_line(i, 0, i, height, tags=("gradient",), fill=color)
    canvas.tag_lower("gradient")

class GatherSyncApp(ctk.CTk):
    def __init__(self, db_conn):
        super().__init__()
        self.conn = db_conn
        self.current_trip_id = None
        self.current_trip_name = None
        self.current_trip_tanggal = None
        self.current_trip_harga = 0.0
        self.edit_trip_id = None
        self.sidebar_buttons = {}

        self.title("GatherSync — Open Trip & Travel Manager")
        self.geometry("1320x780")
        self.configure(fg_color=COLOR["bg_root"])
        self.setup_login_frame()

    def make_gradient_banner(self, parent, height=50, title="", subtitle=""):
        wrapper = ctk.CTkFrame(parent, height=height, corner_radius=10, fg_color="transparent")
        wrapper.pack(fill="x", padx=20, pady=(4, 8))
        wrapper.pack_propagate(False)
        canvas = tk.Canvas(wrapper, height=height, highlightthickness=0, bd=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        def redraw(event=None):
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w > 1 and h > 1:
                draw_gradient(canvas, w, h, COLOR["primary"], COLOR["accent"], vertical=False)
                canvas.delete("gradient_text")
                canvas.create_text(18, h * 0.38, anchor="w", text=title, fill="#ffffff", font=("Segoe UI", 15, "bold"), tags=("gradient_text",))
                canvas.create_text(18, h * 0.72, anchor="w", text=subtitle, fill="#e8e6ff", font=("Segoe UI", 9), tags=("gradient_text",))
        canvas.bind("<Configure>", redraw)
        return wrapper

    def make_card(self, parent, **kwargs):
        defaults = dict(corner_radius=10, fg_color=COLOR["bg_card"], border_width=1, border_color=COLOR["border"])
        defaults.update(kwargs)
        return ctk.CTkFrame(parent, **defaults)

    def make_primary_btn(self, parent, text, command, **kwargs):
        defaults = dict(fg_color=COLOR["primary"], hover_color=COLOR["primary_hover"], corner_radius=6, font=FONT_BODY_BOLD, text_color="#ffffff")
        defaults.update(kwargs)
        return ctk.CTkButton(parent, text=text, command=command, **defaults)

    def make_danger_btn(self, parent, text, command, **kwargs):
        defaults = dict(fg_color=COLOR["danger"], hover_color=COLOR["danger_hover"], corner_radius=6, font=FONT_SMALL, width=50, height=24, text_color="#ffffff")
        defaults.update(kwargs)
        return ctk.CTkButton(parent, text=text, command=command, **defaults)

    def make_entry(self, parent, **kwargs):
        defaults = dict(height=32, corner_radius=6, fg_color=COLOR["bg_input"], border_color=COLOR["border"], text_color=COLOR["text_main"])
        defaults.update(kwargs)
        return ctk.CTkEntry(parent, **defaults)

    def make_badge(self, parent, text, color_key, icon=""):
        badge = ctk.CTkFrame(parent, corner_radius=999, fg_color=COLOR[color_key], height=20)
        lbl = ctk.CTkLabel(badge, text=f"{icon} {text}".strip(), font=("Segoe UI", 9, "bold"), text_color="#ffffff")
        lbl.pack(padx=6, pady=2)
        return badge

    def stat_card_mini(self, parent, label, value, accent=None):
        accent = accent or COLOR["primary"]
        card = self.make_card(parent, height=45)
        card.pack_propagate(False)
        bar = ctk.CTkFrame(card, width=3, fg_color=accent, corner_radius=2)
        bar.pack(side="left", fill="y", padx=(0, 8), pady=8)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(side="left", fill="both", expand=True, pady=6, padx=(0, 8))
        ctk.CTkLabel(inner, text=f"{value}  —  {label}", font=("Segoe UI", 11, "bold"), text_color=COLOR["text_main"]).pack(anchor="w")
        return card

    def buka_kalendar(self, judul, on_pick):
        top = ctk.CTkToplevel(self)
        top.title(judul)
        top.geometry("340x300")
        top.attributes("-topmost", True)
        top.grab_set()
        today = datetime.date.today()
        cal = Calendar(top, selectmode='day', year=today.year, month=today.month, day=today.day,
                       background='#1f538d', foreground='white', headersbackground='#2a2e34', normalbackground='#1b1e22',
                       normalforeground='white', bordercolor='#2a2e34')
        cal.pack(padx=15, pady=15, fill="both", expand=True)

        def set_tgl():
            on_pick(cal.selection_get().strftime("%Y-%m-%d"))
            top.destroy()

        ctk.CTkButton(top, text="Pilih Tanggal Ini", fg_color=COLOR["success"], hover_color=COLOR["success_hover"], command=set_tgl).pack(pady=(0, 15))

    # ---------- Login ----------
    def setup_login_frame(self):
        self.login_frame = ctk.CTkFrame(self, fg_color=COLOR["bg_root"])
        self.login_frame.pack(fill="both", expand=True)
        bg_canvas = tk.Canvas(self.login_frame, highlightthickness=0, bd=0)
        bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        def redraw_bg(event=None):
            w = bg_canvas.winfo_width()
            h = bg_canvas.winfo_height()
            if w > 1 and h > 1:
                draw_gradient(bg_canvas, w, h, "#151a2e", "#1c1030", vertical=True)
        bg_canvas.bind("<Configure>", redraw_bg)

        box = self.make_card(self.login_frame, width=380, height=440, corner_radius=18, fg_color=COLOR["bg_card"])
        box.place(relx=0.5, rely=0.5, anchor="center")
        box.pack_propagate(False)

        badge = ctk.CTkFrame(box, width=64, height=64, corner_radius=32, fg_color=COLOR["primary"])
        badge.pack(pady=(36, 12))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="🚌", font=ctk.CTkFont(size=28)).pack(expand=True)

        ctk.CTkLabel(box, text="GatherSync", font=("Segoe UI", 22, "bold"), text_color=COLOR["text_main"]).pack()
        ctk.CTkLabel(box, text="Open Trip Management Portal", font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(pady=(2, 20))

        self.entry_user = self.make_entry(box, placeholder_text="Username", width=280)
        self.entry_user.pack(pady=6)
        self.entry_pass = self.make_entry(box, placeholder_text="Password", show="•", width=280)
        self.entry_pass.pack(pady=6)
        self.entry_pass.bind("<Return>", lambda e: self.proses_login())

        self.make_primary_btn(box, "Masuk Sistem", self.proses_login, width=280, height=38).pack(pady=(20, 8))
        ctk.CTkLabel(box, text="default: admin / 123", font=FONT_SMALL, text_color=COLOR["text_faint"]).pack()

    def proses_login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get()
        cursor = self.conn.cursor()
        # password dibandingkan dalam bentuk hash
        cursor.execute("SELECT id FROM admin WHERE username=? AND password=?", (u, hash_password(p)))
        if cursor.fetchone():
            self.login_frame.destroy()
            self.setup_main_application()
        else:
            messagebox.showerror("Gagal", "Username atau Password salah!")

    def proses_logout(self):
        if messagebox.askyesno("Konfirmasi", "Keluar dari sesi admin?"):
            for widget in self.winfo_children():
                widget.destroy()
            self.current_trip_id = None
            self.current_trip_name = None
            self.current_trip_tanggal = None
            self.current_trip_harga = 0.0
            self.edit_trip_id = None
            self.sidebar_buttons = {}
            self.setup_login_frame()

    # ---------- Main shell ----------
    def setup_main_application(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLOR["bg_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(len(MENU_ITEMS) + 3, weight=1)

        accent_strip = tk.Canvas(self.sidebar, width=240, height=4, highlightthickness=0, bd=0)
        accent_strip.grid(row=0, column=0, sticky="ew")
        self.after(50, lambda: draw_gradient(accent_strip, 240, 4, COLOR["primary"], COLOR["accent"], vertical=False))

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=1, column=0, padx=18, pady=(16, 6), sticky="w")
        ctk.CTkLabel(brand, text="🚌  GatherSync", font=("Segoe UI", 17, "bold"), text_color=COLOR["text_main"]).pack(anchor="w")

        active_card = self.make_card(self.sidebar, fg_color=COLOR["bg_card"])
        active_card.grid(row=2, column=0, padx=16, pady=(12, 16), sticky="ew")
        ctk.CTkLabel(active_card, text="TRIP AKTIF", font=("Segoe UI", 9, "bold"), text_color=COLOR["text_faint"]).pack(anchor="w", padx=12, pady=(8, 0))
        self.lbl_active_trip = ctk.CTkLabel(active_card, text="Belum dipilih", font=FONT_BODY_BOLD, text_color=COLOR["warning"], wraplength=170, justify="left")
        self.lbl_active_trip.pack(anchor="w", padx=12, pady=(2, 2))
        self.lbl_active_risk = ctk.CTkLabel(active_card, text="", font=FONT_SMALL, text_color=COLOR["danger"], wraplength=170, justify="left")
        self.lbl_active_risk.pack(anchor="w", padx=12, pady=(0, 8))

        handlers = {
            "dash": self.show_dash_frame,
            "kas": self.show_kas_frame,
            "plot": self.show_plot_frame,
            "itin": self.show_itin_frame,
            "manifest": self.show_manifest_frame,
        }
        for i, (key, icon, label) in enumerate(MENU_ITEMS):
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {icon}    {label}", anchor="w", width=200, height=38, corner_radius=6,
                font=FONT_BODY, fg_color="transparent", hover_color=COLOR["bg_card"], text_color=COLOR["text_sub"],
                command=handlers[key],
            )
            btn.grid(row=3 + i, column=0, padx=16, pady=3)
            self.sidebar_buttons[key] = btn

        self.make_danger_btn(self.sidebar, "⏻  Logout", self.proses_logout, width=200, height=34, font=FONT_BODY_BOLD).grid(
            row=len(MENU_ITEMS) + 4, column=0, padx=16, pady=18, sticky="s")

        self.dash_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kas_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.plot_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.itin_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.manifest_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.setup_dash_frame()
        self.setup_kas_frame()
        self.setup_plot_frame()
        self.setup_itin_frame()
        self.setup_manifest_frame()

        self.show_dash_frame()

    def set_active_menu(self, key):
        for k, btn in self.sidebar_buttons.items():
            if k == key:
                btn.configure(fg_color=COLOR["primary"], text_color="#ffffff", hover_color=COLOR["primary_hover"])
            else:
                btn.configure(fg_color="transparent", text_color=COLOR["text_sub"], hover_color=COLOR["bg_card"])

    def update_risk_banner(self):
        if not self.current_trip_id:
            self.lbl_active_risk.configure(text="")
            return
        sisa_hari = hitung_status_risiko(self.current_trip_tanggal)
        if sisa_hari is None:
            self.lbl_active_risk.configure(text="")
            return
        belum_lunas = self.conn.cursor().execute("SELECT COUNT(*) FROM peserta WHERE id_trip=? AND status != 'Lunas'", (self.current_trip_id,)).fetchone()[0]
        if 0 <= sisa_hari <= RULE_RISIKO_H_MINUS and belum_lunas > 0:
            self.lbl_active_risk.configure(text=f"⚠ H-{sisa_hari} · {belum_lunas} belum lunas", text_color=COLOR["danger"])
        elif sisa_hari < 0:
            self.lbl_active_risk.configure(text="")
        else:
            self.lbl_active_risk.configure(text=f"H-{sisa_hari} menuju keberangkatan", text_color=COLOR["text_sub"])

    # --- MENU 1: DASHBOARD ---
    def setup_dash_frame(self):
        self.make_gradient_banner(self.dash_frame, height=50, title="Manajemen Open Trip", subtitle="Tetapkan harga flat di awal · Rekomendasi armada otomatis berdasarkan jumlah peserta")

        self.dash_stats = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        self.dash_stats.pack(fill="x", padx=20, pady=(0, 4))

        form_frame = self.make_card(self.dash_frame)
        form_frame.pack(fill="x", padx=20, pady=4)

        grid_form = ctk.CTkFrame(form_frame, fg_color="transparent")
        grid_form.pack(fill="x", padx=12, pady=8)

        self.entry_trip = self.make_entry(grid_form, placeholder_text="Nama Trip (Cth: Open Trip Anyer)", width=180)
        self.entry_trip.grid(row=0, column=0, padx=3, pady=3)

        self.drop_leader = ctk.CTkComboBox(grid_form, values=LIST_LEADER, width=170, height=32, corner_radius=6,
                                           fg_color=COLOR["bg_input"], border_color=COLOR["border"], button_color=COLOR["primary"],
                                           command=self.on_leader_selected)
        self.drop_leader.grid(row=0, column=1, padx=3, pady=3)
        self.drop_leader.set("Pilih Leader")

        self.lbl_info_tim = ctk.CTkLabel(grid_form, text="Tim: (Pilih Leader)", font=FONT_SMALL, text_color=COLOR["text_sub"])
        self.lbl_info_tim.grid(row=0, column=2, padx=6, pady=3, sticky="w")

        self.entry_harga = self.make_entry(grid_form, placeholder_text="Harga Flat /Org (Rp)", width=130)
        self.entry_harga.grid(row=0, column=3, padx=3, pady=3)

        self.btn_pilih_tgl = ctk.CTkButton(grid_form, text="📅 Pilih Tgl Berangkat", width=150, height=32, corner_radius=6,
                                           fg_color=COLOR["bg_card_alt"], hover_color=COLOR["border"], text_color=COLOR["text_main"],
                                           command=self.buka_kalendar_popup)
        self.btn_pilih_tgl.grid(row=0, column=4, padx=3, pady=3)
        self.selected_date_str = datetime.date.today().strftime("%Y-%m-%d")

        self.btn_simpan_trip = self.make_primary_btn(grid_form, "+ Buat Trip", self.simpan_trip, width=110, height=32)
        self.btn_simpan_trip.grid(row=0, column=5, padx=(6, 3), pady=3)

        ctk.CTkLabel(self.dash_frame, text="Daftar Open Trip Tersedia", font=FONT_H2, text_color=COLOR["text_main"]).pack(
            anchor="w", padx=20, pady=(4, 4))

        self.list_trip_frame = ctk.CTkScrollableFrame(self.dash_frame, fg_color="transparent")
        self.list_trip_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self.load_trips()

    def on_leader_selected(self, choice):
        if choice in LEADER_DAN_TIM:
            anggota_list = LEADER_DAN_TIM[choice]
            self.lbl_info_tim.configure(text=f"Tim: {', '.join(anggota_list)}", text_color=COLOR["info"])

    def buka_kalendar_popup(self):
        def pick(chosen):
            self.selected_date_str = chosen
            self.btn_pilih_tgl.configure(text=f"📅 {chosen}")
        self.buka_kalendar("Pilih Tanggal Keberangkatan", pick)

    def simpan_trip(self):
        nama = self.entry_trip.get().strip()
        leader = self.drop_leader.get()
        harga_raw = self.entry_harga.get().strip()
        tgl = getattr(self, 'selected_date_str', datetime.date.today().strftime("%Y-%m-%d"))

        if not nama:
            messagebox.showwarning("Peringatan", "Nama trip wajib diisi!")
            return
        if leader == "Pilih Leader" or not leader:
            messagebox.showwarning("Peringatan", "Silakan pilih Leader!")
            return

        tim_anggota = LEADER_DAN_TIM.get(leader, [])
        tim_str = ", ".join(tim_anggota)

        is_bentrok, pesan_bentrok = cek_bentrok_jadwal(self.conn, leader, tgl, exclude_trip_id=self.edit_trip_id)
        if is_bentrok:
            messagebox.showerror("Jadwal Bentrok!", f"Gagal menyimpan trip!\n\n{pesan_bentrok}\n\nAturan GatherSync: selang minimal {RULE_SELANG_HARI} hari antar trip untuk leader yang sama.")
            return

        try:
            harga_val = float(harga_raw) if harga_raw else 0.0
        except ValueError:
            messagebox.showwarning("Peringatan", "Harga harus berupa angka!")
            return

        cursor = self.conn.cursor()
        if self.edit_trip_id is None:
            cursor.execute("INSERT INTO trip (nama_trip, leader, tim, tanggal_keberangkatan, harga_trip) VALUES (?, ?, ?, ?, ?)",
                           (nama, leader, tim_str, tgl, harga_val))
            trip_id_baru = cursor.lastrowid
            self.conn.commit()
            catat_audit(self.conn, trip_id_baru, nama, "Buat Trip", f"Leader {leader}, berangkat {tgl}, harga Rp {harga_val:,.0f}")
            messagebox.showinfo("Sukses", "Open Trip baru berhasil dibuat!")
        else:
            cursor.execute("UPDATE trip SET nama_trip=?, leader=?, tim=?, tanggal_keberangkatan=?, harga_trip=? WHERE id=?",
                           (nama, leader, tim_str, tgl, harga_val, self.edit_trip_id))
            self.conn.commit()
            catat_audit(self.conn, self.edit_trip_id, nama, "Ubah Trip", f"Leader {leader}, berangkat {tgl}, harga Rp {harga_val:,.0f}")
            # kalau trip yang diedit sedang aktif, sidebar ikut diperbarui
            if self.edit_trip_id == self.current_trip_id:
                self.current_trip_name = nama
                self.current_trip_tanggal = tgl
                self.current_trip_harga = harga_val
                self.lbl_active_trip.configure(text=nama)
                self.update_risk_banner()
            messagebox.showinfo("Sukses", "Data trip diperbarui!")
            self.edit_trip_id = None
            self.btn_simpan_trip.configure(text="+ Buat Trip", fg_color=COLOR["primary"], hover_color=COLOR["primary_hover"])

        self.conn.commit()
        self.entry_trip.delete(0, 'end')
        self.entry_harga.delete(0, 'end')
        self.drop_leader.set("Pilih Leader")
        self.lbl_info_tim.configure(text="Tim: (Pilih Leader)", text_color=COLOR["text_sub"])
        self.load_trips()

    def mulai_edit_trip(self, t_id, t_nama, t_leader, t_tim, t_tgl, t_harga):
        self.edit_trip_id = t_id
        self.entry_trip.delete(0, 'end')
        self.entry_trip.insert(0, t_nama)
        self.entry_harga.delete(0, 'end')
        self.entry_harga.insert(0, str(int(t_harga or 0)))
        if t_leader in LIST_LEADER:
            self.drop_leader.set(t_leader)
            self.lbl_info_tim.configure(text=f"Tim: {t_tim}", text_color=COLOR["info"])
        if t_tgl:
            self.selected_date_str = t_tgl
            self.btn_pilih_tgl.configure(text=f"📅 {t_tgl}")
        self.btn_simpan_trip.configure(text="Update Trip", fg_color=COLOR["warning"], hover_color="#d68910")

    def load_trips(self):
        for w in self.dash_stats.winfo_children():
            w.destroy()
        for w in self.list_trip_frame.winfo_children():
            w.destroy()

        cursor = self.conn.cursor()
        total_trip = cursor.execute("SELECT COUNT(*) FROM trip").fetchone()[0]
        total_peserta = cursor.execute("SELECT COUNT(*) FROM peserta").fetchone()[0]
        total_lunas = cursor.execute("SELECT COUNT(*) FROM peserta WHERE status='Lunas'").fetchone()[0]
        total_risiko = 0
        for t_id, tgl in cursor.execute("SELECT id, tanggal_keberangkatan FROM trip").fetchall():
            sisa = hitung_status_risiko(tgl)
            if sisa is not None and 0 <= sisa <= RULE_RISIKO_H_MINUS:
                total_risiko += cursor.execute("SELECT COUNT(*) FROM peserta WHERE id_trip=? AND status != 'Lunas'", (t_id,)).fetchone()[0]

        self.dash_stats.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.stat_card_mini(self.dash_stats, "Total Trip", total_trip, COLOR["primary"]).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.stat_card_mini(self.dash_stats, "Peserta", total_peserta, COLOR["info"]).grid(row=0, column=1, sticky="ew", padx=4)
        self.stat_card_mini(self.dash_stats, "Lunas", total_lunas, COLOR["success"]).grid(row=0, column=2, sticky="ew", padx=4)
        self.stat_card_mini(self.dash_stats, "Berisiko (H-3)", total_risiko, COLOR["danger"]).grid(row=0, column=3, sticky="ew", padx=(4, 0))

        rows = cursor.execute("SELECT id, nama_trip, leader, tim, tanggal_keberangkatan, harga_trip FROM trip ORDER BY id DESC").fetchall()
        if not rows:
            ctk.CTkLabel(self.list_trip_frame, text="Belum ada trip terdaftar.", font=FONT_BODY, text_color=COLOR["text_sub"]).pack(pady=20)
            return

        for t_id, t_nama, t_leader, t_tim, t_tgl, t_harga in rows:
            is_active = (t_id == self.current_trip_id)
            jml_p = cursor.execute("SELECT COUNT(*) FROM peserta WHERE id_trip=?", (t_id,)).fetchone()[0]
            rekom_armada = hitung_rekomendasi_armada(jml_p)

            frame = self.make_card(self.list_trip_frame, border_color=COLOR["primary"] if is_active else COLOR["border"], border_width=2 if is_active else 1)
            frame.pack(fill="x", pady=4)

            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            name_row = ctk.CTkFrame(info, fg_color="transparent")
            name_row.pack(anchor="w")
            ctk.CTkLabel(name_row, text=t_nama, font=FONT_BODY_BOLD, text_color=COLOR["text_main"]).pack(side="left")
            if is_active:
                ctk.CTkLabel(name_row, text="  ● AKTIF", font=FONT_SMALL, text_color=COLOR["success"]).pack(side="left")

            keterangan = f"Harga: Rp {t_harga or 0:,.0f}   •   Leader: {t_leader or '-'}   •   👥 Peserta: {jml_p} orang"
            if t_tgl:
                keterangan += f"   •   Berangkat: {t_tgl}"
            ctk.CTkLabel(info, text=keterangan, font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(anchor="w", pady=(2, 0))
            ctk.CTkLabel(info, text=f"🚐 Rekomendasi Armada: {rekom_armada}", font=("Segoe UI", 10, "bold"), text_color=COLOR["info"]).pack(anchor="w", pady=(2, 0))

            actions = ctk.CTkFrame(frame, fg_color="transparent")
            actions.pack(side="right", padx=12, pady=8)

            self.make_danger_btn(actions, "Hapus", lambda i=t_id: self.hapus_trip(i)).pack(side="right", padx=(4, 0))
            ctk.CTkButton(actions, text="Edit", width=50, height=24, corner_radius=6, font=FONT_SMALL,
                          fg_color=COLOR["bg_card"], hover_color=COLOR["border"], text_color=COLOR["text_main"],
                          command=lambda i=t_id, n=t_nama, l=t_leader, tm=t_tim, tg=t_tgl, h=t_harga: self.mulai_edit_trip(i, n, l, tm, tg, h)).pack(side="right", padx=3)
            self.make_primary_btn(actions, "Pilih", lambda i=t_id, n=t_nama, tg=t_tgl, h=t_harga: self.pilih_trip(i, n, tg, h), width=70, height=24, font=FONT_SMALL).pack(side="right")

    def hapus_trip(self, trip_id):
        if messagebox.askyesno("Hapus Trip", "Hapus trip ini beserta data peserta & itinerary terkait?"):
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM trip WHERE id=?", (trip_id,))
            cursor.execute("DELETE FROM peserta WHERE id_trip=?", (trip_id,))
            cursor.execute("DELETE FROM itinerary WHERE id_trip=?", (trip_id,))
            cursor.execute("DELETE FROM audit_log WHERE id_trip=?", (trip_id,))
            self.conn.commit()
            if self.current_trip_id == trip_id:
                self.current_trip_id = None
                self.current_trip_name = None
                self.current_trip_tanggal = None
                self.current_trip_harga = 0.0
                self.lbl_active_trip.configure(text="Belum dipilih", text_color=COLOR["warning"])
                self.lbl_active_risk.configure(text="")
            if self.edit_trip_id == trip_id:
                self.edit_trip_id = None
                self.btn_simpan_trip.configure(text="+ Buat Trip", fg_color=COLOR["primary"], hover_color=COLOR["primary_hover"])
            self.load_trips()

    def pilih_trip(self, trip_id, trip_name, trip_tanggal, trip_harga):
        self.current_trip_id = trip_id
        self.current_trip_name = trip_name
        self.current_trip_tanggal = trip_tanggal
        self.current_trip_harga = trip_harga or 0.0
        self.edit_id = None
        self.lbl_active_trip.configure(text=trip_name, text_color=COLOR["success"])
        self.update_risk_banner()
        self.load_trips()
        messagebox.showinfo("Trip Dipilih", f"Event aktif: {trip_name}\n(Harga Flat: Rp {self.current_trip_harga:,.0f})")

    # --- MENU 2: KAS & REGISTRASI ---
    def setup_kas_frame(self):
        self.edit_id = None
        self.make_gradient_banner(self.kas_frame, height=50, title="Registrasi & Kas Peserta", subtitle="Tagihan otomatis mengikuti harga flat trip yang ditentukan di awal")
        container = ctk.CTkFrame(self.kas_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=0)
        container.grid_columnconfigure(1, weight=1)

        form_frame = self.make_card(container, width=310)
        form_frame.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        form_frame.pack_propagate(False)

        ctk.CTkLabel(form_frame, text="Formulir Pendaftaran", font=FONT_H2, text_color=COLOR["text_main"]).pack(pady=(12, 8), padx=14, anchor="w")
        sub_form = ctk.CTkFrame(form_frame, fg_color="transparent")
        sub_form.pack(padx=14, fill="x")

        self.var_total = ctk.StringVar(value="0")
        self.var_telah_dibayar = ctk.StringVar(value="0")
        self.var_bayar = ctk.StringVar(value="0")
        self.var_sisa = ctk.StringVar(value="0")

        def hitung_otomatis(*args):
            try:
                t = float(self.var_total.get() or 0)
                tb = float(self.var_telah_dibayar.get() or 0)
                b = float(self.var_bayar.get() or 0)
                sisa = t - (tb + b)
                self.var_sisa.set(str(sisa))
                kategori, persen = hitung_kategori(t, tb + b)
                style = STATUS_STYLE[kategori]
                self.lbl_status_display.configure(text=f"{style['icon']} {kategori.upper()} ({persen:.0f}%)", text_color=COLOR[style["color"]])
            except ValueError:
                pass

        for var in [self.var_total, self.var_telah_dibayar, self.var_bayar]:
            var.trace_add("write", hitung_otomatis)

        def field(label_text, widget_row):
            ctk.CTkLabel(sub_form, text=label_text, font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(anchor="w", pady=(6, 2))
            widget_row.pack(fill="x")

        self.entry_nama = self.make_entry(sub_form)
        field("Nama Peserta / PIC Kelompok", self.entry_nama)

        e_total = self.make_entry(sub_form, textvariable=self.var_total)
        field("Total Tagihan (Rp)", e_total)

        e_tb = self.make_entry(sub_form, textvariable=self.var_telah_dibayar, state="disabled")
        field("Telah Dibayar (Rp)", e_tb)

        e_bayar = self.make_entry(sub_form, textvariable=self.var_bayar)
        field("Bayar Sekarang (Rp)", e_bayar)

        e_sisa = self.make_entry(sub_form, textvariable=self.var_sisa, state="disabled")
        field("Sisa Tagihan (Rp)", e_sisa)

        self.lbl_status_display = ctk.CTkLabel(form_frame, text="○ BELUM BAYAR (0%)", font=FONT_BODY_BOLD, text_color=COLOR["danger"])
        self.lbl_status_display.pack(pady=(10, 2))

        self.btn_simpan = self.make_primary_btn(form_frame, "Simpan Data", self.simpan_kas, height=36)
        self.btn_simpan.pack(padx=14, pady=(8, 12), fill="x")

        list_frame = self.make_card(container)
        list_frame.grid(row=0, column=1, sticky="nsew")

        top_row = ctk.CTkFrame(list_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(top_row, text="Daftar Peserta Terdaftar", font=FONT_H2, text_color=COLOR["text_main"]).pack(side="left")
        self.lbl_progress = ctk.CTkLabel(top_row, text="0/0 Lunas", font=FONT_BODY_BOLD, text_color=COLOR["warning"])
        self.lbl_progress.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(list_frame, progress_color=COLOR["success"], fg_color=COLOR["bg_card_alt"], height=6)
        self.progress_bar.pack(fill="x", padx=14, pady=(0, 8))
        self.progress_bar.set(0)

        self.scroll_list = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def reset_form_kas(self):
        self.edit_id = None
        self.entry_nama.delete(0, 'end')
        self.var_total.set(str(int(self.current_trip_harga or 0)))
        self.var_telah_dibayar.set("0")
        self.var_bayar.set("0")
        self.btn_simpan.configure(text="Simpan Data", fg_color=COLOR["primary"], hover_color=COLOR["primary_hover"], text_color="#ffffff")

    def load_kas(self):
        if self.edit_id is None:
            self.reset_form_kas()

        for w in self.scroll_list.winfo_children():
            w.destroy()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status='Lunas' THEN 1 ELSE 0 END) FROM peserta WHERE id_trip=?", (self.current_trip_id,))
        total, lunas = cursor.fetchone()
        total = total or 0
        lunas = lunas or 0
        self.lbl_progress.configure(text=f"{lunas}/{total} Lunas")
        self.progress_bar.set((lunas / total) if total else 0)
        self.update_risk_banner()

        rows = cursor.execute("SELECT id, nama, status, total_tagihan, nominal_bayar FROM peserta WHERE id_trip=? ORDER BY id DESC", (self.current_trip_id,)).fetchall()
        if not rows:
            ctk.CTkLabel(self.scroll_list, text="Belum ada peserta terdaftar.", font=FONT_BODY, text_color=COLOR["text_sub"]).pack(pady=20)
            return

        for p_id, p_nama, p_status, p_total, p_bayar in rows:
            style = STATUS_STYLE.get(p_status, STATUS_STYLE["Belum Bayar"])
            frame = self.make_card(self.scroll_list, fg_color=COLOR["bg_card_alt"])
            frame.pack(fill="x", pady=3)
            avatar = ctk.CTkFrame(frame, width=30, height=30, corner_radius=15, fg_color=COLOR[style["color"]])
            avatar.pack(side="left", padx=(10, 8), pady=6)
            avatar.pack_propagate(False)
            ctk.CTkLabel(avatar, text=(p_nama[:1] or "?").upper(), font=FONT_BODY_BOLD, text_color="#ffffff").pack(expand=True)

            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=6)
            name_row = ctk.CTkFrame(info, fg_color="transparent")
            name_row.pack(anchor="w")
            ctk.CTkLabel(name_row, text=p_nama, font=FONT_BODY_BOLD, text_color=COLOR["text_main"]).pack(side="left")
            self.make_badge(name_row, p_status, style["color"], style["icon"]).pack(side="left", padx=(6, 0))

            sisa = p_total - p_bayar
            sub = "Lunas penuh" if p_status == "Lunas" else f"Kurang Rp {sisa:,.0f}"
            ctk.CTkLabel(info, text=sub, font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(anchor="w", pady=(1, 0))

            actions = ctk.CTkFrame(frame, fg_color="transparent")
            actions.pack(side="right", padx=8, pady=6)
            self.make_danger_btn(actions, "Hapus", lambda i=p_id: self.hapus_peserta(i)).pack(side="right", padx=(3, 0))
            ctk.CTkButton(actions, text="Edit", width=50, height=24, corner_radius=6, font=FONT_SMALL,
                          fg_color=COLOR["bg_card"], hover_color=COLOR["border"], text_color=COLOR["text_main"],
                          command=lambda i=p_id, n=p_nama, t=p_total, b=p_bayar: self.mulai_edit(i, n, t, b)).pack(side="right")

    def mulai_edit(self, p_id, nama, total, bayar_lama):
        self.edit_id = p_id
        self.entry_nama.delete(0, 'end')
        self.entry_nama.insert(0, nama)
        self.var_total.set(str(total))
        self.var_telah_dibayar.set(str(bayar_lama))
        self.var_bayar.set("0")
        self.btn_simpan.configure(text="Update Cicilan", fg_color=COLOR["warning"], hover_color="#d68910", text_color="#1a1a1a")

    def hapus_peserta(self, peserta_id):
        if messagebox.askyesno("Hapus Peserta", "Hapus data peserta ini?"):
            nama = self.conn.cursor().execute("SELECT nama FROM peserta WHERE id=?", (peserta_id,)).fetchone()
            self.conn.cursor().execute("DELETE FROM peserta WHERE id=?", (peserta_id,))
            self.conn.commit()
            if nama:
                catat_audit(self.conn, self.current_trip_id, nama[0], "Hapus Peserta", "Dihapus dari sistem")
            if self.edit_id == peserta_id:
                self.edit_id = None
            self.load_kas()

    def simpan_kas(self):
        nama = self.entry_nama.get().strip()
        try:
            t = float(self.var_total.get() or 0)
            tb = float(self.var_telah_dibayar.get() or 0)
            b = float(self.var_bayar.get() or 0)
        except ValueError:
            messagebox.showwarning("Peringatan", "Tagihan dan pembayaran harus angka!")
            return
        if not nama:
            messagebox.showwarning("Peringatan", "Nama peserta wajib diisi!")
            return
        if t < 0 or b < 0:
            messagebox.showwarning("Peringatan", "Nominal tidak boleh negatif!")
            return

        tm = b if self.edit_id is None else tb + b
        s = t - tm
        kategori, persen = hitung_kategori(t, tm)

        if self.edit_id is None:
            self.conn.cursor().execute("INSERT INTO peserta (id_trip, nama, total_tagihan, nominal_bayar, sisa_tagihan, status, unit_bus) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                       (self.current_trip_id, nama, t, tm, s, kategori, "Unit 1"))
            catat_audit(self.conn, self.current_trip_id, nama, "Registrasi", f"Bayar awal Rp {tm:,.0f} ({persen:.0f}%)")
        else:
            self.conn.cursor().execute("UPDATE peserta SET nama=?, total_tagihan=?, nominal_bayar=?, sisa_tagihan=?, status=? WHERE id=?",
                                       (nama, t, tm, s, kategori, self.edit_id))
            catat_audit(self.conn, self.current_trip_id, nama, "Pembayaran", f"Tambahan bayar Rp {b:,.0f} -> {kategori}")
            self.edit_id = None

        self.conn.commit()
        self.reset_form_kas()
        self.load_kas()

    # --- MENU 3: PLOTTING KURSI & MULTI-UNIT ---
    def setup_plot_frame(self):
        self.make_gradient_banner(self.plot_frame, height=50, title="Plotting Kursi & Multi-Unit Kendaraan", subtitle="Atur penempatan kursi untuk beberapa unit kendaraan (Unit 1, Unit 2, dst.)")
        wrap = ctk.CTkScrollableFrame(self.plot_frame, fg_color="transparent")
        wrap.pack(padx=20, fill="both", expand=True, pady=(0, 12))

        ctrl_card = self.make_card(wrap, fg_color=COLOR["bg_card_alt"])
        ctrl_card.pack(fill="x", pady=(0, 10))

        ctrl_inner = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl_inner.pack(padx=14, pady=10, fill="x")

        self.lbl_rekom_box = ctk.CTkLabel(ctrl_inner, text="🚐 Rekomendasi: Menghitung...", font=FONT_BODY_BOLD, text_color=COLOR["info"])
        self.lbl_rekom_box.pack(side="left")

        unit_selector_frame = ctk.CTkFrame(ctrl_inner, fg_color="transparent")
        unit_selector_frame.pack(side="right")

        ctk.CTkLabel(unit_selector_frame, text="Pilih Unit:", font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(side="left", padx=(0, 6))
        self.selected_unit_var = ctk.StringVar(value="Unit 1")

        self.drop_unit_bus = ctk.CTkComboBox(unit_selector_frame, values=["Unit 1", "Unit 2", "Unit 3", "Unit 4"], width=110, height=30,
                                             fg_color=COLOR["bg_input"], border_color=COLOR["border"], button_color=COLOR["primary"],
                                             command=self.on_unit_changed, variable=self.selected_unit_var)
        self.drop_unit_bus.pack(side="left")

        top_area = ctk.CTkFrame(wrap, fg_color="transparent")
        top_area.pack(fill="x")
        top_area.grid_columnconfigure(0, weight=2)
        top_area.grid_columnconfigure(1, weight=1)

        vehicle_card = self.make_card(top_area, fg_color=COLOR["bg_card_alt"])
        vehicle_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(vehicle_card, text="[ Kiri: Penumpang ]  —  SOPIR (Kanan Depan)", font=FONT_SMALL, text_color=COLOR["text_faint"]).pack(pady=(10, 4))
        self.bus_frame = ctk.CTkFrame(vehicle_card, fg_color="transparent")
        self.bus_frame.pack(padx=14, pady=(0, 12))

        legend = ctk.CTkFrame(vehicle_card, fg_color="transparent")
        legend.pack(pady=(0, 10))
        for color, label in [(COLOR["success"], "Terisi (Lunas)"), (COLOR["bg_card"], "Kosong")]:
            row = ctk.CTkFrame(legend, fg_color="transparent")
            row.pack(side="left", padx=8)
            dot = ctk.CTkFrame(row, width=10, height=10, corner_radius=5, fg_color=color, border_width=1, border_color=COLOR["border"])
            dot.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(row, text=label, font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(side="left")

        queue_card = self.make_card(top_area, fg_color=COLOR["bg_card"])
        queue_card.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(queue_card, text="⏳ Antrian Pelunasan", font=FONT_H2, text_color=COLOR["text_main"]).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(queue_card, text=f"Diurutkan otomatis: % tertinggi (min. {RULE_DP_MIN_PERSEN}%)", font=("Segoe UI", 9), text_color=COLOR["text_faint"], wraplength=220, justify="left").pack(anchor="w", padx=12)

        self.queue_list = ctk.CTkScrollableFrame(queue_card, fg_color="transparent", height=240)
        self.queue_list.pack(fill="both", expand=True, padx=8, pady=(6, 10))

    def on_unit_changed(self, choice):
        self.load_kursi_bus()

    def _baris_sopir(self, teks_pintu, lebar_pintu):
        row_sopir = ctk.CTkFrame(self.bus_frame, fg_color="transparent")
        row_sopir.pack(pady=2)
        ctk.CTkLabel(row_sopir, text=teks_pintu, font=FONT_SMALL, text_color=COLOR["text_faint"], width=lebar_pintu).pack(side="left", padx=5)
        ctk.CTkLabel(row_sopir, text="🚌 KEMUDI (SOPIR KANAN)", font=FONT_SMALL, text_color=COLOR["warning"], width=150, height=30, fg_color=COLOR["bg_card_alt"]).pack(side="left", padx=5)

    def load_kursi_bus(self):
        cursor = self.conn.cursor()
        total_p = cursor.execute("SELECT COUNT(*) FROM peserta WHERE id_trip=?", (self.current_trip_id,)).fetchone()[0]
        rekom = hitung_rekomendasi_armada(total_p)
        self.lbl_rekom_box.configure(text=f"🚐 Rekomendasi ({total_p} Peserta): {rekom}")

        for w in self.bus_frame.winfo_children():
            w.destroy()

        unit_str = self.selected_unit_var.get() or "Unit 1"
        occupied = {r[0]: r[1] for r in cursor.execute("SELECT kursi_bus, nama FROM peserta WHERE id_trip=? AND unit_bus=? AND kursi_bus IS NOT NULL", (self.current_trip_id, unit_str)).fetchall()}

        # layout kursi, sopir di kanan depan
        if "Private Car" in rekom:
            layout_config = [
                [("1A", "Depan Kiri (Samping Sopir)"), ("SOPIR", "Kanan: SOPIR")],
                [("2A", "Tengah Kiri"), ("2B", "Tengah Tengah"), ("2C", "Tengah Kanan")],
                [("3A", "Belakang Kiri"), ("3B", "Belakang Tengah"), ("3C", "Belakang Kanan")]
            ]
            for row_seats in layout_config:
                row_f = ctk.CTkFrame(self.bus_frame, fg_color="transparent")
                row_f.pack(pady=3)
                for seat_id, seat_lbl in row_seats:
                    if seat_id == "SOPIR":
                        ctk.CTkLabel(row_f, text="🚗 KEMUDI\n(SOPIR)", font=FONT_SMALL, text_color=COLOR["warning"], width=100, height=40, corner_radius=6, fg_color=COLOR["bg_card_alt"]).pack(side="left", padx=3)
                    else:
                        self.create_seat_button(row_f, seat_id, seat_lbl, occupied, width=100, height=40)

        elif "Microbus" in rekom:
            layout_config = [
                [("1A", "Depan Kiri"), ("SOPIR", "Kanan: SOPIR")],
                [("2A", "Baris 1 Kiri"), ("2B", "Baris 1 Kanan")],
                [("3A", "Baris 2 Kiri"), ("3B", "Baris 2 Kanan")],
                [("4A", "Baris 3 Kiri"), ("4B", "Baris 3 Kanan")],
                [("5A", "Baris 4 Kiri"), ("5B", "Baris 4 Kanan")],
                [("6A", "Baris 5 Kiri"), ("6B", "Baris 5 Kanan")],
                [("7A", "Belakang 1"), ("7B", "Belakang 2"), ("7C", "Belakang 3")]
            ]
            for row_seats in layout_config:
                row_f = ctk.CTkFrame(self.bus_frame, fg_color="transparent")
                row_f.pack(pady=2)
                for seat_id, seat_lbl in row_seats:
                    if seat_id == "SOPIR":
                        ctk.CTkLabel(row_f, text="🚌 SOPIR", font=FONT_SMALL, text_color=COLOR["warning"], width=85, height=34, corner_radius=6, fg_color=COLOR["bg_card_alt"]).pack(side="left", padx=3)
                    else:
                        self.create_seat_button(row_f, seat_id, seat_lbl, occupied, width=85, height=34, font=FONT_SMALL)

        elif "Medium Bus" in rekom:
            self._baris_sopir("[ PINTU / DEPAN ]", 150)
            for row in range(8):
                row_f = ctk.CTkFrame(self.bus_frame, fg_color="transparent")
                row_f.pack(pady=2)
                for col_idx, col_name in enumerate(['A', 'B', 'C', 'D']):
                    if row == 7 and col_idx >= 2:
                        break
                    if col_idx == 2:
                        ctk.CTkLabel(row_f, text="", width=18).pack(side="left")
                    seat_num = f"{row+1}{col_name}"
                    self.create_seat_button(row_f, seat_num, seat_num, occupied, width=70, height=34, font=FONT_SMALL)

        else:
            # Big Bus / Multi-Unit
            self._baris_sopir("[ PINTU / DEPAN ]", 140)
            for row in range(11):
                row_f = ctk.CTkFrame(self.bus_frame, fg_color="transparent")
                row_f.pack(pady=2)
                for col_idx, col_name in enumerate(['A', 'B', 'C', 'D']):
                    if col_idx == 2:
                        ctk.CTkLabel(row_f, text="", width=20).pack(side="left")
                    seat_num = f"{row+1}{col_name}"
                    self.create_seat_button(row_f, seat_num, seat_num, occupied, width=65, height=30, font=FONT_SMALL)

        self.load_antrian()

    def create_seat_button(self, parent, seat_id, seat_label, occupied_dict, width, height, font=FONT_SMALL):
        if seat_id in occupied_dict:
            btn = ctk.CTkButton(parent, text=f"{seat_id}\n{occupied_dict[seat_id]}", fg_color=COLOR["success"],
                                hover_color=COLOR["success_hover"], text_color="#ffffff", width=width, height=height,
                                corner_radius=6, font=font, command=lambda s=seat_id: self.batal_kursi(s))
        else:
            btn = ctk.CTkButton(parent, text=f"{seat_id}\nKosong", fg_color=COLOR["bg_card"],
                                hover_color=COLOR["border"], text_color=COLOR["text_sub"], width=width, height=height,
                                corner_radius=6, font=font, border_width=1, border_color=COLOR["border"],
                                command=lambda s=seat_id: self.pilih_peserta_plot(s))
        btn.pack(side="left", padx=3)

    def load_antrian(self):
        for w in self.queue_list.winfo_children():
            w.destroy()
        rows = self.conn.cursor().execute("SELECT nama, total_tagihan, nominal_bayar FROM peserta WHERE id_trip=? AND status='Cicilan'", (self.current_trip_id,)).fetchall()
        antrian = []
        for nama, total, bayar in rows:
            _, persen = hitung_kategori(total, bayar)
            antrian.append((nama, persen))
        antrian.sort(key=lambda x: x[1], reverse=True)

        if not antrian:
            ctk.CTkLabel(self.queue_list, text="Tidak ada antrian.", font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(pady=10)
            return

        for idx, (nama, persen) in enumerate(antrian, start=1):
            row = ctk.CTkFrame(self.queue_list, corner_radius=6, fg_color=COLOR["bg_card_alt"])
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"#{idx}", font=FONT_SMALL, text_color=COLOR["text_faint"], width=20).pack(side="left", padx=(6, 0), pady=4)
            ctk.CTkLabel(row, text=nama, font=FONT_BODY, text_color=COLOR["text_main"]).pack(side="left", padx=4, pady=4)
            ctk.CTkLabel(row, text=f"{persen:.0f}%", font=FONT_SMALL, text_color=COLOR["info"]).pack(side="right", padx=6, pady=4)

    def pilih_peserta_plot(self, seat_num):
        unassigned = self.conn.cursor().execute("SELECT id, nama FROM peserta WHERE id_trip=? AND status='Lunas' AND (kursi_bus IS NULL OR kursi_bus='')", (self.current_trip_id,)).fetchall()
        if not unassigned:
            messagebox.showwarning("Info", "Tidak ada peserta Lunas yang tersisa.")
            return
        popup = ctk.CTkToplevel(self)
        popup.title(f"Kursi {seat_num}")
        popup.geometry("300x320")
        popup.configure(fg_color=COLOR["bg_root"])
        popup.attributes("-topmost", True)
        popup.grab_set()

        ctk.CTkLabel(popup, text=f"Kursi {seat_num}", font=FONT_H2, text_color=COLOR["text_main"]).pack(pady=12)
        scroll = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for p_id, p_nama in unassigned:
            ctk.CTkButton(scroll, text=p_nama, height=32, corner_radius=6, fg_color=COLOR["bg_card"],
                          hover_color=COLOR["primary"], text_color=COLOR["text_main"],
                          command=lambda pid=p_id, s=seat_num, w=popup: self.tetapkan_kursi(pid, s, w)).pack(pady=3, fill="x")

    def tetapkan_kursi(self, pid, s, w):
        unit_str = self.selected_unit_var.get() or "Unit 1"
        nama = self.conn.cursor().execute("SELECT nama FROM peserta WHERE id=?", (pid,)).fetchone()
        self.conn.cursor().execute("UPDATE peserta SET kursi_bus=?, unit_bus=? WHERE id=?", (s, unit_str, pid))
        self.conn.commit()
        if nama:
            catat_audit(self.conn, self.current_trip_id, nama[0], "Plotting Kursi", f"Kursi {s} di {unit_str}")
        w.destroy()
        self.load_kursi_bus()

    def batal_kursi(self, seat_num):
        unit_str = self.selected_unit_var.get() or "Unit 1"
        if messagebox.askyesno("Kosongkan Kursi", f"Kosongkan kursi {seat_num} di {unit_str}?"):
            cursor = self.conn.cursor()
            terisi = cursor.execute("SELECT nama FROM peserta WHERE kursi_bus=? AND unit_bus=? AND id_trip=?", (seat_num, unit_str, self.current_trip_id)).fetchall()
            cursor.execute("UPDATE peserta SET kursi_bus=NULL WHERE kursi_bus=? AND unit_bus=? AND id_trip=?", (seat_num, unit_str, self.current_trip_id))
            self.conn.commit()
            for (nama,) in terisi:
                catat_audit(self.conn, self.current_trip_id, nama, "Kosongkan Kursi", f"Kursi {seat_num} di {unit_str} dikosongkan")
            self.load_kursi_bus()

    # --- MENU 4: ITINERARY ---
    def setup_itin_frame(self):
        self.make_gradient_banner(self.itin_frame, height=50, title="Manajemen Itinerary", subtitle="Susun jadwal harian kegiatan")
        form = self.make_card(self.itin_frame)
        form.pack(fill="x", padx=20, pady=(0, 8))

        list_jam = [f"{h:02d}:00" for h in range(6, 23)]
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=10)

        self.btn_itin_tgl = ctk.CTkButton(row1, text="📅 Pilih Tanggal", width=150, height=32, corner_radius=6,
                                          fg_color=COLOR["bg_card_alt"], hover_color=COLOR["border"], text_color=COLOR["text_main"],
                                          command=self.buka_kalendar_itin_popup)
        self.btn_itin_tgl.grid(row=0, column=0, padx=3, pady=3)
        self.itin_selected_date = datetime.date.today().strftime("%Y-%m-%d")

        self.drop_jam = ctk.CTkComboBox(row1, values=list_jam, width=85, height=32, corner_radius=6,
                                        fg_color=COLOR["bg_input"], border_color=COLOR["border"], button_color=COLOR["primary"])
        self.drop_jam.grid(row=0, column=1, padx=3, pady=3)
        self.drop_jam.set("08:00")

        self.entry_kegiatan = self.make_entry(row1, placeholder_text="Kegiatan", width=170)
        self.entry_kegiatan.grid(row=0, column=2, padx=3, pady=3)

        self.entry_tk = self.make_entry(row1, placeholder_text="Titik Kumpul", width=130)
        self.entry_tk.grid(row=0, column=3, padx=3, pady=3)

        self.entry_dc = self.make_entry(row1, placeholder_text="Dresscode", width=100)
        self.entry_dc.grid(row=0, column=4, padx=3, pady=3)

        self.make_primary_btn(row1, "+ Tambah", self.simpan_itin, width=80, height=32).grid(row=0, column=5, padx=(5, 0), pady=3)

        ctk.CTkLabel(self.itin_frame, text="Jadwal", font=FONT_H2, text_color=COLOR["text_main"]).pack(anchor="w", padx=20, pady=(2, 4))
        self.list_itin = ctk.CTkScrollableFrame(self.itin_frame, fg_color="transparent")
        self.list_itin.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    def buka_kalendar_itin_popup(self):
        def pick(chosen):
            self.itin_selected_date = chosen
            self.btn_itin_tgl.configure(text=f"📅 {chosen}")
        self.buka_kalendar("Pilih Tanggal Kegiatan", pick)

    def simpan_itin(self):
        h = getattr(self, 'itin_selected_date', datetime.date.today().strftime("%Y-%m-%d"))
        j = self.drop_jam.get()
        k = self.entry_kegiatan.get().strip()
        tk_ = self.entry_tk.get().strip()
        dc = self.entry_dc.get().strip()
        if not k:
            messagebox.showwarning("Peringatan", "Nama kegiatan wajib diisi!")
            return
        self.conn.cursor().execute("INSERT INTO itinerary (id_trip, hari, jam, kegiatan, titik_kumpul, dresscode) VALUES (?, ?, ?, ?, ?, ?)",
                                   (self.current_trip_id, h, j, k, tk_, dc))
        self.conn.commit()
        for e in [self.entry_kegiatan, self.entry_tk, self.entry_dc]:
            e.delete(0, 'end')
        self.load_itin()

    def load_itin(self):
        for w in self.list_itin.winfo_children():
            w.destroy()
        rows = self.conn.cursor().execute("SELECT id, hari, jam, kegiatan, titik_kumpul, dresscode FROM itinerary WHERE id_trip=? ORDER BY hari ASC, jam ASC, id ASC", (self.current_trip_id,)).fetchall()
        if not rows:
            ctk.CTkLabel(self.list_itin, text="Belum ada jadwal ditambahkan.", font=FONT_BODY, text_color=COLOR["text_sub"]).pack(pady=15)
            return

        for i_id, hari, jam, kegiatan, tk_, dc in rows:
            frame = self.make_card(self.list_itin, fg_color=COLOR["bg_card_alt"])
            frame.pack(fill="x", pady=3)
            time_box = ctk.CTkFrame(frame, width=55, fg_color="transparent")
            time_box.pack(side="left", padx=(10, 6), pady=8)
            ctk.CTkLabel(time_box, text=jam, font=FONT_BODY_BOLD, text_color=COLOR["primary"]).pack(anchor="w")
            ctk.CTkLabel(time_box, text=hari, font=FONT_SMALL, text_color=COLOR["text_faint"]).pack(anchor="w")

            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(info, text=kegiatan, font=FONT_BODY_BOLD, text_color=COLOR["text_main"]).pack(anchor="w")
            ctk.CTkLabel(info, text=f"📍 {tk_ or '-'}   •   👔 {dc or '-'}", font=FONT_SMALL, text_color=COLOR["text_sub"]).pack(anchor="w")

            self.make_danger_btn(frame, "Hapus", lambda i=i_id: self.hapus_itin(i)).pack(side="right", padx=10, pady=8)

    def hapus_itin(self, itin_id):
        self.conn.cursor().execute("DELETE FROM itinerary WHERE id=?", (itin_id,))
        self.conn.commit()
        self.load_itin()

    # --- MENU 5: MANIFEST & AUDIT PDF ---
    def setup_manifest_frame(self):
        self.make_gradient_banner(self.manifest_frame, height=50, title="Manifest & Laporan Audit", subtitle="Rekap keuangan, rekomendasi armada, dan log audit otomatis — siap ekspor PDF")
        card = self.make_card(self.manifest_frame)
        card.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        self.txt_manifest = ctk.CTkTextbox(card, corner_radius=8, font=("Consolas", 11), fg_color=COLOR["bg_input"], text_color=COLOR["text_main"], border_width=0)
        self.txt_manifest.pack(fill="both", expand=True, padx=12, pady=12)

        self.make_primary_btn(self.manifest_frame, "⬇  Download Laporan Format PDF", self.export_pdf, fg_color=COLOR["success"], hover_color=COLOR["success_hover"], width=240, height=36).pack(pady=(0, 12))

    def load_manifest(self):
        self.txt_manifest.delete("0.0", "end")
        cursor = self.conn.cursor()
        trip = cursor.execute("SELECT nama_trip, leader, tim, tanggal_keberangkatan, harga_trip FROM trip WHERE id=?", (self.current_trip_id,)).fetchone()
        jml_p = cursor.execute("SELECT COUNT(*) FROM peserta WHERE id_trip=?", (self.current_trip_id,)).fetchone()[0]
        rekom = hitung_rekomendasi_armada(jml_p)

        laporan = (
            "=========================================\n"
            "PT. GATHERSYNC TOUR & TRAVEL\n"
            f"LAPORAN OPEN TRIP: {trip[0].upper()}\n"
            f"Leader: {trip[1]} | Tim: [{trip[2]}] | Berangkat: {trip[3] or '-'}\n"
            f"Harga Flat /Org: Rp {trip[4] or 0:,.0f} | Total Peserta: {jml_p} orang\n"
            f"Rekomendasi Armada: {rekom}\n"
            "=========================================\n\n"
        )
        uang = cursor.execute("SELECT SUM(nominal_bayar), SUM(sisa_tagihan) FROM peserta WHERE id_trip=?", (self.current_trip_id,)).fetchone()
        laporan += f"[REKAP KEUANGAN]\nTotal Kas Masuk: Rp {uang[0] or 0:,.0f}\nTotal Piutang (Kurang): Rp {uang[1] or 0:,.0f}\n\n"

        laporan += "[RINGKASAN STATUS]\n"
        for kategori in ["Belum Bayar", "DP Diterima", "Cicilan", "Lunas"]:
            jml = cursor.execute("SELECT COUNT(*) FROM peserta WHERE id_trip=? AND status=?", (self.current_trip_id, kategori)).fetchone()[0]
            laporan += f"{kategori:14s}: {jml} peserta\n"
        laporan += "\n"

        laporan += "[MANIFEST PENUMPANG & UNIT KENDARAAN]\n"
        for row in cursor.execute("SELECT unit_bus, kursi_bus, nama FROM peserta WHERE id_trip=? AND kursi_bus IS NOT NULL ORDER BY unit_bus ASC, kursi_bus ASC", (self.current_trip_id,)):
            laporan += f"[{row[0]}] Kursi {row[1]} : {row[2]}\n"
        laporan += "\n"

        laporan += "[LOG AUDIT OTOMATIS]\n"
        audit_rows = cursor.execute("SELECT waktu, nama, aksi, keterangan FROM audit_log WHERE id_trip=? ORDER BY id ASC", (self.current_trip_id,)).fetchall()
        if not audit_rows:
            laporan += "Belum ada aktivitas tercatat.\n"
        for waktu, nama, aksi, ket in audit_rows:
            laporan += f"[{waktu}] {nama} — {aksi}: {ket}\n"

        self.txt_manifest.insert("0.0", laporan)

    def export_pdf(self):
        try:
            nama_aman = "".join(c if (c.isalnum() or c in "-_") else "_" for c in self.current_trip_name.replace(" ", "_"))
            nama_file = f"Laporan_Trip_{nama_aman}.pdf"
            doc = SimpleDocTemplate(nama_file, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=35, bottomMargin=35)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, textColor=colors.HexColor('#1f538d'))
            sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.gray)
            cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, textColor=colors.black)
            cell_head = ParagraphStyle('CellHead', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)

            story.append(Paragraph("<b>PT. GATHERSYNC TOUR &amp; TRAVEL</b>", title_style))
            story.append(Paragraph("Jl. Raya Perjalanan Wisata No. 88, Kota Wisata | Telp: (021) 555-8899", sub_style))
            story.append(Paragraph("Email: support@gathersync.com | Web: www.gathersync.com", sub_style))
            story.append(Spacer(1, 10))

            story.append(Table([['']], colWidths=[552], rowHeights=[2], style=TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1f538d'))])))
            story.append(Spacer(1, 10))

            cursor = self.conn.cursor()
            trip = cursor.execute("SELECT nama_trip, leader, tim, tanggal_keberangkatan, harga_trip FROM trip WHERE id=?", (self.current_trip_id,)).fetchone()
            jml_p = cursor.execute("SELECT COUNT(*) FROM peserta WHERE id_trip=?", (self.current_trip_id,)).fetchone()[0]
            rekom = hitung_rekomendasi_armada(jml_p)

            meta_text = (f"<b>DETAIL OPEN TRIP</b><br/><b>Nama Trip:</b> {trip[0]}<br/>"
                         f"<b>Trip Leader:</b> {trip[1]} | <b>Tim:</b> {trip[2]}<br/>"
                         f"<b>Tanggal Berangkat:</b> {trip[3] or '-'} | <b>Harga Flat:</b> Rp {trip[4] or 0:,.0f}<br/>"
                         f"<b>Total Peserta:</b> {jml_p} orang | <b>Rekomendasi Armada:</b> {rekom}")
            story.append(Paragraph(meta_text, styles['Normal']))
            story.append(Spacer(1, 10))

            uang = cursor.execute("SELECT SUM(nominal_bayar), SUM(sisa_tagihan) FROM peserta WHERE id_trip=?", (self.current_trip_id,)).fetchone()
            fin_data = [
                [Paragraph('<b>Keterangan Finansial</b>', cell_head), Paragraph('<b>Jumlah (IDR)</b>', cell_head)],
                [Paragraph('Total Kas Masuk', cell_style), Paragraph(f"Rp {uang[0] or 0:,.0f}", cell_style)],
                [Paragraph('Total Piutang (Kekurangan)', cell_style), Paragraph(f"Rp {uang[1] or 0:,.0f}", cell_style)]
            ]
            t_fin = Table(fin_data, colWidths=[276, 276])
            t_fin.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f538d')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(t_fin)
            story.append(Spacer(1, 10))

            story.append(Paragraph("<b>MANIFEST PENUMPANG &amp; UNIT KENDARAAN</b>", styles['Heading2']))
            story.append(Spacer(1, 4))
            passengers = cursor.execute("SELECT unit_bus, kursi_bus, nama, status FROM peserta WHERE id_trip=? AND kursi_bus IS NOT NULL ORDER BY unit_bus ASC, kursi_bus ASC", (self.current_trip_id,)).fetchall()
            pas_data = [[Paragraph('<b>Unit</b>', cell_head), Paragraph('<b>No. Kursi</b>', cell_head), Paragraph('<b>Nama Penumpang</b>', cell_head), Paragraph('<b>Status</b>', cell_head)]]
            for p in passengers:
                pas_data.append([Paragraph(str(p[0]), cell_style), Paragraph(str(p[1]), cell_style), Paragraph(str(p[2]), cell_style), Paragraph(str(p[3]), cell_style)])
            if len(pas_data) == 1:
                pas_data.append([Paragraph('-', cell_style), Paragraph('-', cell_style), Paragraph('Belum ada kursi yang di-plot', cell_style), Paragraph('-', cell_style)])
            t_pas = Table(pas_data, colWidths=[90, 80, 242, 140])
            t_pas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(t_pas)
            story.append(Spacer(1, 10))

            story.append(Paragraph("<b>LOG AUDIT OTOMATIS</b>", styles['Heading2']))
            story.append(Spacer(1, 4))
            audit_rows = cursor.execute("SELECT waktu, nama, aksi, keterangan FROM audit_log WHERE id_trip=? ORDER BY id ASC", (self.current_trip_id,)).fetchall()

            audit_data = [[
                Paragraph('<b>Waktu</b>', cell_head),
                Paragraph('<b>Nama</b>', cell_head),
                Paragraph('<b>Aksi</b>', cell_head),
                Paragraph('<b>Keterangan</b>', cell_head)
            ]]
            for waktu, nama, aksi, ket in audit_rows:
                audit_data.append([
                    Paragraph(str(waktu), cell_style),
                    Paragraph(str(nama), cell_style),
                    Paragraph(str(aksi), cell_style),
                    Paragraph(str(ket), cell_style)
                ])
            if len(audit_data) == 1:
                audit_data.append([Paragraph('-', cell_style), Paragraph('-', cell_style), Paragraph('-', cell_style), Paragraph('Belum ada aktivitas tercatat', cell_style)])

            t_audit = Table(audit_data, colWidths=[100, 90, 100, 262])
            t_audit.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(t_audit)

            doc.build(story)
            messagebox.showinfo("Berhasil", f"Laporan PDF berhasil dibuat:\n{nama_file}")
        except Exception as e:
            messagebox.showerror("Gagal", f"Terjadi kesalahan saat membuat PDF:\n{str(e)}")

    # --- NAVIGASI ---
    def check_trip_active(self):
        if self.current_trip_id is None:
            messagebox.showwarning("Akses Ditolak", "Pilih Trip terlebih dahulu di menu Dashboard!")
            return False
        return True

    def hide_all(self):
        for frame in [self.dash_frame, self.kas_frame, self.plot_frame, self.itin_frame, self.manifest_frame]:
            frame.grid_forget()

    def show_dash_frame(self):
        self.hide_all()
        self.set_active_menu("dash")
        self.dash_frame.grid(row=0, column=1, sticky="nsew")
        self.load_trips()

    def show_kas_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("kas")
            self.kas_frame.grid(row=0, column=1, sticky="nsew")
            self.load_kas()

    def show_plot_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("plot")
            self.plot_frame.grid(row=0, column=1, sticky="nsew")
            self.load_kursi_bus()

    def show_itin_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("itin")
            self.itin_frame.grid(row=0, column=1, sticky="nsew")
            self.load_itin()

    def show_manifest_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("manifest")
            self.manifest_frame.grid(row=0, column=1, sticky="nsew")
            self.load_manifest()

if __name__ == "__main__":
    db = setup_database()
    app = GatherSyncApp(db)
    app.mainloop()
    db.close()
