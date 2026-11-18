# Menu 3: Plotting Kursi & Multi-Unit
import customtkinter as ctk
import tkinter.messagebox as messagebox
from konfigurasi import COLOR, FONT_BODY, FONT_BODY_BOLD, FONT_H2, FONT_SMALL, RULE_DP_MIN_PERSEN
from aturan_bisnis import hitung_kategori, hitung_rekomendasi_armada
from database import catat_audit

class PlottingMixin:
    """Menu 3: Plotting Kursi & Multi-Unit"""

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

    def show_plot_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("plot")
            self.plot_frame.grid(row=0, column=1, sticky="nsew")
            self.load_kursi_bus()
