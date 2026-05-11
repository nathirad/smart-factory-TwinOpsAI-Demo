import { Client, Message } from "azure-iot-device";
import { Mqtt } from "azure-iot-device-mqtt";

const connStr = process.env.IOTHUB_DEVICE_CONNECTION_STRING;

if (!connStr) {
  console.error("Missing IOTHUB_DEVICE_CONNECTION_STRING");
  process.exit(1);
}

const client = Client.fromConnectionString(connStr, Mqtt);

function createTelemetry() {
  return {
    deviceId: "simDevice01",
    timestamp: new Date().toISOString(),
    vibration: Number((2 + Math.random() * 2).toFixed(2)),
    temperature: Number((70 + Math.random() * 8).toFixed(2)),
    energyLoad: Number((15 + Math.random() * 6).toFixed(2)),
    status: Math.random() > 0.85 ? "WARN" : "NORMAL"
  };
}

async function sendTelemetry() {
  const telemetry = createTelemetry();

  const message = new Message(JSON.stringify(telemetry));
  message.contentType = "application/json";
  message.contentEncoding = "utf-8";

  await client.sendEvent(message);

  console.log("Sent telemetry:", telemetry);
}

async function main() {
  await client.open();
  console.log("Device simulator connected to Azure IoT Hub");

  await sendTelemetry();

  setInterval(() => {
    sendTelemetry().catch((error) => {
      console.error("Failed to send telemetry:", error);
    });
  }, 5000);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
