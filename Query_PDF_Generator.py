import os
import re
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import black, yellow
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Missing Python packages",
        "Required packages are missing.\n\n"
        "Open Command Prompt in this folder and run:\n"
        "pip install -r requirements.txt"
    )
    raise


APP_TITLE = "Query PDF Generator - V1"
DEFAULT_OUTPUT_NAME = "Query"
LABEL_WIDTH = 115
LABEL_HEIGHT = 30
LABEL_MARGIN_RIGHT = 25
LABEL_MARGIN_TOP = 25
LABEL_FONT_SIZE = 13


def select_pdf(title):
    path = filedialog.askopenfilename(
        title=title,
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    return path


def parse_page_ranges(text, max_page):
    """
    Accepts:
      2
      2,3,5
      2-4
      2,5-7,9
    Returns zero-based page indexes, preserving entered order and removing duplicates.
    """
    text = text.strip()
    if not text:
        raise ValueError("Datasheet page selection cannot be empty.")

    result = []
    seen = set()

    for part in text.split(","):
        part = part.strip()
        if not part:
            continue

        if re.fullmatch(r"\d+", part):
            page = int(part)
            if page < 1 or page > max_page:
                raise ValueError(f"Page {page} is outside the datasheet range 1-{max_page}.")
            indexes = [page - 1]

        elif re.fullmatch(r"\d+\s*-\s*\d+", part):
            start, end = [int(x.strip()) for x in part.split("-")]
            if start < 1 or end < 1 or start > end:
                raise ValueError(f"Invalid page range: {part}")
            if end > max_page:
                raise ValueError(f"Page range {part} exceeds datasheet page count {max_page}.")
            indexes = list(range(start - 1, end))

        else:
            raise ValueError(
                f"Invalid page entry: '{part}'. Use examples such as 2, 2,3, 2-4 or 2,5-7."
            )

        for idx in indexes:
            if idx not in seen:
                seen.add(idx)
                result.append(idx)

    if not result:
        raise ValueError("No valid datasheet pages were selected.")

    return result


def make_label_overlay(page_width, page_height, label, output_path):
    """
    Creates a one-page transparent PDF overlay with the yellow top-right label.
    Coordinates are based on the page's own dimensions.
    """
    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

    x = page_width - LABEL_MARGIN_RIGHT - LABEL_WIDTH
    y = page_height - LABEL_MARGIN_TOP - LABEL_HEIGHT

    c.setFillColor(yellow)
    c.setStrokeColor(black)
    c.setLineWidth(1.0)
    c.rect(x, y, LABEL_WIDTH, LABEL_HEIGHT, fill=1, stroke=1)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", LABEL_FONT_SIZE)

    # Center text vertically/horizontally.
    text_width = c.stringWidth(label, "Helvetica-Bold", LABEL_FONT_SIZE)
    tx = x + max(4, (LABEL_WIDTH - text_width) / 2)
    ty = y + (LABEL_HEIGHT - LABEL_FONT_SIZE) / 2 + 3
    c.drawString(tx, ty, label)

    c.save()


def add_label_to_first_page(reader, label, temp_dir):
    """
    Returns a new PdfReader containing all pages, with the label overlaid
    only on page 1.
    """
    first_page = reader.pages[0]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)

    overlay_path = os.path.join(
        temp_dir, f"label_{re.sub(r'[^A-Za-z0-9]+', '_', label)}.pdf"
    )
    make_label_overlay(width, height, label, overlay_path)

    overlay_reader = PdfReader(overlay_path)
    first_page.merge_page(overlay_reader.pages[0])

    return reader


def add_pdf_section(writer, pdf_path, label, selected_pages=None, temp_dir=None):
    """
    Adds a PDF section to writer.
    selected_pages=None => all pages.
    selected_pages=list => only those zero-based pages.
    Label is applied only to the first page of that section.
    """
    reader = PdfReader(pdf_path)

    if len(reader.pages) == 0:
        raise ValueError(f"PDF contains no pages: {pdf_path}")

    indexes = list(range(len(reader.pages))) if selected_pages is None else selected_pages

    if not indexes:
        raise ValueError(f"No pages selected from: {pdf_path}")

    # Label the first page of the section only.
    first_idx = indexes[0]
    page = reader.pages[first_idx]

    width = float(page.mediabox.width)
    height = float(page.mediabox.height)

    overlay_path = os.path.join(
        temp_dir,
        f"overlay_{len(writer.pages)}_{re.sub(r'[^A-Za-z0-9]+', '_', label)}.pdf"
    )
    make_label_overlay(width, height, label, overlay_path)
    overlay_reader = PdfReader(overlay_path)
    page.merge_page(overlay_reader.pages[0])

    for idx in indexes:
        writer.add_page(reader.pages[idx])


def safe_output_path(folder, name):
    name = name.strip()
    if not name:
        name = DEFAULT_OUTPUT_NAME
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return os.path.join(folder, name)


def main():
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo(
        APP_TITLE,
        "Select the source PDFs in this order:\n\n"
        "1. Input model\n"
        "2. Datasheet\n"
        "3. Pinfo sheet\n"
        "4. Anfr sheet"
    )

    input_model = select_pdf("1. Select Input Model PDF")
    if not input_model:
        return

    datasheet = select_pdf("2. Select Datasheet / Pblatt PDF")
    if not datasheet:
        return

    try:
        ds_reader = PdfReader(datasheet)
        ds_count = len(ds_reader.pages)
    except Exception as e:
        messagebox.showerror("Datasheet Error", f"Could not read datasheet:\n\n{e}")
        return

    pages_text = simpledialog.askstring(
        APP_TITLE,
        f"3. Enter required Datasheet page(s)\n\n"
        f"Datasheet has {ds_count} page(s).\n\n"
        f"Examples:\n"
        f"  2\n"
        f"  2,3,5\n"
        f"  2-4\n"
        f"  2,5-7\n",
        initialvalue="1"
    )
    if pages_text is None:
        return

    try:
        selected_pages = parse_page_ranges(pages_text, ds_count)
    except ValueError as e:
        messagebox.showerror("Invalid Datasheet Pages", str(e))
        return

    pinfo = select_pdf("4. Select Pinfo Sheet PDF")
    if not pinfo:
        return

    anfr = select_pdf("5. Select Anfr Sheet PDF")
    if not anfr:
        return

    output_name = simpledialog.askstring(
        APP_TITLE,
        "Output file name:",
        initialvalue=DEFAULT_OUTPUT_NAME
    )
    if output_name is None:
        return

    output_folder = filedialog.askdirectory(
        title="Select Output Folder"
    )
    if not output_folder:
        return

    output_path = safe_output_path(output_folder, output_name)

    if os.path.exists(output_path):
        overwrite = messagebox.askyesno(
            "File Exists",
            f"The file already exists:\n\n{output_path}\n\nOverwrite it?"
        )
        if not overwrite:
            return

    files = [
        ("Input model", input_model),
        ("Datasheet", datasheet),
        ("Pinfo sheet", pinfo),
        ("Anfr sheet", anfr),
    ]

    for label, path in files:
        if not os.path.isfile(path):
            messagebox.showerror(
                "File Error",
                f"{label} file was not found:\n\n{path}"
            )
            return

    try:
        writer = PdfWriter()

        with tempfile.TemporaryDirectory(prefix="QueryPDF_") as temp_dir:
            # Complete Input Model
            add_pdf_section(
                writer,
                input_model,
                "Input model",
                selected_pages=None,
                temp_dir=temp_dir
            )

            # Selected Datasheet pages only
            add_pdf_section(
                writer,
                datasheet,
                "Datasheet",
                selected_pages=selected_pages,
                temp_dir=temp_dir
            )

            # Complete Pinfo
            add_pdf_section(
                writer,
                pinfo,
                "Pinfo sheet",
                selected_pages=None,
                temp_dir=temp_dir
            )

            # Complete Anfr
            add_pdf_section(
                writer,
                anfr,
                "Anfr sheet",
                selected_pages=None,
                temp_dir=temp_dir
            )

            with open(output_path, "wb") as f:
                writer.write(f)

        total_pages = len(PdfReader(output_path).pages)

        messagebox.showinfo(
            "Query PDF Generated",
            f"Query PDF generated successfully.\n\n"
            f"File:\n{output_path}\n\n"
            f"Datasheet pages: {pages_text}\n"
            f"Total output pages: {total_pages}"
        )

    except Exception as e:
        messagebox.showerror(
            "Generation Failed",
            "The Query PDF could not be generated.\n\n"
            f"Error:\n{e}"
        )


if __name__ == "__main__":
    main()
