"""
Main Execution Script for Bull's Eye SPL-3 Final Technical Report Generation.
Compiles all report modules into a master Markdown document and builds
the corresponding styled Microsoft Word document (.docx).
"""

import os
import sys

# Ensure report_generator directory is on the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from front_matter import get_front_matter
from ch1_introduction import get_chapter_1
from ch2_project_description import get_chapter_2
from ch3_scenario_modeling import get_chapter_3
from ch4_data_modeling import get_chapter_4
from ch5_class_modeling import get_chapter_5
from ch6_architectural_design import get_chapter_6
from ch7_methodology_scoring import get_chapter_7
from ch8_component_implementation import get_chapter_8
from ch9_ui_user_manual import get_chapter_9
from ch10_testing_qa import get_chapter_10
from ch11_conclusion_references import get_chapter_11
from docx_builder import build_docx_from_markdown

def main():
    print("[1/4] Compiling report modules into master document...")
    modules = [
        get_front_matter(),
        get_chapter_1(),
        get_chapter_2(),
        get_chapter_3(),
        get_chapter_4(),
        get_chapter_5(),
        get_chapter_6(),
        get_chapter_7(),
        get_chapter_8(),
        get_chapter_9(),
        get_chapter_10(),
        get_chapter_11()
    ]
    
    full_markdown = "\n\n".join(modules)
    
    docs_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "Documents"))
    os.makedirs(docs_dir, exist_ok=True)
    
    md_output_path = os.path.join(docs_dir, "Final_Technical_Report.md")
    docx_output_path = os.path.join(docs_dir, "Final_Technical_Report.docx")
    
    print(f"[2/4] Writing master Markdown report to: {md_output_path}")
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(full_markdown)
        
    line_count = len(full_markdown.splitlines())
    word_count = len(full_markdown.split())
    char_count = len(full_markdown)
    print(f"      -> Total Markdown Lines: {line_count:,}")
    print(f"      -> Total Words:          {word_count:,}")
    print(f"      -> Total Characters:     {char_count:,}")
    
    print(f"[3/4] Converting Markdown to formatted Word document: {docx_output_path}")
    build_docx_from_markdown(full_markdown, docx_output_path)
    
    md_size_kb = os.path.getsize(md_output_path) / 1024
    docx_size_kb = os.path.getsize(docx_output_path) / 1024
    
    print("[4/4] Generation Complete!")
    print(f"      - Final_Technical_Report.md   : {md_size_kb:.1f} KB")
    print(f"      - Final_Technical_Report.docx : {docx_size_kb:.1f} KB")

if __name__ == "__main__":
    main()
