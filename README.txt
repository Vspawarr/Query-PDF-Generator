# Query PDF Automation V1

## Purpose

Creates a Query PDF in this fixed sequence:

1. Input model - complete PDF
2. Datasheet - only user-selected pages
3. Pinfo sheet - complete PDF
4. Anfr sheet - complete PDF

The first page of each section receives a yellow top-right label:

- Input model
- Datasheet
- Pinfo sheet
- Anfr sheet

Original source PDFs are never modified.

## Requirements

Windows + Python 3.x.

Install the required Python packages:

    pip install -r requirements.txt

## Run

Double-click:

    Run_Query_PDF_Generator.bat

The popup will ask for:

1. Input Model PDF
2. Datasheet PDF
3. Required Datasheet pages
4. Pinfo Sheet PDF
5. Anfr Sheet PDF
6. Output file name (default: Query)
7. Output folder

## Datasheet page formats

Examples:

    2
    2,3
    2,4,6
    2-4
    2,5-7

Page numbers are the PDF page numbers shown in the PDF viewer, starting at 1.

## Output

If the output name is left as:

    Query

the generated file is:

    Query.pdf

The user selects the output folder through the Save/Folder dialog.

## Important

This V1 does not attempt to interpret the engineering query or decide which
datasheet pages are required. The user explicitly selects those pages.

The script preserves the original PDF pages and only overlays the section
label on the first page of each section.
