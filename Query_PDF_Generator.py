# ============================================================
# ADD EDITABLE TEXT COMMENT
# ============================================================

def add_editable_text_comment(page, text):
    """
    Adds a visible editable PDF FreeText annotation.

    Appearance:
        - Larger yellow box
        - Black border
        - Bold black text
        - Center aligned
        - Top-right position
        - Comfortable padding
        - Plain editable text
        - No HTML / rich text
    """

    # --------------------------------------------------------
    # FONT SETTINGS
    # --------------------------------------------------------

    font_size = 14
    font_name = "HeBo"   # Helvetica Bold

    # --------------------------------------------------------
    # CALCULATE TEXT WIDTH
    # --------------------------------------------------------

    text_width = pymupdf.get_text_length(
        text,
        fontname=font_name,
        fontsize=font_size
    )

    # --------------------------------------------------------
    # BOX SIZE
    # --------------------------------------------------------

    # More generous padding than previous version
    padding_x = 12
    padding_y = 6

    label_width = (
        text_width
        + (padding_x * 2)
    )

    label_height = 30

    # --------------------------------------------------------
    # TOP-RIGHT POSITION
    # --------------------------------------------------------

    margin_right = 20
    margin_top = 20

    x1 = (
        page.rect.width
        - margin_right
    )

    x0 = (
        x1
        - label_width
    )

    y0 = margin_top

    y1 = (
        y0
        + label_height
    )

    rect = pymupdf.Rect(
        x0,
        y0,
        x1,
        y1
    )

    # --------------------------------------------------------
    # CREATE PLAIN-TEXT FREETEXT ANNOTATION
    # --------------------------------------------------------

    annot = page.add_freetext_annot(
        rect,
        text,
        fontsize=font_size,
        fontname=font_name,
        text_color=(0, 0, 0),
        fill_color=(1, 1, 0),
        border_width=1,
        opacity=1,
        align=pymupdf.TEXT_ALIGN_CENTER
    )

    # --------------------------------------------------------
    # UPDATE APPEARANCE
    # --------------------------------------------------------

    annot.update(
        fontsize=font_size,
        text_color=(0, 0, 0),
        fill_color=(1, 1, 0)
    )

    return annot
