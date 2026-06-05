"""
Find exactly where paragraph 58 is in the PDF
"""
import pdfplumber
import sys

pdf_path = "../docs/rbi_circulars/rbi_housing_finance_2025.pdf"

print("Searching for paragraph 58 LTV rules...\n")

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text and ("58" in text or "LTV" in text or "90 per" in text or "exceeding 90" in text):
            if "grant housing loans" in text.lower() or "exceeding 90" in text.lower():
                print(f"FOUND on PAGE {page_num + 1}")
                print("="*50)
                print(text[:2000])
                print("="*50)