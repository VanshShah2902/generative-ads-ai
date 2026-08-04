"""
Hybrid ad compositor — uses the reference image as the base layer,
then selectively modifies only the elements the user wants to change.

Approach:
  1. Start with the reference image (keeps background, textures, decorative elements)
  2. For text changes: paint over old text region, render new text
  3. For color changes: apply hue/saturation shift to the entire image or specific regions
  4. For font changes: paint over text regions, re-render with new fonts
  5. For layout changes: crop/extract elements and reposition them
  6. For ratio changes: smart crop/extend the canvas
  7. For doctor toggle: paint over doctor region or paste doctor image
"""

import os
import colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageColor


# ─── Font resolution ──────────────────────────────────────────────────────

FONT_DIR = "C:\\Windows\\Fonts"

FONT_MAP = {
    "sans_serif": {"normal": "arial.ttf", "bold": "arialbd.ttf", "extra_bold": "ariblk.ttf"},
    "serif": {"normal": "times.ttf", "bold": "timesbd.ttf", "extra_bold": "timesbd.ttf"},
    "script": {"normal": "SCRIPTBL.TTF", "bold": "SCRIPTBL.TTF", "extra_bold": "SCRIPTBL.TTF"},
    "decorative": {"normal": "BAUHS93.TTF", "bold": "BAUHS93.TTF", "extra_bold": "BAUHS93.TTF"},
    "modern": {"normal": "bahnschrift.ttf", "bold": "bahnschrift.ttf", "extra_bold": "bahnschrift.ttf"},
    "impact": {"normal": "impact.ttf", "bold": "impact.ttf", "extra_bold": "impact.ttf"},
}

FONT_PRESET_MAP = {
    "trust": {"headline": ("serif", "bold"), "sub": ("serif", "normal"), "cta": ("sans_serif", "bold")},
    "premium": {"headline": ("sans_serif", "bold"), "sub": ("serif", "normal"), "cta": ("sans_serif", "normal")},
    "calm": {"headline": ("sans_serif", "normal"), "sub": ("serif", "normal"), "cta": ("sans_serif", "normal")},
    "natural": {"headline": ("sans_serif", "normal"), "sub": ("sans_serif", "normal"), "cta": ("sans_serif", "bold")},
    "bold_impact": {"headline": ("impact", "bold"), "sub": ("sans_serif", "normal"), "cta": ("sans_serif", "extra_bold")},
    "panic": {"headline": ("decorative", "bold"), "sub": ("sans_serif", "normal"), "cta": ("sans_serif", "bold")},
    "modern": {"headline": ("modern", "bold"), "sub": ("modern", "normal"), "cta": ("modern", "bold")},
}


def _get_font(style: str, weight: str, size: int) -> ImageFont.FreeTypeFont:
    family = FONT_MAP.get(style, FONT_MAP["sans_serif"])
    ttf_name = family.get(weight, family["normal"])
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, ttf_name), size)
    except OSError:
        return ImageFont.truetype(os.path.join(FONT_DIR, "arial.ttf"), size)


def _resolve_font(element: dict, font_preset: str = None) -> tuple:
    style = element.get("font_style", "sans_serif")
    weight = element.get("font_weight", "normal")
    if font_preset and font_preset in FONT_PRESET_MAP:
        preset = FONT_PRESET_MAP[font_preset]
        etype = element.get("type", "")
        if etype in ("headline",) and "headline" in preset:
            style, weight = preset["headline"]
        elif etype in ("subheadline", "body_text") and "sub" in preset:
            style, weight = preset["sub"]
        elif etype in ("cta_button",) and "cta" in preset:
            style, weight = preset["cta"]
    return style, weight


# ─── Color utilities ──────────────────────────────────────────────────────

def hex_to_rgb(h: str) -> tuple:
    if not h or not h.startswith("#"):
        return (128, 128, 128)
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _shift_image_hue(img: Image.Image, target_hue_hex: str, strength: float = 0.7) -> Image.Image:
    """Shift the hue of an entire image toward a target color."""
    arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0

    tr, tg, tb = [c / 255.0 for c in hex_to_rgb(target_hue_hex)]
    target_h, target_s, _ = colorsys.rgb_to_hsv(tr, tg, tb)

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    v = maxc
    s = np.where(maxc > 0, (maxc - minc) / maxc, 0)

    new_h = np.full_like(v, target_h)
    new_s = s * (1 - strength) + target_s * strength * np.where(s > 0.05, 1, 0)

    c = v * new_s
    x = c * (1 - np.abs((new_h * 6) % 2 - 1))
    m = v - c

    hi = (new_h * 6).astype(int) % 6
    out = np.zeros_like(arr)

    for i in range(6):
        mask = hi == i
        if i == 0:
            out[mask] = np.stack([c[mask], x[mask], np.zeros_like(c[mask])], axis=-1)
        elif i == 1:
            out[mask] = np.stack([x[mask], c[mask], np.zeros_like(c[mask])], axis=-1)
        elif i == 2:
            out[mask] = np.stack([np.zeros_like(c[mask]), c[mask], x[mask]], axis=-1)
        elif i == 3:
            out[mask] = np.stack([np.zeros_like(c[mask]), x[mask], c[mask]], axis=-1)
        elif i == 4:
            out[mask] = np.stack([x[mask], np.zeros_like(c[mask]), c[mask]], axis=-1)
        elif i == 5:
            out[mask] = np.stack([c[mask], np.zeros_like(c[mask]), x[mask]], axis=-1)

    out += m[:, :, np.newaxis]
    out = np.clip(out * 255, 0, 255).astype(np.uint8)

    result = Image.fromarray(out, "RGB")
    if img.mode == "RGBA":
        result = result.convert("RGBA")
        result.putalpha(img.split()[3])
    return result


# ─── Text helpers ─────────────────────────────────────────────────────────

def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.getbbox(test)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _sample_region_color(img: Image.Image, bbox: tuple) -> tuple:
    """Sample the dominant color around a region's edges for infill."""
    x1, y1, x2, y2 = bbox
    w, h = img.size
    margin = 5
    samples = []

    for x in range(max(0, x1 - margin), min(w, x1 + margin)):
        for y in range(max(0, y1), min(h, y2)):
            samples.append(img.getpixel((x, y))[:3])
    for x in range(max(0, x2 - margin), min(w, x2 + margin)):
        for y in range(max(0, y1), min(h, y2)):
            samples.append(img.getpixel((x, y))[:3])

    if not samples:
        return (128, 128, 128)

    avg_r = sum(s[0] for s in samples) // len(samples)
    avg_g = sum(s[1] for s in samples) // len(samples)
    avg_b = sum(s[2] for s in samples) // len(samples)
    return (avg_r, avg_g, avg_b)


def _inpaint_region(img: Image.Image, bbox: tuple, margin: int = 8) -> Image.Image:
    """Paint over a region using edge-sampled gradient fill + heavy blur for seamless blending."""
    x1, y1, x2, y2 = bbox
    w, h = img.size
    x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
    x2, y2 = min(w, x2 + margin), min(h, y2 + margin)
    rw, rh = x2 - x1, y2 - y1
    if rw < 2 or rh < 2:
        return img

    # Sample colors from all 4 edges
    top_color = _sample_region_color(img, (x1, max(0, y1 - 15), x2, y1))
    bot_color = _sample_region_color(img, (x1, y2, x2, min(h, y2 + 15)))
    left_color = _sample_region_color(img, (max(0, x1 - 15), y1, x1, y2))
    right_color = _sample_region_color(img, (x2, y1, min(w, x2 + 15), y2))

    # Create a gradient-filled patch blending all 4 edge colors
    patch = Image.new("RGBA", (rw, rh))
    for py in range(rh):
        vy = py / max(1, rh - 1)
        for px in range(rw):
            vx = px / max(1, rw - 1)
            # Bilinear interpolation of 4 edge colors
            top_mix = tuple(int(left_color[c] * (1 - vx) + right_color[c] * vx) for c in range(3))
            bot_mix = tuple(int(left_color[c] * (1 - vx) + right_color[c] * vx) for c in range(3))
            top_edge = tuple(int(top_color[c] * (1 - vx) + top_mix[c] * vx) for c in range(3))
            bot_edge = tuple(int(bot_color[c] * (1 - vx) + bot_mix[c] * vx) for c in range(3))
            final = tuple(int(top_edge[c] * (1 - vy) + bot_edge[c] * vy) for c in range(3))
            patch.putpixel((px, py), final + (255,))

    patch = patch.filter(ImageFilter.GaussianBlur(radius=max(3, min(rw, rh) // 4)))
    img.paste(patch, (x1, y1))
    return img


# ─── Image element helpers ────────────────────────────────────────────────

def _load_and_fit(image_path: str, tw: int, th: int, shape: str = "rectangle") -> Image.Image:
    img = Image.open(image_path).convert("RGBA")
    ratio = min(tw / img.width, th / img.height)
    new_w, new_h = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    if shape == "circle":
        mask = Image.new("L", (new_w, new_h), 0)
        d = ImageDraw.Draw(mask)
        r = min(new_w, new_h) // 2
        cx, cy = new_w // 2, new_h // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        img.putalpha(mask)
    return img


# ─── Main hybrid compositor ──────────────────────────────────────────────

ASPECT_RATIOS = {
    "1:1": (1080, 1080),
    "9:16": (1080, 1920),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),
}


def _merge_adjacent_elements(elements: list) -> list:
    """Merge adjacent elements of the same type (e.g. two headline lines → one headline).
    Gemini often splits multi-line headlines into separate elements."""
    if not elements:
        return elements

    merged = []
    skip = set()

    for i, elem in enumerate(elements):
        if i in skip:
            continue
        etype = elem.get("type", "")
        if etype not in ("headline", "subheadline", "comparison_item"):
            merged.append(elem)
            continue

        # Look for the next element of same type that's vertically adjacent
        combined = dict(elem)
        bbox = list(elem.get("bbox_normalized", [0, 0, 0.1, 0.1]))
        texts = [elem.get("content", "")]

        for j in range(i + 1, len(elements)):
            if j in skip:
                continue
            other = elements[j]
            if other.get("type") != etype:
                continue
            obbox = other.get("bbox_normalized", [0, 0, 0.1, 0.1])
            # Check if vertically adjacent (similar x, y is close to bottom of current)
            x_overlap = abs(bbox[0] - obbox[0]) < 0.1
            y_gap = abs((bbox[1] + bbox[3]) - obbox[1])
            if x_overlap and y_gap < 0.05:
                texts.append(other.get("content", ""))
                # Expand bbox to cover both
                new_y = min(bbox[1], obbox[1])
                new_bottom = max(bbox[1] + bbox[3], obbox[1] + obbox[3])
                new_x = min(bbox[0], obbox[0])
                new_right = max(bbox[0] + bbox[2], obbox[0] + obbox[2])
                bbox = [new_x, new_y, new_right - new_x, new_bottom - new_y]
                skip.add(j)

        combined["content"] = " ".join(texts)
        combined["bbox_normalized"] = bbox
        if len(texts) > 1:
            combined["font_size_ratio"] = (combined.get("font_size_ratio") or 0.04)
        merged.append(combined)

    return merged


class AdCompositor:
    def __init__(self, analysis: dict, reference_image_path: str):
        self.analysis = analysis
        self.ref_path = reference_image_path
        self.elements = _merge_adjacent_elements(analysis.get("elements", []))
        self.palette = analysis.get("color_palette", {})
        self.layout = analysis.get("layout", {})

    def _get_element(self, element_id: str) -> dict:
        return next((e for e in self.elements if e.get("id") == element_id), None)

    def _bbox_to_pixels(self, bbox_norm: list, w: int, h: int) -> tuple:
        return (
            int(bbox_norm[0] * w),
            int(bbox_norm[1] * h),
            int((bbox_norm[0] + bbox_norm[2]) * w),
            int((bbox_norm[1] + bbox_norm[3]) * h),
        )

    # Major text elements safe to inpaint and re-render (large, distinct regions)
    FONT_SAFE_TYPES = {"headline", "subheadline", "price", "cta_button", "brand_logo"}
    # All text element types (including small body text embedded in scene)
    ALL_TEXT_TYPES = {"headline", "subheadline", "body_text", "price", "cta_button", "brand_logo", "comparison_item"}

    def _text_elements(self, font_safe_only: bool = False) -> list:
        types = self.FONT_SAFE_TYPES if font_safe_only else self.ALL_TEXT_TYPES
        return [e for e in self.elements if e.get("type") in types]

    def generate(
        self,
        changes: dict = None,
        product_image_path: str = None,
        doctor_image_path: str = None,
    ) -> Image.Image:
        """
        Generate a variant from the reference.

        changes dict can contain:
            "color": {"primary": "#hex", "secondary": "#hex"} — recolor the ad
            "font": "trust|premium|calm|natural|bold_impact|modern" — change fonts
            "text": {"element_id": "new text", ...} — change specific text
            "ratio": "1:1|9:16|4:5|16:9" — change aspect ratio
            "remove_doctor": True — remove the doctor image
            "add_doctor": "/path/to/doctor.jpg" — add/replace doctor image
            "layout": "mirror" — mirror the layout horizontally
        """
        changes = changes or {}

        ref = Image.open(self.ref_path).convert("RGBA")
        ref_w, ref_h = ref.size

        # ── Step 1: Color shift (applied to full image) ──
        if "color" in changes:
            primary = changes["color"].get("primary")
            if primary:
                ref = _shift_image_hue(ref, primary, strength=0.6)

        # ── Step 2: Text changes (paint over + re-render) ──
        text_changes = changes.get("text", {})
        font_preset = changes.get("font")
        need_text_rerender = bool(text_changes) or bool(font_preset)

        if need_text_rerender:
            # For font-only changes, only touch major elements (headline, price, CTA)
            # For text content changes, touch whichever elements are being changed
            font_only = font_preset and not text_changes
            candidates = self._text_elements(font_safe_only=font_only)

            # Phase 1: Collect all text elements that need re-rendering
            elements_to_render = []
            for elem in candidates:
                eid = elem.get("id", "")
                new_text = text_changes.get(eid)
                has_font_change = font_preset is not None
                has_text_change = new_text is not None
                if not has_font_change and not has_text_change:
                    continue
                bbox_norm = elem.get("bbox_normalized", [0, 0, 0.1, 0.1])
                x1, y1, x2, y2 = self._bbox_to_pixels(bbox_norm, ref_w, ref_h)
                pw, ph = x2 - x1, y2 - y1
                if pw < 5 or ph < 5:
                    continue
                text = new_text or elem.get("content", "")
                if not text:
                    continue
                elements_to_render.append((elem, x1, y1, x2, y2, pw, ph, text))

            # Phase 2: Inpaint ALL text regions first (prevents ghosting)
            for elem, x1, y1, x2, y2, pw, ph, text in elements_to_render:
                expand_x = int(pw * 0.25)
                expand_y = int(ph * 0.35)
                _inpaint_region(ref, (x1 - expand_x, y1 - expand_y, x2 + expand_x, y2 + expand_y), margin=12)

            # Phase 3: Render all new text on the clean surface
            draw = ImageDraw.Draw(ref)
            for elem, x1, y1, x2, y2, pw, ph, text in elements_to_render:
                font_size = max(12, int((elem.get("font_size_ratio") or 0.03) * ref_h))
                style, weight = _resolve_font(elem, font_preset)
                font = _get_font(style, weight, font_size)
                text_color = hex_to_rgb(elem.get("text_color", "#ffffff"))
                align = elem.get("text_align", "left")

                if elem.get("type") == "cta_button":
                    bg_color = hex_to_rgb(elem.get("bg_color", "#ff9900"))
                    radius = min(pw, ph) // 3
                    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg_color)

                lines = _wrap_text(text, font, pw - 8)
                line_h = font_size + 4
                total_h = len(lines) * line_h
                y_off = y1 + max(0, (ph - total_h) // 2)

                for line in lines:
                    lbbox = font.getbbox(line)
                    lw = lbbox[2] - lbbox[0]
                    if align == "center":
                        lx = x1 + (pw - lw) // 2
                    elif align == "right":
                        lx = x2 - lw - 4
                    else:
                        lx = x1 + 4
                    draw.text((lx, y_off), line, fill=text_color, font=font)
                    y_off += line_h

        # ── Step 3: Doctor toggle ──
        if changes.get("remove_doctor"):
            for elem in self.elements:
                eid = elem.get("id", "").lower()
                etype = elem.get("type", "")
                content = elem.get("content", "").lower()
                is_doctor_related = (
                    etype == "doctor_image"
                    or eid in ("doctor_name_text", "doctor_title_text", "doctor_image_bimal")
                    or ("doctor" in eid and "brand" not in eid)
                )
                if is_doctor_related:
                    bbox = self._bbox_to_pixels(elem["bbox_normalized"], ref_w, ref_h)
                    _inpaint_region(ref, bbox, margin=15)

        if changes.get("add_doctor") and doctor_image_path:
            for elem in self.elements:
                if elem.get("type") == "doctor_image":
                    x1, y1, x2, y2 = self._bbox_to_pixels(elem["bbox_normalized"], ref_w, ref_h)
                    pw, ph = x2 - x1, y2 - y1
                    _inpaint_region(ref, (x1, y1, x2, y2), margin=5)
                    doc_img = _load_and_fit(doctor_image_path, pw, ph, elem.get("shape", "circle"))
                    ox = x1 + (pw - doc_img.width) // 2
                    oy = y1 + (ph - doc_img.height) // 2
                    ref.paste(doc_img, (ox, oy), doc_img)

        # ── Step 4: Product image swap ──
        if changes.get("swap_product") and product_image_path:
            for elem in self.elements:
                if elem.get("type") == "product_image":
                    x1, y1, x2, y2 = self._bbox_to_pixels(elem["bbox_normalized"], ref_w, ref_h)
                    pw, ph = x2 - x1, y2 - y1
                    _inpaint_region(ref, (x1, y1, x2, y2), margin=5)
                    prod_img = _load_and_fit(product_image_path, pw, ph)
                    ox = x1 + (pw - prod_img.width) // 2
                    oy = y1 + (ph - prod_img.height) // 2
                    ref.paste(prod_img, (ox, oy), prod_img)

        # ── Step 5: Mirror layout ──
        # Full mirror is too destructive (reverses text on product, icons, etc.)
        # Instead, skip mirror for now — proper layout rearrangement needs layer-based editing
        if changes.get("layout") == "mirror":
            pass  # Reserved for future layer-based layout engine

        # ── Step 6: Aspect ratio change ──
        target_ratio = changes.get("ratio")
        if target_ratio and target_ratio in ASPECT_RATIOS:
            target_w, target_h = ASPECT_RATIOS[target_ratio]
            ref = self._smart_resize(ref, target_w, target_h)

        return ref

    def _smart_resize(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Resize keeping content: scale to cover, then crop from center.
        If target is taller (portrait), pad top/bottom with sampled color."""
        src_w, src_h = img.size
        src_ratio = src_w / src_h
        target_ratio = target_w / target_h

        if abs(src_ratio - target_ratio) < 0.05:
            return img.resize((target_w, target_h), Image.LANCZOS)

        if target_ratio < src_ratio:
            # Target is taller/narrower — scale width to match, extend height
            scale = target_w / src_w
            new_w = target_w
            new_h = int(src_h * scale)
            scaled = img.resize((new_w, new_h), Image.LANCZOS)

            if new_h >= target_h:
                top = (new_h - target_h) // 2
                return scaled.crop((0, top, target_w, top + target_h))
            else:
                # Need to extend — sample edge colors for padding
                canvas = Image.new("RGBA", (target_w, target_h))
                top_color = _sample_region_color(scaled, (0, 0, new_w, min(10, new_h)))
                bot_color = _sample_region_color(scaled, (0, max(0, new_h - 10), new_w, new_h))

                draw = ImageDraw.Draw(canvas)
                y_offset = (target_h - new_h) // 2
                draw.rectangle([0, 0, target_w, y_offset], fill=top_color)
                draw.rectangle([0, y_offset + new_h, target_w, target_h], fill=bot_color)
                canvas.paste(scaled, (0, y_offset))

                top_band = canvas.crop((0, max(0, y_offset - 30), target_w, y_offset + 30))
                top_band = top_band.filter(ImageFilter.GaussianBlur(radius=15))
                canvas.paste(top_band, (0, max(0, y_offset - 30)))

                bot_start = y_offset + new_h
                bot_band = canvas.crop((0, bot_start - 30, target_w, min(target_h, bot_start + 30)))
                bot_band = bot_band.filter(ImageFilter.GaussianBlur(radius=15))
                canvas.paste(bot_band, (0, bot_start - 30))

                return canvas
        else:
            # Target is wider — scale height to match, crop width from center
            scale = target_h / src_h
            new_w = int(src_w * scale)
            new_h = target_h
            scaled = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - target_w) // 2
            return scaled.crop((left, 0, left + target_w, target_h))
