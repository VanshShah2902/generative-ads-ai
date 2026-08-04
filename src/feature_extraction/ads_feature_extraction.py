"""
ads_feature_extraction.py
=========================
End-to-end ML feature extraction pipeline for advertisement creatives.

Works with the project's ads_dataset_filtered.csv which contains:
    ad_id, ad_name, image_path, impressions, clicks, ctr, cpc, spend, frequency

Optional columns (used if present):
    brand, ad_type, ad_text, creative_index, page_name

Extracted features:
  - YOLO object detection features  (YOLOv8n)
  - OCR text features               (pytesseract)
  - Visual style features           (OpenCV)
  - Text features from ad_text      (if column exists)

Output: ads_features.csv  (one level up, inside Dataset/)
"""

import os
import re
import logging
import warnings

import cv2
import numpy as np
import pandas as pd
import pytesseract
from tqdm import tqdm
from ultralytics import YOLO

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — adjust paths as needed
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "..")           # Dataset/
CSV_PATH    = os.path.join(DATASET_DIR, "ads_dataset_filtered.csv")
OUTPUT_PATH = os.path.join(DATASET_DIR, "ads_features.csv")

# ── Tesseract ────────────────────────────────────────────────────────────────
# Uncomment and set if Tesseract is not on your system PATH:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

YOLO_MODEL  = "yolov8n.pt"   # downloaded automatically on first run
COCO_PERSON = 0              # COCO class-id for "person"

CTA_KEYWORDS = {
    "buy", "shop", "order", "try", "learn more", "get", "download",
    "subscribe", "sign up", "signup", "register", "book", "explore",
    "discover", "claim", "grab", "save", "start", "apply",
}

PROMO_WORDS = {
    "free", "discount", "sale", "offer", "deal", "limited", "exclusive",
    "save", "off", "%", "new", "best", "top", "premium", "guarantee",
}

EMOJI_PATTERN = re.compile(
    "[\U00010000-\U0010ffff"
    "\U00002702-\U000027B0"
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_image(path: str):
    """Return an OpenCV BGR image or None if the file cannot be read."""
    img = cv2.imread(path)
    if img is None:
        log.warning("Could not load image: %s", path)
    return img


def resolve_path(raw: str) -> str:
    """Make image path absolute, searching several possible locations."""
    if not isinstance(raw, str) or not raw.strip():
        return ""
    raw = raw.strip()
    if os.path.isabs(raw):
        return raw

    basename = os.path.basename(raw)

    # Search locations in priority order
    candidates = [
        os.path.join(DATASET_DIR, raw),                              # direct join
        os.path.join(DATASET_DIR, "ads_images", "ads_images", basename),  # nested (actual)
        os.path.join(DATASET_DIR, "ads_images", basename),           # flat ads_images/
        os.path.join(DATASET_DIR, "images", basename),               # images/ folder
        os.path.join(DATASET_DIR, "downloaded_images", basename),    # downloaded_images/
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Return most likely candidate (will be logged as missing)
    return candidates[0]


def grid_position(cx_norm: float, cy_norm: float) -> dict:
    """Map normalised centre (0-1) to boolean 3×3 grid layout flags."""
    col = min(int(cx_norm * 3), 2)   # 0=left  1=center  2=right
    row = min(int(cy_norm * 3), 2)   # 0=top   1=center  2=bottom
    return {
        "center_object": int(col == 1 and row == 1),
        "left_object":   int(col == 0),
        "right_object":  int(col == 2),
        "top_object":    int(row == 0),
        "bottom_object": int(row == 2),
    }


# ---------------------------------------------------------------------------
# Step 4 – YOLO object-detection features
# ---------------------------------------------------------------------------

def extract_yolo_features(model: YOLO, img: np.ndarray) -> dict:
    h, w   = img.shape[:2]
    result = model(img, verbose=False)[0]
    boxes  = result.boxes

    _default_layout = {
        "center_object": 0, "left_object":  0,
        "right_object":  0, "top_object":   0, "bottom_object": 0,
    }

    if boxes is None or len(boxes) == 0:
        return {"object_count": 0, "person_present": 0,
                "largest_object_area": 0.0, **_default_layout}

    xyxy   = boxes.xyxy.cpu().numpy()
    cls_id = boxes.cls.cpu().numpy()

    object_count   = len(xyxy)
    person_present = int(COCO_PERSON in cls_id)

    max_area    = 0.0
    largest_box = None
    for box in xyxy:
        x1, y1, x2, y2 = box
        area = ((x2 - x1) / w) * ((y2 - y1) / h)
        if area > max_area:
            max_area    = area
            largest_box = box

    layout = _default_layout
    if largest_box is not None:
        x1, y1, x2, y2 = largest_box
        cx_norm = ((x1 + x2) / 2) / w
        cy_norm = ((y1 + y2) / 2) / h
        layout  = grid_position(cx_norm, cy_norm)

    return {
        "object_count":        object_count,
        "person_present":      person_present,
        "largest_object_area": round(float(max_area), 6),
        **layout,
    }


# ---------------------------------------------------------------------------
# Step 5 – OCR features
# ---------------------------------------------------------------------------

def extract_ocr_features(img: np.ndarray) -> dict:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    try:
        ocr_text = pytesseract.image_to_string(gray, config="--psm 11")
    except Exception as exc:
        log.warning("OCR failed: %s", exc)
        ocr_text = ""

    words    = ocr_text.lower().split()
    flat     = " ".join(words)
    return {
        "ocr_text_length": len(ocr_text.strip()),
        "ocr_word_count":  len(words),
        "cta_present":     int(any(kw in flat for kw in CTA_KEYWORDS)),
    }


# ---------------------------------------------------------------------------
# Step 6 – Visual style features
# ---------------------------------------------------------------------------

def extract_visual_features(img: np.ndarray) -> dict:
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return {
        "brightness":     round(float(np.mean(gray)),           3),
        "contrast":       round(float(np.std(gray)),            3),
        "dominant_r":     round(float(np.mean(img_rgb[:, :, 0])), 3),
        "dominant_g":     round(float(np.mean(img_rgb[:, :, 1])), 3),
        "dominant_b":     round(float(np.mean(img_rgb[:, :, 2])), 3),
        "color_variance": round(float(np.std(img_rgb)),         3),
    }


# ---------------------------------------------------------------------------
# Step 7 – Text features from ad_text (optional column)
# ---------------------------------------------------------------------------

def extract_text_features(ad_text) -> dict:
    if not isinstance(ad_text, str):
        ad_text = ""
    lower   = ad_text.lower()
    words   = lower.split()
    emojis  = EMOJI_PATTERN.findall(ad_text)
    return {
        "ad_text_word_count":        len(words),
        "promotional_word_presence": int(any(w in PROMO_WORDS for w in words)),
        "emoji_count":               sum(len(e) for e in emojis),
        "cta_in_text":               int(any(kw in lower for kw in CTA_KEYWORDS)),
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    # ── Load dataset ──────────────────────────────────────────────────────
    log.info("Loading dataset: %s", CSV_PATH)
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    log.info("Total rows loaded: %d", len(df))
    log.info("Columns found   : %s", df.columns.tolist())

    # ── Optional: filter to image ads only (skip if column absent) ────────
    if "ad_type" in df.columns:
        df = df[df["ad_type"].str.strip().str.lower() == "image"].copy()
        log.info("Rows after ad_type='image' filter: %d", len(df))
    else:
        log.info("Column 'ad_type' not found — processing all rows.")

    if "image_path" not in df.columns:
        raise ValueError("Column 'image_path' is required but not found in CSV.")

    df["_resolved_path"] = df["image_path"].apply(resolve_path)

    # ── Load YOLO ─────────────────────────────────────────────────────────
    log.info("Loading YOLOv8n model …")
    model = YOLO(YOLO_MODEL)
    log.info("YOLO model ready.")

    # ── Process images ────────────────────────────────────────────────────
    records = []
    skipped = 0

    for _, row in tqdm(df.iterrows(), total=len(df),
                       desc="Extracting features", unit="ad"):
        img_path = row["_resolved_path"]

        if not img_path or not os.path.exists(img_path):
            log.warning("Missing image, skip ad_id=%s  path=%s",
                        row.get("ad_id", "?"), img_path)
            skipped += 1
            continue

        img = load_image(img_path)
        if img is None:
            skipped += 1
            continue

        try:
            yolo_feats   = extract_yolo_features(model, img)
            ocr_feats    = extract_ocr_features(img)
            visual_feats = extract_visual_features(img)
            text_feats   = extract_text_features(row.get("ad_text", ""))

            record = {
                # ── Identifiers (use what's available) ──────────────────
                "brand":          row.get("brand",          ""),
                "ad_id":          row.get("ad_id",           ""),
                "ad_name":        row.get("ad_name",         ""),
                "creative_index": row.get("creative_index",  ""),
                "page_name":      row.get("page_name",        ""),
                "ad_type":        row.get("ad_type",          "image"),
                "image_path":     row.get("image_path",       ""),
                # ── Performance metrics (if present) ────────────────────
                "impressions":    row.get("impressions",     ""),
                "clicks":         row.get("clicks",          ""),
                "ctr":            row.get("ctr",             ""),
                "cpc":            row.get("cpc",             ""),
                "spend":          row.get("spend",           ""),
                "frequency":      row.get("frequency",       ""),
                # ── Extracted features ───────────────────────────────────
                **yolo_feats,
                **ocr_feats,
                **visual_feats,
                **text_feats,
            }
            records.append(record)

            log.debug("OK  ad_id=%-20s  objects=%d  brightness=%.1f",
                      row.get("ad_id", "?"),
                      yolo_feats["object_count"],
                      visual_feats["brightness"])

        except Exception as exc:
            log.error("Error processing ad_id=%s (%s): %s",
                      row.get("ad_id", "?"), img_path, exc)
            skipped += 1

    # ── Save ──────────────────────────────────────────────────────────────
    if not records:
        log.warning("No records — output file not created.")
        return

    features_df = pd.DataFrame(records)

    # Drop empty columns (identifiers not in this dataset)
    features_df = features_df.loc[:, (features_df != "").any(axis=0)]

    # Desired column order (spec + extras)
    ordered = [
        "brand", "ad_id", "ad_name", "creative_index", "page_name",
        "ad_type", "image_path",
        "impressions", "clicks", "ctr", "cpc", "spend", "frequency",
        # YOLO
        "object_count", "person_present", "largest_object_area",
        "center_object", "left_object", "right_object", "top_object", "bottom_object",
        # OCR
        "ocr_text_length", "ocr_word_count", "cta_present",
        # Visual
        "brightness", "contrast", "dominant_r", "dominant_g", "dominant_b", "color_variance",
        # Text
        "ad_text_word_count", "promotional_word_presence", "emoji_count", "cta_in_text",
    ]
    ordered = [c for c in ordered if c in features_df.columns]
    features_df = features_df[ordered]

    features_df.to_csv(OUTPUT_PATH, index=False)

    log.info("━" * 60)
    log.info("✅  Feature extraction complete!")
    log.info("    Processed : %d  |  Skipped: %d", len(records), skipped)
    log.info("    Output    : %s", OUTPUT_PATH)
    log.info("━" * 60)
    print("\nSample output:")
    print(features_df.head(3).to_string())


if __name__ == "__main__":
    main()
