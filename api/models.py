from pydantic import BaseModel, Field


class GenerateCreativesRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    benefits: list[str] = Field(..., min_length=1)
    ingredients: list[str] = Field(..., min_length=1)
    price: str = Field(..., min_length=1)
