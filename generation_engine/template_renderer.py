"""
Doctor Template Creative Renderer
==================================
PIL-based template renderer that replicates the winning doctor-endorsement
ad creative layouts exactly — no AI generation, pure compositional rendering.

Two templates:
  - "cards"  : Doctor left 40%, 3 ingredient cards right, product bottom-left
  - "table"  : Doctor left 35%, large product center-right, ingredient table bottom

Usage:
    renderer = DoctorTemplateRenderer()
    img = renderer.render("cards", doctor_img, product_img, campaign_data)
    img.save("output.png")

campaign_data dict:
    {
        "brand_name":   "Dr. Bimal's",
        "product_name": "Arjuna Cardio Care Tea",
        "ingredients": [
            {"name": "Arjun Chaal", "dose_per": "250mg/sachet",
             "dose_daily": "500mg", "benefit": "Supports healthy cholesterol levels"},
            ...
        ],
        "price":    "₹599",
        "sachets":  "50 Sachets",
        "offer":    "24% OFF",
        "tagline":  "Formulated for Quality",
    }
"""

import os
import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# Load layout config
# ---------------------------------------------------------------------------
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "doctor_template_layout.json")

def _load_cfg():
    with open(os.path.abspath(_CONFIG_PATH), "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates_bold = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/verdanab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    candidates_regular = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/verdana.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    candidates = candidates_bold if bold else candidates_regular
    for path in candidates:
        if os.path.exists(path):
            fnt = ImageFont.truetype(path, size)
            _FONT_CACHE[key] = fnt
            return fnt

    # Last resort — PIL default (no size control)
    fnt = ImageFont.load_default()
    _FONT_CACHE[key] = fnt
    return fnt


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    """Return (width, height) of rendered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ---------------------------------------------------------------------------
# Main renderer class
# ---------------------------------------------------------------------------
class DoctorTemplateRenderer:

    def render(self, template: str, doctor_img: Image.Image,
               product_img: Image.Image, campaign_data: dict) -> Image.Image:
        """
        Entry point. template = "cards" | "table"
        """
        cfg = _load_cfg()
        if template == "table":
            return self._render_table(doctor_img, product_img, campaign_data, cfg)
        return self._render_cards(doctor_img, product_img, campaign_data, cfg)

    # ------------------------------------------------------------------
    # Template A — Cards layout
    # ------------------------------------------------------------------
    def _render_cards(self, doctor_img, product_img, campaign_data, cfg):
        W, H = cfg["canvas"]
        banner_h = cfg["banner_height_px"]
        colors    = {k: tuple(v) for k, v in cfg["colors"].items()}

        canvas = self._marble_background(W, H, colors)
        draw   = ImageDraw.Draw(canvas)

        # ── Doctor (left 40%, full usable height) ────────────────────
        doc_w = int(W * cfg["doctor_width_pct_a"])
        usable_h = H - banner_h
        doctor_cut = self._prepare_cutout(doctor_img, doc_w, usable_h)
        doc_x = 0
        doc_y = usable_h - doctor_cut.height  # bottom-align
        canvas.paste(doctor_cut, (doc_x, doc_y), doctor_cut)

        # ── Product box (bottom-left, overlapping doctor) ─────────────
        pw, ph = cfg["product_size_a"]
        product_cut = self._prepare_product(product_img, pw, ph)
        prod_x = doc_w - product_cut.width // 3   # overlap doctor slightly
        prod_y = usable_h - product_cut.height - 10
        canvas.paste(product_cut, (prod_x, prod_y), product_cut)

        # ── Right panel ──────────────────────────────────────────────
        right_x  = doc_w + 20
        right_w  = W - right_x - 20
        title_h  = cfg["title_height_a"]

        # Title block
        self._draw_title_block_a(draw, canvas, campaign_data, right_x, 20, right_w, cfg, colors)

        # Ingredient cards
        ingredients = campaign_data.get("ingredients", [])[:3]
        card_h   = cfg["card_height_px"]
        card_gap = cfg["card_gap_px"]
        cards_top = title_h + 30
        for idx, ing in enumerate(ingredients):
            cy = cards_top + idx * (card_h + card_gap)
            self._draw_ingredient_card(draw, ing, right_x, cy, right_w, card_h, cfg, colors)

        # ── Gold banner ───────────────────────────────────────────────
        self._draw_banner(draw, canvas, campaign_data, W, H, banner_h, cfg, colors)

        return canvas

    # ------------------------------------------------------------------
    # Template B — Table layout
    # ------------------------------------------------------------------
    def _render_table(self, doctor_img, product_img, campaign_data, cfg):
        W, H = cfg["canvas"]
        banner_h  = cfg["banner_height_px"]
        title_h_b = cfg["title_height_b"]
        colors    = {k: tuple(v) for k, v in cfg["colors"].items()}

        canvas = self._marble_background(W, H, colors)
        draw   = ImageDraw.Draw(canvas)

        # ── Full-width title bar (top) ────────────────────────────────
        self._draw_title_bar_b(draw, canvas, campaign_data, W, title_h_b, cfg, colors)

        usable_top = title_h_b + 10
        usable_h   = H - banner_h - usable_top
        table_h    = cfg["table_height_px"]
        mid_area_h = usable_h - table_h - 20

        # ── Doctor (left 35%, middle area) ───────────────────────────
        doc_w = int(W * cfg["doctor_width_pct_b"])
        doctor_cut = self._prepare_cutout(doctor_img, doc_w, mid_area_h + table_h)
        doc_y = usable_top
        canvas.paste(doctor_cut, (0, doc_y), doctor_cut)

        # ── Product box (center-right, floating above table) ──────────
        pw, ph = cfg["product_size_b"]
        product_cut = self._prepare_product(product_img, pw, ph)
        prod_x = doc_w + (W - doc_w - product_cut.width) // 2
        prod_y = usable_top + (mid_area_h - product_cut.height) // 2
        canvas.paste(product_cut, (prod_x, prod_y), product_cut)

        # ── Ingredient table (bottom area, full width) ────────────────
        table_y = H - banner_h - table_h - 5
        self._draw_ingredient_table(draw, campaign_data.get("ingredients", [])[:3],
                                    0, table_y, W, table_h, cfg, colors)

        # ── Gold banner ───────────────────────────────────────────────
        self._draw_banner(draw, canvas, campaign_data, W, H, banner_h, cfg, colors)

        return canvas

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _marble_background(self, W: int, H: int, colors: dict) -> Image.Image:
        """Generate a white-grey marble-look background procedurally."""
        base = Image.new("RGB", (W, H), (248, 246, 244))
        noise = np.random.normal(128, 18, (H, W, 3)).clip(0, 255).astype(np.uint8)
        noise_img = Image.fromarray(noise, "RGB").filter(ImageFilter.GaussianBlur(radius=22))
        # Blend very lightly
        base = Image.blend(base, noise_img.convert("RGB"), alpha=0.08)
        # Add subtle veins
        draw = ImageDraw.Draw(base)
        for _ in range(6):
            x0 = random.randint(0, W)
            y0 = random.randint(0, H // 2)
            x1 = x0 + random.randint(-200, 200)
            y1 = y0 + random.randint(200, H)
            draw.line([(x0, y0), (x1, y1)], fill=(220, 218, 215), width=random.randint(1, 3))
        return base.filter(ImageFilter.GaussianBlur(radius=1))

    def _prepare_cutout(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Resize subject image to fit target dimensions, keep aspect ratio, RGBA."""
        img = img.convert("RGBA")
        aspect = img.width / img.height
        if aspect > (target_w / target_h):
            new_w = target_w
            new_h = int(new_w / aspect)
        else:
            new_h = target_h
            new_w = int(new_h * aspect)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def _prepare_product(self, img: Image.Image, pw: int, ph: int) -> Image.Image:
        """Resize product to target bounding box preserving aspect ratio, RGBA."""
        img = img.convert("RGBA")
        img.thumbnail((pw, ph), Image.Resampling.LANCZOS)
        return img

    def _draw_title_block_a(self, draw, canvas, data, x, y, width, cfg, colors):
        """Two-line title: brand name (dark green) + product name (gold) — Template A."""
        brand   = data.get("brand_name", "")
        product = data.get("product_name", "")
        sz      = cfg["title_font_size"]

        f_brand   = _font(sz, bold=True)
        f_product = _font(sz, bold=True)

        tw, th = _text_size(draw, brand, f_brand)
        draw.text((x + (width - tw) // 2, y), brand, font=f_brand, fill=colors["dark_green"])

        y2 = y + th + 8
        tw2, th2 = _text_size(draw, product, f_product)
        draw.text((x + (width - tw2) // 2, y2), product, font=f_product, fill=colors["gold"])

    def _draw_title_bar_b(self, draw, canvas, data, W, title_h, cfg, colors):
        """Full-width bold all-caps title bar — Template B."""
        brand   = data.get("brand_name", "").upper()
        product = data.get("product_name", "").upper()
        full    = f"{brand} {product}"
        sz      = cfg["title_font_size_b"]
        font    = _font(sz, bold=True)

        # Try to fit on one line, shrink if needed
        tw, th = _text_size(draw, full, font)
        while tw > W - 40 and sz > 28:
            sz -= 2
            font = _font(sz, bold=True)
            tw, th = _text_size(draw, full, font)

        y = (title_h - th) // 2
        draw.text(((W - tw) // 2, y), full, font=font, fill=colors["black"])

    def _draw_ingredient_card(self, draw, ingredient, x, y, width, height, cfg, colors):
        """Render a single white card with dark-green border + gold icon + text."""
        pad = 12

        # Card background + border
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=10,
            fill=colors["white"],
            outline=colors["dark_green"],
            width=2,
        )

        # Gold icon circle
        r = cfg["icon_circle_r"]
        icon_cx = x + pad + r
        icon_cy = y + height // 2
        draw.ellipse(
            [icon_cx - r, icon_cy - r, icon_cx + r, icon_cy + r],
            fill=colors["gold"],
        )

        # Text block
        tx = icon_cx + r + 14
        available_w = x + width - tx - pad

        name    = ingredient.get("name", "").upper()
        dose    = ingredient.get("dose_per", "")
        benefit = ingredient.get("benefit", "")

        f_name    = _font(cfg["ingredient_name_font_size"], bold=True)
        f_dose    = _font(cfg["dosage_font_size"])
        f_benefit = _font(cfg["description_font_size"])

        ty = y + pad + 4
        draw.text((tx, ty), name, font=f_name, fill=colors["dark_green"])
        _, nh = _text_size(draw, name, f_name)

        ty += nh + 4
        dose_line = f"{dose}  |"
        draw.text((tx, ty), dose_line, font=f_dose, fill=colors["black"])
        _, dh = _text_size(draw, dose_line, f_dose)

        ty += dh + 4
        # Wrap benefit text if needed
        words  = benefit.split()
        line   = ""
        lines  = []
        for w in words:
            test = (line + " " + w).strip()
            tw, _ = _text_size(draw, test, f_benefit)
            if tw <= available_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)

        for ln in lines[:2]:
            draw.text((tx, ty), ln, font=f_benefit, fill=colors["black"])
            _, lh = _text_size(draw, ln, f_benefit)
            ty += lh + 2

    def _draw_ingredient_table(self, draw, ingredients, x, y, width, height, cfg, colors):
        """Render ingredient table with gold header — Template B."""
        col1_w = int(width * 0.55)
        col2_w = width - col1_w
        header_h = cfg["table_header_height_px"]
        row_h = (height - header_h) // max(len(ingredients), 1)
        pad = 16

        # Header row background
        draw.rectangle([x, y, x + width, y + header_h], fill=colors["gold"])
        draw.rectangle([x, y, x + width, y + header_h], outline=colors["dark_green"], width=2)

        f_header = _font(cfg["ingredient_name_font_size"], bold=True)
        hdr1 = "PER SACHET"
        hdr2 = "DAILY (2x)"
        _, hh = _text_size(draw, hdr1, f_header)
        hy = y + (header_h - hh) // 2
        draw.text((x + pad, hy), hdr1, font=f_header, fill=colors["dark_green"])
        tw2, _ = _text_size(draw, hdr2, f_header)
        draw.text((x + col1_w + (col2_w - tw2) // 2, hy), hdr2, font=f_header, fill=colors["dark_green"])

        # Column divider in header
        draw.line([(x + col1_w, y), (x + col1_w, y + header_h)], fill=colors["dark_green"], width=2)

        # Data rows
        r = cfg["icon_circle_r"] - 4
        f_name  = _font(cfg["ingredient_name_font_size"], bold=True)
        f_sub   = _font(cfg["description_font_size"])
        f_dose  = _font(cfg["dosage_font_size"])

        for idx, ing in enumerate(ingredients):
            ry = y + header_h + idx * row_h

            # Row background alternating
            row_fill = (255, 255, 255) if idx % 2 == 0 else (248, 248, 245)
            draw.rectangle([x, ry, x + width, ry + row_h], fill=row_fill)
            draw.rectangle([x, ry, x + width, ry + row_h], outline=colors["gold"], width=1)
            draw.line([(x + col1_w, ry), (x + col1_w, ry + row_h)], fill=colors["gold"], width=1)

            # Gold icon circle
            icon_cx = x + pad + r
            icon_cy = ry + row_h // 2
            draw.ellipse([icon_cx - r, icon_cy - r, icon_cx + r, icon_cy + r], fill=colors["gold"])

            # Ingredient name + benefit
            tx = icon_cx + r + 12
            name    = ing.get("name", "").upper()
            benefit = ing.get("benefit", "")
            dose    = ing.get("dose_per", "")

            draw.text((tx, ry + 8), name, font=f_name, fill=colors["dark_green"])
            _, nh = _text_size(draw, name, f_name)
            draw.text((tx, ry + 8 + nh + 2), f"({benefit})", font=f_sub, fill=colors["black"])

            # Daily dose (right column)
            daily = ing.get("dose_daily", "")
            dose_text = f"{dose} → {daily}"
            tw, _ = _text_size(draw, dose_text, f_dose)
            draw.text((x + col1_w + (col2_w - tw) // 2, ry + (row_h - _text_size(draw, dose_text, f_dose)[1]) // 2),
                      dose_text, font=f_dose, fill=colors["black"])

    def _draw_banner(self, draw, canvas, data, W, H, banner_h, cfg, colors):
        """Full-width gold bottom banner with tagline + price."""
        y = H - banner_h
        draw.rectangle([0, y, W, H], fill=colors["amber_bg"])

        tagline = data.get("tagline", "Formulated for Quality")
        sachets = data.get("sachets", "")
        price   = data.get("price", "")
        offer   = data.get("offer", "")

        parts = [tagline]
        if sachets and price:
            parts.append(f"{sachets} {price}")
        if offer:
            parts[-1] += f" ({offer})"
        text = "  |  ".join(parts)

        f = _font(cfg["banner_font_size"], bold=True)
        tw, th = _text_size(draw, text, f)
        tx = (W - tw) // 2
        ty = y + (banner_h - th) // 2
        draw.text((tx, ty), text, font=f, fill=colors["dark_green"])

        # Decorative diamond ◆ at right end
        draw.text((W - 40, ty), "◆", font=f, fill=colors["dark_green"])
