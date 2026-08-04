from dotenv import load_dotenv
import os
import time
import google.generativeai as genai
from PIL import Image

load_dotenv()

def enforce_square(image_path: str):
    """Lightly crops the image to 1:1, trimming at most 10% of each side
    so important composition elements are never cut off."""
    img = Image.open(image_path)
    width, height = img.size
    print(f"[AspectRatio] Original size: {width}x{height}")
    
    if width == height:
        return  # already square, nothing to do

    # Allow at most 10% crop of the shorter dimension per side
    min_dim = min(width, height)
    max_crop = int(min_dim * 0.10)
    target = min(width, height, max(width, height) - 2 * max_crop)
    target = max(target, min_dim)  # never go below min_dim

    left   = (width  - target) // 2
    top    = (height - target) // 2
    right  = left + target
    bottom = top  + target

    img = img.crop((left, top, right, bottom))
    img.save(image_path)
    print(f"[PostProcess] Safe-cropped to {target}x{target}: {image_path}")

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=API_KEY)
print("[Config] Gemini API Key loaded successfully")

model = genai.GenerativeModel("gemini-2.5-flash-image")

def build_input_parts(prompt, product_path=None, person_path=None):
    from PIL import Image
    import io
    
    parts = [{"text": prompt}]

    def _process_image(path):
        if not path:
            return None
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image not found: {path}")
            
        try:
            # Optional optimization: resize to max 1024px to reduce payload size
            img = Image.open(path).convert("RGB")
            max_size = 1024
            if max(img.width, img.height) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        except ImportError:
            # Fallback if Pillow is not installed
            with open(path, "rb") as f:
                return f.read()

    if product_path:
        data = _process_image(product_path)
        if data:
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": data
                }
            })

    if person_path:
        data = _process_image(person_path)
        if data:
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": data
                }
            })

    return parts


class SceneGenerator:
    """Handles single-shot ad generation using Gemini multimodal image generation."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to the 'configs' folder in the project root
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.config_dir = os.path.join(project_root, "configs")
        else:
            self.config_dir = config_dir

    def generate_scene(self, payload: dict) -> str:
        prompt = payload.get("scene_prompt", "")
        product_path = payload.get("product_image")
        person_path = payload.get("person_image")

        print(f"[Gemini Prompt]: {prompt[:300]}...")

        # Validate input files
        if product_path and not os.path.exists(product_path):
            raise FileNotFoundError(f"Product image not found: {product_path}")
            
        if person_path and not os.path.exists(person_path):
            raise FileNotFoundError(f"Person image not found: {person_path}")

        # Build parts with resizing
        parts = build_input_parts(prompt, product_path, person_path)

        try:
            print("[SceneGenerator] Calling Gemini API single-shot...")
            response = model.generate_content(parts)

            if not response.candidates:
                raise ValueError("No candidates returned from Gemini")

            print(f"[Gemini RAW RESPONSE]: {response}")

            image_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_data = part.inline_data.data
                    break

            if not image_data:
                print("[Gemini WARNING] No image returned, saving debug response")
                debug_path = "outputs/debug_gemini.txt"
                os.makedirs("outputs", exist_ok=True)
                with open(debug_path, "w") as f:
                    f.write(str(response))
                raise ValueError("Gemini returned no image — check outputs/debug_gemini.txt")

            cluster_id = payload.get("cluster_id", f"ad_{int(time.time())}")
            output_dir = "outputs/generated_ads"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{cluster_id}.png")

            with open(output_path, "wb") as f:
                f.write(image_data)

            print(f"[Pipeline] Saved image for {cluster_id} at {output_path}")

            # Hard-enforce 1:1 aspect ratio via center-crop
            enforce_square(output_path)

            return output_path

        except Exception as e:
            print(f"[SceneGenerator ERROR]: {e}")
            raise e
