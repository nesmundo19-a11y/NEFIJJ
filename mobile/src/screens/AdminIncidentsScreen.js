import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Button,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
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

const STATUS_FILTERS = [
  { value: "", label: "Todas" },
  { value: "pendiente", label: "Pendientes" },
  { value: "en_proceso", label: "En proceso" },
  { value: "resuelta", label: "Resueltas" },
  { value: "cerrada", label: "Cerradas" },
];

async function fetchAllPages(endpoint) {
  const results = [];
  let page = 1;

  while (true) {
    const { data } = await api.get(endpoint, { params: { page } });
    results.push(...data.results);
    if (!data.next) {
      return results;
    }
    page += 1;
  }
}

export default function AdminIncidentsScreen({ navigation }) {
  const { user, logout } = useAuth();
  const [incidents, setIncidents] = useState([]);
  const [locations, setLocations] = useState([]);
  const [users, setUsers] = useState([]);
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [assignmentTarget, setAssignmentTarget] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [optionsError, setOptionsError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busyIncidentId, setBusyIncidentId] = useState(null);

  const locationNames = useMemo(
    () => new Map(locations.map((location) => [location.id, location.name])),
    [locations],
  );
  const usersById = useMemo(
    () => new Map(users.map((account) => [account.id, account])),
    [users],
  );

  const loadIncidents = useCallback(async () => {
    setError("");
    try {
      const params = {};
      if (locationFilter) {
        params.location = locationFilter;
      }
      if (statusFilter) {
        params.status = statusFilter;
      }
      const { data } = await api.get("/incidents/", { params });
      setIncidents(data.results);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [locationFilter, statusFilter]);

  useFocusEffect(
    useCallback(() => {
      loadIncidents();
    }, [loadIncidents]),
  );

  useEffect(() => {
    let active = true;
    Promise.all([fetchAllPages("/locations/"), fetchAllPages("/users/")])
      .then(([locationResults, userResults]) => {
        if (active) {
          setLocations(locationResults);
          setUsers(userResults.filter((account) => account.is_active));
        }
      })
      .catch((requestError) => {
        if (active) {
          setOptionsError(getApiErrorMessage(requestError));
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function assignTechnician(incident, technicianId) {
    setBusyIncidentId(incident.id);
    setActionError("");
    try {
      await api.patch(`/incidents/${incident.id}/assign/`, { assigned_to: technicianId });
      setAssignmentTarget(null);
      await loadIncidents();
    } catch (requestError) {
      setActionError(getApiErrorMessage(requestError));
    } finally {
      setBusyIncidentId(null);
    }
  }

  async function changeStatus(incident) {
    const nextStatus =
      incident.status === "resuelta"
        ? "cerrada"
        : incident.status === "cerrada"
          ? "en_proceso"
          : null;
    if (!nextStatus) {
      return;
    }

    setBusyIncidentId(incident.id);
    setActionError("");
    try {
      await api.patch(`/incidents/${incident.id}/status/`, { status: nextStatus });
      await loadIncidents();
    } catch (requestError) {
      setActionError(getApiErrorMessage(requestError));
    } finally {
      setBusyIncidentId(null);
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
    const assignedUser = usersById.get(item.assigned_to);
    const siteTechnicians = users.filter(
      (account) => account.role === "technician" && account.location_id === item.location_id,
    );
    const nextStatusLabel =
      item.status === "resuelta"
        ? "Cerrar incidencia"
        : item.status === "cerrada"
          ? "Reabrir en proceso"
          : null;
    const busy = busyIncidentId === item.id;

    return (
      <View style={styles.card}>
        <View style={styles.cardHeading}>
          <Text style={styles.incidentTitle}>{item.title}</Text>
        </View>
        <IncidentBadges priority={item.priority} status={item.status} />
        <Text style={styles.description}>{item.description}</Text>
        {item.evidence_image ? <EvidenceImage uri={item.evidence_image} /> : null}
        <Text style={styles.meta}>
          {locationNames.get(item.location_id) ?? `Sede ${item.location_id}`}
        </Text>
        <Text style={styles.meta}>
          Reportó: {usersById.get(item.reported_by)?.username ?? `usuario ${item.reported_by}`}
        </Text>
        <Text style={styles.meta}>
          Asignado a: {assignedUser?.username ?? "Sin asignar"}
        </Text>

        <Pressable
          accessibilityRole="button"
          disabled={busy || optionsError !== ""}
          onPress={() =>
            setAssignmentTarget(assignmentTarget === item.id ? null : item.id)
          }
          style={[styles.secondaryButton, busy && styles.disabled]}
        >
          <Text style={styles.secondaryButtonText}>
            {assignmentTarget === item.id ? "Cancelar asignación" : "Asignar técnico"}
          </Text>
        </Pressable>

        {assignmentTarget === item.id ? (
          <View style={styles.assignmentOptions}>
            {siteTechnicians.map((technician) => (
              <Pressable
                accessibilityRole="button"
                disabled={busy || item.assigned_to === technician.id}
                key={technician.id}
                onPress={() => assignTechnician(item, technician.id)}
                style={[
                  styles.choice,
                  item.assigned_to === technician.id && styles.selectedChoice,
                  busy && styles.disabled,
                ]}
              >
                <Text
                  style={[
                    styles.choiceText,
                    item.assigned_to === technician.id && styles.selectedChoiceText,
                  ]}
                >
                  {technician.username}
                </Text>
              </Pressable>
            ))}
            {item.assigned_to ? (
              <Pressable
                accessibilityRole="button"
                disabled={busy}
                onPress={() => assignTechnician(item, null)}
                style={[styles.choice, busy && styles.disabled]}
              >
                <Text style={styles.choiceText}>Quitar asignación</Text>
              </Pressable>
            ) : null}
            {!siteTechnicians.length ? (
              <Text style={styles.helper}>No hay técnicos activos en esta sede.</Text>
            ) : null}
          </View>
        ) : null}

        {nextStatusLabel ? (
          <Pressable
            accessibilityRole="button"
            disabled={busy}
            onPress={() => changeStatus(item)}
            style={[styles.primaryButton, busy && styles.disabled]}
          >
            <Text style={styles.primaryButtonText}>{nextStatusLabel}</Text>
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
          <Text style={styles.role}>Administración de incidencias</Text>
        </View>
        <Button onPress={handleLogout} title="Salir" />
      </View>

      <Pressable
        accessibilityRole="button"
        onPress={() => navigation.navigate("Emergencies")}
        style={styles.secondaryButton}
      >
        <Text style={styles.secondaryButtonText}>Protocolos de emergencia</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        onPress={() => navigation.navigate("CreateUser")}
        style={styles.secondaryButton}
      >
        <Text style={styles.secondaryButtonText}>Crear usuario</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        onPress={() => navigation.navigate("Categories")}
        style={styles.secondaryButton}
      >
        <Text style={styles.secondaryButtonText}>Administrar categorías</Text>
      </Pressable>

      <Text style={styles.filterLabel}>Sede</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow}>
        <FilterChip
          label="Todas"
          onPress={() => setLocationFilter("")}
          selected={!locationFilter}
        />
        {locations.map((location) => (
          <FilterChip
            key={location.id}
            label={location.name}
            onPress={() => setLocationFilter(String(location.id))}
            selected={locationFilter === String(location.id)}
          />
        ))}
      </ScrollView>

      <Text style={styles.filterLabel}>Estado</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow}>
        {STATUS_FILTERS.map((status) => (
          <FilterChip
            key={status.value || "all"}
            label={status.label}
            onPress={() => setStatusFilter(status.value)}
            selected={statusFilter === status.value}
          />
        ))}
      </ScrollView>

      {optionsError ? (
        <Text accessibilityRole="alert" style={styles.error}>{optionsError}</Text>
      ) : null}
      {actionError ? (
        <Text accessibilityRole="alert" style={styles.error}>{actionError}</Text>
      ) : null}
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
          ListEmptyComponent={
            <Text style={styles.empty}>No hay incidencias para estos filtros.</Text>
          }
          renderItem={renderIncident}
        />
      )}
    </View>
  );
}

function FilterChip({ label, onPress, selected }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.filterChip, selected && styles.selectedFilterChip]}
    >
      <Text style={[styles.filterChipText, selected && styles.selectedFilterChipText]}>
        {label}
      </Text>
    </Pressable>
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
    paddingVertical: 12,
  },
  welcome: {
    color: "#172321",
    fontSize: 18,
    fontWeight: "700",
  },
  role: {
    marginTop: 2,
    color: "#52615e",
  },
  filterLabel: {
    marginTop: 10,
    marginBottom: 6,
    color: "#263238",
    fontWeight: "700",
  },
  filterRow: {
    flexGrow: 0,
  },
  filterChip: {
    marginRight: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 18,
    backgroundColor: "#ffffff",
  },
  selectedFilterChip: {
    borderColor: "#0b6b63",
    backgroundColor: "#0b6b63",
  },
  filterChipText: {
    color: "#263238",
  },
  selectedFilterChipText: {
    color: "#ffffff",
    fontWeight: "600",
  },
  list: {
    paddingTop: 12,
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
    marginTop: 8,
    color: "#52615e",
    fontSize: 12,
  },
  secondaryButton: {
    minHeight: 40,
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
  primaryButton: {
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    borderRadius: 8,
    backgroundColor: "#0b6b63",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  assignmentOptions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  choice: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 18,
  },
  selectedChoice: {
    borderColor: "#0b6b63",
    backgroundColor: "#0b6b63",
  },
  choiceText: {
    color: "#263238",
  },
  selectedChoiceText: {
    color: "#ffffff",
  },
  helper: {
    color: "#52615e",
  },
  disabled: {
    opacity: 0.5,
  },
  loading: {
    marginTop: 32,
  },
  empty: {
    padding: 24,
    color: "#52615e",
    textAlign: "center",
  },
  error: {
    marginTop: 8,
    color: "#a42323",
  },
});
