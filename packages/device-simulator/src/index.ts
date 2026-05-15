import { Client, Message } from "azure-iot-device";
import { Mqtt } from "azure-iot-device-mqtt";

const connStr = process.env.IOTHUB_DEVICE_CONNECTION_STRING;
const iotDeviceId = process.env.DEVICE_ID ?? "simDevice01";

if (!connStr) {
  console.error("Missing IOTHUB_DEVICE_CONNECTION_STRING");
  process.exit(1);
}

const client = Client.fromConnectionString(connStr, Mqtt);

const assets = [
  {
    deviceId: iotDeviceId,
    machineId: "motor-A",
    vibrationBase: 2.2,
    temperatureBase: 72,
    energyBase: 16,
  },
  {
    deviceId: iotDeviceId,
    machineId: "motor-B",
    vibrationBase: 2.6,
    temperatureBase: 74,
    energyBase: 18,
  },
  {
    deviceId: iotDeviceId,
    machineId: "conveyor-C",
    vibrationBase: 1.4,
    temperatureBase: 62,
    energyBase: 12,
  },
];

function randomNumber(base: number, range: number) {
  return Number((base + Math.random() * range).toFixed(2));
}

function createTelemetry(asset: (typeof assets)[number]) {
  const isWarn = Math.random() > 0.85;

  return {
    deviceId: asset.deviceId,
    machineId: asset.machineId,
    timestamp: new Date().toISOString(),
    vibration: isWarn
      ? randomNumber(3.6, 0.8)
      : randomNumber(asset.vibrationBase, 0.8),
    temperature: isWarn
      ? randomNumber(77, 4)
      : randomNumber(asset.temperatureBase, 5),
    energyLoad: isWarn
      ? randomNumber(20.5, 3)
      : randomNumber(asset.energyBase, 4),
    status: isWarn ? "WARN" : "NORMAL",
  };
}

async function sendTelemetryForAsset(asset: (typeof assets)[number]) {
  const telemetry = createTelemetry(asset);

  const message = new Message(JSON.stringify(telemetry));
  message.contentType = "application/json";
  message.contentEncoding = "utf-8";

  await client.sendEvent(message);

  console.log("Sent telemetry:", telemetry);
}

async function sendTelemetryBatch() {
  for (const asset of assets) {
    await sendTelemetryForAsset(asset);
  }
}

async function main() {
  await client.open();
  console.log("Device simulator connected to Azure IoT Hub");

  await sendTelemetryBatch();

  setInterval(() => {
    sendTelemetryBatch().catch((error) => {
      console.error("Failed to send telemetry:", error);
    });
  }, 5000);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});