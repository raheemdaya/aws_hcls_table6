"""Generate synthetic BMR (Batch Manufacturing Record) page images for testing.

Creates simple simulated scanned pages with text-like content, form fields,
and table structures using Pillow. Output goes to data/sample_bmr/.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

OUTPUT_DIR = Path(__file__).parent / "sample_bmr"

# Page dimensions simulating a scanned letter-size page at ~150 DPI
PAGE_WIDTH = 1275
PAGE_HEIGHT = 1650
BG_COLOR = (245, 243, 238)  # Slightly off-white, like scanned paper
INK_COLOR = (30, 30, 60)
LIGHT_LINE = (180, 180, 180)
HEADER_BG = (220, 220, 230)


def _get_font(size: int = 18) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font, fall back to default."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


def _draw_header(draw: ImageDraw.ImageDraw, title: str, batch: str) -> int:
    """Draw a BMR page header block. Returns the y position after the header."""
    font_title = _get_font(28)
    font_sub = _get_font(16)

    # Header background
    draw.rectangle([40, 30, PAGE_WIDTH - 40, 130], fill=HEADER_BG, outline=INK_COLOR)
    draw.text((60, 45), title, fill=INK_COLOR, font=font_title)
    draw.text((60, 90), f"Batch: {batch}", fill=INK_COLOR, font=font_sub)
    draw.text((PAGE_WIDTH - 350, 90), "CONFIDENTIAL", fill=(180, 40, 40), font=font_sub)
    return 150


def _draw_form_fields(draw: ImageDraw.ImageDraw, y: int, fields: list[tuple[str, str]]) -> int:
    """Draw labeled form fields with simulated handwritten values."""
    font_label = _get_font(14)
    font_value = _get_font(18)
    for label, value in fields:
        draw.text((60, y), label, fill=INK_COLOR, font=font_label)
        # Underline for the field
        draw.line([(220, y + 22), (600, y + 22)], fill=LIGHT_LINE, width=1)
        # Simulated handwritten value (slightly offset)
        draw.text((230, y + 2), value, fill=(20, 20, 120), font=font_value)
        y += 40
    return y + 10


def _draw_table(draw: ImageDraw.ImageDraw, y: int, headers: list[str], rows: list[list[str]]) -> int:
    """Draw a simple data table with grid lines."""
    font_hdr = _get_font(14)
    font_cell = _get_font(13)
    col_width = (PAGE_WIDTH - 120) // len(headers)
    x_start = 60

    # Header row
    draw.rectangle([x_start, y, PAGE_WIDTH - 60, y + 28], fill=HEADER_BG, outline=INK_COLOR)
    for i, hdr in enumerate(headers):
        draw.text((x_start + i * col_width + 6, y + 6), hdr, fill=INK_COLOR, font=font_hdr)
    y += 28

    # Data rows
    for row in rows:
        draw.line([(x_start, y), (PAGE_WIDTH - 60, y)], fill=LIGHT_LINE, width=1)
        for i, cell in enumerate(row):
            draw.text((x_start + i * col_width + 6, y + 4), cell, fill=INK_COLOR, font=font_cell)
        y += 26
    # Bottom border
    draw.line([(x_start, y), (PAGE_WIDTH - 60, y)], fill=INK_COLOR, width=1)
    return y + 20


def _draw_signature_block(draw: ImageDraw.ImageDraw, y: int) -> int:
    """Draw signature and date lines at the bottom of a page."""
    font = _get_font(14)
    for label in ["Prepared by:", "Reviewed by:", "Approved by:"]:
        draw.text((60, y), label, fill=INK_COLOR, font=font)
        draw.line([(200, y + 18), (500, y + 18)], fill=LIGHT_LINE, width=1)
        draw.text((520, y), "Date:", fill=INK_COLOR, font=font)
        draw.line([(580, y + 18), (780, y + 18)], fill=LIGHT_LINE, width=1)
        y += 40
    return y


def generate_page_1(batch: str) -> Image.Image:
    """Page 1: General batch information and raw materials."""
    img = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _draw_header(draw, "BATCH MANUFACTURING RECORD", batch)

    y = _draw_form_fields(draw, y + 10, [
        ("Product Name:", "Acetaminophen 500mg Tablets"),
        ("Batch Number:", batch),
        ("Batch Size:", "50,000 tablets"),
        ("Mfg Date:", "2024-11-15"),
        ("Exp Date:", "2026-11-14"),
        ("Room/Area:", "Production Suite B-12"),
    ])

    y += 20
    draw.text((60, y), "RAW MATERIALS", fill=INK_COLOR, font=_get_font(20))
    y += 35

    y = _draw_table(draw, y,
        ["Material", "Lot #", "Qty Required", "Qty Dispensed", "Verified"],
        [
            ["Acetaminophen API", "RM-2024-0891", "25.0 kg", "25.02 kg", "Yes"],
            ["Microcryst. Cellulose", "RM-2024-0455", "15.0 kg", "15.01 kg", "Yes"],
            ["Stearic Acid", "RM-2024-0672", "1.5 kg", "1.50 kg", "Yes"],
            ["Povidone K30", "RM-2024-0318", "3.0 kg", "3.00 kg", "Yes"],
            ["Purified Water", "WFI-2024-112", "8.0 L", "8.1 L", "Yes"],
        ])

    _draw_signature_block(draw, PAGE_HEIGHT - 180)
    return img


def generate_page_2(batch: str) -> Image.Image:
    """Page 2: Manufacturing steps and in-process checks."""
    img = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _draw_header(draw, "MANUFACTURING STEPS", batch)

    steps = [
        ("1.", "Sift Acetaminophen API through 40-mesh screen into granulator bowl."),
        ("2.", "Add Microcrystalline Cellulose and blend for 10 minutes at 25 RPM."),
        ("3.", "Prepare binder solution: dissolve Povidone K30 in Purified Water."),
        ("4.", "Spray binder solution onto powder blend while granulating at 150 RPM."),
        ("5.", "Dry granules in fluid bed dryer at 55°C until LOD < 2.0%."),
        ("6.", "Mill dried granules through 20-mesh screen."),
        ("7.", "Add Stearic Acid to milled granules and blend for 5 minutes."),
        ("8.", "Compress tablets using 12mm round tooling at 15 kN compression force."),
    ]

    font_step = _get_font(14)
    font_check = _get_font(12)
    for num, desc in steps:
        draw.text((60, y + 10), num, fill=INK_COLOR, font=_get_font(16))
        draw.text((90, y + 12), desc, fill=INK_COLOR, font=font_step)
        # Checkbox area
        draw.rectangle([PAGE_WIDTH - 120, y + 8, PAGE_WIDTH - 100, y + 28], outline=INK_COLOR)
        draw.text((PAGE_WIDTH - 95, y + 10), "Done", fill=LIGHT_LINE, font=font_check)
        y += 45

    y += 30
    draw.text((60, y), "IN-PROCESS CHECKS", fill=INK_COLOR, font=_get_font(20))
    y += 35

    y = _draw_table(draw, y,
        ["Check", "Specification", "Result", "Pass/Fail"],
        [
            ["Granule LOD", "< 2.0%", "1.6%", "Pass"],
            ["Blend Uniformity", "RSD < 5.0%", "2.3%", "Pass"],
            ["Avg Tablet Weight", "500 ± 25 mg", "498 mg", "Pass"],
            ["Hardness", "8-12 kP", "10.2 kP", "Pass"],
            ["Friability", "< 1.0%", "0.3%", "Pass"],
        ])

    _draw_signature_block(draw, PAGE_HEIGHT - 180)
    return img


def generate_page_3(batch: str) -> Image.Image:
    """Page 3: Equipment log and environmental monitoring."""
    img = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _draw_header(draw, "EQUIPMENT & ENVIRONMENT LOG", batch)

    y = _draw_form_fields(draw, y + 10, [
        ("Equipment ID:", "GRAN-B12-003"),
        ("Calibration Due:", "2025-03-01"),
        ("Clean Status:", "Verified Clean"),
    ])

    y += 20
    draw.text((60, y), "ENVIRONMENTAL MONITORING", fill=INK_COLOR, font=_get_font(20))
    y += 35

    y = _draw_table(draw, y,
        ["Time", "Temp (°C)", "RH (%)", "Differential Pressure (Pa)", "Operator"],
        [
            ["08:00", "21.5", "42", "15.2", "J. Smith"],
            ["10:00", "22.0", "44", "15.0", "J. Smith"],
            ["12:00", "22.3", "45", "14.8", "M. Jones"],
            ["14:00", "21.8", "43", "15.1", "M. Jones"],
            ["16:00", "21.6", "41", "15.3", "J. Smith"],
        ])

    y += 30
    draw.text((60, y), "DEVIATION / NOTES", fill=INK_COLOR, font=_get_font(20))
    y += 35
    # Simulated handwritten note area
    draw.rectangle([60, y, PAGE_WIDTH - 60, y + 120], outline=LIGHT_LINE)
    draw.text((80, y + 10), "No deviations observed during this batch.", fill=(20, 20, 120), font=_get_font(16))

    _draw_signature_block(draw, PAGE_HEIGHT - 180)
    return img


def generate_page_4(batch: str) -> Image.Image:
    """Page 4: Final QC results and batch disposition."""
    img = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _draw_header(draw, "FINAL QC & BATCH DISPOSITION", batch)

    y += 10
    draw.text((60, y), "FINISHED PRODUCT TESTING", fill=INK_COLOR, font=_get_font(20))
    y += 35

    y = _draw_table(draw, y,
        ["Test", "Method", "Specification", "Result", "Status"],
        [
            ["Assay", "HPLC", "95.0-105.0%", "99.8%", "Pass"],
            ["Dissolution", "USP <711>", ">80% in 30 min", "92%", "Pass"],
            ["Content Uniformity", "USP <905>", "AV < 15.0", "4.2", "Pass"],
            ["Microbial Limits", "USP <61>", "< 1000 CFU/g", "< 10 CFU/g", "Pass"],
            ["Appearance", "Visual", "White, round", "Conforms", "Pass"],
        ])

    y += 30
    y = _draw_form_fields(draw, y, [
        ("Yield:", "49,250 tablets (98.5%)"),
        ("Disposition:", "APPROVED FOR RELEASE"),
        ("QA Review:", "Completed - No issues"),
    ])

    y += 20
    draw.text((60, y), "BATCH DISPOSITION", fill=INK_COLOR, font=_get_font(20))
    y += 35
    draw.rectangle([60, y, PAGE_WIDTH - 60, y + 80], outline=INK_COLOR, width=2)
    draw.text((80, y + 25), "BATCH APPROVED FOR COMMERCIAL RELEASE", fill=(0, 100, 0), font=_get_font(22))

    _draw_signature_block(draw, PAGE_HEIGHT - 180)
    return img


def generate_all(output_dir: Path | None = None) -> list[Path]:
    """Generate all synthetic BMR pages and save as PNGs."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    batch_id = f"BMR-2024-{random.randint(1000, 9999):04d}"
    generators = [generate_page_1, generate_page_2, generate_page_3, generate_page_4]
    saved: list[Path] = []

    for i, gen in enumerate(generators, start=1):
        img = gen(batch_id)
        path = out / f"bmr_page_{i}.png"
        img.save(path)
        saved.append(path)
        print(f"  Created {path}")

    return saved


if __name__ == "__main__":
    print("Generating synthetic BMR pages...")
    paths = generate_all()
    print(f"Done — {len(paths)} pages saved to {OUTPUT_DIR}/")
