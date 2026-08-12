"""
Ad Variant Generator — Gemini-powered ad editing with batch queue.

Run:  streamlit run dashboard.py
"""

import os
import sys
import json
import time
import base64
from datetime import datetime
from io import BytesIO

import streamlit as st
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

if "GEMINI_API_KEY" not in os.environ:
    try:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

from google import genai
from google.genai import types

from src.pipeline.reference_analyzer import analyze_reference
from src.pipeline.ai_compositor import (
    generate_variant, generate_with_verification,
    COLOR_THEMES, FONT_PRESETS, ASPECT_RATIOS,
    _build_edit_prompt,
)

LANGUAGES = {
    "English": "en", "Hindi": "hi", "Marathi": "mr", "Bengali": "bn",
    "Gujarati": "gu", "Tamil": "ta", "Telugu": "te", "Kannada": "kn",
    "Punjabi": "pa", "Malayalam": "ml",
}


def translate_texts(texts: dict, source_lang: str, target_lang: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    items = "\n".join(f"{k}: {v}" for k, v in texts.items())
    prompt = (
        f"Translate the following advertisement text fields from {source_lang} to {target_lang}.\n"
        f"Keep the translations natural and suitable for advertising — short, punchy, compelling.\n"
        f"Return ONLY a JSON object with the same keys and translated values. No explanation.\n\n"
        f"{items}"
    )
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


OUTPUT_DIR = os.path.join(BASE_DIR, "tests", "variant_results")
BATCH_DIR = os.path.join(OUTPUT_DIR, "batches")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(BATCH_DIR, exist_ok=True)

# ── Page config ──
st.set_page_config(
    page_title="Ad Variant Generator",
    page_icon="https://img.icons8.com/fluency/48/design.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
# Streamlit uses [data-testid="stAppViewContainer"] with theme classes.
# We use CSS variables so both light and dark themes work automatically.
st.markdown("""
<style>
    /* Global */
    .block-container { padding: 1.5rem 2rem 3rem; max-width: 1400px; }

    /* Header — gradient works on both themes */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem;
        color: white; position: relative; overflow: hidden;
    }
    .main-header::after {
        content: ''; position: absolute; top: -50%; right: -20%; width: 300px; height: 300px;
        background: rgba(255,255,255,0.08); border-radius: 50%;
    }
    .main-header h1 { font-size: 1.8rem; font-weight: 700; margin: 0; color: white !important; }
    .main-header p { font-size: 0.95rem; opacity: 0.9; margin: 0.3rem 0 0; color: white !important; }

    /* Queue badge */
    .queue-badge {
        display: inline-block; padding: 2px 8px; border-radius: 6px;
        font-size: 0.75rem; font-weight: 600; margin-right: 6px;
    }
    .badge-color { background: #dbeafe; color: #1e40af; }
    .badge-font { background: #fce7f3; color: #9d174d; }
    .badge-text { background: #d1fae5; color: #065f46; }
    .badge-ratio { background: #fef3c7; color: #92400e; }
    .badge-doctor { background: #fee2e2; color: #991b1b; }
    .badge-combo { background: #ede9fe; color: #5b21b6; }
    .badge-translate { background: #cffafe; color: #155e75; }

    /* Color swatch */
    .color-swatch { display: flex; gap: 3px; margin-bottom: 6px; }
    .color-swatch div {
        width: 32px; height: 32px; border-radius: 8px;
        border: 2px solid transparent;
    }

    /* Image grid */
    .stImage > img { border-radius: 10px; }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; font-weight: 500; font-size: 0.88rem;
        padding: 0.5rem 1rem;
    }

    /* Buttons */
    .stButton > button { border-radius: 8px; font-weight: 500; }

    /* Batch/submit status cards — use semi-transparent backgrounds */
    .batch-card {
        border-radius: 12px; padding: 1.2rem 1.5rem; margin: 1rem 0;
    }
    .batch-success {
        background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .batch-success h3 { margin: 0 0 0.5rem; color: #10b981; font-size: 1.1rem; }
    .batch-success p { margin: 0; }
    .batch-pending {
        background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .batch-pending h3 { margin: 0 0 0.5rem; color: #3b82f6; font-size: 1.1rem; }
    .batch-pending p { margin: 0; }
    .batch-submit {
        background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .batch-submit h3 { margin: 0 0 0.5rem; color: #f59e0b; font-size: 1.1rem; }
    .batch-submit p { margin: 0; }

    /* Hide default streamlit chrome */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ──
for key, default in {
    "analysis": None, "ref_path": None, "total_cost": 0.0, "gen_count": 0,
    "queue": [], "batch_id": None, "batch_status": None, "batch_jobs": [],
    "queue_counter": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Header ──
st.markdown("""
<div class="main-header">
    <h1>Ad Variant Generator</h1>
    <p>Upload a reference ad, pick your changes, and generate production-ready variants with AI</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ──
with st.sidebar:
    st.markdown("### Upload Reference")
    uploaded = st.file_uploader("Drop an ad image here", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")

    # Show existing images only if any exist locally
    test_images = []
    for d in ["tests/generation_results", "assets"]:
        full = os.path.join(BASE_DIR, d)
        if os.path.isdir(full):
            for f in os.listdir(full):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    test_images.append(os.path.join(full, f))

    existing_choice = None
    if test_images:
        names = ["Select existing..."] + [os.path.basename(p) for p in test_images]
        pick = st.selectbox("Or pick an existing image", names, label_visibility="collapsed")
        if pick != "Select existing...":
            existing_choice = test_images[names.index(pick) - 1]

    st.markdown("---")

    # Analysis
    st.markdown("### Analysis")
    analysis_files = sorted(
        [f for f in os.listdir(OUTPUT_DIR) if f.startswith("analysis_") and f.endswith(".json")],
        reverse=True,
    )
    use_cached = st.checkbox("Use cached analysis", value=bool(analysis_files))
    cached_path = None
    if use_cached and analysis_files:
        picked_analysis = st.selectbox("Cached file", analysis_files, label_visibility="collapsed")
        cached_path = os.path.join(OUTPUT_DIR, picked_analysis)

    run_analysis = st.button("Analyze Reference", type="primary", use_container_width=True, help="Costs ~₹0.03")

    st.markdown("---")

    # Queue
    st.markdown("### Queue")
    queue = st.session_state.queue
    if queue:
        badge_map = {"color": "badge-color", "font": "badge-font", "text": "badge-text",
                     "ratio": "badge-ratio", "doctor": "badge-doctor", "combo": "badge-combo",
                     "translate": "badge-translate"}
        to_remove = None
        for i, item in enumerate(queue):
            uid, cat, label, _, item_ref, _ = item
            ref_name = os.path.basename(item_ref) if item_ref else "?"
            badge_cls = badge_map.get(cat, "badge-combo")
            col_item, col_rm = st.columns([5, 1])
            with col_item:
                st.markdown(f'<span class="queue-badge {badge_cls}">{cat}</span> {label}', unsafe_allow_html=True)
                st.caption(ref_name)
            if col_rm.button("✕", key=f"rm_{uid}"):
                to_remove = uid
        if to_remove is not None:
            st.session_state.queue = [q for q in st.session_state.queue if q[0] != to_remove]
            st.rerun()

        n_items = len(queue)
        est_batch = n_items * 3.50
        st.caption(f"**{n_items}** items · ~₹{est_batch:.0f} batch")

        if st.button("Clear Queue", use_container_width=True):
            st.session_state.queue = []
            st.rerun()
    else:
        st.caption("Empty — add items from the tabs below.")

    st.markdown("---")

    # Stats
    st.markdown("### Session Stats")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Generated", st.session_state.gen_count)
    col_s2.metric("Spent", f"₹{st.session_state.total_cost:.1f}")


# ── Resolve reference image ──
ref_image_path = None
if uploaded:
    ref_image_path = os.path.join(OUTPUT_DIR, f"uploaded_{uploaded.name}")
    with open(ref_image_path, "wb") as f:
        f.write(uploaded.getvalue())
elif existing_choice:
    ref_image_path = existing_choice

# ── Run analysis ──
if run_analysis and ref_image_path:
    if use_cached and cached_path and os.path.exists(cached_path):
        with open(cached_path, "r", encoding="utf-8") as f:
            st.session_state.analysis = json.load(f)
        st.session_state.ref_path = ref_image_path
        st.toast("Loaded cached analysis")
    else:
        with st.sidebar, st.spinner("Analyzing..."):
            analysis_result = analyze_reference(ref_image_path)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(OUTPUT_DIR, f"analysis_{ts}.json")
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            st.session_state.analysis = analysis_result
            st.session_state.ref_path = ref_image_path
            st.session_state.total_cost += 0.03
        st.toast("Analysis complete!")

analysis = st.session_state.analysis
ref_path = st.session_state.ref_path or ref_image_path


# ── Reference + Analysis display ──
if ref_path and os.path.exists(ref_path):
    col_ref, col_info = st.columns([1, 1], gap="large")
    with col_ref:
        st.subheader("Reference Ad")
        st.image(ref_path, use_container_width=True)

    with col_info:
        if analysis:
            st.subheader("Detected Content")

            fields = [
                ("Headline", analysis.get("headline")),
                ("Subheadline", analysis.get("subheadline")),
                ("Price", analysis.get("price")),
                ("CTA", analysis.get("cta_text")),
                ("Offer", analysis.get("offer_text")),
            ]
            for label, val in fields:
                if val:
                    st.markdown(f"**{label}:** {val}")

            mc1, mc2 = st.columns(2)
            mc1.metric("Doctor photo", "Yes" if analysis.get("has_doctor_photo") else "No")
            mc2.metric("Layout", analysis.get("layout_type", "—"))

            palette = analysis.get("color_palette", {})
            if palette:
                pcols = st.columns(len(palette))
                for i, (k, v) in enumerate(palette.items()):
                    if v:
                        pcols[i].color_picker(k.title(), v, disabled=True, key=f"pal_{k}")

            extras = analysis.get("extra_texts", [])
            if extras:
                with st.expander(f"Other text ({len(extras)} items)"):
                    for t in extras:
                        st.write(f"· {t}")
        else:
            st.info("Upload an image and click **Analyze Reference** in the sidebar.")

if not analysis:
    st.stop()


# ── Helper: add to queue ──
def add_to_queue(items):
    for cat, label, changes in items:
        uid = st.session_state.queue_counter
        st.session_state.queue_counter += 1
        st.session_state.queue.append((uid, cat, label, changes, st.session_state.ref_path, st.session_state.analysis))
    st.toast(f"Added {len(items)} item(s) to queue")


# ── Variant Controls ──
st.subheader("Variant Options")

tab_color, tab_font, tab_text, tab_ratio, tab_doctor, tab_combo = st.tabs(
    ["Color", "Font", "Text & Translate", "Aspect Ratio", "Doctor", "Combo"]
)

# ── Color Tab ──
with tab_color:
    selected_colors = []
    cols_per_row = 4
    theme_items = list(COLOR_THEMES.items())
    for row_start in range(0, len(theme_items), cols_per_row):
        row = theme_items[row_start:row_start + cols_per_row]
        color_cols = st.columns(cols_per_row)
        for i, (name, theme) in enumerate(row):
            with color_cols[i]:
                st.markdown(
                    f'<div class="color-swatch">'
                    f'<div style="background:{theme["primary"]};"></div>'
                    f'<div style="background:{theme["secondary"]};"></div>'
                    f'</div>', unsafe_allow_html=True)
                if st.checkbox(name.replace("_", " ").title(), key=f"color_{name}"):
                    selected_colors.append(name)
    c1, c2 = st.columns(2)
    if selected_colors:
        if c1.button(f"Add {len(selected_colors)} selected", key="q_color", type="primary", use_container_width=True):
            add_to_queue([("color", n, {"color": n}) for n in selected_colors])
            st.rerun()
    if c2.button(f"Add all {len(COLOR_THEMES)}", key="q_color_all", use_container_width=True):
        add_to_queue([("color", n, {"color": n}) for n in COLOR_THEMES])
        st.rerun()

# ── Font Tab ──
with tab_font:
    selected_fonts = []
    for preset, info in FONT_PRESETS.items():
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f'<span style="{info["css"]} font-size:1.2em;">{info["example"]}</span><br>'
                f'<span style="color:#6b7280;font-size:0.8em;">{preset} — {info["desc"]}</span>',
                unsafe_allow_html=True)
        with c2:
            if st.checkbox("Add", key=f"font_{preset}"):
                selected_fonts.append(preset)
        st.markdown("<div style='border-bottom:1px solid #f3f4f6;margin:4px 0;'></div>", unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    if selected_fonts:
        if f1.button(f"Add {len(selected_fonts)} selected", key="q_font", type="primary", use_container_width=True):
            add_to_queue([("font", p, {"font": p}) for p in selected_fonts])
            st.rerun()
    if f2.button(f"Add all {len(FONT_PRESETS)}", key="q_font_all", use_container_width=True):
        add_to_queue([("font", p, {"font": p}) for p in FONT_PRESETS])
        st.rerun()

# ── Text & Translate Tab ──
with tab_text:
    text_mode = st.radio("Mode", ["Edit Text", "Translate"], horizontal=True, key="text_mode", label_visibility="collapsed")

    text_fields = [
        ("headline", "Headline", analysis.get("headline", "")),
        ("subheadline", "Subheadline", analysis.get("subheadline", "") or ""),
        ("price", "Price", analysis.get("price", "") or ""),
        ("cta_text", "CTA Button", analysis.get("cta_text", "") or ""),
        ("offer_text", "Offer Badge", analysis.get("offer_text", "") or ""),
    ]
    extra_texts = analysis.get("extra_texts", [])

    if text_mode == "Edit Text":
        overrides = {}
        for field_key, label, current in text_fields:
            if not current:
                continue
            new_val = st.text_input(label, value=current, key=f"text_{field_key}")
            if new_val != current:
                overrides[field_key] = new_val
        if overrides:
            if st.button("Add text changes", key="q_text", type="primary", use_container_width=True):
                add_to_queue([("text", "custom", {"text": overrides})])
                st.rerun()

    else:
        lang_names = list(LANGUAGES.keys())
        c1, c2 = st.columns(2)
        source_lang = c1.selectbox("From", lang_names, index=0, key="src_lang")
        target_options = [l for l in lang_names if l != source_lang]
        target_lang = c2.selectbox("To", target_options, key="tgt_lang")

        selected_for_translation = {}
        for field_key, label, current in text_fields:
            if not current:
                continue
            if st.checkbox(f"**{label}**: {current}", key=f"tr_{field_key}", value=(field_key != "price")):
                selected_for_translation[field_key] = current

        if extra_texts:
            with st.expander("Other ad texts"):
                for i, txt in enumerate(extra_texts):
                    if st.checkbox(txt, key=f"tr_extra_{i}"):
                        selected_for_translation[f"extra_{i}"] = txt

        if selected_for_translation:
            st.caption(f"{len(selected_for_translation)} fields · ~₹0.03")
            if st.button(f"Translate to {target_lang} & add", key="q_translate", type="primary", use_container_width=True):
                with st.spinner(f"Translating to {target_lang}..."):
                    try:
                        translated = translate_texts(selected_for_translation, source_lang, target_lang)
                        st.session_state.total_cost += 0.03
                        for k, v in translated.items():
                            st.write(f"**{k}**: {selected_for_translation.get(k, '')} → **{v}**")
                        text_overrides = {}
                        extra_overrides = []
                        for k, v in translated.items():
                            if k.startswith("extra_"):
                                extra_overrides.append(v)
                            else:
                                text_overrides[k] = v
                        changes = {"text": text_overrides} if text_overrides else {}
                        if extra_overrides:
                            changes["translated_extras"] = extra_overrides
                        add_to_queue([("translate", target_lang, changes)])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Translation failed: {e}")

# ── Ratio Tab ──
with tab_ratio:
    selected_ratios = []
    ratio_cols = st.columns(4)
    ratio_icons = {"1:1": "⬜", "9:16": "📱", "4:5": "📷", "16:9": "🖥️"}
    for i, (ratio_name, (w, h)) in enumerate(ASPECT_RATIOS.items()):
        with ratio_cols[i]:
            icon = ratio_icons.get(ratio_name, "📐")
            st.markdown(f"### {icon} {ratio_name}")
            st.caption(f"{w}×{h}")
            if st.checkbox("Select", key=f"ratio_{ratio_name}"):
                selected_ratios.append(ratio_name)
    r1, r2 = st.columns(2)
    if selected_ratios:
        if r1.button(f"Add {len(selected_ratios)} selected", key="q_ratio", type="primary", use_container_width=True):
            add_to_queue([("ratio", r, {"ratio": r}) for r in selected_ratios])
            st.rerun()
    if r2.button("Add all 4", key="q_ratio_all", use_container_width=True):
        add_to_queue([("ratio", r, {"ratio": r}) for r in ASPECT_RATIOS])
        st.rerun()

# ── Doctor Tab ──
with tab_doctor:
    has_doc = analysis.get("has_doctor_photo", False)
    if has_doc:
        doc_desc = analysis.get("doctor_photo_description", "")
        if doc_desc:
            st.info(f"Detected: {doc_desc}")
        st.write("Remove the standalone doctor photo. The small logo on the product box stays.")
        if st.button("Add doctor removal", key="q_doctor", type="primary", use_container_width=True):
            add_to_queue([("doctor", "no_doctor", {"remove_doctor": True})])
            st.rerun()
    else:
        st.info("No standalone doctor photo detected in this ad.")

# ── Combo Tab ──
with tab_combo:
    st.caption("Mix and match multiple changes in a single generation")
    cc1, cc2 = st.columns(2)
    combo_color = cc1.selectbox("Color", ["—"] + list(COLOR_THEMES.keys()))
    combo_font = cc2.selectbox("Font", ["—"] + list(FONT_PRESETS.keys()))
    cc3, cc4 = st.columns(2)
    combo_ratio = cc3.selectbox("Ratio", ["—"] + list(ASPECT_RATIOS.keys()))
    combo_no_doc = cc4.checkbox("Remove doctor", key="combo_doc")

    lang_names = list(LANGUAGES.keys())
    combo_lang = st.selectbox("Translate to", ["—"] + lang_names, key="combo_lang")
    combo_translate_fields = {}
    if combo_lang != "—":
        combo_src_lang = st.selectbox("Source language", lang_names, index=0, key="combo_src_lang")
        for field_key, label, current in [
            ("headline", "Headline", analysis.get("headline", "")),
            ("subheadline", "Subheadline", analysis.get("subheadline", "") or ""),
            ("price", "Price", analysis.get("price", "") or ""),
            ("cta_text", "CTA Button", analysis.get("cta_text", "") or ""),
            ("offer_text", "Offer Badge", analysis.get("offer_text", "") or ""),
        ]:
            if not current:
                continue
            if st.checkbox(f"{label}: {current}", key=f"combo_tr_{field_key}", value=(field_key != "price")):
                combo_translate_fields[field_key] = current

        combo_extra_texts = analysis.get("extra_texts", [])
        if combo_extra_texts:
            with st.expander("Other ad texts"):
                for i, txt in enumerate(combo_extra_texts):
                    if st.checkbox(txt, key=f"combo_tr_extra_{i}"):
                        combo_translate_fields[f"extra_{i}"] = txt

    if st.button("Add combo to queue", key="q_combo", type="primary", use_container_width=True):
        combo_changes = {}
        label_parts = []
        if combo_color != "—":
            combo_changes["color"] = combo_color
            label_parts.append(combo_color)
        if combo_font != "—":
            combo_changes["font"] = combo_font
            label_parts.append(combo_font)
        if combo_ratio != "—":
            combo_changes["ratio"] = combo_ratio
            label_parts.append(combo_ratio)
        if combo_no_doc:
            combo_changes["remove_doctor"] = True
            label_parts.append("no_doctor")

        if combo_lang != "—" and combo_translate_fields:
            with st.spinner(f"Translating to {combo_lang}..."):
                try:
                    translated = translate_texts(combo_translate_fields, combo_src_lang, combo_lang)
                    st.session_state.total_cost += 0.03
                    text_overrides = {}
                    extra_overrides = []
                    for k, v in translated.items():
                        if k.startswith("extra_"):
                            extra_overrides.append(v)
                        else:
                            text_overrides[k] = v
                    if text_overrides:
                        combo_changes["text"] = text_overrides
                    if extra_overrides:
                        combo_changes["translated_extras"] = extra_overrides
                    label_parts.append(combo_lang)
                except Exception as e:
                    st.error(f"Translation failed: {e}")

        if combo_changes:
            add_to_queue([("combo", " + ".join(label_parts), combo_changes)])
            st.rerun()
        else:
            st.warning("Select at least one change.")


# ── Batch Submit ──
queue = st.session_state.queue
batch_id = st.session_state.batch_id

if queue and not batch_id:
    st.markdown("---")
    n = len(queue)
    est_batch = n * 3.50

    st.markdown(f"""
    <div class="batch-card batch-submit">
        <h3>Ready to generate</h3>
        <p><strong>{n} variant(s)</strong> · Estimated: <strong>~₹{est_batch:.0f}</strong> (batch) · Processing: 5–15 min</p>
    </div>
    """, unsafe_allow_html=True)

    verify_enabled = st.checkbox("Auto-verify & fix (adds ~₹0.03 + retry cost per issue)", value=False, key="verify_toggle")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("🚀 Submit Batch", type="primary", use_container_width=True):
            ref_cache = {}
            inline_requests = []
            for uid, cat, label, changes, item_ref, item_analysis in queue:
                if item_ref not in ref_cache:
                    with open(item_ref, "rb") as f:
                        ref_cache[item_ref] = base64.b64encode(f.read()).decode()
                img_b64 = ref_cache[item_ref]
                prompt = _build_edit_prompt(item_analysis, changes)
                inline_requests.append({
                    "contents": [{"parts": [
                        {"text": "REFERENCE AD IMAGE — edit this image according to the instructions:"},
                        {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                        {"text": prompt},
                    ], "role": "user"}],
                    "config": {
                        "response_modalities": ["IMAGE", "TEXT"],
                        "safety_settings": [
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                        ],
                    },
                })

            with st.spinner("Submitting batch..."):
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                batch_job = client.batches.create(
                    model="models/gemini-3.1-flash-image",
                    src=inline_requests,
                    config={"display_name": f"ad-variants-{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
                )

            st.session_state.batch_id = batch_job.name
            st.session_state.batch_status = str(batch_job.state)
            st.session_state.batch_jobs = [(cat, label, changes) for uid, cat, label, changes, _, _ in queue]
            st.session_state.batch_submit_time = time.time()
            st.session_state.queue = []
            st.rerun()

    with b2:
        if st.button("⚡ Real-time (instant)", use_container_width=True):
            st.session_state.confirmed_jobs = [(cat, label, changes, item_ref, item_analysis) for uid, cat, label, changes, item_ref, item_analysis in queue]
            st.session_state.queue = []
            st.rerun()


# ── Batch Status ──
if batch_id:
    st.markdown("---")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    try:
        batch_job = client.batches.get(name=batch_id)
        state = str(batch_job.state)
        elapsed = time.time() - st.session_state.get("batch_submit_time", time.time())

        if "SUCCEEDED" in state:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_out_dir = os.path.join(BATCH_DIR, ts)
            os.makedirs(batch_out_dir, exist_ok=True)

            results = []
            total_in = total_out = 0

            for i, resp in enumerate(batch_job.dest.inlined_responses):
                cat, label, changes = st.session_state.batch_jobs[i]
                response = resp.response
                usage = response.usage_metadata
                inp_t = usage.prompt_token_count if usage else 0
                out_t = usage.candidates_token_count if usage else 0
                total_in += inp_t
                total_out += out_t

                candidate = response.candidates[0] if response.candidates else None
                parts = getattr(getattr(candidate, "content", None), "parts", None) if candidate else None

                if parts:
                    for part in parts:
                        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.mime_type.startswith("image/"):
                            img_bytes = part.inline_data.data
                            save_name = f"{cat}_{label}.png"
                            with open(os.path.join(batch_out_dir, save_name), "wb") as f:
                                f.write(img_bytes)
                            img = Image.open(BytesIO(img_bytes))
                            results.append((cat, label, img, img_bytes, save_name, inp_t, out_t))
                            st.session_state.gen_count += 1
                            break
                    else:
                        results.append((cat, label, None, None, None, inp_t, out_t))
                else:
                    results.append((cat, label, None, None, None, inp_t, out_t))

            cost_usd = (total_in * 0.05 / 1_000_000) + (total_out * 30 / 1_000_000)
            cost_inr = cost_usd * 84
            st.session_state.total_cost += cost_inr

            success_count = sum(1 for r in results if r[2] is not None)

            st.success(f"Batch Complete — {success_count}/{len(results)} succeeded · {elapsed:.0f}s · ₹{cost_inr:.2f} · {total_in}+{total_out} tokens")

            cols_per_row = min(3, max(1, len(results)))
            for row_start in range(0, len(results), cols_per_row):
                row_items = results[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for i, item in enumerate(row_items):
                    cat, label, img, img_bytes, save_name, inp_t, out_t = item
                    with cols[i]:
                        if img:
                            st.image(img, caption=f"{cat}: {label}", use_container_width=True)
                            st.caption(f"Tokens: {inp_t}↑ {out_t}↓")
                            st.download_button("Download", data=img_bytes, file_name=save_name,
                                             mime="image/png", use_container_width=True, key=f"dl_{row_start}_{i}")
                        else:
                            st.error(f"Failed: {cat}: {label}")

            if st.button("Start new batch", use_container_width=True, type="primary"):
                st.session_state.batch_id = None
                st.session_state.batch_status = None
                st.session_state.batch_jobs = []
                st.rerun()

        elif "FAILED" in state:
            st.error(f"Batch failed after {elapsed:.0f}s")
            if st.button("Clear & retry", use_container_width=True):
                st.session_state.batch_id = None
                st.rerun()

        else:
            st.info(f"Processing {len(st.session_state.batch_jobs)} variants... {elapsed:.0f}s elapsed")
            st.progress(min(elapsed / 600, 0.95))
            time.sleep(15)
            st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        if st.button("Clear batch state"):
            st.session_state.batch_id = None
            st.rerun()


# ── Real-time generation ──
confirmed = st.session_state.get("confirmed_jobs", [])
if confirmed:
    st.markdown("---")
    st.subheader("Generating...")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []
    progress = st.progress(0)

    use_verify = st.session_state.get("verify_toggle", True)
    status_area = st.empty()

    for idx, (category, label, changes, item_ref, item_analysis) in enumerate(confirmed):
        progress.progress(idx / len(confirmed), text=f"{label} ({idx+1}/{len(confirmed)})")

        if use_verify:
            def on_status(msg, _sa=status_area):
                _sa.caption(msg)
            result = generate_with_verification(
                item_ref, item_analysis, changes,
                max_retries=2, on_status=on_status,
                allowed_models=["gemini-3.1-flash-image"],
            )
        else:
            result = generate_variant(item_ref, item_analysis, changes, allowed_models=["gemini-3.1-flash-image"])

        if result.get("success"):
            img_bytes = result["output_bytes"]
            img = Image.open(BytesIO(img_bytes))
            save_name = f"ai_{category}_{label}_{ts}.png"
            with open(os.path.join(OUTPUT_DIR, save_name), "wb") as f:
                f.write(img_bytes)
            results.append((category, label, img, img_bytes, save_name, result))
            st.session_state.gen_count += 1
            st.session_state.total_cost += result.get("cost_inr", 0)
        else:
            results.append((category, label, None, None, None, result))

    status_area.empty()
    progress.progress(1.0, text="Done!")

    st.session_state["last_results"] = []
    cols_per_row = min(3, max(1, len(results)))
    for row_start in range(0, len(results), cols_per_row):
        row_items = results[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for i, (category, label, img, img_bytes, save_name, result) in enumerate(row_items):
            global_idx = row_start + i
            with cols[i]:
                if img:
                    st.image(img, caption=f"{category}: {label}", use_container_width=True)
                    st.caption(f"{result.get('time_seconds', '?')}s · ₹{result.get('cost_inr', 0)}")
                    st.download_button("Download", data=img_bytes, file_name=save_name,
                                     mime="image/png", use_container_width=True, key=f"rt_dl_{row_start}_{i}")
                    st.session_state["last_results"].append({
                        "category": category, "label": label,
                        "ref_path": confirmed[global_idx][3],
                        "analysis": confirmed[global_idx][4],
                        "changes": confirmed[global_idx][2],
                    })
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown')}")

    st.session_state.confirmed_jobs = []

# ── Fix This ──
last_results = st.session_state.get("last_results", [])
if last_results:
    st.markdown("---")
    st.subheader("Fix an issue")
    st.caption("See a problem? Describe it and regenerate with a targeted fix (~₹7)")

    fix_options = [f"{r['category']}: {r['label']}" for r in last_results]
    fix_idx = st.selectbox("Which image to fix?", range(len(fix_options)), format_func=lambda i: fix_options[i], key="fix_select")
    fix_desc = st.text_input("What's wrong?", placeholder="e.g. product box color changed, price shows 599 instead of 499, 'sachet' was translated to Hindi", key="fix_desc")

    if st.button("Regenerate with fix", type="primary", key="fix_btn") and fix_desc:
        fix_item = last_results[fix_idx]
        fixed_changes = dict(fix_item["changes"])
        fixed_changes["_user_fix"] = fix_desc

        with st.spinner(f"Fixing: {fix_desc}..."):
            fix_result = generate_variant(
                fix_item["ref_path"], fix_item["analysis"], fixed_changes,
                allowed_models=["gemini-3.1-flash-image"],
            )

        if fix_result.get("success"):
            fix_bytes = fix_result["output_bytes"]
            fix_img = Image.open(BytesIO(fix_bytes))
            fix_name = f"fix_{fix_item['category']}_{fix_item['label']}_{datetime.now().strftime('%H%M%S')}.png"
            with open(os.path.join(OUTPUT_DIR, fix_name), "wb") as f:
                f.write(fix_bytes)
            st.image(fix_img, caption=f"Fixed: {fix_item['label']}", use_container_width=True)
            st.caption(f"{fix_result.get('time_seconds', '?')}s · ₹{fix_result.get('cost_inr', 0)}")
            st.download_button("Download fixed", data=fix_bytes, file_name=fix_name,
                             mime="image/png", use_container_width=True, key="fix_dl")
            st.session_state.gen_count += 1
            st.session_state.total_cost += fix_result.get("cost_inr", 0)
        else:
            st.error(f"Fix failed: {fix_result.get('error', 'Unknown')}")
