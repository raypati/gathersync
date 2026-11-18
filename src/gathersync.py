# GatherSync (TripMate): program utama.
# Bagian lima menu ada di file menu_*.py, aturan bisnis di aturan_bisnis.py,
# database di database.py, dan konfigurasi di konfigurasi.py.
import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox
import datetime
from tkcalendar import Calendar
from konfigurasi import COLOR, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, MENU_ITEMS, RULE_RISIKO_H_MINUS
# (sebagian impor di bawah juga dipakai test_gathersync.py lewat gathersync.<nama>)
from aturan_bisnis import cek_bentrok_jadwal, hash_password, hitung_kategori, hitung_rekomendasi_armada, hitung_status_risiko
from database import catat_audit, setup_database
from ui_umum import draw_gradient
from menu_dashboard import DashboardMixin
from menu_kas import KasMixin
from menu_plotting import PlottingMixin
from menu_itinerary import ItineraryMixin
from menu_manifest import ManifestMixin

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class GatherSyncApp(DashboardMixin, KasMixin, PlottingMixin, ItineraryMixin, ManifestMixin, ctk.CTk):
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

    def check_trip_active(self):
        if self.current_trip_id is None:
            messagebox.showwarning("Akses Ditolak", "Pilih Trip terlebih dahulu di menu Dashboard!")
            return False
        return True

    def hide_all(self):
        for frame in [self.dash_frame, self.kas_frame, self.plot_frame, self.itin_frame, self.manifest_frame]:
            frame.grid_forget()


if __name__ == "__main__":
    db = setup_database()
    app = GatherSyncApp(db)
    app.mainloop()
    db.close()
