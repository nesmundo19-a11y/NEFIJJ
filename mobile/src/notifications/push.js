import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";

import api from "../api/client";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerPushDevice() {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("emergency-alerts", {
      name: "Alertas de emergencia",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      sound: "default",
    });
  }

  let { status } = await Notifications.getPermissionsAsync();
  if (status !== "granted") {
    ({ status } = await Notifications.requestPermissionsAsync());
  }
  if (status !== "granted") {
    return { status: "permission-denied" };
  }

  const projectId =
    Constants.easConfig?.projectId ?? Constants.expoConfig?.extra?.eas?.projectId;
  if (!projectId) {
    throw new Error(
      "Falta el ID del proyecto EAS. Configúralo antes de habilitar notificaciones push.",
    );
  }

  const token = await Notifications.getExpoPushTokenAsync({ projectId });
  const { data } = await api.post("/push-devices/", {
    expo_push_token: token.data,
    platform: Platform.OS === "ios" ? "ios" : "android",
  });
  await SecureStore.setItemAsync("push_device_id", String(data.id));
  return { status: "registered" };
}

export async function unregisterPushDevice() {
  const deviceId = await SecureStore.getItemAsync("push_device_id");
  if (!deviceId) {
    return;
  }
  await api.delete(`/push-devices/${deviceId}/`);
  await SecureStore.deleteItemAsync("push_device_id");
}
