from fastapi import APIRouter, HTTPException, status

from api.models import GenerateCreativesRequest
from api.services import generate_creatives, get_creative
from src.modeling.creative import Creative, CreativeResponse

router = APIRouter(prefix="/api/v1", tags=["creatives"])


@router.post(
    "/generate-creatives",
    response_model=CreativeResponse,
    status_code=status.HTTP_200_OK,
)
def generate_creatives_endpoint(request: GenerateCreativesRequest) -> CreativeResponse:
    try:
        return generate_creatives(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creative generation failed.")


@router.get(
    "/creatives/{creative_id}",
    response_model=Creative,
    status_code=status.HTTP_200_OK,
)
def get_creative_endpoint(creative_id: str) -> Creative:
    creative = get_creative(creative_id)
    if creative is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Creative '{creative_id}' not found.")
    return creative
