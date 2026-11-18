# Konfigurasi: warna, font, daftar menu, daftar leader, dan konstanta aturan bisnis

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
