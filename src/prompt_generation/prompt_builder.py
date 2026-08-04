import random
from src.compliance.nmc_filter import (
    sanitise_prompt as _nmc_sanitise,
    audit_payload,
    DOCTOR_DISCLAIMER_NOTE,
)

def sanitize_prompt(prompt: str) -> str:
    """Remove layout-banned phrases then apply full NMC compliance filter."""
    banned_phrases = [
        "clean split-frame horizontal composition",
        "split-frame composition",
        "dual panel composition"
    ]
    for phrase in banned_phrases:
        prompt = prompt.replace(phrase, "")
    # NMC compliance pass — replaces cure/guarantee/disease-claim language
    return _nmc_sanitise(prompt.strip())

from src.config.config_loader import load_fonts, load_prompts, load_ingredient_benefits

FONT_CONFIG = load_fonts()
FONT_PRESETS = FONT_CONFIG.get("presets", [])

# Ingredient → NMC-compliant ad benefit phrases (from ingredient_benefits.json)
INGREDIENT_BENEFITS: dict = load_ingredient_benefits()

if not FONT_PRESETS:
    raise ValueError("Font config not loaded")

print("[Config] Fonts Loaded:", len(FONT_PRESETS))

PROMPT_CONFIG = load_prompts()

# Variation indices (within a 5-variation cycle) that get a product name
# text overlay — 4 out of 5 = 80%
_NAME_OVERLAY_INDICES = {0, 1, 2, 3}

# ---------------------------------------------------------------------------
# Competitor-intelligence-derived winning patterns
# Based on analysis of OZiva, Woolah, Plix, Kapiva ads + our own winning ads
# ---------------------------------------------------------------------------

# Winning color palettes per cluster (derived from competitor + winning ad analysis)
CLUSTER_COLORS = {
    "product_first": [
        ("deep green", "white", "gold"),
        ("dark green", "cream", "white"),
        ("forest green", "white", "dark brown"),
        ("olive green", "white", "earth tones"),
    ],
    "solution_first": [
        ("forest green", "cream", "gold"),
        ("maroon", "cream", "forest green"),
        ("deep green", "beige", "white"),
        ("teal", "cream", "yellow"),
    ],
    "doctor_first": [
        ("maroon", "cream", "forest green"),
        ("navy blue", "white", "forest green"),
        ("deep green", "white", "red"),
        ("white", "deep green", "dark brown"),
    ],
    "ingredient_first": [
        ("deep green", "earth tones", "white"),
        ("white", "deep green", "tan"),
        ("forest green", "white", "brown"),
        ("dark green", "white", "black"),
    ],
    "problem_first": [
        ("vibrant red", "dark green", "beige"),
        ("red", "beige", "dark green"),
        ("maroon", "cream", "forest green"),
        ("vibrant red", "fatty yellow", "dark green"),
    ],
}

# Hook type cycling per variation — drives the compositional intent of each ad
# Derived from winning patterns: fear, benefit, authority, problem, curiosity
CLUSTER_HOOK_CYCLES = {
    "product_first":    ["benefit", "curiosity", "authority", "benefit", "curiosity"],
    "solution_first":   ["benefit", "relief", "authority", "benefit", "relief"],
    "doctor_first":     ["authority", "trust", "authority", "trust", "benefit"],
    "ingredient_first": ["curiosity", "benefit", "authority", "curiosity", "benefit"],
    "problem_first":    ["fear", "problem", "fear", "problem", "fear"],
}

# Winning visual patterns per cluster (from competitor analysis)
# Each cluster has 5 visual pattern signals — one per variation
CLUSTER_VISUAL_PATTERNS = {
    "product_first": [
        "product elevated on plain background with dramatic rim lighting, clean white space, minimal elements",
        "product as central hero surrounded by soft ingredient halos, lifestyle context blurred in background",
        "product macro close-up filling 60% of frame, ingredient raw elements scattered naturally around it",
        "product in soft glow-effect circle, feature benefit list on the left side, plain background",
        "dramatic product shot with medical-grade clean aesthetic, dark background with product illuminated",
    ],
    "solution_first": [
        "vertical split: left side shows solution text in bold, right side product as glowing hero answer",
        "product hero centered, solution outcome text floating above in large bold type, lifestyle context",
        "before-after vertical split: dark tense left, bright hopeful right with product as the turning point",
        "product in spotlight circle, solution benefit statements radiating outward as visual anchors",
        "lifestyle scene showing positive transformation, product prominently anchored at bottom-right",
    ],
    "doctor_first": [
        "doctor face as primary emotional trust anchor taking 50% of frame, product on desk in foreground",
        "doctor in white coat pointing to product, clinical background, credential badge visible, no stethoscope",
        "split: doctor recommendation quote on left in large serif, product hero on right with glow",
        "doctor holding product at eye level, direct eye contact, clean clinical background, trust focus",
        "scientific diagram or ingredient chart in background, doctor and product in foreground as authority",
    ],
    "ingredient_first": [
        "top-down flat lay: product centered, raw ingredients symmetrically arranged around it on natural surface",
        "ingredient macro shots in grid formation with product center-bottom, botanical aesthetic",
        "ingredient sourcing story: raw herbs and botanical elements flowing into product shot, earthy background",
        "product hero with ingredient pills or capsules spilling naturally, each ingredient labeled",
        "ingredient symmetry: product in center glow circle, key ingredients positioned at cardinal points",
    ],
    "problem_first": [
        "macro medical illustration of artery or heart taking 70% of frame, product anchored at bottom with urgency text",
        "split composition: left side shows person with visible distress, right side shows product as the clear answer",
        "bold problem statement in large red text dominating upper frame, product as the solution below",
        "dramatic close-up of person's concerned face, problem text overlay, product in corner as hope",
        "visual metaphor showing blockage or health risk (anatomical), product positioned as the solution",
    ],
}

# Emotion to facial expression mapping (specific, not abstract)
EMOTION_EXPRESSIONS = {
    "fear":       "person's face showing genuine fear and worry, furrowed brows, tense jaw",
    "panic":      "person showing visible panic, wide eyes, tense posture, hand on chest",
    "worry":      "person expressing quiet concern, troubled eyes, slightly pursed lips",
    "shock":      "person showing shock and disbelief, raised eyebrows, open mouth",
    "relief":     "person showing deep relief, eyes closing softly, shoulders dropping, warm smile",
    "calm":       "person with calm, serene expression, soft eyes, relaxed posture",
    "hope":       "person with hopeful, uplifted expression, gentle smile, looking upward",
    "trust":      "doctor or expert showing confident, reassuring expression, direct eye contact",
    "confidence": "person with strong, assured posture, direct gaze, slight smile",
    "premium":    "person with sophisticated, discerning expression, poised posture",
    "freshness":  "person showing energized, refreshed expression, bright eyes, natural smile",
    "natural":    "person with relaxed, wholesome expression, genuine warm smile",
    "urgency":    "person showing urgent concern, pointing or gesturing toward the problem",
}

# Background type per cluster (from competitor analysis — plain wins most)
CLUSTER_BACKGROUND = {
    "product_first":    ["plain", "gradient", "plain"],
    "solution_first":   ["plain", "gradient", "real_scene"],
    "doctor_first":     ["plain", "plain", "gradient"],
    "ingredient_first": ["real_scene", "plain", "real_scene"],
    "problem_first":    ["plain", "gradient", "plain"],
}


# ---------------------------------------------------------------------------
# 5 Visual Themes — layout signals injected per theme
# ---------------------------------------------------------------------------

THEME_LAYOUTS = {
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
            '"[PRODUCT_UPPER]" in large ultra-bold type at top-left of frame, '
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


class PromptBuilder:
    """
    Converts structured campaign payload into high-fidelity image generation prompts.
    Built on competitor intelligence from OZiva, Woolah, Plix, Kapiva analysis
    and our own winning ad patterns.
    """

    # Cluster intent — used as a HINT only when theme doesn't specify layout
    # Theme always wins for composition/position; cluster adds content focus
    CLUSTER_CONTENT_FOCUS = {
        "product_first":    "product as undisputed hero — large, elevated, maximum breathing space, pristine clarity",
        "solution_first":   "positive outcome and transformation — hopeful, aspirational, benefit-forward visual storytelling",
        "doctor_first":     "medical authority and trust — expert credibility, clean clinical confidence, formulation expertise",
        "ingredient_first": "ingredient transparency — key Ayurvedic ingredients visually present, botanical authenticity",
        "problem_first":    "urgent relatable health concern — problem stated clearly, product positioned as the answer",
    }

    # Cluster-specific subject/person intent (who is in the scene)
    CLUSTER_SUBJECT_INTENT = {
        "product_first":    "product-focused, no person required — product IS the hero",
        "solution_first":   "optional: person experiencing positive transformation or relief, warm and hopeful expression",
        "doctor_first":     "professional Indian doctor in white coat, authoritative and reassuring, direct eye contact, NO stethoscope",
        "ingredient_first": "no human required — ingredients and product tell the story",
        "problem_first":    "middle-aged Indian person showing visible health concern, tense posture, relatable distress",
    }

    # Camera style allowed per theme — flat-lay conflicts with standing-doctor themes
    _DOCTOR_THEMES = {"KR_2D", "DR_1ST", "KR_2C"}
    _NO_DOCTOR_THEMES = {"SIGNS", "CF"}

    # Variation sets: (lighting_mood, camera_style)
    # Doctor-present themes skip flat-lay (variation index 2)
    VARIATIONS_ALL = [
        "bright high-key studio lighting, clean clinical mood, eye-level product shot",
        "warm natural sunlight, wide lifestyle scene, relatable human environment, eye-level",
        "top-down flat lay, soft natural daylight, organic botanical overhead composition",  # index 2 — doctor themes skip
        "soft diffused lighting, minimal luxury feel, eye-level premium shot",
        "high contrast dramatic lighting, bold angled shot, attention-grabbing urgency",
    ]
    VARIATIONS_DOCTOR = [
        "bright high-key studio lighting, clean clinical mood, three-quarter portrait angle",
        "warm natural light from left, open confident stance, three-quarter portrait angle",
        "soft diffused studio lighting, authoritative frontal stance, direct camera gaze",
        "dramatic side-lighting, strong confident posture, premium portrait mood",
        "natural warm lighting, relaxed yet professional stance, approachable portrait angle",
    ]

    def build_prompt_core(self, cluster_id: str) -> str:
        """Return the cluster's content focus — used as a hint, not a layout override."""
        return self.CLUSTER_CONTENT_FOCUS.get(cluster_id, "product as hero, clean focused composition")

    def build_multiple_prompts(self, payload, cluster_id, blueprint=None, strategy=None, num_variations=5):
        print("[PromptBuilder] Building prompts for cluster:", cluster_id)
        prompts = []

        # ── NMC Compliance: sanitise all claim fields before building ────────
        payload = audit_payload(dict(payload))

        product_name = payload.get("product_name", "").strip()
        if not product_name:
            raise ValueError("product_name is required and cannot be empty")
        benefits     = payload.get("benefits", [])
        solutions    = payload.get("solutions", [])
        problems     = payload.get("problems", [])
        ingredients  = payload.get("ingredients", [])
        price        = payload.get("price", "")

        # ── Theme — MASTER AUTHORITY ─────────────────────────────────────────
        theme_key  = payload.get("theme", "KR_2D")
        theme      = THEME_LAYOUTS.get(theme_key, THEME_LAYOUTS["KR_2D"])
        has_doctor = theme.get("has_doctor", False)
        no_doctor  = not has_doctor
        print(f"[PromptBuilder] Theme: {theme_key} — {theme['label']} | doctor={has_doctor}")

        from src.config.config_loader import load_emotions
        EMOTION_CONFIG = load_emotions()
        cluster_emotions = EMOTION_CONFIG.get(cluster_id, ["confidence"])
        headline_tone = strategy.get("headline_tone") if strategy else "informative"

        hook_cycle     = CLUSTER_HOOK_CYCLES.get(cluster_id, ["benefit"] * 5)
        color_options  = CLUSTER_COLORS.get(cluster_id, [("deep green", "white", "gold")])

        # Pick variation set: doctor themes get portrait-safe camera styles
        variation_pool = self.VARIATIONS_DOCTOR if has_doctor else self.VARIATIONS_ALL

        for i in range(num_variations):
            variation = variation_pool[i % len(variation_pool)]
            emotion   = random.choice(cluster_emotions)
            hook_type = hook_cycle[i % len(hook_cycle)]
            print(f"[PromptBuilder][{cluster_id}][V{i}] Theme:{theme_key} Hook:{hook_type} Emotion:{emotion}")

            components = []

            # ══ BLOCK 1: THEME — highest priority, exact pixel-level layout ═══
            # Substitute [PRODUCT] and [PRODUCT_UPPER] placeholders with actual name
            def _t(s: str) -> str:
                return s.replace("[PRODUCT]", product_name).replace("[PRODUCT_UPPER]", product_name.upper())

            components.append(f"AD LAYOUT THEME: {theme['label']}")
            components.append(f"HEADLINE: {_t(theme['headline'])}")
            components.append(f"BACKGROUND: {theme['background']}")
            components.append(f"DECORATIVE ELEMENTS: {theme['decorative']}")
            # KR_2C / DR_1ST headlines already contain product name — skip prefix to avoid duplication
            _headline_has_name = theme_key in ("KR_2C", "DR_1ST")
            _placement_prefix = "" if _headline_has_name else f"{product_name} — "
            components.append(f"PRODUCT PLACEMENT: {_placement_prefix}{theme['product_placement']}")
            components.append(f"BADGES AND HERB DISPLAY: {theme['badges']}")
            components.append(f"FOOTER: {_t(theme['footer'])}")
            components.append(f"CTA: {theme['cta']}")

            # ══ BLOCK 2: SUBJECT — derived from theme's doctor field ═══════════
            if no_doctor:
                components.append(f"SUBJECT: {theme['doctor']}")
            elif has_doctor:
                components.append(f"SUBJECT: {theme['doctor']}")
                if cluster_id == "doctor_first":
                    components.append(DOCTOR_DISCLAIMER_NOTE)

            # ══ BLOCK 3: CAMERA & LIGHTING (theme-safe variation) ════════════
            components.append(f"CAMERA & LIGHTING: {variation}")

            # ══ BLOCK 4: CLUSTER CONTENT FOCUS — defines WHAT the ad communicates ══
            # Theme controls WHERE things go; Cluster controls WHAT story is told
            components.append(f"PRIMARY CREATIVE GOAL: {self.build_prompt_core(cluster_id)}")

            # Cluster-specific content signals — these define the unique story per cluster
            if cluster_id == "product_first":
                components.append("STORY: the product IS the entire hero — isolated, elevated, glorified, large")
                components.append("MOOD: premium, aspirational, brand-forward — NO lifestyle context, NO people, product commands 100% of attention")
                components.append("VISUAL EMPHASIS: product packaging ultra-sharp and detailed, clean breathing space around it, dramatic product lighting only")

            elif cluster_id == "solution_first":
                if solutions:
                    sel_sol = random.sample(solutions, min(2, len(solutions)))
                    components.append(f"STORY: ad communicates a clear positive outcome — '{' | '.join(sel_sol)}' — shown as the central message")
                components.append("MOOD: hopeful, warm, transformative — viewer sees a better future through this product")
                components.append("VISUAL EMPHASIS: positive outcome text is large and prominent, product is the solution vehicle, aspirational tone")

            elif cluster_id == "doctor_first":
                if has_doctor:
                    components.append("STORY: expert authority validates this product — formulation credibility is the entire message")
                    components.append("MOOD: clinical trust, medical authority, expert confidence — viewer feels safe choosing this product")
                    components.append("TEXT OVERLAY: 'Formulated by Dr. Bimal Chhajer' or 'Expert-formulated for heart health' — authority signal is primary")
                else:
                    # No-doctor theme (CF/SIGNS) but doctor_first cluster — shift to brand authority
                    components.append("STORY: brand authority and scientific credibility — expert formulation conveyed through design language, not portrait")
                    components.append("MOOD: premium, science-backed, authoritative — clinical precision in the visual")
                    components.append("TEXT OVERLAY: 'Expert-formulated' or 'Clinically researched ingredients' — authority through text, not person")

            elif cluster_id == "ingredient_first":
                if ingredients:
                    sel_ings = random.sample(ingredients, min(3, len(ingredients)))
                    components.append(f"STORY: the ingredients ARE the hero — '{', '.join(sel_ings)}' shown as raw botanical elements alongside the product")
                components.append("MOOD: natural, transparent, scientifically curious — viewer can see exactly what goes into the product")
                components.append("VISUAL EMPHASIS: raw herbs, botanical elements, or ingredient close-ups integrated into the composition organically")

            elif cluster_id == "problem_first":
                if problems:
                    prob = random.choice(problems)
                    components.append(f"STORY: starts with a relatable health problem — '{prob}' — product is clearly the answer")
                    components.append(f"TEXT OVERLAY: '{prob}' in bold prominent text — problem stated directly, product shown as the solution")
                components.append("MOOD: urgent and emotionally honest problem → product as clear relief — viewer recognizes their own struggle")
                components.append("VISUAL EMPHASIS: problem text is large and prominent, product positioned as the direct answer to that specific problem")

            # Product name carried by theme HEADLINE and PRODUCT PLACEMENT fields above
            # No separate PRODUCT block needed — avoids duplication

            # ══ BLOCK 6: INGREDIENT BENEFIT CALLOUTS ══════════════════════════
            if ingredients:
                known_ings = [ing for ing in ingredients if ing in INGREDIENT_BENEFITS]
                if not known_ings:
                    known_ings = [
                        kb for kb in INGREDIENT_BENEFITS
                        if any(kb.lower() in ing.lower() or ing.lower() in kb.lower() for ing in ingredients)
                    ]
                sample_ings = random.sample(known_ings, min(3, len(known_ings))) if known_ings else []
                if sample_ings:
                    callouts = [random.choice(INGREDIENT_BENEFITS[ing]) for ing in sample_ings]
                    components.append(f"INGREDIENT CALLOUTS (text overlay badges): {' | '.join(callouts)}")

            # ══ BLOCK 7: HOOK & EMOTION ════════════════════════════════════════
            hook_signals = {
                "fear":      "fear-based hook — urgent warning, alarming visual anchor, medical authority tone",
                "benefit":   "benefit-led hook — clear positive outcome promise, aspirational visual",
                "curiosity": "curiosity hook — open question, knowledge gap, viewer wants to know more",
                "authority": "authority hook — scientific credibility, expert validation, trust signals",
                "problem":   "problem identification hook — relatable pain point, viewer sees themselves in it",
                "relief":    "relief hook — stress lifting, positive transformation, hopeful resolution",
                "trust":     "trust hook — clean professional aesthetic, credibility proof elements",
            }
            components.append(f"HOOK: {hook_signals.get(hook_type, 'benefit-led hook')}")
            if not no_doctor:  # skip facial expression for no-human themes
                expression = EMOTION_EXPRESSIONS.get(emotion, f"subject expressing {emotion}")
                components.append(f"EXPRESSION: {expression}")

            # ══ BLOCK 8: COLOR ════════════════════════════════════════════════
            color_pick = random.choice(color_options)
            primary, secondary, accent = color_pick
            components.append(f"COLOR: {primary} primary, {secondary} secondary, {accent} accent — high contrast, clear hierarchy")

            # ══ BLOCK 9: PRICE ════════════════════════════════════════════════
            if price and theme_key != "SIGNS":
                components.append(f"PRICE DISPLAY: {price}")

            # ══ BLOCK 10: TYPOGRAPHY ══════════════════════════════════════════
            CLUSTER_FONT_MAP = {
                "product_first":    "premium",
                "solution_first":   "calm",
                "doctor_first":     "trust",
                "ingredient_first": "natural",
                "problem_first":    "panic",
            }
            preset_name = CLUSTER_FONT_MAP.get(cluster_id, "premium")
            if cluster_id == "problem_first" and hook_type == "benefit":
                preset_name = "calm"   # resolution pivot
            if hook_type == "authority" and cluster_id != "doctor_first":
                preset_name = "trust"
            font_preset = next((p for p in FONT_PRESETS if p["name"] == preset_name), FONT_PRESETS[0])
            print("[FontPreset]", font_preset["name"])
            components.append(f"TYPOGRAPHY: headline — {font_preset['headline']} | supporting — {font_preset['sub']}")
            components.append("clean typography hierarchy, high readability, low text density, text never overwhelms the visual")

            # Product name overlay removed — product name appears once in BLOCK 5 only

            # ══ BLOCK 12: HEADLINE TONE ═══════════════════════════════════════
            components.append(f"HEADLINE TONE: {headline_tone}, emotionally resonant, concise and punchy")

            # ══ BLOCK 13: PRODUCT PRESERVATION (CRITICAL) ════════════════════
            components.extend([
                "CRITICAL: preserve exact product packaging, label, logo, and design — do NOT alter, modify, replace, reimagine, or reinterpret the product in any way",
                "product must appear exactly as provided — no changes to shape, color, text, or branding",
            ])

            # ══ BLOCK 14: QUALITY ═════════════════════════════════════════════
            components.extend([
                "clear visual hierarchy, single focal point, no clutter",
                "clean professional advertisement composition, 1:1 square format",
                "8k resolution, ultra realistic, photographic quality",
            ])

            # Join and clean up
            prompt = ", ".join(c for c in components if c.strip())
            while ", ," in prompt:
                prompt = prompt.replace(", ,", ",")

            prompts.append(sanitize_prompt(prompt))
            print(f"[PromptBuilder] Variation {i} built ({len(prompt)} chars)")

        return prompts
