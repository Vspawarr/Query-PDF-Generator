import os
import re
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
except ImportError:
    messagebox.showerror(
        "Missing Libraries",
        "Required libraries are missing.\n\n"
        "Please install:\n"
        "pip install pypdf reportlab"
    )
    raise


# ============================================================
# PAGE RANGE PARSER
# ============================================================

def parse_page_ranges(page_text, total_pages):
    """
    Converts user input such as:

        2
        2,3
        2,4,6
        2-4
        2,5-7

    into zero-based PDF page indexes.

    Example:
        1,3-5
    becomes:
        [0, 2, 3, 4]
    """

    if not page_text.strip():
        raise ValueError("No page numbers were entered.")

    pages = []

    parts = page_text.split(",")

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # Range, e.g. 2-5
        if "-" in part:
            range_parts = part.split("-")

            if len(range_parts) != 2:
                raise ValueError(
                    f"Invalid page range: {part}"
                )

            start = int(range_parts[0].strip())
            end = int(range_parts[1].strip())

            if start > end:
                raise ValueError(
                    f"Invalid page range: {part}"
                )

            for page_number in range(start, end + 1):

                if page_number < 1 or page_number > total_pages:
                    raise ValueError(
                        f"Page {page_number} is outside the PDF."
                    )

                pages.append(page_number - 1)

        else:
            # Single page
            page_number = int(part)

            if page_number < 1 or page_number > total_pages:
                raise ValueError(
                    f"Page {page_number} is outside the PDF."
                )

            pages.append(page_number - 1)

    # Remove duplicates while preserving order
    unique_pages = []

    for page in pages:
        if page not in unique_pages:
            unique_pages.append(page)

    return unique_pages


# ============================================================
# SECTION LABEL OVERLAY
# ============================================================

def make_label_overlay(
    page_width,
    page_height,
    label,
    output_path
):
    """
    Creates ONLY the small section-name label.

    Appearance:
        Yellow background
        Black border
        Black text

    The rectangle is tightly fitted around the text.

    No other shapes, patches or colored areas are created.
    """

    c = canvas.Canvas(
        output_path,
        pagesize=(page_width, page_height)
    )

    font_name = "Helvetica-Bold"
    font_size = 13

    c.setFont(
        font_name,
        font_size
    )

    # Calculate exact text width
    text_width = c.stringWidth(
        label,
        font_name,
        font_size
    )

    # Small padding around text
    padding_x = 7
    padding_y = 5

    label_width = text_width + (padding_x * 2)
    label_height = font_size + (padding_y * 2)

    # Position at top-right
    margin_right = 25
    margin_top = 25

    x = (
        page_width
        - margin_right
        - label_width
    )

    y = (
        page_height
        - margin_top
        - label_height
    )

    # --------------------------------------------------------
    # YELLOW RECTANGLE WITH BLACK BORDER
    # --------------------------------------------------------

    c.setFillColorRGB(
        1,
        1,
        0
    )

    c.setStrokeColorRGB(
        0,
        0,
        0
    )

    c.setLineWidth(1)

    c.rect(
        x,
        y,
        label_width,
        label_height,
        fill=1,
        stroke=1
    )

    # --------------------------------------------------------
    # BLACK TEXT
    # --------------------------------------------------------

    c.setFillColorRGB(
        0,
        0,
        0
    )

    text_x = x + padding_x
    text_y = y + padding_y + 1

    c.drawString(
        text_x,
        text_y,
        label
    )

    c.save()


# ============================================================
# ADD PDF SECTION
# ============================================================

def add_pdf_section(
    writer,
    pdf_path,
    label,
    selected_pages=None
):
    """
    Adds pages from one PDF into the final PDF.

    selected_pages:
        None = all pages
        List = selected zero-based page indexes

    The section label is applied only to the first page
    of the section.
    """

    reader = PdfReader(pdf_path)

    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError(
            f"The PDF contains no pages:\n{pdf_path}"
        )

    # --------------------------------------------------------
    # Determine pages to add
    # --------------------------------------------------------

    if selected_pages is None:
        pages_to_add = list(range(total_pages))
    else:
        pages_to_add = selected_pages

    if not pages_to_add:
        raise ValueError(
            f"No pages selected from:\n{pdf_path}"
        )

    # --------------------------------------------------------
    # Add selected pages
    # --------------------------------------------------------

    for position, page_index in enumerate(pages_to_add):

        if page_index < 0 or page_index >= total_pages:
            raise ValueError(
                f"Invalid page index {page_index + 1} "
                f"for:\n{pdf_path}"
            )

        page = reader.pages[page_index]

        # ----------------------------------------------------
        # Add label ONLY to first page of this section
        # ----------------------------------------------------

        if position == 0:

            page_width = float(
                page.mediabox.width
            )

            page_height = float(
                page.mediabox.height
            )

            with tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False
            ) as temp_file:

                overlay_path = temp_file.name

            try:

                make_label_overlay(
                    page_width,
                    page_height,
                    label,
                    overlay_path
                )

                overlay_reader = PdfReader(
                    overlay_path
                )

                overlay_page = (
                    overlay_reader.pages[0]
                )

                page.merge_page(
                    overlay_page
                )

            finally:

                if os.path.exists(
                    overlay_path
                ):
                    os.remove(
                        overlay_path
                    )

        writer.add_page(page)


# ============================================================
# SELECT PDF FILE
# ============================================================

def select_pdf(title):
    """
    Opens a PDF file selection dialog.
    """

    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[
            (
                "PDF files",
                "*.pdf"
            )
        ]
    )

    return file_path


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():

    # --------------------------------------------------------
    # Hide main Tkinter window
    # --------------------------------------------------------

    root = tk.Tk()
    root.withdraw()

    try:

        # ====================================================
        # STEP 1 - INPUT MODEL
        # ====================================================

        input_model = select_pdf(
            "Select Input Model PDF"
        )

        if not input_model:
            return

        # ====================================================
        # STEP 2 - DATASHEET
        # ====================================================

        datasheet = select_pdf(
            "Select Datasheet / Pblatt PDF"
        )

        if not datasheet:
            return

        # Read datasheet page count
        datasheet_reader = PdfReader(
            datasheet
        )

        datasheet_total_pages = len(
            datasheet_reader.pages
        )

        # ----------------------------------------------------
        # Ask which datasheet pages are required
        # ----------------------------------------------------

        page_text = simpledialog.askstring(
            "Datasheet Pages",
            (
                "Enter required Datasheet pages.\n\n"
                "Examples:\n"
                "2\n"
                "2,3\n"
                "2,4,6\n"
                "2-4\n"
                "2,5-7\n\n"
                f"Total pages available: "
                f"{datasheet_total_pages}"
            )
        )

        if page_text is None:
            return

        try:

            datasheet_pages = parse_page_ranges(
                page_text,
                datasheet_total_pages
            )

        except Exception as error:

            messagebox.showerror(
                "Invalid Page Selection",
                str(error)
            )

            return

        # ====================================================
        # STEP 3 - PINFO SHEET
        # ====================================================

        pinfo = select_pdf(
            "Select Pinfo Sheet PDF"
        )

        if not pinfo:
            return

        # ====================================================
        # STEP 4 - ANFR SHEET
        # ====================================================

        anfr = select_pdf(
            "Select Anfr Sheet PDF"
        )

        if not anfr:
            return

        # ====================================================
        # STEP 5 - OUTPUT FILE NAME
        # ====================================================

        output_name = simpledialog.askstring(
            "Output File Name",
            "Enter output file name:",
            initialvalue="Query"
        )

        if output_name is None:
            return

        output_name = output_name.strip()

        if not output_name:
            output_name = "Query"

        # Remove .pdf if user entered it
        if output_name.lower().endswith(
            ".pdf"
        ):
            output_name = output_name[:-4]

        # Remove invalid Windows filename characters
        output_name = re.sub(
            r'[<>:"/\\|?*]',
            "_",
            output_name
        )

        if not output_name:
            output_name = "Query"

        # ====================================================
        # STEP 6 - SELECT OUTPUT FOLDER
        # ====================================================

        output_folder = filedialog.askdirectory(
            title="Select Output Folder"
        )

        if not output_folder:
            return

        output_path = os.path.join(
            output_folder,
            output_name + ".pdf"
        )

        # ====================================================
        # PREVENT OVERWRITING SOURCE FILES
        # ====================================================

        source_files = [
            os.path.abspath(input_model),
            os.path.abspath(datasheet),
            os.path.abspath(pinfo),
            os.path.abspath(anfr)
        ]

        if os.path.abspath(output_path) in source_files:

            messagebox.showerror(
                "Invalid Output Location",
                "The output file cannot overwrite "
                "one of the source PDFs."
            )

            return

        # ====================================================
        # CREATE FINAL PDF
        # ====================================================

        writer = PdfWriter()

        # ----------------------------------------------------
        # SECTION 1
        # Input model - COMPLETE PDF
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=input_model,
            label="Input model",
            selected_pages=None
        )

        # ----------------------------------------------------
        # SECTION 2
        # Datasheet - SELECTED PAGES ONLY
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=datasheet,
            label="Datasheet",
            selected_pages=datasheet_pages
        )

        # ----------------------------------------------------
        # SECTION 3
        # Pinfo sheet - COMPLETE PDF
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=pinfo,
            label="Pinfo sheet",
            selected_pages=None
        )

        # ----------------------------------------------------
        # SECTION 4
        # Anfr sheet - COMPLETE PDF
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=anfr,
            label="Anfr sheet",
            selected_pages=None
        )

        # ====================================================
        # WRITE FINAL PDF
        # ====================================================

        with open(
            output_path,
            "wb"
        ) as output_file:

            writer.write(
                output_file
            )

        # ====================================================
        # SUCCESS MESSAGE
        # ====================================================

        messagebox.showinfo(
            "Query PDF Generated",
            (
                "Query PDF generated successfully!\n\n"
                f"Output:\n{output_path}"
            )
        )

    except Exception as error:

        messagebox.showerror(
            "Error",
            (
                "An error occurred while generating "
                "the Query PDF.\n\n"
                f"{error}"
            )
        )

    finally:

        root.destroy()


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":
    main()
