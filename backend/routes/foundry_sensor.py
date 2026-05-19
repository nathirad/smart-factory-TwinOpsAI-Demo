from fastapi import APIRouter, Query, HTTPException

from services.sensor_agent_service import (
    get_latest_sensor_telemetry,
    evaluate_sensor_anomaly,
    get_sensor_history,
)

router = APIRouter(prefix="/api/foundry/sensor", tags=["foundry-sensor"])


@router.get("/latest")
async def latest_sensor_telemetry(
    machineId: str = Query("motor-A"),
):
    try:
        return await get_latest_sensor_telemetry(machine_id=machineId)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/anomaly")
async def sensor_anomaly(
    machineId: str = Query("motor-A"),
):
    try:
        return await evaluate_sensor_anomaly(machine_id=machineId)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history")
async def sensor_history(
    machineId: str = Query("motor-A"),
    minutes: int = Query(60, ge=5, le=1440),
):
    try:
        return await get_sensor_history(machine_id=machineId, minutes=minutes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
