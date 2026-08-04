import streamlit as st
import json
import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from other modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from generation_engine.pipeline_runner import AdGenerationPipeline
from src.config.config_loader import load_fonts, load_emotions, load_prompts

# Page Config
st.set_page_config(page_title="AI Ad Creative Generator", layout="wide")

st.title("🎨 AI Advertisement Creative Generator")
st.markdown("---")

# Layout: Two columns for input and output
col1, col2 = st.columns([1, 1.2])

from src.memory.product_memory import ProductMemory

memory = ProductMemory()
products = memory.get_all_products()
product_names = [p["product_name"] for p in products if "product_name" in p]

with col1:
    st.header("📋 Campaign Configuration")
    
    if "previous_product" not in st.session_state:
        st.session_state.previous_product = "New Product"

    selected_product = st.selectbox("Select Existing Product", ["New Product"] + product_names)
    
    if selected_product != st.session_state.previous_product:
        st.session_state.previous_product = selected_product
        if selected_product != "New Product":
            selected_data = next((p for p in products if p.get("product_name") == selected_product), {})
            
            st.session_state["product_name_input"] = selected_data.get("product_name", "")
            st.session_state["brand_name_input"] = selected_data.get("brand_name", "")
            st.session_state["category_input"] = selected_data.get("category", "")
            
            benefits = selected_data.get("benefits", [])
            for i in range(5):
                st.session_state[f"benefit_{i}"] = benefits[i] if i < len(benefits) else ""
                
            problems = selected_data.get("problems", [])
            for i in range(3):
                st.session_state[f"problem_{i}"] = problems[i] if i < len(problems) else ""
                
            solutions = selected_data.get("solutions", [])
            for i in range(3):
                st.session_state[f"solution_{i}"] = solutions[i] if i < len(solutions) else ""
                
            ingredients = selected_data.get("ingredients", [])
            for i in range(5):
                st.session_state[f"ingredient_{i}"] = ingredients[i] if i < len(ingredients) else ""
                
            st.session_state["price_input"] = selected_data.get("price", "")
            st.session_state["offer_input"] = selected_data.get("offer", "")
            
            if "creative_style" in selected_data:
                st.session_state["creative_style_input"] = selected_data["creative_style"]
                
        else:
            st.session_state["product_name_input"] = ""
            st.session_state["brand_name_input"] = ""
            st.session_state["category_input"] = ""
            for i in range(5): st.session_state[f"benefit_{i}"] = ""
            for i in range(3): st.session_state[f"problem_{i}"] = ""
            for i in range(3): st.session_state[f"solution_{i}"] = ""
            for i in range(5): st.session_state[f"ingredient_{i}"] = ""
            st.session_state["price_input"] = ""
            st.session_state["offer_input"] = ""

    with st.form("campaign_form"):
        st.subheader("Basic Info")
        product_name = st.text_input("Product Name", key="product_name_input", placeholder="e.g., Arjuna Cardio Care Tea")
        brand_name = st.text_input("Brand Name", key="brand_name_input", placeholder="e.g., Vedic Roots")
        category = st.text_input("Category", key="category_input", placeholder="e.g., Ayurvedic Supplement")
        
        st.subheader("Benefits")
        st.write("Benefits (Add 3–5)")
        benefits = []
        for i in range(5):
            b = st.text_input(f"Benefit {i+1}", key=f"benefit_{i}")
            if b:
                benefits.append(b)
                
        st.subheader("Problems & Solutions")
        st.write("Problems (Optional - for solution ads)")
        problems = []
        for i in range(3):
            p = st.text_input(f"Problem {i+1}", key=f"problem_{i}")
            if p:
                problems.append(p)
                
        st.write("Solutions (Optional)")
        solutions = []
        for i in range(3):
            s = st.text_input(f"Solution {i+1}", key=f"solution_{i}")
            if s:
                solutions.append(s)
                
        st.subheader("Ingredients")
        st.write("Ingredients (Optional - for ingredient ads)")
        ingredients = []
        for i in range(5):
            ing = st.text_input(f"Ingredient {i+1}", key=f"ingredient_{i}")
            if ing:
                ingredients.append(ing)
                
        st.subheader("Pricing")
        price = st.text_input("Price (e.g. Rs. 599)", key="price_input")
        offer = st.text_input("Offer (e.g. 24% OFF)", key="offer_input")
        
        st.subheader("Creative Settings")
        creative_type = st.selectbox(
            "Creative Type",
            ["product_first", "solution_first", "doctor_first", "ingredient_first", "problem_first"],
            key="creative_style_input"
        )
        
        st.subheader("Media Assets")
        product_image_file = st.file_uploader("Upload Product Image (Required)", type=["png", "jpg", "jpeg"])
        person_image_file = st.file_uploader("Upload Person/Infulencer Image (Optional)", type=["png", "jpg", "jpeg"])
        
        submit_button = st.form_submit_button("🚀 Generate Creative")

# Image Saving Logic
def save_uploaded_file(uploaded_file, folder):
    if uploaded_file is not None:
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

if submit_button:
    if not product_image_file:
        st.error("❌ Product image is required!")
    else:
        with st.status("🏗️ Processing Campaign...", expanded=True) as status:
            try:
                # 1. Save Assets
                st.write("💾 Saving assets...")
                prod_path = save_uploaded_file(product_image_file, "assets/products")
                pers_path = save_uploaded_file(person_image_file, "assets/people")
                
                # 2. Build Campaign JSON
                st.write("📝 Building campaign payload...")
                campaign_input = {
                    "product_name": product_name,
                    "brand_name": brand_name,
                    "category": category,
                    "benefits": benefits,
                    "benefit_points": benefits,
                    "problems": problems,
                    "solutions": solutions,
                    "ingredients": ingredients,
                    "price": price,
                    "offer": offer,
                    "creative_style": creative_type,
                    "product_image": prod_path,
                    "person_image": pers_path
                }
                
                input_path = "inputs/campaign_input.json"
                os.makedirs("inputs", exist_ok=True)
                with open(input_path, "w") as f:
                    json.dump(campaign_input, f, indent=4)
                
                # 3. Trigger Pipeline (Prompt Generation Stage)
                st.write("⚡ Generating Prompt Variations...")
                pipeline = AdGenerationPipeline()
                pipeline.run(input_path, num_variations=5)
                
                # Clear selected prompts to force re-selection
                if os.path.exists("outputs/prompts/selected_prompts.json"):
                    os.remove("outputs/prompts/selected_prompts.json")
                
                status.update(label="✅ Prompts Generated!", state="complete", expanded=False)
                st.success("Prompts generated! Select your favorite variations in the right panel.")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Pipeline Failed: {str(e)}")
                status.update(label="❌ Generation Failed", state="error")

with col2:
    st.header("🖼️ Creative Generation")
    
    prompts_path = "outputs/prompts/cluster_prompts.json"
    selected_path = "outputs/prompts/selected_prompts.json"
    ads_dir = "outputs/generated_ads"
    
    if os.path.exists(prompts_path):
        with open(prompts_path, "r") as f:
            cluster_prompts = json.load(f)
            
        if not cluster_prompts:
            st.info("No generated prompts found.")
        else:
            st.subheader("Step 1: Select One Prompt per Cluster")
            
            selected_prompts = {}
            sorted_clusters = sorted(cluster_prompts.keys())
            total_selected = 0
            
            for cluster_id in sorted_clusters:
                prompts = cluster_prompts[cluster_id]
                selected_prompts[cluster_id] = []
                
                with st.expander(f"✨ {cluster_id.replace('_', ' ').title()} Variations", expanded=True):
                    for i, prompt in enumerate(prompts):
                        # checkbox for selection
                        if st.checkbox(f"Select Option {i+1} ({cluster_id})", key=f"check_{cluster_id}_{i}"):
                            selected_prompts[cluster_id].append(prompt)
                            total_selected += 1
                        
                        # Show full prompt in a nested expander
                        with st.expander(f"View Prompt {i+1}", expanded=False):
                            st.code(prompt, language="text")
                            st.button(
                                f"Copy Prompt {i+1}",
                                key=f"copy_{cluster_id}_{i}"
                            )

            st.markdown("---")
            
            # Step 2: Generate Final Images (only if at least one selected)
            if total_selected == 0:
                st.warning("⚠️ Please select at least one prompt variation to generate images.")
                generate_btn = st.button("🚀 Step 2: Generate Final Images", use_container_width=True, disabled=True)
            else:
                generate_btn = st.button("🚀 Step 2: Generate Final Images", use_container_width=True)

            if generate_btn:
                with st.status("🎨 Generating Final Images (this may take a minute)...") as status:
                    # Save selected prompts
                    os.makedirs("outputs/prompts", exist_ok=True)
                    with open(selected_path, "w") as f:
                        json.dump(selected_prompts, f, indent=4)
                    
                    # Trigger image generation
                    pipeline = AdGenerationPipeline()
                    pipeline.generate_from_selected()
                    
                    status.update(label="✅ All Images Generated!", state="complete")
                    st.success("Generation complete! Scroll down to see results.")
                    # No rerun here to keep the images visible if we show them below

            # Display Generated Images (if they exist)
            st.markdown("---")
            st.subheader("Step 3: Final Results")
            
            has_results = False
            for cluster_id in sorted_clusters:
                # Find all images for this cluster (handling suffixes like _1, _2)
                cluster_imgs = [f for f in os.listdir(ads_dir) if f.startswith(f"{cluster_id}") and f.endswith(".png")] if os.path.exists(ads_dir) else []
                cluster_imgs.sort() # Ensure consistent order
                
                for img_file in cluster_imgs:
                    has_results = True
                    img_path = os.path.join(ads_dir, img_file)
                    
                    # Extract index if suffix exists
                    display_name = cluster_id.replace('_', ' ').title()
                    if "_" in img_file.replace(f"{cluster_id}", ""):
                        try:
                            idx_str = img_file.replace(f"{cluster_id}_", "").replace(".png", "")
                            display_name += f" (Option {idx_str})"
                        except: pass

                    with st.expander(f"✅ Final Ad: {display_name}", expanded=True):
                        st.image(img_path, width='stretch')
                        
                        # Show the specific prompt for this image
                        if os.path.exists(selected_path):
                            with open(selected_path, "r") as f:
                                sel = json.load(f)
                                if cluster_id in sel:
                                    prompts = sel[cluster_id]
                                    if isinstance(prompts, list):
                                        # Try to match the index
                                        try:
                                            idx = int(img_file.replace(f"{cluster_id}_", "").replace(".png", "")) - 1
                                            if 0 <= idx < len(prompts):
                                                st.caption(f"📝 Prompt for Option {idx+1}:")
                                                st.code(prompts[idx], language="text")
                                        except:
                                            # Fallback if no index or mismatch
                                            pass
                                    elif isinstance(prompts, str) and img_file == f"{cluster_id}.png":
                                        st.caption("📝 Selected Prompt:")
                                        st.code(prompts, language="text")
                        
                        with open(img_path, "rb") as file:
                            st.download_button(
                                label=f"📥 Download {img_file}",
                                data=file,
                                file_name=img_file,
                                mime="image/png",
                                key=f"download_{img_file}"
                            )
            
            if not has_results:
                st.info("Images will appear here after you click 'Generate Final Images'.")
    else:
        st.info("Fill out the campaign form and click 'Generate Creative' to start.")
        st.write("---")
        st.caption("A preview will appear here once you hit 'Generate Creative'.")


# ─────────────────────────────────────────────────────────
# ⚙️ Config Editor Section
# ─────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️ Config Editor (Advanced)", expanded=False):
    st.caption("Edit emotion lists, font presets, and prompt rules. Changes are saved directly to JSON config files.")

    config_base_path = os.path.dirname(os.path.dirname(__file__))

    try:
        fonts_config   = load_fonts()
        emotions_config = load_emotions()
        prompts_config  = load_prompts()
    except Exception as e:
        st.error(f"Failed to load config: {e}")
        fonts_config, emotions_config, prompts_config = {"presets": []}, {}, {}

    tab_emotions, tab_fonts, tab_prompts = st.tabs(["😤 Emotions", "🔤 Font Presets", "💬 Prompt Rules"])

    # ── Emotions Tab ──────────────────────────────────────
    with tab_emotions:
        st.subheader("Cluster Emotions")
        st.info("Each cluster picks one emotion randomly per variation from this list.")
        edited_emotions = {}
        for cluster, values in emotions_config.items():
            new_val = st.text_input(
                f"{cluster.replace('_', ' ').title()} emotions (comma-separated)",
                ", ".join(values),
                key=f"em_{cluster}"
            )
            edited_emotions[cluster] = [v.strip() for v in new_val.split(",") if v.strip()]

        if st.button("💾 Save Emotions", key="save_emotions"):
            with open(os.path.join(config_base_path, "config", "emotions.json"), "w") as f:
                json.dump(edited_emotions, f, indent=2)
            st.success("✅ emotions.json saved!")
            st.info("Restart the app to apply changes to the pipeline.")

    # ── Fonts Tab ─────────────────────────────────────────
    with tab_fonts:
        st.subheader("Font Presets")
        st.info("Each preset is mapped to an emotional tone. Fonts are injected into every generated prompt.")
        edited_fonts = []
        for i, preset in enumerate(fonts_config.get("presets", [])):
            with st.container():
                st.markdown(f"**Preset {i+1}: `{preset['name']}`**")
                c1, c2, c3 = st.columns(3)
                headline = c1.text_input("Headline", preset.get("headline", ""), key=f"font_hl_{i}")
                sub      = c2.text_input("Sub",      preset.get("sub", ""),      key=f"font_sub_{i}")
                cta      = c3.text_input("CTA",      preset.get("cta", ""),      key=f"font_cta_{i}")
                edited_fonts.append({"name": preset["name"], "headline": headline, "sub": sub, "cta": cta})
                st.markdown("---")

        if st.button("💾 Save Fonts", key="save_fonts"):
            with open(os.path.join(config_base_path, "config", "fonts.json"), "w") as f:
                json.dump({"presets": edited_fonts}, f, indent=2)
            st.success("✅ fonts.json saved!")
            st.info("Restart the app to apply changes to the pipeline.")

    # ── Prompt Rules Tab ──────────────────────────────────
    with tab_prompts:
        st.subheader("Prompt Rules per Cluster")
        st.info("Define default headline style and layout hint for each cluster.")
        edited_prompts = {}
        for cluster, rules in prompts_config.items():
            st.markdown(f"**{cluster.replace('_', ' ').title()}**")
            c1, c2 = st.columns(2)
            hl_style    = c1.text_input("Headline Style",  rules.get("headline_style", ""),  key=f"pr_hl_{cluster}")
            layout_hint = c2.text_input("Layout Hint",     rules.get("layout_hint", ""),     key=f"pr_lh_{cluster}")
            edited_prompts[cluster] = {"headline_style": hl_style, "layout_hint": layout_hint}
            st.markdown("---")

        if st.button("💾 Save Prompt Rules", key="save_prompts"):
            with open(os.path.join(config_base_path, "config", "prompts.json"), "w") as f:
                json.dump(edited_prompts, f, indent=2)
            st.success("✅ prompts.json saved!")
            st.info("Restart the app to apply changes to the pipeline.")

# Instructions for Running
# To run this app:
# streamlit run ui/app.py
