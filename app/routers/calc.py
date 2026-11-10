"""API routes for safe AST calculator and commercial finance calculations."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.models import CalcRequest, CalcResponse, FinanceCalcRequest
from app.services.calc import calculate_finance, evaluate_expression

router = APIRouter(prefix="/calc", tags=["Calculator & Finance"])


@router.post(
    "",
    response_model=CalcResponse,
    summary="Safe AST mathematical expression evaluator",
    description="Evaluate arithmetic, powers, modulo, square roots, and trigonometric expressions using a sandboxed AST visitor (no eval or exec).",
)
async def calc_endpoint(payload: CalcRequest) -> Dict[str, Any]:
    try:
        return evaluate_expression(payload.expression)
    except ZeroDivisionError as zd_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "ZERO_DIVISION", "message": str(zd_err)},
        ) from zd_err
    except ValueError as val_err:
        raise HTTPException(
            status_code=422,
            detail={"code": "CALCULATION_ERROR", "message": str(val_err)},
        ) from val_err


@router.post(
    "/finance",
    summary="Finance and commercial calculator",
    description="Perform commercial math: discounts, sales tax / VAT, tip split, simple interest, compound interest, and loan EMI.",
)
async def finance_calc_endpoint(payload: FinanceCalcRequest) -> Dict[str, Any]:
    try:
        return calculate_finance(
            operation=payload.operation,
            amount=payload.amount,
            percent=payload.percent,
            value=payload.value,
            total=payload.total,
            old_value=payload.old_value,
            new_value=payload.new_value,
            original_price=payload.original_price,
            discount_percent=payload.discount_percent,
            tax_percent=payload.tax_percent,
            tax_included=payload.tax_included,
            bill_amount=payload.bill_amount,
            tip_percent=payload.tip_percent,
            num_people=payload.num_people,
            principal=payload.principal,
            rate_annual_percent=payload.rate_annual_percent,
            time_years=payload.time_years,
            compounding_frequency=payload.compounding_frequency,
            tenure_months=payload.tenure_months,
        )
    except ZeroDivisionError as zd_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "ZERO_DIVISION", "message": str(zd_err)},
        ) from zd_err
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail={"code": "FINANCE_CALC_ERROR", "message": str(val_err)},
        ) from val_err
