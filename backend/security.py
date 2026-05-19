from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/status")
async def security_status():
    return {
        "status": "ok",
        "defender_mode": "mock",
        "defender_for_iot": "simulated",
        "sentinel": "not_configured",
    }


@router.get("/risk/latest")
async def latest_security_risk(
    assetId: str = Query("motor-A"),
):
    return {
        "status": "ok",
        "mode": "mock",
        "source": "mock-defender-iot",
        "asset_id": assetId,
        "security_risk": "HIGH",
        "risk_score": 85,
        "alerts": [
            {
                "id": "DFIOT-MOCK-001",
                "severity": "High",
                "title": "Suspicious OT communication pattern",
                "description": "Unexpected communication from engineering workstation to motor controller.",
                "asset_id": assetId,
                "source": "Microsoft Defender for IoT",
                "status": "simulated",
            }
        ],
        "safety_signal": {
            "security_blocker": True,
            "approval_required": True,
            "dispatch_allowed": False,
            "reason": "High OT security risk detected. Supervisor approval is required before critical dispatch.",
            "evidence": [
                "High: Suspicious OT communication pattern"
            ],
        },
    }


@router.get("/defender/alerts")
async def defender_alerts(
    assetId: str = Query("motor-A"),
):
    risk = await latest_security_risk(assetId=assetId)
    return {
        "status": "ok",
        "mode": risk["mode"],
        "source": risk["source"],
        "asset_id": assetId,
        "alerts": risk["alerts"],
    }
