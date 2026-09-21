import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText


# ============================================================
# PAGE RANGE PARSER
# ============================================================

def parse_page_ranges(page_text, total_pages):
    """
    Converts page input such as:
        2
        2,3
        2,4,6
        2-4
        2,5-7

    into zero-based PDF page indexes.
    """

    if not page_text.strip():
        raise ValueError("No page numbers were entered.")

    pages = []

    for part in page_text.split(","):

        part = part.strip()

        if not part:
            continue

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
# EDITABLE PDF LABEL
# ============================================================

def add_editable_label(page, label):
    """
    Adds an EDITABLE FreeText PDF annotation.

    Appearance:
        Yellow background
        Black border
        Black text

    The label is an annotation object rather than a
    permanently drawn graphic.

    Therefore compatible PDF editors can edit/move/resize it.
    """

    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)

    # --------------------------------------------------------
    # Label appearance
    # --------------------------------------------------------

    font_size = 13

    # Approximate width of the text.
    # Helvetica-Bold is approximately 7.5 points per character
    # at this font size.
    text_width = len(label) * 7.5

    padding_x = 7
    padding_y = 5

    label_width = text_width + (padding_x * 2)
    label_height = font_size + (padding_y * 2)

    # --------------------------------------------------------
    # Top-right position
    # --------------------------------------------------------

    margin_right = 25
    margin_top = 25

    x1 = page_width - margin_right
    y1 = page_height - margin_top

    x0 = x1 - label_width
    y0 = y1 - label_height

    # --------------------------------------------------------
    # FreeText annotation
    # --------------------------------------------------------

    annotation = FreeText(
        text=label,
        rect=(
            x0,
            y0,
            x1,
            y1
        ),
        font="Helvetica-Bold",
        bold=True,
        font_size=f"{font_size}pt",
        font_color="000000",
        border_color="000000",
        background_color="FFFF00"
    )

    # Add editable annotation to page
    page.add_annotation(annotation)


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
    Adds a PDF section to the final document.

    selected_pages=None
        Adds the complete PDF.

    selected_pages=[...]
        Adds only selected pages.

    An editable label is added ONLY to the first page
    of each section.
    """

    reader = PdfReader(pdf_path)

    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError(
            f"The PDF contains no pages:\n{pdf_path}"
        )

    # --------------------------------------------------------
    # Determine pages
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
    # Add pages
    # --------------------------------------------------------

    for position, page_index in enumerate(pages_to_add):

        if page_index < 0 or page_index >= total_pages:
            raise ValueError(
                f"Invalid page index {page_index + 1} "
                f"for:\n{pdf_path}"
            )

        page = reader.pages[page_index]

        # ----------------------------------------------------
        # Add editable label only to first section page
        # ----------------------------------------------------

        if position == 0:
            add_editable_label(
                page,
                label
            )

        writer.add_page(page)


# ============================================================
# SELECT PDF
# ============================================================

def select_pdf(title):

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
# MAIN
# ============================================================

def main():

    root = tk.Tk()
    root.withdraw()

    try:

        # ====================================================
        # 1. INPUT MODEL
        # ====================================================

        input_model = select_pdf(
            "Select Input Model PDF"
        )

        if not input_model:
            return

        # ====================================================
        # 2. DATASHEET
        # ====================================================

        datasheet = select_pdf(
            "Select Datasheet / Pblatt PDF"
        )

        if not datasheet:
            return

        datasheet_reader = PdfReader(
            datasheet
        )

        datasheet_total_pages = len(
            datasheet_reader.pages
        )

        # ----------------------------------------------------
        # Datasheet page selection
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
        # 3. PINFO SHEET
        # ====================================================

        pinfo = select_pdf(
            "Select Pinfo Sheet PDF"
        )

        if not pinfo:
            return

        # ====================================================
        # 4. ANFR SHEET
        # ====================================================

        anfr = select_pdf(
            "Select Anfr Sheet PDF"
        )

        if not anfr:
            return

        # ====================================================
        # 5. OUTPUT FILE NAME
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

        if output_name.lower().endswith(".pdf"):
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
        # 6. OUTPUT FOLDER
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
        # PREVENT SOURCE OVERWRITE
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
        # INPUT MODEL
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=input_model,
            label="Input model",
            selected_pages=None
        )

        # ----------------------------------------------------
        # DATASHEET
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=datasheet,
            label="Datasheet",
            selected_pages=datasheet_pages
        )

        # ----------------------------------------------------
        # PINFO
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=pinfo,
            label="Pinfo sheet",
            selected_pages=None
        )

        # ----------------------------------------------------
        # ANFR
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=anfr,
            label="Anfr sheet",
            selected_pages=None
        )

        # ====================================================
        # WRITE PDF
        # ====================================================

        with open(
            output_path,
            "wb"
        ) as output_file:

            writer.write(
                output_file
            )

        # ====================================================
        # SUCCESS
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
