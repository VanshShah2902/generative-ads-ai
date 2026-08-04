"""
NMC (National Medical Commission) Compliance Filter
====================================================
Ensures all generated ad prompts, headlines, and benefit claims comply with
NMC advertising guidelines for health/medical products in India.

Key NMC rules enforced:
  1. No "cure" or "treat" language — use "supports", "helps maintain"
  2. No guaranteed results — avoid "will", "guaranteed", "proven to heal"
  3. No disease-diagnosis or prescription claims
  4. No absolute superlatives for health outcomes — "100% effective", "clinically proven to cure"
  5. No fear-based claims implying disease severity (modify to informational)
  6. Doctor endorsements must not imply personal prescription — must say "formulated by"
  7. All health benefits must be qualified — "may help", "supports", "helps maintain"
  8. No before/after claims implying medical treatment
  9. No patient testimonials implying cure
 10. Price/discount claims allowed but must not imply medical value

References:
  - NMC Professional Conduct Regulations 2023
  - ASCI (Advertising Standards Council of India) health guidelines
  - Drugs & Magic Remedies (Objectionable Advertisements) Act 1954
"""

import re

# ---------------------------------------------------------------------------
# Banned phrases → safe replacements
# Applied to prompts, headlines, and subheadlines
# ---------------------------------------------------------------------------

NMC_REPLACEMENTS = [
    # Cure / treat language
    (r"\bcures?\b",              "supports management of"),
    (r"\btreats?\b",             "helps with"),
    (r"\bheals?\b",              "helps support"),
    (r"\beliminate[sd]?\b",      "helps reduce"),
    (r"\breverse[sd]?\b",        "helps manage"),
    (r"\bremove[sd]?\b",         "helps reduce"),
    (r"\bfight[sd]?\b",          "helps manage"),
    (r"\bovercome[sd]?\b",       "helps with"),

    # Guarantee / absolute promise language
    (r"\bguaranteed?\b",         "designed to"),
    (r"\b100%\s+effective\b",    "effective for many users"),
    (r"\bproven to cure\b",      "formulated to support"),
    (r"\bproven to treat\b",     "formulated to help"),
    (r"\bclinically proven to cure\b",  "clinically studied"),
    (r"\bclinically proven to treat\b", "clinically studied"),
    (r"\bwill cure\b",           "may help support"),
    (r"\bwill treat\b",          "may help with"),
    (r"\bwill heal\b",           "may help support"),
    (r"\bwill eliminate\b",      "may help reduce"),
    (r"\binstant relief\b",      "supports comfort"),
    (r"\bpermanent cure\b",      "long-term support"),

    # Disease-diagnosis / prescription claims
    (r"\bprescribed by\b",       "formulated with guidance from"),
    (r"\bmedically prescribed\b","formulated by"),
    (r"\bdoctor prescribed\b",   "doctor formulated"),
    (r"\bmedically proven\b",    "research-backed"),

    # Fear / severity amplification
    (r"\bdangerous levels of\b", "elevated levels of"),
    (r"\blife-threatening\b",    "concerning"),
    (r"\bdeadly\b",              "serious"),

    # Before-after medical treatment claims
    (r"\bbefore[- ]after\b",     "wellness journey"),
]

# Phrases that should be stripped entirely (too risky to replace)
NMC_BANNED_ABSOLUTE = [
    "cures cancer",
    "cures diabetes",
    "cures heart disease",
    "cures hypertension",
    "cures thyroid",
    "treats cancer",
    "treats diabetes",
    "prevents heart attack",
    "reverses diabetes",
    "reverses heart disease",
    "miracle cure",
    "miracle treatment",
    "100% cure",
    "permanent weight loss",
    "guaranteed weight loss",
]

# ---------------------------------------------------------------------------
# Benefit / claim sanitiser
# Applied to benefits[], solutions[], problems[] lists before they hit the prompt
# ---------------------------------------------------------------------------

BENEFIT_REPLACEMENTS = [
    # Replace unqualified direct claims with NMC-safe qualified language
    (r"^(supports?)\b",                     r"\1"),           # "supports" is already safe
    (r"^(helps? maintain)\b",               r"\1"),           # already safe
    (r"^(helps? support)\b",                r"\1"),           # already safe
    (r"^(may help)\b",                      r"\1"),           # already safe
    (r"^(promotes?)\b",                     r"\1"),           # "promotes" is safe
    # Unqualified claims → add "Supports"
    (r"^(lowers?)\s",                       r"Helps maintain healthy "),
    (r"^(reduces?)\s",                      r"Helps reduce "),
    (r"^(controls?)\s",                     r"Helps manage "),
    (r"^(improves?)\s",                     r"Helps improve "),
    (r"^(boosts?)\s",                       r"Helps boost "),
    (r"^(increases?)\s",                    r"Helps increase "),
    (r"^(decreases?)\s",                    r"Helps decrease "),
    (r"^(prevents?)\s",                     r"Helps support prevention of "),
    (r"^(cures?)\s",                        r"Helps manage "),
    (r"^(treats?)\s",                       r"Helps with "),
    (r"^(heals?)\s",                        r"Helps support "),
    (r"^(eliminates?)\s",                   r"Helps reduce "),
    (r"^(reverses?)\s",                     r"Helps manage "),
    (r"^(fights?)\s",                       r"Helps manage "),
]


def _apply_replacements(text: str, replacements: list) -> str:
    """Apply a list of (pattern, replacement) tuples to text."""
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def sanitise_claim(claim: str) -> str:
    """
    Make a single benefit/solution/problem string NMC-compliant.
    Applies qualified language prefix if the claim starts with an unqualified verb.
    """
    claim = claim.strip()
    if not claim:
        return claim
    return _apply_replacements(claim, BENEFIT_REPLACEMENTS)


def sanitise_claims_list(claims: list) -> list:
    """Apply NMC sanitisation to an entire list of benefit/solution/problem strings."""
    return [sanitise_claim(c) for c in claims]


def sanitise_prompt(prompt: str) -> str:
    """
    Apply full NMC compliance filter to a completed image generation prompt.
    Removes/replaces banned phrases; strips absolute disease-cure claims.
    """
    # 1. Strip absolutely banned phrases
    for phrase in NMC_BANNED_ABSOLUTE:
        prompt = re.sub(re.escape(phrase), "", prompt, flags=re.IGNORECASE)

    # 2. Apply contextual replacements
    prompt = _apply_replacements(prompt, NMC_REPLACEMENTS)

    # 3. Normalise whitespace artefacts left by removals
    prompt = re.sub(r",\s*,", ",", prompt)
    prompt = re.sub(r"\s{2,}", " ", prompt)

    return prompt.strip()


def sanitise_headline(headline: str) -> str:
    """
    Apply NMC compliance to ad copy headline/subheadline strings.
    Same rules as prompt sanitisation.
    """
    headline = _apply_replacements(headline, NMC_REPLACEMENTS)
    for phrase in NMC_BANNED_ABSOLUTE:
        headline = re.sub(re.escape(phrase), "", headline, flags=re.IGNORECASE)
    return headline.strip()


def audit_payload(payload: dict) -> dict:
    """
    Sanitise the entire campaign payload in-place before it reaches the prompt builder.
    Modifies benefits, solutions, problems lists to be NMC-compliant.

    Returns the sanitised payload (also mutates in place).
    """
    for field in ("benefits", "solutions", "problems"):
        if field in payload and isinstance(payload[field], list):
            original = payload[field]
            sanitised = sanitise_claims_list(original)
            if sanitised != original:
                changed = [(o, s) for o, s in zip(original, sanitised) if o != s]
                for orig, safe in changed:
                    print(f"[NMC] '{orig}' → '{safe}'")
            payload[field] = sanitised
    return payload


# ---------------------------------------------------------------------------
# NMC compliance notes — injected into doctor_first prompts
# ---------------------------------------------------------------------------

DOCTOR_DISCLAIMER_NOTE = (
    "doctor image represents formulation expertise, not personal prescription endorsement"
)
