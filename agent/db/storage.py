"""
Supabase storage — save approved creatives to the shared cloud database.

Table: generated_ads
Columns:
    id              uuid (auto)
    created_at      timestamptz (auto)
    product_name    text
    brand_name      text
    category        text
    cluster_id      text
    headline        text
    subheadline     text
    image_url       text   (public URL from Supabase Storage)
    prompts         jsonb
    campaign_payload jsonb
    status          text   ('approved')

Table: reference_analyses
Columns:
    id              uuid (auto)
    created_at      timestamptz (auto)
    title           text   (user-provided name for this analysis)
    product_context text   (optional product/brand hint given by user)
    analysis        text   (Gemini's analysis of the reference image)
    prompts         jsonb  (list of 3 structured prompt strings)
    image_url       text   (public URL of the uploaded reference image)
"""

import os
import uuid
from datetime import datetime, timezone

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY")
_BUCKET = "ad-creatives"
_TABLE = "generated_ads"
_REF_TABLE = "reference_analyses"

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        if not _SUPABASE_URL or not _SUPABASE_KEY:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_KEY must be set in your .env file"
            )
        _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _client


def store_approved_creative(
    image_path: str,
    product_name: str,
    brand_name: str,
    category: str,
    cluster_id: str,
    headline: str = "",
    subheadline: str = "",
    prompts: dict = None,
    campaign_payload: dict = None,
) -> dict:
    """
    Upload the image to Supabase Storage, then insert a record into generated_ads.

    Returns:
        {"status": "success", "record_id": "...", "image_url": "..."}
    """
    client = _get_client()

    # 1. Upload image to Supabase Storage
    image_url = _upload_image(client, image_path, product_name, cluster_id)

    # 2. Insert record into generated_ads table
    record = {
        "product_name": product_name,
        "brand_name": brand_name,
        "category": category,
        "cluster_id": cluster_id,
        "headline": headline,
        "subheadline": subheadline,
        "image_url": image_url,
        "prompts": prompts or {},
        "campaign_payload": campaign_payload or {},
        "status": "approved",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = client.table(_TABLE).insert(record).execute()
    record_id = result.data[0]["id"] if result.data else "unknown"

    return {
        "status": "success",
        "record_id": record_id,
        "image_url": image_url,
    }


def store_approved_prompts(
    product_name: str,
    brand_name: str,
    category: str,
    selected_prompts: dict,
    prompt_images: dict = None,
    campaign_payload: dict = None,
) -> dict:
    """
    Store user-approved prompts to the shared library.
    Optionally upload per-prompt reference images to Supabase Storage.

    prompt_images: dict mapping "{cluster}_{i}" → image bytes (bytes)

    Returns:
        {"status": "success", "record_id": "...", "images_uploaded": N}
    """
    client = _get_client()

    # Upload per-prompt images and build a URL map
    prompt_image_urls: dict[str, str] = {}
    if prompt_images:
        safe_product = product_name.lower().replace(" ", "_")
        for upload_key, image_bytes in prompt_images.items():
            filename = f"{safe_product}/prompt_{upload_key}_{uuid.uuid4().hex[:8]}.png"
            try:
                client.storage.from_(_BUCKET).upload(
                    path=filename,
                    file=image_bytes,
                    file_options={"content-type": "image/png", "upsert": "true"},
                )
                public_url = client.storage.from_(_BUCKET).get_public_url(filename)
                prompt_image_urls[upload_key] = public_url
                print(f"[Storage] Uploaded prompt image for {upload_key}: {public_url}")
            except Exception as e:
                print(f"[Storage] Failed to upload image for {upload_key}: {e}")

    record = {
        "product_name": product_name,
        "brand_name": brand_name,
        "category": category,
        "cluster_id": "multiple",
        "headline": "",
        "subheadline": "",
        "image_url": next(iter(prompt_image_urls.values()), ""),  # first image as preview
        "prompts": selected_prompts,
        "prompt_image_urls": prompt_image_urls,  # full map stored as jsonb
        "campaign_payload": campaign_payload or {},
        "status": "prompts_approved",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = client.table(_TABLE).insert(record).execute()
    record_id = result.data[0]["id"] if result.data else "unknown"

    return {
        "status": "success",
        "record_id": record_id,
        "images_uploaded": len(prompt_image_urls),
    }


def delete_approved_creative(record_id: str) -> dict:
    """
    Delete a record from the shared library by its UUID.

    Returns:
        {"status": "deleted", "record_id": "..."} or {"status": "error", "message": "..."}
    """
    client = _get_client()
    result = client.table(_TABLE).delete().eq("id", record_id).execute()
    # Supabase returns the deleted rows in result.data — if empty, RLS blocked it
    if not result.data:
        print(f"[Storage] Delete returned no rows for id={record_id} — check Supabase RLS policy")
        return {"status": "error", "message": "Delete failed — no rows affected. Check Supabase RLS policy (enable delete for anon/service role)."}
    print(f"[Storage] Deleted record {record_id}")
    return {"status": "deleted", "record_id": record_id}


def get_approved_creatives(product_name: str = "", brand_name: str = "") -> list:
    """
    Fetch approved creatives from the shared library.
    Optionally filter by product_name or brand_name.

    Returns list of record dicts.
    """
    client = _get_client()
    query = client.table(_TABLE).select("*").in_("status", ["approved", "prompts_approved"])

    if product_name:
        query = query.ilike("product_name", f"%{product_name}%")
    if brand_name:
        query = query.ilike("brand_name", f"%{brand_name}%")

    result = query.order("created_at", desc=True).execute()
    return result.data or []


# ---------------------------------------------------------------------------
# Reference Image Analysis — memory storage
# ---------------------------------------------------------------------------

def save_reference_analysis(
    title: str,
    product_context: str,
    analysis: str,
    prompts: list,
    image_path: str = "",
) -> dict:
    """
    Save a reference image analysis (title, Gemini analysis text, 3 prompts,
    and optionally the reference image itself) to the reference_analyses table.

    Returns:
        {"status": "success", "record_id": "..."} or {"status": "error", "message": "..."}
    """
    client = _get_client()

    image_url = ""
    if image_path and os.path.exists(image_path):
        try:
            safe_title = title.lower().replace(" ", "_")[:40]
            ext = os.path.splitext(image_path)[-1] or ".png"
            filename = f"reference/{safe_title}_{uuid.uuid4().hex[:8]}{ext}"
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            client.storage.from_(_BUCKET).upload(
                path=filename,
                file=img_bytes,
                file_options={"content-type": "image/png", "upsert": "true"},
            )
            image_url = client.storage.from_(_BUCKET).get_public_url(filename)
            print(f"[Storage] Uploaded reference image: {image_url}")
        except Exception as e:
            print(f"[Storage] Reference image upload failed: {e}")

    record = {
        "title": title,
        "product_context": product_context,
        "analysis": analysis,
        "prompts": prompts,
        "image_url": image_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = client.table(_REF_TABLE).insert(record).execute()
        record_id = result.data[0]["id"] if result.data else "unknown"
        print(f"[Storage] Saved reference analysis '{title}' → {record_id}")
        return {"status": "success", "record_id": record_id}
    except Exception as e:
        print(f"[Storage] Failed to save reference analysis: {e}")
        return {"status": "error", "message": str(e)}


def get_reference_analyses() -> list:
    """
    Fetch all saved reference image analyses, newest first.
    Returns list of record dicts.
    """
    client = _get_client()
    try:
        result = client.table(_REF_TABLE).select("*").order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"[Storage] Failed to fetch reference analyses: {e}")
        return []


def delete_reference_analysis(record_id: str) -> dict:
    """
    Delete a reference analysis record by UUID.
    Returns {"status": "deleted"} or {"status": "error", "message": "..."}
    """
    client = _get_client()
    result = client.table(_REF_TABLE).delete().eq("id", record_id).execute()
    if not result.data:
        return {"status": "error", "message": "Delete failed — check Supabase RLS policy for reference_analyses table."}
    return {"status": "deleted", "record_id": record_id}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upload_image(client: Client, local_path: str, product_name: str, cluster_id: str) -> str:
    """Upload a local image file to Supabase Storage and return its public URL."""
    ext = os.path.splitext(local_path)[-1] or ".png"
    safe_product = product_name.lower().replace(" ", "_")
    filename = f"{safe_product}/{cluster_id}_{uuid.uuid4().hex[:8]}{ext}"

    with open(local_path, "rb") as f:
        image_bytes = f.read()

    client.storage.from_(_BUCKET).upload(
        path=filename,
        file=image_bytes,
        file_options={"content-type": "image/png", "upsert": "true"},
    )

    public_url = client.storage.from_(_BUCKET).get_public_url(filename)
    return public_url
