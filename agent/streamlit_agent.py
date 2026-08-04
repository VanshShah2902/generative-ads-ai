"""
Streamlit Chat UI for the Ad Agent.

Run with:
    streamlit run agent/streamlit_agent.py
"""

import json
import os
import sys

# Ensure project root is importable
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from agent.agent import AdAgent
from agent.db.storage import (
    store_approved_creative, store_approved_prompts, get_approved_creatives, delete_approved_creative,
    save_reference_analysis, get_reference_analyses, delete_reference_analysis,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Ad Creative Agent",
    page_icon="🎯",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Helper functions — defined FIRST so they are available everywhere below
# ---------------------------------------------------------------------------

def _add_message(role: str, content: str, images: list = None):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "images": images or [],
    })


def _display_images(image_paths: list):
    if not image_paths:
        return
    cols = st.columns(min(len(image_paths), 3))
    for i, path in enumerate(image_paths):
        with cols[i % 3]:
            if path.startswith("http"):
                st.image(path, use_container_width=True)
            elif os.path.exists(path):
                st.image(path, use_container_width=True)
                st.caption(os.path.basename(path))
            else:
                st.warning(f"Image not found: {path}")


def _save_reference_image(uploaded_file) -> str:
    """Save a Streamlit UploadedFile to a temp path and return the path."""
    import uuid
    out_dir = os.path.join("outputs", "temp")
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[-1] or ".png"
    path = os.path.join(out_dir, f"reference_{uuid.uuid4().hex[:8]}{ext}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def _send(text: str):
    """Add user message, call agent, render assistant reply."""
    _add_message("user", text)

    with st.chat_message("user"):
        st.markdown(text)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.agent.chat(text)

        st.markdown(response.text)

        if response.cluster_prompts:
            st.session_state.cluster_prompts = response.cluster_prompts

        if response.template_prompts:
            st.session_state.template_prompts = response.template_prompts

        if response.analysis_meta:
            # Capture raw analysis data from analyse_reference_image for saving to memory
            st.session_state.reference_analysis_result = response.analysis_meta

        if response.campaign_context:
            st.session_state.campaign_context.update(response.campaign_context)

        if response.images:
            _display_images(response.images)
            if response.awaiting_approval:
                st.session_state.pending_approval = response.approval_payload

        _add_message(
            "assistant",
            response.text,
            images=response.images if response.images else None,
        )

    st.rerun()


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "agent" not in st.session_state:
    st.session_state.agent = AdAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "cluster_prompts" not in st.session_state:
    st.session_state.cluster_prompts = {}

if "selected_prompts" not in st.session_state:
    st.session_state.selected_prompts = {}

if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = {}

if "campaign_context" not in st.session_state:
    st.session_state.campaign_context = {}

if "view_library" not in st.session_state:
    st.session_state.view_library = False

if "prompt_uploads" not in st.session_state:
    st.session_state.prompt_uploads = {}  # key: "cluster_i" → UploadedFile

if "template_prompts" not in st.session_state:
    st.session_state.template_prompts = []  # single prompt from analyse_reference_image

if "show_reference_uploader" not in st.session_state:
    st.session_state.show_reference_uploader = False

if "reference_analysis_result" not in st.session_state:
    # Stores the last analysis result for saving: {analysis, prompts, image_path, product_context}
    st.session_state.reference_analysis_result = {}

if "view_reference_library" not in st.session_state:
    st.session_state.view_reference_library = False

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🎯 Ad Creative Agent")
st.caption("Your AI-powered advertising assistant. Click a button below to get started.")

# ---------------------------------------------------------------------------
# Action buttons
# ---------------------------------------------------------------------------
col1, col2, col4, col5, col6, col_reset = st.columns([1, 1, 1, 1, 1, 1])

with col1:
    if st.button("✨ Generate Prompts", use_container_width=True):
        st.session_state.view_library = False
        st.session_state.campaign_context = {}   # clear previous campaign
        _send(
            "I want to generate new ad prompts. "
            "IMPORTANT: Start fresh — ask me which visual theme I want first "
            "(KR_2D, DR_1ST, KR_2C, SIGNS, or CF), then collect all product details "
            "from scratch. Do NOT reuse any previous campaign data."
        )

with col2:
    if st.button("🖼️ Generate Ad Images", use_container_width=True):
        st.session_state.view_library = False
        _send("Generate Ad Images")

with col4:
    if st.button("🔍 Analyse Reference Image", use_container_width=True):
        st.session_state.view_library = False
        st.session_state.view_reference_library = False
        st.session_state.show_reference_uploader = not st.session_state.show_reference_uploader

with col5:
    if st.button("📚 View Approved Ads", use_container_width=True):
        st.session_state.view_library = True
        st.session_state.view_reference_library = False

with col6:
    if st.button("📖 Reference Library", use_container_width=True):
        st.session_state.view_reference_library = True
        st.session_state.view_library = False

with col_reset:
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.agent.reset()
        st.session_state.messages = []
        st.session_state.cluster_prompts = {}
        st.session_state.selected_prompts = {}
        st.session_state.pending_approval = {}
        st.session_state.campaign_context = {}
        st.session_state.view_library = False
        st.session_state.prompt_uploads = {}
        st.session_state.template_prompts = []
        st.session_state.show_reference_uploader = False
        st.session_state.reference_analysis_result = {}
        st.session_state.view_reference_library = False
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Reference Image Uploader widget
# ---------------------------------------------------------------------------
if st.session_state.show_reference_uploader:
    with st.container(border=True):
        st.markdown("### 🔍 Analyse Reference Image")
        st.caption("Upload any ad image — competitor creative, winning ad, or inspiration. "
                   "Gemini extracts the visual style and layout, then generates prompts for YOUR product.")

        ref_file = st.file_uploader(
            "Choose a reference image",
            type=["png", "jpg", "jpeg", "webp"],
            key="ref_image_upload",
        )

        if ref_file:
            col_prev, col_btn = st.columns([1, 2])
            with col_prev:
                st.image(ref_file, caption="Reference image", use_container_width=True)
            with col_btn:
                st.caption("Gemini will analyse this image and produce a prompt to recreate the same visual style.")
                if st.button("🔍 Analyse & Generate Prompt", type="primary", use_container_width=True):
                    with st.spinner("Saving image..."):
                        saved_path = _save_reference_image(ref_file)
                    st.session_state.show_reference_uploader = False
                    _send(
                        f"Analyse the reference image at: '{saved_path}'. "
                        f"Call analyse_reference_image with image_path='{saved_path}'. "
                        f"Then show me the full generated prompt."
                    )

# ---------------------------------------------------------------------------
# Library view
# ---------------------------------------------------------------------------
if st.session_state.view_library:
    st.subheader("📚 Approved Ad Library")
    records = get_approved_creatives()
    if not records:
        st.info("No approved records yet. Generate prompts or creatives and approve them.")
    else:
        for rec in records:
            status = rec.get("status", "")
            product = rec.get("product_name", "Unknown")
            brand = rec.get("brand_name", "")
            created = rec.get("created_at", "")[:19].replace("T", " ")

            with st.container(border=True):
                col_info, col_badge, col_del = st.columns([4, 1, 1])
                with col_info:
                    st.markdown(f"**{product}** — {brand}")
                    st.caption(f"Cluster: {rec.get('cluster_id', '')} | Created: {created}")
                with col_badge:
                    if status == "approved":
                        st.success("✅ Image Approved")
                    else:
                        st.info("📋 Prompts Approved")
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_{rec['id']}", use_container_width=True):
                        result = delete_approved_creative(rec["id"])
                        if result.get("status") == "deleted":
                            st.rerun()
                        else:
                            st.error(result.get("message", "Delete failed."))

                if rec.get("image_url"):
                    st.image(rec["image_url"], width=300)

                if rec.get("prompts"):
                    with st.expander("View Prompts"):
                        prompt_urls = rec.get("prompt_image_urls") or {}
                        prompts_data = rec["prompts"]
                        if isinstance(prompts_data, dict):
                            for cluster_key, cluster_prompts in prompts_data.items():
                                st.markdown(f"**{cluster_key.replace('_', ' ').title()}**")
                                if isinstance(cluster_prompts, list):
                                    for idx, p in enumerate(cluster_prompts):
                                        st.markdown(f"_{p}_")
                                        img_url = prompt_urls.get(f"{cluster_key}_{idx}")
                                        if img_url:
                                            st.image(img_url, caption=f"Reference image", width=200)
                                else:
                                    st.write(cluster_prompts)
                        else:
                            st.json(prompts_data)
    st.stop()

# ---------------------------------------------------------------------------
# Reference Library view
# ---------------------------------------------------------------------------
if st.session_state.view_reference_library:
    st.subheader("📖 Reference Image Analysis Library")
    st.caption("All saved reference ad analyses. Each entry stores the original image, Gemini's analysis, and the generated prompts.")

    records = get_reference_analyses()
    if not records:
        st.info("No saved analyses yet. Analyse a reference image and save it using the 💾 Save to Memory button.")
    else:
        for rec in records:
            created = rec.get("created_at", "")[:19].replace("T", " ")
            title = rec.get("title", "Untitled")
            product_ctx = rec.get("product_context", "")

            with st.container(border=True):
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.markdown(f"### {title}")
                    if product_ctx:
                        st.caption(f"Product context: {product_ctx}  |  Saved: {created}")
                    else:
                        st.caption(f"Saved: {created}")
                with col_del:
                    if st.button("🗑️ Delete", key=f"refdel_{rec['id']}", use_container_width=True):
                        result = delete_reference_analysis(rec["id"])
                        if result.get("status") == "deleted":
                            st.rerun()
                        else:
                            st.error(result.get("message", "Delete failed."))

                col_img, col_analysis = st.columns([1, 2])
                with col_img:
                    if rec.get("image_url"):
                        st.image(rec["image_url"], caption="Reference image", use_container_width=True)

                with col_analysis:
                    if rec.get("analysis"):
                        with st.expander("📊 Gemini Analysis"):
                            st.text(rec["analysis"])

                if rec.get("prompts"):
                    with st.expander("📋 Generated Prompts"):
                        prompts_data = rec["prompts"]
                        if isinstance(prompts_data, list):
                            for i, p in enumerate(prompts_data):
                                st.markdown(f"**Prompt {i+1}**")
                                st.text(p)
                                st.divider()
                        else:
                            st.write(prompts_data)
    st.stop()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("images"):
            _display_images(msg["images"])

# ---------------------------------------------------------------------------
# Reference Image Analysis — generated prompt display
# ---------------------------------------------------------------------------
if st.session_state.template_prompts:
    st.markdown("### 🔍 Reference Image — Generated Prompt")
    st.caption("Copy this prompt and paste it into your image generation tool to recreate the same visual style.")

    prompt_text = st.session_state.template_prompts[0] if st.session_state.template_prompts else ""
    st.code(prompt_text, language=None)

    ref_col1, ref_col2 = st.columns(2)
    with ref_col1:
        if st.button("✅ Save Prompt to Library", use_container_width=True):
            ctx = st.session_state.campaign_context
            with st.spinner("Saving..."):
                result = store_approved_prompts(
                    product_name=ctx.get("product_name", "Reference Analysis"),
                    brand_name=ctx.get("brand_name", ""),
                    category=ctx.get("category", ""),
                    selected_prompts={"reference_style": [prompt_text]},
                    campaign_payload=ctx,
                )
            st.session_state.template_prompts = []
            _add_message("assistant", f"✅ Prompt saved to library. Record ID: `{result.get('record_id', '?')}`")
            st.rerun()
    with ref_col2:
        if st.button("🗑️ Dismiss", use_container_width=True):
            st.session_state.template_prompts = []
            st.rerun()

    # ── Save Reference Analysis to Memory ──────────────────────────────────
    if st.session_state.reference_analysis_result:
        with st.container(border=True):
            st.markdown("#### 💾 Save Analysis to Memory")
            st.caption("Give this analysis a title and save it to the Reference Library for future use.")
            ref_title = st.text_input(
                "Title for this analysis",
                placeholder="e.g. Arjuna Tea – Winning Dr. Bimal Creative",
                key="ref_save_title",
            )
            if st.button("💾 Save to Reference Library", type="primary", use_container_width=True):
                if not ref_title.strip():
                    st.warning("Please enter a title before saving.")
                else:
                    meta = st.session_state.reference_analysis_result
                    with st.spinner("Saving analysis to memory..."):
                        result = save_reference_analysis(
                            title=ref_title.strip(),
                            product_context=meta.get("product_context", ""),
                            analysis=meta.get("analysis", ""),
                            prompts=meta.get("prompts", []),
                            image_path=meta.get("image_path", ""),
                        )
                    if result.get("status") == "success":
                        st.session_state.reference_analysis_result = {}
                        _add_message("assistant", f"✅ Reference analysis saved as **\"{ref_title}\"**. View it in 📖 Reference Library.")
                        st.rerun()
                    else:
                        st.error(f"Save failed: {result.get('message', 'Unknown error')}. Check Supabase RLS policy for reference_analyses table.")

    st.divider()

# ---------------------------------------------------------------------------
# Prompt selection widget
# ---------------------------------------------------------------------------
if st.session_state.cluster_prompts:
    st.markdown("### 📋 Generated Prompts — Select to Generate Images")
    st.caption("Expand any prompt to read the full text. Check the ones you want, then use the buttons below.")

    selections: dict[str, list[str]] = {}

    for cluster, prompts in st.session_state.cluster_prompts.items():
        st.markdown(f"#### {cluster.replace('_', ' ').title()}")
        selected_for_cluster = []
        for i, prompt in enumerate(prompts):
            short = prompt[:100] + "..." if len(prompt) > 100 else prompt
            col_check, col_text = st.columns([0.04, 0.96])
            with col_check:
                checked = st.checkbox("", key=f"prompt_{cluster}_{i}", label_visibility="collapsed")
            with col_text:
                with st.expander(f"**{i + 1}.** {short}"):
                    st.write(prompt)
                    # Per-prompt image attachment
                    upload_key = f"{cluster}_{i}"
                    uploaded = st.file_uploader(
                        "📎 Attach a reference image for this prompt (optional)",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"upload_{cluster}_{i}",
                    )
                    if uploaded is not None:
                        st.session_state.prompt_uploads[upload_key] = uploaded
                        st.image(uploaded, caption="Attached image", width=200)
                    elif upload_key in st.session_state.prompt_uploads:
                        # Show previously attached image (if widget cleared but state retained)
                        st.image(st.session_state.prompt_uploads[upload_key], caption="Attached image", width=200)
            if checked:
                selected_for_cluster.append(prompt)
        selections[cluster] = selected_for_cluster
        st.divider()

    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("🖼️ Generate Images from Selected", type="primary", use_container_width=True):
            chosen = {k: v for k, v in selections.items() if v}
            if not chosen:
                st.warning("Please select at least one prompt.")
            else:
                st.session_state.selected_prompts = chosen
                st.session_state.cluster_prompts = {}
                _send(f"Please generate images for these selected prompts: {json.dumps(chosen)}")

    with btn_col2:
        if st.button("✅ Approve & Store Prompts", use_container_width=True):
            chosen = {k: v for k, v in selections.items() if v}
            if not chosen:
                st.warning("Please select at least one prompt to store.")
            else:
                ctx = st.session_state.campaign_context
                # Collect only uploads for selected prompts
                uploads = st.session_state.get("prompt_uploads", {})
                # Build a dict of {upload_key: bytes} for selected prompts
                prompt_images: dict[str, bytes] = {}
                for cluster, prompt_list in chosen.items():
                    for i, prompt in enumerate(st.session_state.cluster_prompts.get(cluster, [])):
                        if prompt in prompt_list:
                            upload_key = f"{cluster}_{i}"
                            if upload_key in uploads and uploads[upload_key] is not None:
                                prompt_images[upload_key] = uploads[upload_key].getvalue()
                with st.spinner("Storing approved prompts to shared library..."):
                    result = store_approved_prompts(
                        product_name=ctx.get("product_name", ""),
                        brand_name=ctx.get("brand_name", ""),
                        category=ctx.get("category", ""),
                        selected_prompts=chosen,
                        prompt_images=prompt_images,
                        campaign_payload=ctx,
                    )
                st.session_state.selected_prompts = chosen
                st.session_state.cluster_prompts = {}
                st.session_state.prompt_uploads = {}
                img_count = result.get("images_uploaded", 0)
                img_note = f" ({img_count} image(s) attached)" if img_count else ""
                _add_message("assistant", f"✅ Prompts stored to shared library{img_note}. Record ID: `{result.get('record_id', '?')}`")
                st.rerun()

# ---------------------------------------------------------------------------
# Image approval widget
# ---------------------------------------------------------------------------
if st.session_state.pending_approval:
    payload = st.session_state.pending_approval
    images = payload.get("images", [])

    st.markdown("### ✅ Approve Generated Images")
    st.caption("Review your creatives below. Approve to save to the shared library or reject to discard.")
    _display_images(images)

    # Show local file paths
    if images:
        with st.expander("📁 Local file paths"):
            for p in images:
                st.code(os.path.abspath(p))

    col_approve, col_reject = st.columns(2)
    with col_approve:
        if st.button("✅ Approve & Save to Library", type="primary", use_container_width=True):
            ctx = st.session_state.campaign_context
            with st.spinner("Uploading to shared library..."):
                results = []
                for img_path in images:
                    cluster = os.path.splitext(os.path.basename(img_path))[0]
                    res = store_approved_creative(
                        image_path=img_path,
                        product_name=ctx.get("product_name", ""),
                        brand_name=ctx.get("brand_name", ""),
                        category=ctx.get("category", ""),
                        cluster_id=cluster,
                        headline=ctx.get("headline", ""),
                        subheadline=ctx.get("subheadline", ""),
                        prompts=st.session_state.selected_prompts,
                        campaign_payload=ctx,
                    )
                    results.append(res)

            ids = [r.get("record_id", "?") for r in results]
            urls = [r.get("image_url", "") for r in results if r.get("image_url")]
            msg = f"✅ Saved {len(ids)} creative(s) to the shared library.\n\n**Record IDs:** {', '.join(ids)}"
            if urls:
                msg += "\n\n**Cloud URLs:**\n" + "\n".join(f"- {u}" for u in urls)
            _add_message("assistant", msg)
            st.session_state.pending_approval = {}
            st.rerun()

    with col_reject:
        if st.button("❌ Reject", use_container_width=True):
            _add_message("assistant", "Creatives rejected. You can generate new ones or go back to select different prompts.")
            st.session_state.pending_approval = {}
            st.rerun()

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Type your message here...")
if user_input:
    _send(user_input)
