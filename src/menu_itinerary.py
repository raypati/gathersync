# Menu 4: Itinerary
import customtkinter as ctk
import tkinter.messagebox as messagebox
import datetime
from konfigurasi import COLOR, FONT_BODY, FONT_BODY_BOLD, FONT_H2, FONT_SMALL

class ItineraryMixin:
    """Menu 4: Itinerary"""

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

    def show_itin_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("itin")
            self.itin_frame.grid(row=0, column=1, sticky="nsew")
            self.load_itin()
