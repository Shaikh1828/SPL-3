"""
DOCX Builder for Bull's Eye SPL-3 Final Technical Report.
Converts structured markdown and elements into a professionally styled Microsoft Word document (.docx).
"""

import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

NAVY_PRIMARY = RGBColor(30, 58, 138)      # #1E3A8A
BLUE_SECONDARY = RGBColor(30, 64, 175)    # #1E40AF
BLUE_TERTIARY = RGBColor(37, 99, 235)     # #2563EB
TEXT_DARK = RGBColor(31, 41, 55)          # #1F2937
TEXT_MUTED = RGBColor(75, 85, 99)         # #4B5563
WHITE = RGBColor(255, 255, 255)

def set_cell_background(cell, hex_color):
    """Sets background color of a table cell."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets inner margins for a table cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    """Sets thin subtle borders around and inside table."""
    tblPr = table._tbl.tblPr
    borders_elm = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders_elm)

def add_styled_paragraph(doc, text="", style='Normal', space_before=0, space_after=6, line_spacing=1.15):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    if text:
        add_formatted_runs(p, text)
    return p

def clean_xml_string(s):
    """Filters out characters that are invalid in XML 1.0."""
    if not isinstance(s, str):
        return str(s)
    def is_xml_valid(ch):
        c = ord(ch)
        return (c == 0x9 or c == 0xA or c == 0xD or
                (0x20 <= c <= 0xD7FF) or
                (0xE000 <= c <= 0xFFFD) or
                (0x10000 <= c <= 0x10FFFF))
    return ''.join(ch for ch in s if is_xml_valid(ch))

def add_formatted_runs(paragraph, text, default_font="Calibri", default_size=11, default_color=TEXT_DARK, bold=False, italic=False):
    """Parses inline bold (**text**), code (`code`), and italics (*text*) into formatted runs."""
    text = clean_xml_string(text)
    # Pattern to find **bold**, `code`, *italic*
    pattern = re.compile(r'(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)')
    parts = pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        run = paragraph.add_run()
        run.font.name = default_font
        run.font.size = Pt(default_size)
        run.font.color.rgb = default_color
        run.bold = bold
        run.italic = italic

        if part.startswith('**') and part.endswith('**'):
            run.text = clean_xml_string(part[2:-2])
            run.bold = True
        elif part.startswith('`') and part.endswith('`'):
            run.text = clean_xml_string(part[1:-1])
            run.font.name = 'Consolas'
            run.font.size = Pt(default_size - 1)
            run.font.color.rgb = RGBColor(180, 40, 40)
        elif part.startswith('*') and part.endswith('*'):
            run.text = clean_xml_string(part[1:-1])
            run.italic = True
        else:
            run.text = clean_xml_string(part)


def build_docx_from_markdown(markdown_text, output_docx_path):
    """Converts complete markdown document to a beautifully formatted Word document."""
    doc = Document()
    
    # Configure 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        # Header & Footer setup
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Bull's Eye: Automated Archery Scoring System | SPL-3 Final Technical Report")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(140, 150, 160)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("Institute of Information Technology, University of Dhaka")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(140, 150, 160)

    lines = markdown_text.split('\n')
    i = 0
    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # Handle Code Block fences
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block
                code_text = '\n'.join(code_lines)
                tbl = doc.add_table(rows=1, cols=1)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl.autofit = False
                tbl.columns[0].width = Inches(6.5)
                
                cell = tbl.cell(0, 0)
                set_cell_background(cell, "F1F5F9")
                set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
                
                # Single paragraph with monospaced text
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.05
                run = p.add_run(clean_xml_string(code_text))
                run.font.name = 'Consolas'
                run.font.size = Pt(9.0)
                run.font.color.rgb = RGBColor(30, 41, 59)
                
                set_table_borders(tbl, color="CBD5E1", sz="6", val="single")
                doc.add_paragraph().paragraph_format.space_after = Pt(4)
                
                in_code_block = False
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue
            
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Tables
        if line.strip().startswith('|') and line.strip().endswith('|'):
            table_lines.append(line)
            i += 1
            # Check if next line is also a table row
            if i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                continue
            else:
                # Render table
                render_markdown_table(doc, table_lines)
                table_lines = []
                continue
        elif table_lines:
            render_markdown_table(doc, table_lines)
            table_lines = []

        stripped = line.strip()

        # Handle Page Break
        if stripped == '---':
            doc.add_page_break()
            i += 1
            continue

        # Handle Headings
        if stripped.startswith('# '):
            text = stripped[2:].strip()
            # If it's a major chapter, give it a page break unless at very top
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(clean_xml_string(text))
            run.font.name = "Calibri"
            run.font.size = Pt(20)
            run.font.bold = True
            run.font.color.rgb = NAVY_PRIMARY
            i += 1
            continue
        elif stripped.startswith('## '):
            text = stripped[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(clean_xml_string(text))
            run.font.name = "Calibri"
            run.font.size = Pt(15)
            run.font.bold = True
            run.font.color.rgb = BLUE_SECONDARY
            i += 1
            continue
        elif stripped.startswith('### '):
            text = stripped[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(clean_xml_string(text))
            run.font.name = "Calibri"
            run.font.size = Pt(13)
            run.font.bold = True
            run.font.color.rgb = BLUE_TERTIARY
            i += 1
            continue
        elif stripped.startswith('#### '):
            text = stripped[5:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(clean_xml_string(text))
            run.font.name = "Calibri"
            run.font.size = Pt(11.5)
            run.font.bold = True
            run.font.color.rgb = TEXT_DARK
            i += 1
            continue

        # Handle Blockquotes
        if stripped.startswith('> '):
            quote_text = stripped[2:].strip()
            # Handle callout tokens like [!NOTE], [!TIP], [!IMPORTANT]
            callout_title = None
            if quote_text.startswith('[!') and ']' in quote_text:
                callout_title = quote_text[2:quote_text.index(']')]
                quote_text = quote_text[quote_text.index(']')+1:].strip()
                
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = False
            tbl.columns[0].width = Inches(6.5)
            cell = tbl.cell(0, 0)
            set_cell_background(cell, "EFF6FF")
            set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
            
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            if callout_title:
                r_title = p.add_run(f"[{callout_title}] ")
                r_title.bold = True
                r_title.font.name = "Calibri"
                r_title.font.size = Pt(10.5)
                r_title.font.color.rgb = NAVY_PRIMARY
            add_formatted_runs(p, quote_text, default_size=10.5, italic=True)
            set_table_borders(tbl, color="3B82F6", sz="12", val="single")
            i += 1
            continue

        # Handle Bullet points
        if stripped.startswith('- ') or stripped.startswith('* '):
            bullet_text = stripped[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, bullet_text)
            i += 1
            continue

        # Handle Numbered list
        num_match = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if num_match:
            num_text = num_match.group(2)
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, num_text)
            i += 1
            continue

        # Empty line
        if not stripped:
            i += 1
            continue

        # Normal Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        add_formatted_runs(p, stripped)
        i += 1

    doc.save(output_docx_path)
    print(f"[SUCCESS] Built DOCX at {output_docx_path}")

def render_markdown_table(doc, table_lines):
    """Renders a block of markdown table lines into a styled docx Table."""
    if len(table_lines) < 2:
        return
        
    def parse_row(row_str):
        parts = [p.strip() for p in row_str.strip().split('|')]
        if len(parts) >= 2 and parts[0] == '' and parts[-1] == '':
            return parts[1:-1]
        elif len(parts) >= 2 and parts[0] == '':
            return parts[1:]
        elif len(parts) >= 2 and parts[-1] == '':
            return parts[:-1]
        return parts

    header_cols = parse_row(table_lines[0])
    num_cols = len(header_cols)
    if num_cols == 0:
        return

    # Filter out separator row (e.g., |---|---|)
    data_rows = []
    for r in table_lines[1:]:
        cols = parse_row(r)
        if all(re.match(r'^:?-+:?$', c) for c in cols if c):
            continue  # Separator line
        data_rows.append(cols)

    table = doc.add_table(rows=len(data_rows) + 1, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # Style Header Row
    hdr_cells = table.rows[0].cells
    for c_idx, col_text in enumerate(header_cols):
        cell = hdr_cells[c_idx]
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(clean_xml_string(col_text))
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.color.rgb = WHITE

    # Repeat header row on every page
    trPr = table.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:tblHeader'))

    # Style Data Rows
    for r_idx, row_data in enumerate(data_rows):
        row = table.rows[r_idx + 1]
        # Prevent row split across pages
        rPr = row._tr.get_or_add_trPr()
        rPr.append(OxmlElement('w:cantSplit'))
        
        bg_color = "F8FAFC" if (r_idx % 2 == 1) else "FFFFFF"
        for c_idx in range(num_cols):
            cell = row.cells[c_idx]
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            cell_text = row_data[c_idx] if c_idx < len(row_data) else ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.05
            add_formatted_runs(p, cell_text, default_size=9.5)

    set_table_borders(table, color="CBD5E1", sz="4", val="single")
    
    # Add spacing after table
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
