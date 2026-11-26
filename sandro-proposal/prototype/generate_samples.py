"""Generate SYNTHETIC sample documents for the gap-list prototype.

Everything here is invented: names, numbers and layouts. No real person or document is
represented. Dates are relative to today so the "expired" and "recent" cases stay true.

Writes, into samples/:
  NN_name.png     the document image
  NN_name.json    sidecar with the ground-truth extraction (used only by offline demo mode)
  expected.json   the gaps the checker should report for this set
"""
import json
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "samples"
APPLICANT = "Juan M. Dela Cruz"
TODAY = date.today()


def font(size, bold=False):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def make(stem, title, lines, ground_truth, stamp=None):
    img = Image.new("RGB", (900, 600), (248, 246, 238))
    d = ImageDraw.Draw(img)
    d.rectangle([12, 12, 887, 587], outline=(60, 60, 60), width=3)
    d.text((40, 36), "SYNTHETIC SAMPLE - NOT A REAL DOCUMENT", fill=(170, 40, 40), font=font(18))
    d.text((40, 76), title, fill=(20, 20, 20), font=font(34))
    y = 150
    for line in lines:
        d.text((40, y), line, fill=(30, 30, 30), font=font(24))
        y += 44
    if stamp:
        d.text((560, 500), stamp, fill=(40, 70, 160), font=font(26))
    img.save(OUT / f"{stem}.png")
    (OUT / f"{stem}.json").write_text(json.dumps(ground_truth, indent=2))


def iso(d):
    return d.isoformat()


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*"):
        if old.is_file():
            old.unlink()

    expired = TODAY - timedelta(days=400)
    recent = TODAY - timedelta(days=45)

    # 01: ID, expired. Problem: expired.
    make("01_drivers_license", "LAND TRANSPORTATION OFFICE - DRIVER'S LICENSE",
         [f"Name: DELA CRUZ, JUAN M.", "License No: N01-23-456789", "Address: Brgy. San Isidro, Sample Town",
          f"Expiry date: {iso(expired)}"],
         {"doc_type": "other_gov_id", "legible": True, "legibility_note": "", "name_on_document": "DELA CRUZ, JUAN M.",
          "issue_date": None, "expiry_date": iso(expired)})

    # 02: tax declaration. OK.
    make("02_tax_declaration", "TAX DECLARATION OF REAL PROPERTY",
         ["Owner: Juan M. Dela Cruz", "Property: Agricultural land, 1.8 hectares", "Crop: Palay (rice)",
          "TD No: 2019-04-0123", f"Date issued: {iso(TODAY - timedelta(days=900))}"],
         {"doc_type": "tax_declaration", "legible": True, "legibility_note": "", "name_on_document": "Juan M. Dela Cruz",
          "issue_date": iso(TODAY - timedelta(days=900)), "expiry_date": None})

    # 03: RSBSA certificate. OK.
    make("03_rsbsa_certificate", "RSBSA - REGISTRY SYSTEM FOR BASIC SECTORS IN AGRICULTURE",
         ["Farmer: Juan Dela Cruz", "Farm size: 1.8 ha", "Main crop: Palay", "RSBSA No: 00-00-00-000-000000",
          f"Date registered: {iso(TODAY - timedelta(days=700))}"],
         {"doc_type": "rsbsa_certificate", "legible": True, "legibility_note": "", "name_on_document": "Juan Dela Cruz",
          "issue_date": iso(TODAY - timedelta(days=700)), "expiry_date": None})

    # 04: barangay clearance, recent but for a DIFFERENT person. Problem: name mismatch.
    make("04_barangay_clearance", "BARANGAY CLEARANCE",
         ["This certifies that JOSE M. DELA CRUZ", "is a resident of Brgy. San Isidro, Sample Town",
          "and has no pending case on record.", f"Date issued: {iso(recent)}"],
         {"doc_type": "barangay_clearance", "legible": True, "legibility_note": "", "name_on_document": "Jose M. Dela Cruz",
          "issue_date": iso(recent), "expiry_date": None}, stamp="Brgy. Captain")

    # 05: GCash statement. OK.
    make("05_gcash_statement", "E-WALLET STATEMENT (SAMPLE)",
         ["Account name: Juan M. Dela Cruz", f"Period: {iso(TODAY - timedelta(days=120))} to {iso(TODAY - timedelta(days=30))}",
          "Cash-in total: PHP 48,500.00", "Cash-out total: PHP 41,200.00", "Transactions: 63"],
         {"doc_type": "gcash_statement", "legible": True, "legibility_note": "", "name_on_document": "Juan M. Dela Cruz",
          "issue_date": iso(TODAY - timedelta(days=30)), "expiry_date": None})

    # 06: not on the checklist. Should be listed as unrecognised.
    make("06_unrelated_photo", "FAMILY OUTING",
         ["Photo caption: Fiesta 2025", "(not a loan document)"],
         {"doc_type": "other", "legible": True, "legibility_note": "", "name_on_document": None,
          "issue_date": None, "expiry_date": None})

    # The loan application form is deliberately absent. Problem: missing.
    expected = {
        "applicant": APPLICANT,
        "status": {
            "identity": "problem",
            "farm_tenure": "present",
            "farmer_registration": "present",
            "barangay_clearance": "problem",
            "income_evidence": "present",
            "application_form": "missing",
        },
        "unrecognised": ["06_unrelated_photo.png"],
    }
    (OUT / "expected.json").write_text(json.dumps(expected, indent=2))
    print(f"Wrote {len(list(OUT.glob('*.png')))} documents to {OUT}")


if __name__ == "__main__":
    main()
