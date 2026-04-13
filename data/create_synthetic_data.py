#!/usr/bin/env python3
"""Generate placeholder BMR test data PDFs for the IDP Pharma Workshop."""

from fpdf import FPDF


def create_bmr_pdf(filename: str, difficulty: str, description: str, fields: dict):
    """Create a single BMR placeholder PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Watermark-style header
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, "SAMPLE - FOR WORKSHOP USE ONLY", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Document title
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Batch Manufacturing Record (BMR)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Difficulty badge
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Difficulty Variant: {difficulty.upper()} - {description}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Placeholder notice
    pdf.set_draw_color(180, 180, 180)
    pdf.set_fill_color(255, 255, 230)
    pdf.rect(15, pdf.get_y(), 180, 24, style="DF")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(120, 80, 0)
    y = pdf.get_y() + 3
    pdf.set_xy(20, y)
    pdf.multi_cell(170, 5,
        "PLACEHOLDER DOCUMENT\n"
        "This file is a placeholder to be replaced with actual handwritten\n"
        "document scans provided by the workshop facilitator.",
        align="C")
    pdf.ln(6)

    # Separator
    pdf.set_draw_color(0, 0, 0)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    # Form fields section
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "Form Fields:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    for label, value in fields.items():
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, f"{label}:")
        pdf.set_font("Helvetica", "", 10)
        if value is None:
            pdf.set_text_color(180, 0, 0)
            pdf.cell(0, 7, "[FIELD LEFT BLANK]", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    # Ingredients table
    if "ingredients" in fields and fields["ingredients"]:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Ingredients:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(60, 7, "Ingredient Name", border=1, fill=True)
        pdf.cell(30, 7, "Weight (kg)", border=1, fill=True)
        pdf.cell(40, 7, "Lot Number", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        # Table rows
        pdf.set_font("Helvetica", "", 9)
        for ing in fields["ingredients"]:
            pdf.cell(60, 7, ing["name"], border=1)
            pdf.cell(30, 7, str(ing["weight"]) if ing["weight"] else "", border=1)
            pdf.cell(40, 7, ing["lot"] if ing["lot"] else "", border=1, new_x="LMARGIN", new_y="NEXT")

    # Footer watermark
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 5, "SAMPLE - FOR WORKSHOP USE ONLY | IDP Pharma Workshop", align="C")

    pdf.output(filename)
    print(f"Created: {filename}")


def main():
    # --- BMR Sample 01: Clean ---
    create_bmr_pdf(
        filename="bmr/bmr-sample-01-clean.pdf",
        difficulty="clean",
        description="Neat handwriting, all fields filled",
        fields={
            "Product Name": "Amoxicillin 500mg Capsules",
            "Batch Number": "BMR-2024-0847",
            "Equipment IDs": "MIX-401, GRAN-205, TAB-112",
            "Operator Initials": "JKL",
            "Start Timestamp": "2024-11-15 08:30:00",
            "End Timestamp": "2024-11-15 14:45:00",
            "ingredients": [
                {"name": "Amoxicillin Trihydrate", "weight": 125.0, "lot": "AMX-2024-1001"},
                {"name": "Microcrystalline Cellulose", "weight": 45.5, "lot": "MCC-2024-0553"},
                {"name": "Magnesium Stearate", "weight": 2.5, "lot": "MGS-2024-0221"},
                {"name": "Sodium Starch Glycolate", "weight": 15.0, "lot": "SSG-2024-0334"},
            ],
        },
    )

    # --- BMR Sample 02: Messy ---
    create_bmr_pdf(
        filename="bmr/bmr-sample-02-messy.pdf",
        difficulty="messy",
        description="Difficult handwriting with corrections and crossed-out entries",
        fields={
            "Product Name": "Metformin HCl 850mg Tablets",
            "Batch Number": "BMR-2024-1203 (corrected from BMR-2024-1103)",
            "Equipment IDs": "MIX-402, GRAN-207, TAB-115, COAT-301",
            "Operator Initials": "RNP",
            "Start Timestamp": "2024-12-03 07:15:00",
            "End Timestamp": "2024-12-03 16:30:00",
            "ingredients": [
                {"name": "Metformin Hydrochloride", "weight": 212.5, "lot": "MET-2024-2201"},
                {"name": "Povidone K30", "weight": 18.0, "lot": "PVD-2024-0887"},
                {"name": "Magnesium Stearate", "weight": 3.0, "lot": "MGS-2024-0225"},
                {"name": "Hypromellose", "weight": 8.5, "lot": "HPM-2024-0412"},
                {"name": "Colloidal Silicon Dioxide", "weight": 1.5, "lot": "CSD-2024-0109"},
            ],
        },
    )

    # --- BMR Sample 03: Partial ---
    create_bmr_pdf(
        filename="bmr/bmr-sample-03-partial.pdf",
        difficulty="partial",
        description="Partially filled fields with missing entries",
        fields={
            "Product Name": "Lisinopril 10mg Tablets",
            "Batch Number": "BMR-2024-0592",
            "Equipment IDs": None,
            "Operator Initials": "TMS",
            "Start Timestamp": None,
            "End Timestamp": None,
            "ingredients": [
                {"name": "Lisinopril Dihydrate", "weight": 52.0, "lot": "LIS-2024-0771"},
                {"name": "Calcium Phosphate", "weight": 30.0, "lot": None},
                {"name": "Mannitol", "weight": None, "lot": None},
            ],
        },
    )


if __name__ == "__main__":
    main()