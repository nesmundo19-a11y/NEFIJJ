import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Button,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import EvidenceImage from "../components/EvidenceImage";
import { IncidentBadges } from "../components/IncidentBadges";

const NEXT_STATUS = {
  pendiente: "en_proceso",
  en_proceso: "resuelta",
};

export default function IncidentsScreen({ navigation }) {
  const { user, logout } = useAuth();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  const loadIncidents = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get("/incidents/");
      setIncidents(data.results);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadIncidents();
    }, [loadIncidents]),
  );

  async function changeStatus(incident) {
    const nextStatus = NEXT_STATUS[incident.status];
    if (!nextStatus) {
      return;
    }

    setActionError("");
    try {
      await api.patch(`/incidents/${incident.id}/status/`, { status: nextStatus });
      await loadIncidents();
    } catch (requestError) {
      setActionError(getApiErrorMessage(requestError));
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      setActionError("No se pudo cerrar la sesión segura. Inténtalo de nuevo.");
    }
  }

  function renderIncident({ item }) {
    const canUpdate =
      user.role === "technician" &&
      item.assigned_to === user.id &&
      Boolean(NEXT_STATUS[item.status]);

    return (
      <View style={styles.card}>
        <View style={styles.cardHeading}>
          <Text style={styles.incidentTitle}>{item.title}</Text>
        </View>
        <IncidentBadges priority={item.priority} status={item.status} />
        <Text style={styles.description}>{item.description}</Text>
        {item.evidence_image ? <EvidenceImage uri={item.evidence_image} /> : null}
        <Text style={styles.meta}>{new Date(item.created_at).toLocaleDateString()}</Text>
        {canUpdate ? (
          <Pressable
            accessibilityRole="button"
            onPress={() => changeStatus(item)}
            style={styles.secondaryButton}
          >
            <Text style={styles.secondaryButtonText}>
              {item.status === "pendiente" ? "Iniciar atención" : "Marcar resuelta"}
            </Text>
          </Pressable>
        ) : null}
      </View>
    );
  }

  return (
    <View style={styles.page}>
      <View style={styles.header}>
        <View>
          <Text style={styles.welcome}>Hola, {user.username}</Text>
          <Text style={styles.role}>{user.role}</Text>
        </View>
        <Button onPress={handleLogout} title="Salir" />
      </View>
      <View style={styles.actions}>
        {user.role === "user" ? (
          <Pressable
            accessibilityRole="button"
            onPress={() => navigation.navigate("CreateIncident")}
            style={styles.primaryButton}
          >
            <Text style={styles.primaryButtonText}>Reportar incidencia</Text>
          </Pressable>
        ) : null}
        <Pressable
          accessibilityRole="button"
          onPress={() => navigation.navigate("Emergencies")}
          style={styles.secondaryButton}
        >
          <Text style={styles.secondaryButtonText}>Protocolos de emergencia</Text>
        </Pressable>
      </View>
      {actionError ? <Text accessibilityRole="alert" style={styles.error}>{actionError}</Text> : null}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {loading ? (
        <ActivityIndicator color="#0b6b63" size="large" style={styles.loading} />
      ) : (
        <FlatList
          contentContainerStyle={incidents.length === 0 ? styles.emptyList : styles.list}
          data={incidents}
          keyExtractor={(item) => String(item.id)}
          refreshControl={
            <RefreshControl
              onRefresh={() => {
                setRefreshing(true);
                loadIncidents();
              }}
              refreshing={refreshing}
            />
          }
          ListEmptyComponent={<Text style={styles.empty}>No hay incidencias para mostrar.</Text>}
          renderItem={renderIncident}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    paddingHorizontal: 16,
    backgroundColor: "#f4f7f6",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 16,
  },
  welcome: {
    color: "#172321",
    fontSize: 18,
    fontWeight: "700",
  },
  role: {
    marginTop: 2,
    color: "#52615e",
    textTransform: "capitalize",
  },
  actions: {
    gap: 8,
    marginBottom: 12,
  },
  primaryButton: {
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    backgroundColor: "#0b6b63",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  secondaryButton: {
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#0b6b63",
    borderRadius: 8,
  },
  secondaryButtonText: {
    color: "#075b55",
    fontWeight: "600",
  },
  list: {
    paddingBottom: 24,
  },
  emptyList: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  card: {
    marginBottom: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2eae7",
    borderRadius: 16,
    backgroundColor: "#ffffff",
    elevation: 2,
  },
  cardHeading: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  incidentTitle: {
    flex: 1,
    color: "#172321",
    fontSize: 16,
    fontWeight: "700",
  },
  description: {
    marginTop: 8,
    color: "#34433f",
  },
  meta: {
    marginTop: 12,
    color: "#52615e",
    fontSize: 12,
  },
  loading: {
    marginTop: 32,
  },
  empty: {
    color: "#52615e",
  },
  error: {
    marginVertical: 6,
    color: "#a42323",
  },
});
