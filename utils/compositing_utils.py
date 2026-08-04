import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove
import os

def remove_background(pil_img):
    """Removes background from an image if it doesn't have an alpha channel."""
    if pil_img.mode == 'RGBA':
        # Check if alpha channel is actually used (not just all 255)
        alpha = np.array(pil_img.split()[-1])
        if np.any(alpha < 255):
            return pil_img
            
    print("[CompositingUtils] Removing background using rembg...")
    return remove(pil_img)

def scale_asset(pil_img, scene_size, scale_ratio, scale_by='width'):
    """Resizes asset relative to scene dimensions."""
    sw, sh = scene_size
    if scale_by == 'width':
        target_w = int(sw * scale_ratio)
        aspect = pil_img.height / pil_img.width
        target_h = int(target_w * aspect)
    else: # scale_by 'height'
        target_h = int(sh * scale_ratio)
        aspect = pil_img.width / pil_img.height
        target_w = int(target_h * aspect)
        
    return pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

def match_lighting(asset_pil, scene_np, anchor, region_radius=50):
    """Adjusts asset brightness to match the local scene region."""
    # Convert anchor to indices
    ax, ay = anchor
    sh, sw = scene_np.shape[:2]
    
    # 1. Sample local region
    y1, y2 = max(0, ay - region_radius), min(sh, ay + region_radius)
    x1, x2 = max(0, ax - region_radius), min(sw, ax + region_radius)
    
    region = scene_np[y1:y2, x1:x2]
    if region.size == 0:
        return asset_pil
        
    scene_brightness = np.mean(cv2.cvtColor(region, cv2.COLOR_BGR2GRAY))
    
    # 2. Compute asset brightness (weighted by alpha)
    asset_np = np.array(asset_pil.convert('RGBA'))
    rgb = asset_np[:, :, :3]
    alpha = asset_np[:, :, 3] / 255.0
    
    gray_asset = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    mask = alpha > 0.1
    if not np.any(mask):
        return asset_pil
        
    asset_brightness = np.mean(gray_asset[mask])
    
    # 3. Apply enhancement
    if asset_brightness > 0:
        factor = scene_brightness / asset_brightness
        # Clamp factor to avoid extreme blowouts
        factor = np.clip(factor, 0.7, 1.3)
        enhancer = ImageEnhance.Brightness(asset_pil)
        return enhancer.enhance(factor)
        
    return asset_pil

def generate_shadow(asset_pil, blur_radius=15, offset=(10, 10), opacity=0.5):
    """Creates a soft shadow based on the asset's alpha mask."""
    # Extract alpha as mask
    alpha = asset_pil.split()[-1]
    
    # Create black image of same size
    shadow = Image.new('L', asset_pil.size, 0)
    # The mask itself is the shadow shape
    shadow_mask = alpha.point(lambda p: p * opacity if p > 0 else 0)
    
    # Blur the shadow
    shadow_soft = Image.merge('L', (shadow_mask,)).filter(ImageFilter.GaussianBlur(blur_radius))
    
    # Create the shadow layer (Full black with blurred alpha)
    shadow_layer = Image.new('RGBA', asset_pil.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_soft)
    
    return shadow_layer

def composite_with_shadow(scene_pil, asset_pil, anchor):
    """Composites asset and its shadow onto the scene."""
    # Shadow offset (slighty down and right)
    sh_offset = (int(asset_pil.width * 0.05), int(asset_pil.height * 0.05))
    shadow = generate_shadow(asset_pil, blur_radius=int(asset_pil.width*0.05))
    
    # Anchor is center of asset in our LayoutEngine logic
    pos_x = anchor[0] - asset_pil.width // 2
    pos_y = anchor[1] - asset_pil.height // 2
    
    # Paste shadow first
    scene_pil.paste(shadow, (pos_x + sh_offset[0], pos_y + sh_offset[1]), shadow)
    # Paste asset
    scene_pil.paste(asset_pil, (pos_x, pos_y), asset_pil)
    
    return scene_pil
