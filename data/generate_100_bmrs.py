#!/usr/bin/env python3
"""Generate 100 synthetic BMR PDF files into the examples/ directory."""

import os
import random
from create_synthetic_data import create_bmr_pdf

PRODUCT_NAMES = [
    "Amoxicillin 500mg Capsules", "Metformin HCl 850mg Tablets",
    "Lisinopril 10mg Tablets", "Atorvastatin 20mg Tablets",
    "Omeprazole 40mg Capsules", "Amlodipine 5mg Tablets",
    "Losartan 50mg Tablets", "Simvastatin 40mg Tablets",
    "Levothyroxine 100mcg Tablets", "Gabapentin 300mg Capsules",
    "Hydrochlorothiazide 25mg Tablets", "Sertraline 50mg Tablets",
    "Montelukast 10mg Tablets", "Escitalopram 10mg Tablets",
    "Pantoprazole 40mg Tablets", "Rosuvastatin 10mg Tablets",
    "Clopidogrel 75mg Tablets", "Tamsulosin 0.4mg Capsules",
    "Duloxetine 60mg Capsules", "Venlafaxine 75mg Capsules",
]

INGREDIENTS = [
    "Microcrystalline Cellulose", "Magnesium Stearate",
    "Sodium Starch Glycolate", "Povidone K30",
    "Hypromellose", "Colloidal Silicon Dioxide",
    "Calcium Phosphate", "Mannitol", "Lactose Monohydrate",
    "Croscarmellose Sodium", "Talc", "Titanium Dioxide",
    "Stearic Acid", "Pregelatinized Starch", "Hydroxypropyl Cellulose",
]

DIFFICULTIES = [
    ("clean", "Neat handwriting, all fields filled"),
    ("messy", "Difficult handwriting with corrections and crossed-out entries"),
    ("partial", "Partially filled fields with missing entries"),
]

OPERATORS = ["JKL", "RNP", "TMS", "AKB", "CDW", "EFG", "HMN", "PQR", "SVT", "WXY"]

EQUIPMENT_PREFIXES = ["MIX", "GRAN", "TAB", "COAT", "DRY", "FILL", "CAP", "BLEND"]


def random_lot(prefix, year=2024):
    return f"{prefix}-{year}-{random.randint(100, 9999):04d}"


def random_timestamp(year=2024, month=None):
    m = month or random.randint(1, 12)
    d = random.randint(1, 28)
    h = random.randint(6, 10)
    mi = random.choice([0, 15, 30, 45])
    return f"{year}-{m:02d}-{d:02d} {h:02d}:{mi:02d}:00"


def random_end_timestamp(start):
    parts = start.split(" ")
    date = parts[0]
    h = int(parts[1].split(":")[0]) + random.randint(4, 8)
    mi = random.choice([0, 15, 30, 45])
    return f"{date} {h:02d}:{mi:02d}:00"


def generate_fields(difficulty, idx):
    product = random.choice(PRODUCT_NAMES)
    batch = f"BMR-2024-{idx:04d}"
    if difficulty == "messy":
        old = f"BMR-2024-{idx - 1:04d}"
        batch = f"{batch} (corrected from {old})"

    equip_count = random.randint(2, 4)
    equips = ", ".join(
        f"{random.choice(EQUIPMENT_PREFIXES)}-{random.randint(100, 499)}"
        for _ in range(equip_count)
    )

    operator = random.choice(OPERATORS)
    start_ts = random_timestamp()
    end_ts = random_end_timestamp(start_ts)

    ing_count = random.randint(3, 6)
    ingredients = []
    used = set()
    for _ in range(ing_count):
        choices = [i for i in INGREDIENTS if i not in used]
        if not choices:
            break
        name = random.choice(choices)
        used.add(name)
        prefix = "".join(w[0] for w in name.split()).upper()
        weight = round(random.uniform(1.0, 250.0), 1)
        lot = random_lot(prefix)

        if difficulty == "partial" and random.random() < 0.35:
            weight = None
        if difficulty == "partial" and random.random() < 0.35:
            lot = None

        ingredients.append({"name": name, "weight": weight, "lot": lot})

    fields = {
        "Product Name": product,
        "Batch Number": batch,
        "Equipment IDs": equips if difficulty != "partial" or random.random() > 0.4 else None,
        "Operator Initials": operator,
        "Start Timestamp": start_ts if difficulty != "partial" or random.random() > 0.5 else None,
        "End Timestamp": end_ts if difficulty != "partial" or random.random() > 0.5 else None,
        "ingredients": ingredients,
    }
    return fields


def main():
    os.makedirs("examples", exist_ok=True)
    random.seed(42)

    for i in range(1, 101):
        diff_name, diff_desc = random.choice(DIFFICULTIES)
        fields = generate_fields(diff_name, i)
        filename = f"examples/bmr-sample-{i:03d}-{diff_name}.pdf"
        create_bmr_pdf(
            filename=filename,
            difficulty=diff_name,
            description=diff_desc,
            fields=fields,
        )

    print(f"\nDone! Generated 100 BMR files in examples/")


if __name__ == "__main__":
    main()
