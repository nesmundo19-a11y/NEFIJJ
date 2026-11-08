import { useRef, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import ActionButton from "../components/ActionButton";

const INVITATION_CODE_PATTERN = /^[A-Za-z0-9_-]{43}$/;

export default function JoinOrganizationScreen() {
  const { refreshMemberships } = useAuth();
  const [permission, requestPermission] = useCameraPermissions();
  const [code, setCode] = useState("");
  const [invitation, setInvitation] = useState(null);
  const [locationId, setLocationId] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [joining, setJoining] = useState(false);
  const [joinedOrganizationId, setJoinedOrganizationId] = useState(null);
  const [error, setError] = useState("");
  const scanHandled = useRef(false);

  async function previewInvitation(value = code) {
    const normalizedCode = value.trim();
    setCode(normalizedCode);
    setInvitation(null);
    setLocationId(null);
    setError("");
    if (!INVITATION_CODE_PATTERN.test(normalizedCode)) {
      setError(
        "El código no tiene el formato de una invitación NEFIJJ. El QR de Expo Go no es una invitación.",
      );
      return;
    }

    setLoadingPreview(true);
    try {
      const { data } = await api.post("/memberships/invitations/preview/", {
        code: normalizedCode,
      });
      setInvitation(data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoadingPreview(false);
    }
  }

  async function startScanning() {
    setError("");
    try {
      const cameraPermission =
        permission?.granted ? permission : await requestPermission();
      if (!cameraPermission?.granted) {
        setError("Se necesita permiso de cámara para escanear. También puedes escribir el código.");
        return;
      }
      scanHandled.current = false;
      setScanning(true);
    } catch {
      setError("No se pudo solicitar permiso de cámara. Puedes ingresar el código manualmente.");
    }
  }

  function handleBarcodeScanned({ data }) {
    if (scanHandled.current) {
      return;
    }
    scanHandled.current = true;
    setScanning(false);
    previewInvitation(data);
  }

  async function joinOrganization() {
    if (!invitation || !locationId) {
      setError("Selecciona una sede activa antes de continuar.");
      return;
    }
    setJoining(true);
    setError("");
    try {
      await api.post("/memberships/join/", {
        code: code.trim(),
        location_id: locationId,
      });
      setJoinedOrganizationId(invitation.organization_id);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
      setJoining(false);
      return;
    }

    try {
      await refreshMemberships(invitation.organization_id);
    } catch (requestError) {
      setError(
        `La invitación fue aceptada, pero no se pudo actualizar tu sesión. ${getApiErrorMessage(requestError)}`,
      );
    } finally {
      setJoining(false);
    }
  }

  async function refreshAccess() {
    setJoining(true);
    setError("");
    try {
      await refreshMemberships(joinedOrganizationId);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setJoining(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Vincular una organización</Text>
      <Text style={styles.description}>
        Inicia sesión con una cuenta NEFIJJ existente. Escanea un QR de invitación
        o escribe su código; el QR de desarrollo de Expo Go no sirve para vincularte.
      </Text>

      {scanning ? (
        <View style={styles.cameraFrame}>
          <CameraView
            barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            onBarcodeScanned={handleBarcodeScanned}
            style={styles.camera}
          />
          <ActionButton
            onPress={() => setScanning(false)}
            title="Cancelar escaneo"
            variant="quiet"
          />
        </View>
      ) : (
        <ActionButton onPress={startScanning} title="Escanear QR de invitación" />
      )}

      {permission && !permission.granted ? (
        <Text style={styles.help}>
          La cámara no está disponible sin permiso. Puedes continuar con el código manual.
        </Text>
      ) : null}

      <Text style={styles.label}>Código de invitación</Text>
      <TextInput
        accessibilityLabel="Código de invitación"
        autoCapitalize="none"
        autoCorrect={false}
        editable={!loadingPreview && !joining}
        onChangeText={setCode}
        placeholder="Pega o escribe el código del QR"
        style={styles.input}
        value={code}
      />
      <ActionButton
        disabled={loadingPreview || joining}
        onPress={() => previewInvitation()}
        title={loadingPreview ? "Verificando código…" : "Verificar invitación"}
        variant="secondary"
      />

      {loadingPreview ? <ActivityIndicator color="#0b6b63" /> : null}

      {invitation ? (
        <View style={styles.invitationCard}>
          <Text style={styles.organizationName}>{invitation.organization_name}</Text>
          <Text style={styles.help}>Selecciona la sede a la que perteneces:</Text>
          {invitation.locations.length ? (
            invitation.locations.map((location) => {
              const selected = String(locationId) === String(location.id);
              return (
                <ActionButton
                  key={location.id}
                  onPress={() => setLocationId(location.id)}
                  title={location.name}
                  variant={selected ? "primary" : "quiet"}
                />
              );
            })
          ) : (
            <Text style={styles.help}>
              Esta organización no tiene sedes activas. Contacta a su administrador.
            </Text>
          )}
          <ActionButton
            disabled={!locationId || joining || !invitation.locations.length}
            onPress={joinOrganization}
            title={joining ? "Vinculando…" : "Confirmar y unirme"}
          />
        </View>
      ) : null}

      {joinedOrganizationId !== null ? (
        <ActionButton
          disabled={joining}
          onPress={refreshAccess}
          title={joining ? "Actualizando acceso…" : "Actualizar mi acceso"}
          variant="secondary"
        />
      ) : null}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    gap: 14,
    padding: 18,
    backgroundColor: "#f4f7f6",
  },
  title: {
    color: "#172321",
    fontSize: 21,
    fontWeight: "700",
  },
  description: {
    color: "#52615e",
    lineHeight: 21,
  },
  label: {
    color: "#263238",
    fontWeight: "700",
  },
  input: {
    minHeight: 48,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 8,
    backgroundColor: "#ffffff",
    color: "#172321",
  },
  cameraFrame: {
    gap: 10,
    overflow: "hidden",
    borderRadius: 12,
  },
  camera: {
    height: 300,
    width: "100%",
  },
  invitationCard: {
    gap: 12,
    padding: 14,
    borderRadius: 12,
    backgroundColor: "#ffffff",
  },
  organizationName: {
    color: "#172321",
    fontSize: 17,
    fontWeight: "700",
  },
  help: {
    color: "#52615e",
    lineHeight: 20,
  },
  error: {
    color: "#a42323",
  },
});
