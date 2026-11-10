"""API routes for physical unit conversion and supported measurement catalogs."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.models import ConvertRequest, ConvertResponse, UnitCategoriesResponse
from app.services.units import convert_measurement, get_supported_categories

router = APIRouter(tags=["Unit Conversion"])


@router.post(
    "/convert",
    response_model=ConvertResponse,
    summary="Convert measurement units",
    description="Convert numeric values across physical units including temperature with offsets, data storage (MB vs MiB), length, speed, mass, and volume.",
)
async def convert_endpoint(payload: ConvertRequest) -> Dict[str, Any]:
    try:
        return convert_measurement(
            value=payload.value,
            from_unit_input=payload.from_unit,
            to_unit_input=payload.to_unit,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "UNIT_CONVERSION_ERROR", "message": str(val_err)},
        ) from val_err


@router.get(
    "/convert/units",
    response_model=UnitCategoriesResponse,
    summary="List supported unit categories",
    description="Inspect supported physical measurement dimensions, unit symbols, and examples.",
)
async def list_units_endpoint() -> Dict[str, Any]:
    return {"categories": get_supported_categories()}
