# Menu 1: Dashboard Trip (buat, ubah, hapus, pilih trip)
import customtkinter as ctk
import tkinter.messagebox as messagebox
import datetime
from konfigurasi import COLOR, FONT_BODY, FONT_BODY_BOLD, FONT_H2, FONT_SMALL, LEADER_DAN_TIM, LIST_LEADER, RULE_RISIKO_H_MINUS, RULE_SELANG_HARI
from aturan_bisnis import cek_bentrok_jadwal, hitung_rekomendasi_armada, hitung_status_risiko
from database import catat_audit

class DashboardMixin:
    """Menu 1: Dashboard Trip (buat, ubah, hapus, pilih trip)""" edit by riski

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

    def show_dash_frame(self):
        self.hide_all()
        self.set_active_menu("dash")
        self.dash_frame.grid(row=0, column=1, sticky="nsew")
        self.load_trips()
