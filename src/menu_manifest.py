# Menu 5: Manifest & Audit PDF
import customtkinter as ctk
import tkinter.messagebox as messagebox
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from konfigurasi import COLOR
from aturan_bisnis import hitung_rekomendasi_armada

class ManifestMixin:
    """Menu 5: Manifest & Audit PDF"""

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

    def show_manifest_frame(self):
        if self.check_trip_active():
            self.hide_all()
            self.set_active_menu("manifest")
            self.manifest_frame.grid(row=0, column=1, sticky="nsew")
            self.load_manifest()
