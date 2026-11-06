import { useState } from "react";
import {
  Button,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

export default function OrganizationSelectScreen({ navigation }) {
  const { user, selectOrganization, logout } = useAuth();
  const [error, setError] = useState("");
  const [savingId, setSavingId] = useState(null);
  const organizations = user?.organizations ?? [];

  async function handleSelect(organizationId) {
    setSavingId(String(organizationId));
    setError("");
    try {
      await selectOrganization(organizationId);
      if (String(user.active_organization_id) === String(organizationId)) {
        navigation.goBack();
      }
    } catch (selectionError) {
      setError(getApiErrorMessage(selectionError));
    } finally {
      setSavingId(null);
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch (logoutError) {
      setError(getApiErrorMessage(logoutError));
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>Selecciona una organización</Text>
      <Text style={styles.subtitle}>
        Tus incidencias y permisos dependen de la organización activa.
      </Text>
      {organizations.map((membership) => {
        const isActive = membership.organization_status === "active";
        const isSelected =
          String(membership.organization_id) ===
          String(user.active_organization_id);
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: !isActive, selected: isSelected }}
            disabled={!isActive || savingId !== null}
            key={membership.organization_id}
            onPress={() => handleSelect(membership.organization_id)}
            style={[
              styles.organization,
              isSelected && styles.selectedOrganization,
              !isActive && styles.disabledOrganization,
            ]}
          >
            <View style={styles.organizationText}>
              <Text style={styles.organizationName}>
                {membership.organization_name}
              </Text>
              <Text style={styles.organizationDetail}>
                {isActive ? membership.role : "Organización suspendida"}
              </Text>
            </View>
            <Text style={styles.action}>
              {savingId === String(membership.organization_id)
                ? "Guardando…"
                : isSelected
                  ? "Activa"
                  : isActive
                    ? "Usar"
                    : ""}
            </Text>
          </Pressable>
        );
      })}
      {!organizations.length ? (
        <Text style={styles.empty}>
          Esta cuenta todavía no tiene una organización activa. Solicita una
          invitación al administrador de tu organización.
        </Text>
      ) : null}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Button onPress={handleLogout} title="Cerrar sesión" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    gap: 12,
    padding: 20,
    backgroundColor: "#f4f7f6",
  },
  title: {
    color: "#172321",
    fontSize: 22,
    fontWeight: "700",
  },
  subtitle: {
    marginBottom: 8,
    color: "#52615e",
  },
  organization: {
    minHeight: 72,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 10,
    backgroundColor: "#ffffff",
  },
  selectedOrganization: {
    borderColor: "#0b6b63",
  },
  disabledOrganization: {
    opacity: 0.55,
  },
  organizationText: {
    flex: 1,
  },
  organizationName: {
    color: "#172321",
    fontWeight: "700",
  },
  organizationDetail: {
    marginTop: 4,
    color: "#52615e",
    textTransform: "capitalize",
  },
  action: {
    color: "#075b55",
    fontWeight: "700",
  },
  empty: {
    marginVertical: 16,
    color: "#52615e",
    lineHeight: 21,
  },
  error: {
    color: "#a42323",
  },
});
