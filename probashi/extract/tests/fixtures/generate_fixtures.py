"""Generate the synthetic document fixtures for the extract tests.

Everything here is SYNTHETIC. The employers, agencies, workers, licence
numbers, passport numbers and amounts are made up for testing, are labelled
as fictional on the page, and must never be used as real data.

The generated files are committed, so the tests do not need this script.
Re-run it only to change the fixtures:

    python probashi/extract/tests/fixtures/generate_fixtures.py

It needs macOS system fonts (Arial, Kohinoor Bangla, Bradley
Hand) and a Pillow build with libraqm for Arabic and Bangla shaping.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

OUT = Path(__file__).parent
FONT_DIR = Path("/System/Library/Fonts")
FONTS = {
    "title": (FONT_DIR / "Supplemental/Arial Bold.ttf", 46),
    "body": (FONT_DIR / "Supplemental/Arial.ttf", 32),
    "small": (FONT_DIR / "Supplemental/Arial.ttf", 22),
    "hand": (FONT_DIR / "Supplemental/Bradley Hand Bold.ttf", 44),
    "ar": (FONT_DIR / "Supplemental/Arial.ttf", 36),
    "ar_title": (FONT_DIR / "Supplemental/Arial.ttf", 50),
    "bn": (FONT_DIR / "KohinoorBangla.ttc", 34),
    "bn_title": (FONT_DIR / "KohinoorBangla.ttc", 46),
}
PAGE = (1240, 1754)  # A4 at 150 dpi
MARGIN = 110
INK = (25, 25, 35)
HAND_INK = (20, 40, 150)


def font(key: str) -> ImageFont.FreeTypeFont:
    path, size = FONTS[key]
    return ImageFont.truetype(str(path), size)


def blank_page() -> Image.Image:
    """White page with a SAMPLE watermark and a banner."""
    img = Image.new("RGB", PAGE, "white")
    mark = Image.new("RGBA", (1900, 1900), (0, 0, 0, 0))
    d = ImageDraw.Draw(mark)
    for y in range(0, 1900, 260):
        d.text((0, y), "SAMPLE - SYNTHETIC TEST DOCUMENT - NOT REAL   " * 3,
               font=font("body"), fill=(205, 205, 225, 255))
    mark = mark.rotate(32)
    img.paste(mark, (-330, -70), mark)
    ImageDraw.Draw(img).text(
        (MARGIN, 40), "SAMPLE - synthetic test document. All names and numbers are fictional.",
        font=font("small"), fill=(190, 30, 30))
    return img


def render(lines: list) -> Image.Image:
    """Each line is a list of (text, font key) segments, or None for a gap.
    A line whose first font key starts with "ar" is right-aligned (RTL)."""
    img = blank_page()
    d = ImageDraw.Draw(img)
    y = 130
    for line in lines:
        if line is None:
            y += 34
            continue
        rtl = line[0][1].startswith("ar")
        x = PAGE[0] - MARGIN if rtl else MARGIN
        height = 0
        for text, key in line:
            f = font(key)
            ink = HAND_INK if key == "hand" else INK
            if rtl:
                d.text((x, y), text, font=f, fill=ink, anchor="ra", direction="rtl", language="ar")
            else:
                d.text((x, y), text, font=f, fill=ink)
                x += d.textlength(text, font=f) + 14
            height = max(height, f.size)
        y += int(height * 1.9)
    return img


def L(text: str, key: str = "body") -> list:
    return [(text, key)]


def as_photo(page: Image.Image, skew: float, quarter_turns: int) -> Image.Image:
    """Page lying on a dark table, shot at an angle, with uneven light."""
    table = Image.new("RGB", (PAGE[0] + 260, PAGE[1] + 260), (58, 48, 42))
    table.paste(page, (130, 130))
    table = table.rotate(skew, resample=Image.BICUBIC, fillcolor=(58, 48, 42))
    shade = Image.linear_gradient("L").resize(table.size).point(lambda v: 150 + v * 105 // 255)
    table = Image.composite(table, Image.new("RGB", table.size, "black"), shade)
    for _ in range(quarter_turns):
        table = table.transpose(Image.ROTATE_270)
    return table


DOCS = [
    {
        "file": "01_en_offer_clean.png",
        "case": "clean English offer letter, every field present",
        "lines": [
            L("JOB OFFER LETTER", "title"),
            L("Ref: SAMPLE/0001        Date: 01 January 2030"),
            None,
            L("Employer: Sample Cleaning Services Co. (FICTIONAL)"),
            L("Country of employment: Kingdom of Saudi Arabia"),
            L("Worker name: SAMPLE WORKER ONE"),
            L("Passport No: ZZ0000001"),
            None,
            L("Position: Cleaner"),
            L("Basic salary: SAR 1,200 per month"),
            L("Contract period: 2 years"),
            L("Visa type: Work visa"),
            None,
            L("Recruiting agency: Sample Overseas Ltd. (FICTIONAL)"),
            L("Recruiting licence: RL-99991"),
            L("Total recruitment cost payable by worker: BDT 1,65,000"),
        ],
        "expected": {
            "employer_name": ["Sample Cleaning Services Co."],
            "job_title": ["cleaner"],
            "destination_country": "SA",
            "salary_amount": 1200, "salary_currency": "SAR",
            "agency_name": ["Sample Overseas Ltd."],
            "agency_license_no": "RL-99991",
            "fees_charged_bdt": 165000,
            "contract_duration_months": 24,
            "visa_type": "work",
            "document_language": ["en"],
        },
    },
    {
        "file": "02_en_offer_no_licence.png",
        "case": "agency named but no licence number anywhere",
        "lines": [
            L("OFFER OF EMPLOYMENT", "title"),
            L("Ref: SAMPLE/0002"),
            None,
            L("Company: Example Security Services LLC (FICTIONAL)"),
            L("Location: Dubai, United Arab Emirates"),
            L("Candidate: SAMPLE WORKER TWO"),
            None,
            L("Job title: Security Guard"),
            L("Monthly salary: AED 1,500"),
            L("Duration: 24 months"),
            L("Visa: Employment visa"),
            None,
            L("Processed through: Example Manpower Services (FICTIONAL)"),
            L("Service charge to be paid to the agency: Tk. 4,20,000"),
        ],
        "expected": {
            "employer_name": ["Example Security Services LLC"],
            "job_title": ["security guard", "guard"],
            "destination_country": "AE",
            "salary_amount": 1500, "salary_currency": "AED",
            "agency_name": ["Example Manpower Services"],
            "agency_license_no": None,
            "fees_charged_bdt": 420000,
            "contract_duration_months": 24,
            "visa_type": "work",
            "document_language": ["en"],
        },
    },
    {
        "file": "03_en_contract_malaysia_myr.png",
        "case": "salary in ringgit, fee in words (lakh), 'Visit Pass (Temporary Employment)'",
        "lines": [
            L("CONTRACT OF EMPLOYMENT", "title"),
            L("Ref: SAMPLE/0003"),
            None,
            L("Employer: Contoh Sample Manufacturing Sdn. Bhd. (FICTIONAL)"),
            L("Place of work: Johor, Malaysia"),
            L("Employee: SAMPLE WORKER THREE"),
            None,
            L("Job: Factory Worker (Production Operator)"),
            L("Basic wage: RM 1,700.00 per month"),
            L("Period of contract: Three (3) years"),
            L("Pass type: Visit Pass (Temporary Employment)"),
            None,
            L("Bangladesh recruiting agent: Namuna International (FICTIONAL)"),
            L("RL No. 99992"),
            L("Migration cost paid in Bangladesh: Taka 3 lakh 80 thousand"),
        ],
        "expected": {
            "employer_name": ["Contoh Sample Manufacturing Sdn. Bhd."],
            "job_title": ["factory worker", "production operator"],
            "destination_country": "MY",
            "salary_amount": 1700, "salary_currency": "MYR",
            "agency_name": ["Namuna International"],
            "agency_license_no": "RL-99992",
            "fees_charged_bdt": 380000,
            "contract_duration_months": 36,
            "visa_type": "work",
            "document_language": ["en"],
        },
    },
    {
        "file": "04_ar_only_offer.png",
        "case": "Arabic-only document, Arabic-Indic digits, no agency or fee",
        "lines": [
            L("عرض عمل", "ar_title"),
            L("نموذج تجريبي - ليس مستنداً حقيقياً", "ar"),
            None,
            L("صاحب العمل: شركة النموذج للنظافة (وهمية)", "ar"),
            L("اسم العامل: عامل نموذجي", "ar"),
            L("المهنة: عامل نظافة", "ar"),
            L("بلد العمل: المملكة العربية السعودية", "ar"),
            L("الراتب الأساسي: ١٥٠٠ ريال سعودي شهرياً", "ar"),
            L("مدة العقد: سنتان", "ar"),
            L("نوع التأشيرة: تأشيرة عمل", "ar"),
        ],
        "expected": {
            "employer_name": ["شركة النموذج للنظافة", "النموذج للنظافة"],
            "job_title": ["cleaner", "cleaning worker"],
            "destination_country": "SA",
            "salary_amount": 1500, "salary_currency": "SAR",
            "agency_name": None,
            "agency_license_no": None,
            "fees_charged_bdt": None,
            "contract_duration_months": 24,
            "visa_type": "work",
            "document_language": ["ar"],
        },
    },
    {
        "file": "05_en_offer_rotated_photo.jpg",
        "case": "phone photo turned 90 degrees with no EXIF, skewed, uneven light",
        "photo": {"skew": 4, "quarter_turns": 1, "quality": 60},
        "lines": [
            L("EMPLOYMENT OFFER", "title"),
            L("Ref: SAMPLE/0005"),
            None,
            L("Employer: Demo Transport W.L.L. (FICTIONAL)"),
            L("Work location: Doha, Qatar"),
            L("Name: SAMPLE WORKER FIVE"),
            None,
            L("Position: Light Vehicle Driver"),
            L("Salary: QR 1,800 / month"),
            L("Contract: 2 years"),
            L("Visa: Work"),
            None,
            L("Agency: Specimen Recruiting Agency (FICTIONAL)"),
            L("License No: RL-99993"),
            L("Agency fee: BDT 2,50,000"),
        ],
        "expected": {
            "employer_name": ["Demo Transport W.L.L."],
            "job_title": ["light vehicle driver", "driver"],
            "destination_country": "QA",
            "salary_amount": 1800, "salary_currency": "QAR",
            "agency_name": ["Specimen Recruiting Agency"],
            "agency_license_no": "RL-99993",
            "fees_charged_bdt": 250000,
            "contract_duration_months": 24,
            "visa_type": "work",
            "document_language": ["en"],
        },
    },
    {
        "file": "06_en_form_handwritten_amounts.png",
        "case": "printed form, handwritten-style values, fee in words, licence left blank",
        "lines": [
            L("OFFER SUMMARY FORM", "title"),
            L("Ref: SAMPLE/0006"),
            None,
            [("Agency:", "body"), ("Test Travels & Overseas (FICTIONAL)", "body")],
            [("Licence no:", "body"), ("______________", "body")],
            [("Employer:", "body"), ("Sample Builders LLC (fake)", "hand")],
            [("Country:", "body"), ("Oman", "hand")],
            [("Job:", "body"), ("Mason", "hand")],
            [("Salary per month:", "body"), ("140 Omani Rial", "hand")],
            [("Contract:", "body"), ("2 yrs", "hand")],
            [("Amount to pay agent:", "body"), ("4 lakh 50 thousand taka", "hand")],
        ],
        "expected": {
            "employer_name": ["Sample Builders LLC"],
            "job_title": ["mason"],
            "destination_country": "OM",
            "salary_amount": 140, "salary_currency": "OMR",
            "agency_name": ["Test Travels & Overseas"],
            "agency_license_no": None,
            "fees_charged_bdt": 450000,
            "contract_duration_months": 24,
            "visa_type": None,
            "document_language": ["en"],
        },
    },
    {
        "file": "07_bn_agency_receipt.png",
        "case": "Bangla receipt, Bangla digits, fee in lakh/hazar, no employer or visa type",
        "lines": [
            L("টাকা জমার রসিদ (নমুনা)", "bn_title"),
            L("এই কাগজটি নমুনা। আসল নয়।", "bn"),
            None,
            L("এজেন্সি: নমুনা ইন্টারন্যাশনাল (কাল্পনিক)", "bn"),
            L("লাইসেন্স নং: আরএল-৯৯৯৯৪", "bn"),
            L("কর্মীর নাম: নমুনা কর্মী দুই", "bn"),
            [("পাসপোর্ট নং:", "bn"), ("ZZ0000002", "body")],
            None,
            L("দেশ: কুয়েত", "bn"),
            L("কাজ: গাড়ি চালক (ড্রাইভার)", "bn"),
            L("মাসিক বেতন: ১২০ কুয়েতি দিনার", "bn"),
            L("চুক্তির মেয়াদ: ২ বছর", "bn"),
            L("মোট খরচ: ৩ লাখ ৮০ হাজার টাকা", "bn"),
        ],
        "expected": {
            "employer_name": None,
            "job_title": ["driver"],
            "destination_country": "KW",
            "salary_amount": 120, "salary_currency": "KWD",
            "agency_name": ["নমুনা ইন্টারন্যাশনাল", "Namuna International"],
            "agency_license_no": "RL-99994",
            "fees_charged_bdt": 380000,
            "contract_duration_months": 24,
            "visa_type": None,
            "document_language": ["bn"],
        },
    },
    {
        "file": "08_ar_en_visit_visa.png",
        "case": "bilingual VISIT visa: no job, salary or agency; stay length is not a contract",
        "lines": [
            L("ENTRY PERMIT - SPECIMEN, NOT VALID", "title"),
            L("تصريح دخول - نموذج غير صالح", "ar"),
            None,
            L("Visa No: 0000000008"),
            L("Visa type: VISIT"),
            L("نوع التأشيرة: زيارة", "ar"),
            L("Country: United Arab Emirates"),
            L("الدولة: الإمارات العربية المتحدة", "ar"),
            L("Full name: SAMPLE WORKER EIGHT"),
            L("Passport No: ZZ0000008"),
            L("Duration of stay: 60 days"),
            L("مدة الإقامة: ٦٠ يوماً", "ar"),
        ],
        "expected": {
            "employer_name": None,
            "job_title": None,
            "destination_country": "AE",
            "salary_amount": None, "salary_currency": None,
            "agency_name": None,
            "agency_license_no": None,
            "fees_charged_bdt": None,
            "contract_duration_months": None,
            "visa_type": "visit",
            "document_language": ["en", "ar"],
        },
    },
    {
        "file": "09_en_offer_blurry.jpg",
        "case": "small, blurry, heavily compressed photo; ambiguous 'BD' currency",
        "blur": {"width": 900, "radius": 1.5, "quality": 45},
        "lines": [
            L("JOB OFFER", "title"),
            L("Ref: SAMPLE/0009"),
            None,
            L("Employer: Mock Hospitality W.L.L. (FICTIONAL)"),
            L("Location: Manama, Kingdom of Bahrain"),
            L("Name: SAMPLE WORKER NINE"),
            None,
            L("Position: Kitchen Helper"),
            L("Salary: BD 110 per month"),
            L("Contract: 24 months"),
            L("Visa: Work"),
            None,
            L("Agency: Sample Overseas Ltd. (FICTIONAL)"),
            L("Licence: RL-99991"),
            L("Fee: Tk 3,00,000"),
        ],
        "expected": {
            "employer_name": ["Mock Hospitality W.L.L."],
            "job_title": ["kitchen helper"],
            "destination_country": "BH",
            "salary_amount": 110, "salary_currency": "BHD",
            "agency_name": ["Sample Overseas Ltd."],
            "agency_license_no": "RL-99991",
            "fees_charged_bdt": 300000,
            "contract_duration_months": 24,
            "visa_type": "work",
            "document_language": ["en"],
        },
    },
    {
        "file": "10_en_offer_two_pages.pdf",
        "case": "two-page PDF: job on page 1, agency and fee on page 2",
        "lines": [
            L("LETTER OF APPOINTMENT", "title"),
            L("Ref: SAMPLE/0010        Page 1 of 2"),
            None,
            L("Employer: Sample Garments Co. (FICTIONAL)"),
            L("Place of work: Jordan"),
            L("Employee: SAMPLE WORKER TEN"),
            None,
            L("Position: Sewing Machine Operator"),
            L("Basic salary: JOD 220 per month"),
            L("Contract period: 3 years"),
        ],
        "page2": [
            L("RECRUITMENT DETAILS", "title"),
            L("Ref: SAMPLE/0010        Page 2 of 2"),
            None,
            L("Recruiting agency: Example Manpower Services (FICTIONAL)"),
            L("Recruiting Licence No: RL-99995"),
            L("Amount to be paid by the worker in Bangladesh: BDT 95,000"),
            L("Visa type: Work visa"),
        ],
        "expected": {
            "employer_name": ["Sample Garments Co."],
            "job_title": ["sewing machine operator", "machine operator", "garment worker"],
            "destination_country": "JO",
            "salary_amount": 220, "salary_currency": "JOD",
            "agency_name": ["Example Manpower Services"],
            "agency_license_no": "RL-99995",
            "fees_charged_bdt": 95000,
            "contract_duration_months": 36,
            "visa_type": "work",
            "document_language": ["en"],
        },
    },
]


def main() -> None:
    if not features.check("raqm"):
        raise SystemExit("Pillow was built without libraqm: Arabic and Bangla would be garbled")
    for doc in DOCS:
        page = render(doc["lines"])
        path = OUT / doc["file"]
        if "page2" in doc:
            page.save(path, "PDF", save_all=True, append_images=[render(doc["page2"])],
                      resolution=150)
        elif "photo" in doc:
            p = doc["photo"]
            as_photo(page, p["skew"], p["quarter_turns"]).save(path, quality=p["quality"])
        elif "blur" in doc:
            b = doc["blur"]
            small = page.resize((b["width"], b["width"] * PAGE[1] // PAGE[0]))
            small.filter(ImageFilter.GaussianBlur(b["radius"])).save(path, quality=b["quality"])
        else:
            page.save(path, optimize=True)
        print("wrote", path.name)
    index = [{"file": d["file"], "case": d["case"], "expected": d["expected"]} for d in DOCS]
    (OUT / "image_fixtures.json").write_text(
        json.dumps({"_note": "SYNTHETIC test data. Nothing here is real.", "fixtures": index},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote image_fixtures.json")


if __name__ == "__main__":
    main()
