import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import * as SecureStore from "expo-secure-store";

import { refreshSessionAccessToken } from "../api/client";

export default function EvidenceImage({ uri }) {
  const [imageUri, setImageUri] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setImageUri(null);
    setLoadError("");
    setLoading(true);

    async function loadImage() {
      try {
        const [access, organizationId] = await Promise.all([
          SecureStore.getItemAsync("access_token"),
          SecureStore.getItemAsync("active_organization_id"),
        ]);
        if (!access) {
          throw new Error("Inicia sesión nuevamente para ver la foto.");
        }
        if (!FileSystem.cacheDirectory) {
          throw new Error("El dispositivo no permite guardar la foto temporalmente.");
        }

        const evidenceId = uri.split("/").filter(Boolean).slice(-2, -1)[0] ?? "image";
        const destination = `${FileSystem.cacheDirectory}evidence-${evidenceId}.image`;
        const headers = { Authorization: `Bearer ${access}` };
        if (organizationId) {
          headers["X-Organization-ID"] = organizationId;
        }

        let result = await FileSystem.downloadAsync(uri, destination, { headers });
        if (result.status === 401) {
          const renewedAccess = await refreshSessionAccessToken();
          headers.Authorization = `Bearer ${renewedAccess}`;
          result = await FileSystem.downloadAsync(uri, destination, { headers });
        }

        if (result.status !== 200) {
          await FileSystem.deleteAsync(result.uri, { idempotent: true });
          throw new Error(`El servidor respondió ${result.status} al cargar la foto.`);
        }
        if (result.mimeType && !result.mimeType.startsWith("image/")) {
          await FileSystem.deleteAsync(result.uri, { idempotent: true });
          throw new Error("El servidor no devolvió un archivo de imagen.");
        }

        if (active) {
          setImageUri(result.uri);
        }
      } catch (error) {
        if (active) {
          setLoadError(error.message || "No se pudo cargar la foto.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadImage();
    return () => {
      active = false;
    };
  }, [uri, attempt]);

  return (
    <View style={styles.container}>
      {loading ? (
        <View style={styles.loading}>
          <ActivityIndicator color="#0b6b63" />
          <Text style={styles.helper}>Cargando foto de evidencia…</Text>
        </View>
      ) : null}
      {imageUri ? (
        <Image
          accessibilityLabel="Foto de evidencia de la incidencia"
          onError={() => {
            setImageUri(null);
            setLoadError("No se pudo mostrar la foto descargada.");
          }}
          source={{ uri: imageUri }}
          style={styles.image}
        />
      ) : null}
      {loadError ? (
        <View style={styles.errorContainer}>
          <Text accessibilityRole="alert" style={styles.message}>{loadError}</Text>
          <Pressable
            accessibilityRole="button"
            onPress={() => setAttempt((current) => current + 1)}
            style={({ pressed }) => [styles.retryButton, pressed && styles.pressed]}
          >
            <Text style={styles.retryText}>Reintentar</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
  },
  loading: {
    minHeight: 120,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 14,
    backgroundColor: "#edf4f2",
  },
  helper: {
    color: "#52615e",
    fontSize: 13,
  },
  image: {
    width: "100%",
    height: 220,
    borderRadius: 14,
    backgroundColor: "#e1e9e6",
  },
  errorContainer: {
    alignItems: "flex-start",
    gap: 10,
    padding: 14,
    borderRadius: 14,
    backgroundColor: "#fff1f0",
  },
  message: {
    color: "#8f2722",
  },
  retryButton: {
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: "#0b6b63",
  },
  retryText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  pressed: {
    opacity: 0.78,
    transform: [{ scale: 0.98 }],
  },
});
