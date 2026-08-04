# Generation Interface Documentation

This document describes the interface between the **Creative Engine** (analytical pipeline) and the **Image Generation System**.

## 1. Overview
The Creative Engine outputs a structured JSON specification that defines the visual and marketing requirements for an advertisement. The generation system is responsible for taking these specifications and producing a high-quality background scene.

## 2. Input: `generation_payload.json`
The primary input for the generation system is `data/generation_payload.json`.

### Payload Structure:
- `scene_prompt`: A dense, descriptive string optimized for image generation models (Base scene + lighting + aesthetic).
- `product_image`: Path to the product asset to be inserted later.
- `person_image`: Path to the person asset to be inserted later (if applicable).
- `composition`: Spatial layout specifications.
  - `product_position`: (left, right, center)
  - `person_position`: (left, right, center, or null)
  - `text_position`: (top, bottom, center)
- `copy`: The marketing copy (headline, subheadline, CTA).
- `generator_constraints`: Critical rules for the image model.

## 3. Image Generator Requirements (Constraints)
To ensure the final ad can be correctly composed, the image generator MUST follow these rules:
1. **DO NOT** generate the product itself.
2. **DO NOT** generate a person/subject if a person asset is provided in the payload.
3. **RESERVE EMPTY SPACE** according to the `composition` positions.
4. Output should be a high-resolution background scene.

## 4. Expected Output
The generator should produce:
- `generated_scene.png`: A background-only image file.

This image will be passed to the **Composition Engine** which will automatically layer the product, person, and text elements according to the specifications.
