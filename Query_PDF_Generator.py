import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import pymupdf


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

    into zero-based page indexes.
    """

    if not page_text.strip():
        raise ValueError("No page numbers were entered.")

    pages = []

    for part in page_text.split(","):

        part = part.strip()

        if not part:
            continue

        # ----------------------------------------------------
        # Page range
        # ----------------------------------------------------

        if "-" in part:

            range_parts = part.split("-")

            if len(range_parts) != 2:
                raise ValueError(
                    f"Invalid page range: {part}"
                )

            start = int(
                range_parts[0].strip()
            )

            end = int(
                range_parts[1].strip()
            )

            if start > end:
                raise ValueError(
                    f"Invalid page range: {part}"
                )

            for page_number in range(
                start,
                end + 1
            ):

                if (
                    page_number < 1
                    or page_number > total_pages
                ):
                    raise ValueError(
                        f"Page {page_number} "
                        f"is outside the PDF."
                    )

                pages.append(
                    page_number - 1
                )

        # ----------------------------------------------------
        # Single page
        # ----------------------------------------------------

        else:

            try:
                page_number = int(part)
            except ValueError:
                raise ValueError(
                    f"Invalid page number: {part}"
                )

            if (
                page_number < 1
                or page_number > total_pages
            ):
                raise ValueError(
                    f"Page {page_number} "
                    f"is outside the PDF."
                )

            pages.append(
                page_number - 1
            )

    # --------------------------------------------------------
    # Remove duplicates while preserving order
    # --------------------------------------------------------

    unique_pages = []

    for page in pages:

        if page not in unique_pages:
            unique_pages.append(page)

    return unique_pages


# ============================================================
# ADD EDITABLE TEXT COMMENT
# ============================================================

def add_editable_text_comment(page, text):
    """
    Adds a visible editable PDF FreeText annotation.

    Appearance:
        - Yellow background
        - Black border
        - Bold black text
        - Center aligned
        - Tight fit around text
        - Top-right position

    IMPORTANT:
        This uses plain text only.
        No HTML.
        No richtext.
    """

    # --------------------------------------------------------
    # FONT SETTINGS
    # --------------------------------------------------------

    font_size = 10

    # Helvetica Bold
    font_name = "HeBo"

    # --------------------------------------------------------
    # CALCULATE TEXT WIDTH
    # --------------------------------------------------------

    text_width = pymupdf.get_text_length(
        text,
        fontname=font_name,
        fontsize=font_size
    )

    # --------------------------------------------------------
    # LABEL SIZE
    # --------------------------------------------------------

    padding_x = 7

    label_width = (
        text_width
        + (padding_x * 2)
    )

    label_height = 20

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


# ============================================================
# ADD PDF SECTION
# ============================================================

def add_pdf_section(
    output_doc,
    source_path,
    label,
    selected_pages=None
):
    """
    Adds one PDF section to the output document.

    selected_pages=None
        Adds the complete PDF.

    selected_pages=[...]
        Adds only selected pages.

    The editable label is added only to the
    first page of the section.
    """

    source_doc = pymupdf.open(
        source_path
    )

    try:

        total_pages = source_doc.page_count

        if total_pages == 0:
            raise ValueError(
                f"The PDF contains no pages:\n"
                f"{source_path}"
            )

        # ----------------------------------------------------
        # DETERMINE PAGES TO ADD
        # ----------------------------------------------------

        if selected_pages is None:

            pages_to_add = list(
                range(total_pages)
            )

        else:

            pages_to_add = selected_pages

        if not pages_to_add:
            raise ValueError(
                f"No pages selected from:\n"
                f"{source_path}"
            )

        # ----------------------------------------------------
        # INSERT PAGES
        # ----------------------------------------------------

        first_output_page = None

        for page_index in pages_to_add:

            if (
                page_index < 0
                or page_index >= total_pages
            ):
                raise ValueError(
                    f"Invalid page "
                    f"{page_index + 1} "
                    f"for:\n{source_path}"
                )

            # Current output page number
            output_page_number = (
                output_doc.page_count
            )

            # Insert exactly one page
            output_doc.insert_pdf(
                source_doc,
                from_page=page_index,
                to_page=page_index
            )

            # Remember first page of section
            if first_output_page is None:

                first_output_page = (
                    output_page_number
                )

        # ----------------------------------------------------
        # ADD LABEL TO FIRST PAGE ONLY
        # ----------------------------------------------------

        if first_output_page is not None:

            output_page = output_doc[
                first_output_page
            ]

            add_editable_text_comment(
                output_page,
                label
            )

    finally:

        source_doc.close()


# ============================================================
# SELECT PDF
# ============================================================

def select_pdf(title):

    return filedialog.askopenfilename(
        title=title,
        filetypes=[
            (
                "PDF files",
                "*.pdf"
            )
        ]
    )


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():

    root = tk.Tk()
    root.withdraw()

    try:

        # ====================================================
        # STEP 1
        # INPUT MODEL
        # ====================================================

        input_model = select_pdf(
            "Select Input Model PDF"
        )

        if not input_model:
            return

        # ====================================================
        # STEP 2
        # DATASHEET / PBLATT
        # ====================================================

        datasheet = select_pdf(
            "Select Datasheet / Pblatt PDF"
        )

        if not datasheet:
            return

        # ----------------------------------------------------
        # GET DATASHEET PAGE COUNT
        # ----------------------------------------------------

        datasheet_doc = pymupdf.open(
            datasheet
        )

        datasheet_total_pages = (
            datasheet_doc.page_count
        )

        datasheet_doc.close()

        # ----------------------------------------------------
        # ASK REQUIRED DATASHEET PAGES
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

        # ----------------------------------------------------
        # VALIDATE PAGE SELECTION
        # ----------------------------------------------------

        try:

            datasheet_pages = (
                parse_page_ranges(
                    page_text,
                    datasheet_total_pages
                )
            )

        except Exception as error:

            messagebox.showerror(
                "Invalid Page Selection",
                str(error)
            )

            return

        # ====================================================
        # STEP 3
        # PINFO SHEET
        # ====================================================

        pinfo = select_pdf(
            "Select Pinfo Sheet PDF"
        )

        if not pinfo:
            return

        # ====================================================
        # STEP 4
        # ANFR SHEET
        # ====================================================

        anfr = select_pdf(
            "Select Anfr Sheet PDF"
        )

        if not anfr:
            return

        # ====================================================
        # STEP 5
        # OUTPUT FILE NAME
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

        # ----------------------------------------------------
        # REMOVE .PDF IF USER ENTERED IT
        # ----------------------------------------------------

        if output_name.lower().endswith(
            ".pdf"
        ):
            output_name = output_name[:-4]

        # ----------------------------------------------------
        # REMOVE INVALID WINDOWS CHARACTERS
        # ----------------------------------------------------

        output_name = re.sub(
            r'[<>:"/\\|?*]',
            "_",
            output_name
        )

        if not output_name:
            output_name = "Query"

        # ====================================================
        # STEP 6
        # OUTPUT FOLDER
        # ====================================================

        output_folder = (
            filedialog.askdirectory(
                title="Select Output Folder"
            )
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

            os.path.abspath(
                input_model
            ),

            os.path.abspath(
                datasheet
            ),

            os.path.abspath(
                pinfo
            ),

            os.path.abspath(
                anfr
            )
        ]

        if (
            os.path.abspath(
                output_path
            )
            in source_files
        ):

            messagebox.showerror(
                "Invalid Output Location",

                (
                    "The output file cannot "
                    "overwrite one of the "
                    "source PDFs."
                )
            )

            return

        # ====================================================
        # CREATE OUTPUT DOCUMENT
        # ====================================================

        output_doc = pymupdf.open()

        try:

            # ------------------------------------------------
            # SECTION 1
            # INPUT MODEL
            # ------------------------------------------------

            add_pdf_section(
                output_doc,
                input_model,
                "Input model",
                None
            )

            # ------------------------------------------------
            # SECTION 2
            # DATASHEET
            # ------------------------------------------------

            add_pdf_section(
                output_doc,
                datasheet,
                "Datasheet",
                datasheet_pages
            )

            # ------------------------------------------------
            # SECTION 3
            # PINFO SHEET
            # ------------------------------------------------

            add_pdf_section(
                output_doc,
                pinfo,
                "Pinfo sheet",
                None
            )

            # ------------------------------------------------
            # SECTION 4
            # ANFR SHEET
            # ------------------------------------------------

            add_pdf_section(
                output_doc,
                anfr,
                "Anfr sheet",
                None
            )

            # =================================================
            # SAVE OUTPUT
            # =================================================

            output_doc.save(
                output_path,
                garbage=4,
                deflate=True
            )

        finally:

            output_doc.close()

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
