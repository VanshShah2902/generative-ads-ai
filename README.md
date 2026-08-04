# AI Advertisement Creative Generation System

## 1. Project Overview
`generative_ads_ai` is a modular AI pipeline designed to automate the creation of high-quality advertisement creatives. It transforms structured specifications (JSON) into final ad compositions by layering AI-generated backgrounds with product and person assets.

## 2. System Architecture
The system follows a multi-stage generation and composition flow:
1. **Layout Engine**: Determines spatial anchors.
2. **Scene Generator**: Produces background images using generative AI (e.g., SDXL, Flux).
3. **Asset Placement**: Procedurally inserts product and subject images.
4. **Text Rendering**: Overlays marketing copy using designated typography rules.

## 3. Directory Structure
```
generative_ads_ai/
├── generation_engine/      # Core AI logic and pipeline runners
├── utils/                  # Helper utilities for image and data processing
├── configs/                # System and layout configurations
├── assets/                 # Storage for products, subjects, and design assets
├── inputs/                 # Generation specification files (JSON)
└── outputs/                # Generated scenes, text, and final ads
```

## 4. Payload Format
The system consumes `inputs/generation_payload.json` which includes:
- `scene_prompt`: Visual description for the background.
- `layout_cluster`: Design pattern to follow.
- `headline`, `subheadline`, `cta`: Marketing copy and call to action.

## 5. Module Responsibilities
- `scene_generator.py`: Interfaces with generative models.
- `product_placer.py`: Handles geometric transformations and blending of bottles/products.
- `person_placer.py`: Inserts human subjects/influencers into the scene.
- `text_renderer.py`: Manages font placement and readability.
- `layout_engine.py`: Computes (x, y) anchors to enforce advertisement design structure.

## 6. Execution Flow
Run the system using the `pipeline_runner.py` or the high-level `test_pipeline.py`:
1. Load specification.
2. Calculate design grid.
3. Generate background.
4. Blend assets.
5. Render copy.

## 7. Setup Instructions
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Configure API keys in `.env` (copied from `.env.example`).
4. Run verification: `python test_pipeline.py`.

## 8. Future Extensions
- Automated performance scoring.
- Video creative generation.
- Dynamic color palette derivation from product assets.
