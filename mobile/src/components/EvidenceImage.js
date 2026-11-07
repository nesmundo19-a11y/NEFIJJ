import { useEffect, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import * as SecureStore from "expo-secure-store";

export default function EvidenceImage({ uri }) {
  const [headers, setHeaders] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [credentialError, setCredentialError] = useState(false);

  useEffect(() => {
    let active = true;
    setHeaders(null);
    setLoadError("");
    setCredentialError(false);
    Promise.all([
      SecureStore.getItemAsync("access_token"),
      SecureStore.getItemAsync("active_organization_id"),
    ])
      .then(([access, organizationId]) => {
        if (!active) {
          return;
        }
        if (!access) {
          setCredentialError(true);
          return;
        }
        const requestHeaders = {};
        requestHeaders.Authorization = `Bearer ${access}`;
        if (organizationId) {
          requestHeaders["X-Organization-ID"] = organizationId;
        }
        setHeaders(requestHeaders);
      })
      .catch(() => {
        if (active) {
          setCredentialError(true);
        }
      });

    return () => {
      active = false;
    };
  }, [uri]);

  if (credentialError) {
    return <Text style={styles.message}>No se pudo preparar la foto protegida.</Text>;
  }
  if (!headers) {
    return null;
  }

  return (
    <View>
      <Image
        accessibilityLabel="Foto de evidencia de la incidencia"
        onError={() => setLoadError("No se pudo cargar la foto.")}
        source={{ uri, headers }}
        style={styles.image}
      />
      {loadError ? <Text style={styles.message}>{loadError}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  image: {
    width: "100%",
    height: 190,
    marginTop: 12,
    borderRadius: 12,
    backgroundColor: "#e1e9e6",
  },
  message: {
    marginTop: 8,
    color: "#7a3030",
  },
});
