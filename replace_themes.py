import re

NEW_THEME = r'''THEME_LAYOUTS = {
    # KR 2D
    "KR_2D": {
        "label": "14 Ayurvedic Heritage",
        "has_doctor": True,
        "headline": (
            'large bold "14" numeral in red/gold at top-left, '
            'beside it "Ayurvedic [Subtitle]" where subtitle is one of: '
            '"Premium Herbal Blend" / "Heart Support Formula" / "Natural Herbs" / "Cardio Wellness Formula"'
        ),
        "doctor": (
            "Dr. Bimal Chhajer full body, LEFT side of frame, 60% of frame height, "
            "professional confident pose, formal shirt and trousers, "
            "NO lab coat, NO white coat, NO stethoscope, NO medical equipment"
        ),
        "product_placement": (
            "product packshot anchored at doctor chest level, positioned beside doctor toward center-right, "
            "tea cup always present alongside packshot"
        ),
        "badges": (
            "RIGHT side: exactly 4 rounded-rectangle pill badges stacked vertically, "
            "each badge: herb name in bold at top + one benefit text line below it"
        ),
        "footer": "\"50 Sachets Rs.599 | Formulated by Dr. Bimal Chhajer\" full-width footer text at bottom of ad",
        "cta": "NO Shop Now button",
        "background": "background: choose one from cream / ivory / marble texture / forest green / navy / saffron / champagne",
        "decorative": (
            "botanical leaf line-art corner decorations at all 4 corners, "
            "ECG heartbeat line as subtle horizontal decoration, "
            "gold accent rule lines and borders"
        ),
    },

    # DR 1ST
    "DR_1ST": {
        "label": "Doctor Dominant",
        "has_doctor": True,
        "headline": (
            '"ARJUNA CARDIO CARE TEA" in large ultra-bold type at top-left of frame, '
            "NO 14 prefix, product name dominates the entire top section"
        ),
        "doctor": (
            "Dr. Bimal Chhajer full body, LEFT side of frame, very dominant 70-75% of frame height, "
            "commanding authoritative presence, formal shirt and trousers, "
            "NO lab coat, NO white coat, NO stethoscope, NO medical equipment"
        ),
        "product_placement": (
            "product packshot smaller, at doctor waist or hand level, positioned center-right, "
            "tea cup always present alongside packshot"
        ),
        "badges": (
            "RIGHT side: 3 or 4 herb badges in decorative shapes, "
            "choose from: circles / medallions / scrolls / ribbons / oval plaques, "
            "each badge: herb name + benefit text"
        ),
        "footer": "\"50 Sachets Rs.599 | Formulated by Dr. Bimal Chhajer\" full-width footer at bottom",
        "cta": "NO Shop Now button",
        "background": "background: choose one from marble / ivory / cream / forest green / burgundy / copper / olive / sand",
        "decorative": (
            "gold coin effects in background, botanical corner decorations, "
            "ECG heartbeat lines, mandala border elements"
        ),
    },

    # KR 2C
    "KR_2C": {
        "label": "14-IN-1 Formula E-Commerce",
        "has_doctor": True,
        "headline": (
            'top banner headline: "14-IN-1 FORMULA" or "13-IN-1 BLEND" in bold sans-serif, '
            'sub-headline directly below in elegant script font: "Dr. Bimal\'s Arjuna Cardio Care Tea"'
        ),
        "doctor": (
            "Dr. Bimal Chhajer bust and head ONLY on RIGHT side, NOT full body, "
            "confident approachable expression, formal shirt, NO lab coat, NO stethoscope"
        ),
        "product_placement": (
            "product packshot as CENTER HERO, large, elevated on pedestal or marble platform, "
            "tea cup always present on platform alongside packshot"
        ),
        "badges": (
            "BOTTOM horizontal strip: exactly 4 herbs evenly spaced across full width, "
            "each herb: small line-art botanical icon ABOVE the herb name text, clean text layout, NO pill badges, "
            "LEFT side: separate dedicated Rs.599 price badge AND separate 50 Sachets badge"
        ),
        "footer": "SHOP NOW green rounded button always present",
        "cta": "SHOP NOW green rounded button always present",
        "background": "background: choose one from cream / ivory / marble texture / forest green / saffron / champagne / terracotta",
        "decorative": (
            "product on elevated pedestal platform, gold rule lines separating sections, "
            "botanical watermark elements in background"
        ),
    },

    # SIGNS
    "SIGNS": {
        "label": "Signs Your Body Is Asking For",
        "has_doctor": False,
        "headline": (
            'bold dark charcoal headline at top: "X signs your body is asking for" '
            "(X = a number like 5 or 6), "
            "sub-headline uses ingredient names NOT product name, "
            'e.g. "Arjuna Chhal, Tulsi & Ashwagandha"'
        ),
        "doctor": "NO doctor, NO human portrait, product-only layout",
        "product_placement": (
            "product packshot perfectly centered, only the CENTER FACE of the box in sharp focus, "
            "sides of packshot are blurred and faded outward with vignette effect, "
            "tea cup always present beside packshot"
        ),
        "badges": (
            "5 to 6 floating benefit or symptom text labels placed organically around the packshot, "
            "simple clean text, regular font weight, NO icons, NO badge shapes, NO borders, "
            "text floats freely like scattered soft labels"
        ),
        "footer": (
            "\"Dr. Bimal's\" small text centered at very top of ad, "
            "minimal footer, nothing heavy at bottom"
        ),
        "cta": "NO Shop Now, NO price, awareness-only layout",
        "background": "clean minimal background: choose one from ivory / sage green / marble / sand / champagne / forest green",
        "decorative": "clean minimal clinical-wellness DTC health brand aesthetic, subtle and understated",
    },

    # CF
    "CF": {
        "label": "Scientific Gradient 3D",
        "has_doctor": False,
        "headline": (
            "bold white headline in top-RIGHT area, benefit or action statement, "
            "smaller lighter sub-headline text below it also top-right, "
            "\"Dr Bimal's\" white/gold small text logo pinned to very top-RIGHT corner"
        ),
        "doctor": "NO doctor portrait, Dr Bimal's appears as white/gold text logo in top-right corner only",
        "product_placement": (
            "product packshot on LEFT side on white marble surface, "
            "center face of packshot ZOOMED and MAGNIFIED with spotlight glow effect, sides blurred and faded, "
            "\"Dr Bimal's\" logo text + \"ARJUNA\" text large and sharp overlaid on spotlight center face, "
            "tea cup always present beside packshot on marble"
        ),
        "badges": (
            "BOTTOM horizontal strip: exactly 4 herbs, line-art botanical icon + bold herb name + benefit text, "
            "RIGHT side: 3D scientific illustration, choose from: "
            "human circulatory system / Arjuna tree cross-section / DNA double helix / "
            "body silhouette with heart or energy glow, detailed premium CGI quality"
        ),
        "footer": "dark rounded CTA button at bottom center, always present",
        "cta": "CTA dark rounded button at bottom center, always present",
        "background": (
            "rich-to-cream gradient background, choose base color from: "
            "burgundy / forest green / saffron / navy / terracotta, "
            "gradient flows from rich color at outer edges fading to cream/ivory at center"
        ),
        "decorative": "medical-premium scientific clinical trust Ayurvedic science, premium 3D CGI illustration",
    },
}

'''

with open("src/prompt_generation/prompt_builder.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'THEME_LAYOUTS = \{.*?\n\}\n\n'
match = re.search(pattern, content, re.DOTALL)
if match:
    new_content = content[:match.start()] + NEW_THEME + content[match.end():]
    with open("src/prompt_generation/prompt_builder.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"OK: replaced {match.end()-match.start()} chars with {len(NEW_THEME)} chars")
else:
    print("PATTERN NOT FOUND")
    # Show what the area looks like
    idx = content.find("THEME_LAYOUTS")
    print(repr(content[idx:idx+100]))
