# Fungsi tampilan yang dipakai bersama

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
