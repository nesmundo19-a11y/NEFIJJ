import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import ActionButton from "../components/ActionButton";
import EvidenceImage from "../components/EvidenceImage";
import { IncidentBadges } from "../components/IncidentBadges";

const NEXT_STATUS = {
  pendiente: "en_proceso",
  en_proceso: "resuelta",
};

export default function IncidentsScreen({ navigation, route }) {
  const { user, logout } = useAuth();
  const isMyReports = route.name === "MyReports";
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
        <Text style={styles.meta}>
          Reportado: {new Date(item.created_at).toLocaleString()}
        </Text>
        {canUpdate ? (
          <ActionButton
            onPress={() => changeStatus(item)}
            title={item.status === "pendiente" ? "Iniciar atención" : "Marcar resuelta"}
            variant="primary"
          />
        ) : null}
      </View>
    );
  }

  return (
    <View style={styles.page}>
      <View style={styles.header}>
        <View>
          <Text style={styles.welcome}>{isMyReports ? "Mis reportes" : `Hola, ${user.username}`}</Text>
          {!isMyReports ? <Text style={styles.role}>{user.role}</Text> : null}
        </View>
        <ActionButton
          compact
          fullWidth={false}
          onPress={handleLogout}
          title="Salir"
          variant="quiet"
        />
      </View>
      {!isMyReports ? (
        <View style={styles.actions}>
          <ActionButton
            onPress={() => navigation.navigate("JoinOrganization")}
            title="Unirse a otra organización"
            variant="quiet"
          />
          {user.role === "user" ? (
            <ActionButton
              onPress={() => navigation.navigate("CreateIncident")}
              title="Reportar incidencia"
            />
          ) : null}
          <ActionButton
            onPress={() => navigation.navigate("Emergencies")}
            title="Protocolos de emergencia"
            variant="secondary"
          />
        </View>
      ) : null}
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
    gap: 10,
    marginBottom: 12,
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
