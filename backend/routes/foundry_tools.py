from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/foundry", tags=["foundry-tools"])

@router.get("/health")
async def foundry_health():
    return {
        "status": "ok",
        "service": "TwinOpsAI Foundry Tools",
        "message": "Foundry can reach backend"
    }

WORK_ORDERS: dict[str, dict[str, Any]] = {}


class WorkOrderCreateRequest(BaseModel):
    asset_id: str = "motor-A"
    title: str = "Inspect motor-A vibration anomaly"
    priority: str = "Critical"
    recommended_action: str = "Inspect bearing, lubrication, and shaft alignment"
    created_by: str = "TwinOpsAI Foundry Agent"


class ApprovalRequest(BaseModel):
    approved_by: str = "supervisor"
    note: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_risk(vibration: float, temperature: float) -> str:
    if vibration >= 4.0 or temperature >= 85:
        return "CRITICAL"
    if vibration >= 3.5 or temperature >= 75:
        return "WARNING"
    return "NORMAL"


@router.get("/impact")
async def get_foundry_impact(machineId: str = "motor-A", minutes: int = 1440):
    latest_telemetry = {
        "deviceId": machineId,
        "vibration": 4.2,
        "temperature": 82,
        "energyLoad": 23,
        "status": "FAULT",
        "timestamp": now_iso(),
    }

    risk_level = classify_risk(
        vibration=float(latest_telemetry["vibration"]),
        temperature=float(latest_telemetry["temperature"]),
    )

    downtime_minutes = 45
    cost_per_minute = 500
    estimated_cost_avoided = downtime_minutes * cost_per_minute

    return {
        "status": "ok",
        "run_id": f"foundry-impact-{uuid4().hex[:8]}",
        "risk_level": risk_level,
        "affected_asset": machineId,
        "impacted_assets": ["motor-B", "conveyor-C"],
        "latest_telemetry": latest_telemetry,
        "evidence": {
            "telemetry": [
                "vibration 4.2 exceeds critical threshold 4.0",
                "temperature 82 is above warning threshold 75",
            ],
            "digital_twin": [
                "motor-A feeds motor-B",
                "motor-B feeds conveyor-C",
                "conveyor-C supports packaging line",
            ],
            "sop": [
                "SOP-MA-101 recommends bearing inspection when vibration spike is detected",
                "Check lubrication and shaft alignment before restart",
            ],
            "business_assumptions": {
                "estimated_downtime_minutes": downtime_minutes,
                "cost_per_minute": cost_per_minute,
            },
        },
        "agent_flow": [
            {
                "agent": "Sensor Agent",
                "decision": f"{risk_level} anomaly detected",
            },
            {
                "agent": "Digital Twin Agent",
                "decision": "motor-B and conveyor-C may be impacted",
            },
            {
                "agent": "Maintenance Agent",
                "decision": "Bearing, lubrication, and shaft alignment should be inspected",
            },
            {
                "agent": "Energy Agent",
                "decision": "Reduce motor load before maintenance window",
            },
            {
                "agent": "Safety Agent",
                "decision": "Supervisor approval required before dispatch",
            },
            {
                "agent": "Business Impact Agent",
                "decision": f"Estimated cost avoided: {estimated_cost_avoided} THB",
            },
        ],
        "action_plan": {
            "root_cause": "Possible bearing wear, lubrication issue, or shaft misalignment",
            "recommended_actions": [
                "Create critical maintenance work order",
                "Inspect bearing condition",
                "Check lubrication level",
                "Check shaft alignment",
                "Reduce motor load before maintenance window",
                "Request supervisor approval before dispatch",
            ],
            "approval_required": risk_level == "CRITICAL",
        },
        "work_order_draft": {
            "asset_id": machineId,
            "title": f"Inspect {machineId} vibration anomaly",
            "priority": "Critical" if risk_level == "CRITICAL" else "Medium",
            "status": "Draft",
        },
        "approval": {
            "required": risk_level == "CRITICAL",
            "status": "pending" if risk_level == "CRITICAL" else "not_required",
            "policy": "Critical work orders require supervisor approval before dispatch.",
            "next_step": "Request supervisor approval before dispatch."
            if risk_level == "CRITICAL"
            else "Dispatch allowed.",
        },
        "business_impact": {
            "estimated_downtime_minutes": downtime_minutes,
            "cost_per_minute": cost_per_minute,
            "estimated_cost_avoided": estimated_cost_avoided,
            "oee_impact": "High",
            "priority": "P1",
        },
        "generated_at": now_iso(),
    }


@router.get("/twins/{twinId}/dependencies")
async def get_twin_dependencies(twinId: str):
    return {
        "status": "ok",
        "twin_id": twinId,
        "dependency_path": ["motor-A", "motor-B", "conveyor-C"]
        if twinId == "motor-A"
        else [],
        "impacted_assets": ["motor-B", "conveyor-C"] if twinId == "motor-A" else [],
        "evidence": [
            "motor-A feeds motor-B",
            "motor-B feeds conveyor-C",
            "conveyor-C supports packaging line",
        ]
        if twinId == "motor-A"
        else ["No demo dependency found for this asset"],
    }


@router.get("/sop")
async def get_sop_recommendation(machineId: str = "motor-A"):
    return {
        "status": "ok",
        "machine_id": machineId,
        "sop_id": "SOP-MA-101",
        "root_cause": "Possible bearing wear, lubrication issue, or shaft misalignment",
        "recommended_actions": [
            "Inspect bearing condition",
            "Check lubrication level",
            "Check shaft alignment",
            "Verify vibration after maintenance",
        ],
        "evidence": [
            "SOP-MA-101 recommends bearing inspection for abnormal vibration",
            "SOP-MA-101 recommends lubrication and alignment check before restart",
        ],
    }


@router.get("/energy/recommendation")
async def get_energy_recommendation(machineId: str = "motor-A"):
    return {
        "status": "ok",
        "machine_id": machineId,
        "energy_load": 23,
        "recommendation": "Reduce motor load by 15% before maintenance window",
        "reason": "High vibration under high load can increase bearing damage risk",
        "estimated_energy_impact": "Medium",
    }


@router.post("/work-orders")
async def create_work_order(request: WorkOrderCreateRequest):
    work_order_id = f"WO-{uuid4().hex[:6].upper()}"

    work_order = {
        "id": work_order_id,
        "asset_id": request.asset_id,
        "title": request.title,
        "priority": request.priority,
        "recommended_action": request.recommended_action,
        "status": "Draft",
        "approval_status": "pending" if request.priority.lower() == "critical" else "not_required",
        "created_by": request.created_by,
        "created_at": now_iso(),
    }

    WORK_ORDERS[work_order_id] = work_order

    return {
        "status": "ok",
        "work_order": work_order,
    }


@router.post("/work-orders/{workOrderId}/approve")
async def approve_work_order(workOrderId: str, request: ApprovalRequest):
    work_order = WORK_ORDERS.get(workOrderId)

    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")

    work_order["status"] = "Approved"
    work_order["approval_status"] = "approved"
    work_order["approved_by"] = request.approved_by
    work_order["approval_note"] = request.note
    work_order["approved_at"] = now_iso()

    return {
        "status": "ok",
        "work_order": work_order,
    }


@router.post("/work-orders/{workOrderId}/dispatch")
async def dispatch_work_order(workOrderId: str):
    work_order = WORK_ORDERS.get(workOrderId)

    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")

    if work_order["priority"].lower() == "critical" and work_order.get("approval_status") != "approved":
        raise HTTPException(
            status_code=409,
            detail="Critical work order must be approved before dispatch.",
        )

    work_order["status"] = "Dispatched"
    work_order["dispatched_at"] = now_iso()

    return {
        "status": "ok",
        "work_order": work_order,
    }


@router.get("/reports/impact/latest")
async def get_latest_business_impact():
    return {
        "status": "ok",
        "business_impact": {
            "estimated_downtime_minutes": 45,
            "cost_per_minute": 500,
            "estimated_cost_avoided": 22500,
            "manual_sop_search_time_minutes": 15,
            "ai_sop_retrieval_time_minutes": 1,
            "manual_work_order_draft_time_minutes": 10,
            "ai_work_order_draft_time_minutes": 1,
            "oee_impact": "High",
            "roi_note": "TwinOpsAI reduces time from anomaly detection to maintenance decision.",
        },
        "generated_at": now_iso(),
    }
