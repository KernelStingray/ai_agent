import os
import html
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация кириллических шрифтов DejaVu Sans или других TrueType
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

font_candidates = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/freefont/FreeSans.ttf", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
]

for regular_path, bold_path in font_candidates:
    if os.path.exists(regular_path) and os.path.exists(bold_path):
        try:
            pdfmetrics.registerFont(TTFont("CustomSans", regular_path))
            pdfmetrics.registerFont(TTFont("CustomSans-Bold", bold_path))
            FONT_NAME = "CustomSans"
            FONT_BOLD = "CustomSans-Bold"
            break
        except Exception:
            pass


def _safe_text(val: Any) -> str:
    """Безопасное экранирование спецсимволов HTML/XML для ReportLab Paragraph."""
    return html.escape(str(val) if val is not None else "")


def create_styled_pdf(
    filepath: str,
    title: str,
    subtitle: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
    theme_color: str = "#4F46E5",  # Indigo
) -> str:
    """
    Создает высококачественный PDF документ с поддержкой кириллицы,
    таблицами и форматированием.
    """
    out_path = Path(filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Нормализация hex цвета (гарантируем ведущий # для reportlab HexColor)
    clean_hex = "#" + (theme_color or "4F46E5").lstrip("#")
    theme_hex_color = colors.HexColor(clean_hex)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    # Стили
    title_style = ParagraphStyle(
        "CustomTitle",
        fontName=FONT_BOLD,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "CustomSubTitle",
        fontName=FONT_NAME,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "CustomH1",
        fontName=FONT_BOLD,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        fontName=FONT_NAME,
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1E293B"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName=FONT_BOLD,
        fontSize=9.5,
        leading=13,
        textColor=colors.white,
    )

    story = []

    # Заголовок
    story.append(Paragraph(_safe_text(title), title_style))
    if subtitle:
        story.append(Paragraph(_safe_text(subtitle), subtitle_style))

    # Декоративная линия
    story.append(HRFlowable(width="100%", thickness=2, color=theme_hex_color, spaceAfter=14))

    if sections:
        for sec in sections:
            sec_type = sec.get("type", "paragraph")

            if sec_type == "heading":
                story.append(Paragraph(_safe_text(sec.get("text", "")), h1_style))

            elif sec_type == "paragraph":
                story.append(Paragraph(_safe_text(sec.get("text", "")), body_style))

            elif sec_type == "bullet":
                for it in sec.get("items", []):
                    bullet_text = f"• &nbsp; {_safe_text(it)}"
                    story.append(Paragraph(bullet_text, body_style))

            elif sec_type == "table":
                raw_headers = sec.get("headers", [])
                raw_rows = sec.get("rows", [])

                if raw_headers or raw_rows:
                    table_data = []
                    has_headers = bool(raw_headers)

                    if has_headers:
                        header_row = [Paragraph(_safe_text(h), table_header_style) for h in raw_headers]
                        table_data.append(header_row)

                    for r in raw_rows:
                        row = [Paragraph(_safe_text(val), table_cell_style) for val in r]
                        table_data.append(row)

                    if table_data:
                        t = Table(table_data, repeatRows=1 if has_headers else 0)
                        style_commands = [
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ]
                        if has_headers:
                            style_commands.append(("BACKGROUND", (0, 0), (-1, 0), theme_hex_color))

                        # Чередующаяся подсветка строк (Zebra)
                        start_zebra = 1 if has_headers else 0
                        for r_idx in range(start_zebra, len(table_data)):
                            if (r_idx - start_zebra) % 2 == 1:
                                style_commands.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor("#F8FAFC")))

                        t.setStyle(TableStyle(style_commands))
                        story.append(Spacer(1, 6))
                        story.append(t)
                        story.append(Spacer(1, 10))

    doc.build(story)
    return str(out_path)
