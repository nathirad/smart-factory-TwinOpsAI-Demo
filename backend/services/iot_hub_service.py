import asyncio
import json
import os
import re
from typing import Any, Callable, Dict, Optional

try:
    from azure.eventhub.aio import EventHubConsumerClient
except ImportError:
    EventHubConsumerClient = None

_latest_telemetry: Optional[Dict[str, Any]] = None
_client: Optional[Any] = None
_task: Optional[asyncio.Task] = None
_telemetry_handler: Optional[Callable[[Dict[str, Any]], None]] = None


def set_telemetry_handler(handler: Callable[[Dict[str, Any]], None]) -> None:
    global _telemetry_handler
    _telemetry_handler = handler


def is_eventhub_sdk_available() -> bool:
    return EventHubConsumerClient is not None


def _parse_telemetry(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    obj = json.loads(raw)

    # Case 1: TypeScript simulator sends clean JSON directly
    if isinstance(obj, dict) and "deviceId" in obj:
        return obj

    # Case 2: az iot device simulate wraps payload inside data string and adds #1
    if isinstance(obj, dict) and isinstance(obj.get("data"), str):
        data_text = obj["data"].strip()
        data_text = re.sub(r"\s+#\d+$", "", data_text)
        return json.loads(data_text)

    return obj


async def _on_event(partition_context, event):
    global _latest_telemetry

    try:
        raw = event.body_as_str(encoding="utf-8")
        telemetry = _parse_telemetry(raw)

        _latest_telemetry = telemetry
        if _telemetry_handler:
            _telemetry_handler(telemetry)
        print("Received telemetry from IoT Hub:", telemetry)

        await partition_context.update_checkpoint(event)

    except Exception as error:
        print("Failed to parse IoT Hub event:", error)


async def start_iot_hub_listener():
    global _client, _task

    use_azure = os.getenv("USE_AZURE", "false").lower() == "true"
    if not use_azure:
        print("USE_AZURE=false, IoT Hub listener disabled")
        return

    if EventHubConsumerClient is None:
        print("azure-eventhub is not installed, IoT Hub listener disabled")
        return

    conn_str = os.getenv("IOTHUB_EVENTHUB_CONNECTION_STRING")
    consumer_group = os.getenv("IOTHUB_CONSUMER_GROUP", "twinops-cg")

    if not conn_str:
        print("Missing IOTHUB_EVENTHUB_CONNECTION_STRING")
        return

    _client = EventHubConsumerClient.from_connection_string(
        conn_str=conn_str,
        consumer_group=consumer_group,
    )

    _task = asyncio.create_task(
        _client.receive(
            on_event=_on_event,
            starting_position="@latest",
        )
    )

    print(f"IoT Hub listener started with consumer group: {consumer_group}")


async def stop_iot_hub_listener():
    global _client, _task

    if _task:
        _task.cancel()

    if _client:
        await _client.close()

    print("IoT Hub listener stopped")


def get_latest_telemetry():
    return _latest_telemetry
