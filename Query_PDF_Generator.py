import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    NameObject,
    DictionaryObject,
    ArrayObject,
    FloatObject,
    NumberObject,
    TextStringObject,
    DecodedStreamObject,
    RectangleObject,
    BooleanObject,
)


# ============================================================
# PAGE RANGE PARSER
# ============================================================

def parse_page_ranges(page_text, total_pages):
    """
    Converts:
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

        # Page range
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

        # Single page
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
# EDITABLE YELLOW LABEL / PDF FORM FIELD
# ============================================================

def add_editable_label(writer, page_number, label):
    """
    Adds a visible and editable PDF text field.

    Appearance:
        Yellow background
        Black border
        Black bold text

    The field is an actual PDF form field, not a static drawing.
    """

    page = writer.pages[page_number]

    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)

    # --------------------------------------------------------
    # Label settings
    # --------------------------------------------------------

    font_size = 13

    # Approximate Helvetica width
    text_width = len(label) * 7.5

    padding_x = 7
    padding_y = 5

    label_width = (
        text_width
        + (padding_x * 2)
    )

    label_height = (
        font_size
        + (padding_y * 2)
    )

    # --------------------------------------------------------
    # Position - top right
    # --------------------------------------------------------

    margin_right = 25
    margin_top = 25

    x1 = page_width - margin_right
    y1 = page_height - margin_top

    x0 = x1 - label_width
    y0 = y1 - label_height

    # --------------------------------------------------------
    # Appearance stream
    # --------------------------------------------------------

    appearance = DecodedStreamObject()

    # Escape PDF text characters
    safe_label = (
        label
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )

    appearance_content = f"""
q

1 1 0 rg
0 0 {label_width} {label_height} re
f

0 0 0 RG
1 w

0.5 0.5 m
{label_width - 0.5} 0.5 l
{label_width - 0.5} {label_height - 0.5} l
0.5 {label_height - 0.5} l
0.5 0.5 l
S

BT
/Helv {font_size} Tf
0 0 0 rg
{padding_x} {padding_y + 1} Td
({safe_label}) Tj
ET

Q
"""

    appearance.set_data(
        appearance_content.encode("latin-1")
    )

    appearance[
        NameObject("/Type")
    ] = NameObject("/XObject")

    appearance[
        NameObject("/Subtype")
    ] = NameObject("/Form")

    appearance[
        NameObject("/BBox")
    ] = RectangleObject(
        (
            0,
            0,
            label_width,
            label_height
        )
    )

    # Helvetica resource
    appearance[
        NameObject("/Resources")
    ] = DictionaryObject({

        NameObject("/Font"): DictionaryObject({

            NameObject("/Helv"): DictionaryObject({

                NameObject("/Type"):
                    NameObject("/Font"),

                NameObject("/Subtype"):
                    NameObject("/Type1"),

                NameObject("/BaseFont"):
                    NameObject("/Helvetica")
            })
        })
    })

    appearance_ref = writer._add_object(
        appearance
    )

    # --------------------------------------------------------
    # PDF Form Widget
    # --------------------------------------------------------

    widget = DictionaryObject({

        NameObject("/Type"):
            NameObject("/Annot"),

        NameObject("/Subtype"):
            NameObject("/Widget"),

        NameObject("/FT"):
            NameObject("/Tx"),

        NameObject("/T"):
            TextStringObject(label),

        NameObject("/V"):
            TextStringObject(label),

        NameObject("/DV"):
            TextStringObject(label),

        NameObject("/Rect"):
            RectangleObject(
                (
                    x0,
                    y0,
                    x1,
                    y1
                )
            ),

        # Printable
        NameObject("/F"):
            NumberObject(4),

        # Editable text field
        NameObject("/Ff"):
            NumberObject(0),

        # Default appearance
        NameObject("/DA"):
            TextStringObject(
                "/Helv 13 Tf 0 0 0 rg"
            ),

        # Visible appearance
        NameObject("/AP"):
            DictionaryObject({
                NameObject("/N"):
                    appearance_ref
            }),

        # Yellow background + black border
        NameObject("/MK"):
            DictionaryObject({

                NameObject("/BG"):
                    ArrayObject([
                        FloatObject(1),
                        FloatObject(1),
                        FloatObject(0)
                    ]),

                NameObject("/BC"):
                    ArrayObject([
                        FloatObject(0),
                        FloatObject(0),
                        FloatObject(0)
                    ])
            }),

        # Border
        NameObject("/BS"):
            DictionaryObject({

                NameObject("/W"):
                    NumberObject(1),

                NameObject("/S"):
                    NameObject("/S")
            })
    })

    widget_ref = writer._add_object(
        widget
    )

    # --------------------------------------------------------
    # Add widget to page annotations
    # --------------------------------------------------------

    existing_annots = page.get(
        NameObject("/Annots")
    )

    if existing_annots is None:

        page[
            NameObject("/Annots")
        ] = ArrayObject([
            widget_ref
        ])

    else:

        annot_array = (
            existing_annots.get_object()
        )

        annot_array.append(
            widget_ref
        )

    # --------------------------------------------------------
    # Add field to AcroForm
    # --------------------------------------------------------

    root = writer._root_object

    acro_form = root.get(
        NameObject("/AcroForm")
    )

    if acro_form is None:

        acro_form = DictionaryObject()

        root[
            NameObject("/AcroForm")
        ] = acro_form

    fields = acro_form.get(
        NameObject("/Fields")
    )

    if fields is None:

        fields = ArrayObject()

        acro_form[
            NameObject("/Fields")
        ] = fields

    fields.append(
        widget_ref
    )

    # --------------------------------------------------------
    # Form appearance configuration
    # --------------------------------------------------------

    acro_form[
        NameObject("/NeedAppearances")
    ] = BooleanObject(True)

    acro_form[
        NameObject("/DA")
    ] = TextStringObject(
        "/Helv 13 Tf 0 0 0 rg"
    )

    # Default resources
    acro_form[
        NameObject("/DR")
    ] = DictionaryObject({

        NameObject("/Font"): DictionaryObject({

            NameObject("/Helv"): DictionaryObject({

                NameObject("/Type"):
                    NameObject("/Font"),

                NameObject("/Subtype"):
                    NameObject("/Type1"),

                NameObject("/BaseFont"):
                    NameObject("/Helvetica")
            })
        })
    })


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
    Adds one PDF section.

    selected_pages=None:
        Complete PDF.

    selected_pages=[...]:
        Selected pages only.

    Adds the editable label only to the
    first page of the section.
    """

    reader = PdfReader(
        pdf_path
    )

    total_pages = len(
        reader.pages
    )

    if total_pages == 0:

        raise ValueError(
            f"The PDF contains no pages:\n{pdf_path}"
        )

    # --------------------------------------------------------
    # Determine pages
    # --------------------------------------------------------

    if selected_pages is None:

        pages_to_add = list(
            range(total_pages)
        )

    else:

        pages_to_add = selected_pages

    if not pages_to_add:

        raise ValueError(
            f"No pages selected from:\n{pdf_path}"
        )

    # --------------------------------------------------------
    # Add pages
    # --------------------------------------------------------

    for position, page_index in enumerate(
        pages_to_add
    ):

        if (
            page_index < 0
            or page_index >= total_pages
        ):

            raise ValueError(
                f"Invalid page index "
                f"{page_index + 1} "
                f"for:\n{pdf_path}"
            )

        page = reader.pages[
            page_index
        ]

        # Add page
        writer.add_page(
            page
        )

        # ----------------------------------------------------
        # First page of section only
        # ----------------------------------------------------

        if position == 0:

            output_page_number = (
                len(writer.pages) - 1
            )

            add_editable_label(
                writer,
                output_page_number,
                label
            )


# ============================================================
# SELECT PDF
# ============================================================

def select_pdf(title):

    file_path = (
        filedialog.askopenfilename(
            title=title,
            filetypes=[
                (
                    "PDF files",
                    "*.pdf"
                )
            ]
        )
    )

    return file_path


# ============================================================
# MAIN APPLICATION
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
        # Ask Datasheet pages
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
        # 5. OUTPUT NAME
        # ====================================================

        output_name = simpledialog.askstring(
            "Output File Name",
            "Enter output file name:",
            initialvalue="Query"
        )

        if output_name is None:
            return

        output_name = (
            output_name.strip()
        )

        if not output_name:
            output_name = "Query"

        if output_name.lower().endswith(
            ".pdf"
        ):

            output_name = (
                output_name[:-4]
            )

        # Remove invalid Windows characters
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
        # PINFO SHEET
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=pinfo,
            label="Pinfo sheet",
            selected_pages=None
        )

        # ----------------------------------------------------
        # ANFR SHEET
        # ----------------------------------------------------

        add_pdf_section(
            writer=writer,
            pdf_path=anfr,
            label="Anfr sheet",
            selected_pages=None
        )

        # ====================================================
        # WRITE OUTPUT
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
