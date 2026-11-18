# Menu 2: Registrasi & Kas peserta
import customtkinter as ctk
import tkinter.messagebox as messagebox
from konfigurasi import COLOR, FONT_BODY, FONT_BODY_BOLD, FONT_H2, FONT_SMALL, STATUS_STYLE
from aturan_bisnis import hitung_kategori
from database import catat_audit

class KasMixin:
    """Menu 2: Registrasi & Kas peserta"""

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

    def show_kas_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("kas")
            self.kas_frame.grid(row=0, column=1, sticky="nsew")
            self.load_kas()
