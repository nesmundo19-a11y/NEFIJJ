import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import QRCode from "react-native-qrcode-svg";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import ActionButton from "../components/ActionButton";

function formatDate(value) {
  return new Date(value).toLocaleString();
}

export default function InvitationManagementScreen({ route }) {
  const { user, activeMembership } = useAuth();
  const organizationId =
    route.params?.organizationId ?? user.active_organization_id;
  const organizationName =
    route.params?.organizationName ?? activeMembership?.organization_name;
  const [invitations, setInvitations] = useState([]);
  const [currentInvitation, setCurrentInvitation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [revokingId, setRevokingId] = useState(null);
  const [error, setError] = useState("");

  const loadInvitations = useCallback(async () => {
    if (!organizationId) {
      setError("Selecciona una organización activa antes de gestionar invitaciones.");
      setLoading(false);
      return;
    }
    setError("");
    try {
      const { data } = await api.get(
        `/organizations/${organizationId}/invitations/`,
        { headers: { "X-Organization-ID": String(organizationId) } },
      );
      setInvitations(data);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useFocusEffect(
    useCallback(() => {
      loadInvitations();
    }, [loadInvitations]),
  );

  async function createInvitation() {
    if (!organizationId) {
      setError("No hay una organización seleccionada.");
      return;
    }
    setCreating(true);
    setError("");
    try {
      const { data } = await api.post(
        `/organizations/${organizationId}/invitations/`,
        {},
        { headers: { "X-Organization-ID": String(organizationId) } },
      );
      setCurrentInvitation(data);
      await loadInvitations();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setCreating(false);
    }
  }

  async function revokeInvitation(invitationId) {
    setRevokingId(invitationId);
    setError("");
    try {
      await api.post(
        `/organizations/${organizationId}/invitations/${invitationId}/revoke/`,
        {},
        { headers: { "X-Organization-ID": String(organizationId) } },
      );
      if (currentInvitation?.id === invitationId) {
        setCurrentInvitation(null);
      }
      await loadInvitations();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setRevokingId(null);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>{organizationName ?? "Invitaciones"}</Text>
      <Text style={styles.description}>
        Genera un QR de un solo uso. Quien lo reciba debe iniciar sesión en NEFIJJ
        y elegir una sede activa para vincularse. El QR de Expo Go solo abre la
        app de desarrollo y no sirve como invitación.
      </Text>

      <ActionButton
        disabled={creating || !organizationId}
        onPress={createInvitation}
        title={creating ? "Generando invitación…" : "Generar invitación QR"}
      />

      {currentInvitation ? (
        <View style={styles.qrCard}>
          <Text style={styles.sectionTitle}>Invitación lista para escanear</Text>
          <View style={styles.qr}>
            <QRCode value={currentInvitation.code} size={220} />
          </View>
          <Text style={styles.codeLabel}>Código alternativo</Text>
          <Text selectable style={styles.code}>{currentInvitation.code}</Text>
          <Text style={styles.expiry}>
            Vence: {formatDate(currentInvitation.expires_at)}
          </Text>
          <Text style={styles.note}>
            El código se muestra solo ahora. No lo compartas públicamente.
          </Text>
          <ActionButton
            disabled={revokingId === currentInvitation.id}
            onPress={() => revokeInvitation(currentInvitation.id)}
            title={revokingId === currentInvitation.id ? "Revocando…" : "Revocar QR"}
            variant="quiet"
          />
        </View>
      ) : null}

      <Text style={styles.sectionTitle}>Invitaciones pendientes</Text>
      {loading ? (
        <ActivityIndicator color="#0b6b63" size="large" />
      ) : invitations.length ? (
        invitations.map((invitation) => (
          <View key={invitation.id} style={styles.invitation}>
            <View style={styles.invitationDetails}>
              <Text style={styles.invitationTitle}>
                Invitación #{invitation.id}
              </Text>
              <Text style={styles.expiry}>
                Vence: {formatDate(invitation.expires_at)}
              </Text>
            </View>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: revokingId === invitation.id }}
              disabled={revokingId === invitation.id}
              onPress={() => revokeInvitation(invitation.id)}
              style={styles.revokeButton}
            >
              <Text style={styles.revokeText}>
                {revokingId === invitation.id ? "…" : "Revocar"}
              </Text>
            </Pressable>
          </View>
        ))
      ) : (
        <Text style={styles.empty}>No hay invitaciones pendientes.</Text>
      )}
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
  qrCard: {
    alignItems: "center",
    gap: 10,
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#ffffff",
  },
  qr: {
    padding: 12,
    backgroundColor: "#ffffff",
  },
  sectionTitle: {
    color: "#172321",
    fontWeight: "700",
  },
  codeLabel: {
    alignSelf: "flex-start",
    color: "#52615e",
    fontSize: 13,
  },
  code: {
    color: "#172321",
    fontFamily: "monospace",
    textAlign: "center",
  },
  expiry: {
    color: "#52615e",
    fontSize: 13,
  },
  note: {
    color: "#52615e",
    fontSize: 13,
    textAlign: "center",
  },
  invitation: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 12,
    borderRadius: 10,
    backgroundColor: "#ffffff",
  },
  invitationDetails: {
    flex: 1,
    gap: 4,
  },
  invitationTitle: {
    color: "#172321",
    fontWeight: "600",
  },
  revokeButton: {
    minHeight: 40,
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  revokeText: {
    color: "#a42323",
    fontWeight: "700",
  },
  empty: {
    color: "#52615e",
  },
  error: {
    color: "#a42323",
  },
});
