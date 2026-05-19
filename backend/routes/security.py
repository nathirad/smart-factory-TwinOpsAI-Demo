from fastapi import APIRouter, HTTPException, Query

from services.defender_iot_service import (
    get_defender_security_risk,
    get_security_status,
)

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/status")
async def security_status():
    return get_security_status()


@router.get("/defender/alerts")
async def defender_alerts(
    assetId: str = Query("motor-A"),
    hours: int = Query(24, ge=1, le=168),
):
    try:
        result = await get_defender_security_risk(asset_id=assetId, hours=hours)
        return {
            "status": result["status"],
            "mode": result["mode"],
            "source": result["source"],
            "asset_id": result["asset_id"],
            "alerts": result["alerts"],
            "generated_at": result["generated_at"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/risk/latest")
async def latest_security_risk(
    assetId: str = Query("motor-A"),
    hours: int = Query(24, ge=1, le=168),
):
    try:
        return await get_defender_security_risk(asset_id=assetId, hours=hours)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))