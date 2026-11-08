import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
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
import ActionButton from "../components/ActionButton";
import EvidenceImage from "../components/EvidenceImage";
import { IncidentBadges } from "../components/IncidentBadges";

const STATUS_FILTERS = [
  { value: "", label: "Todas" },
  { value: "pendiente", label: "Pendientes" },
  { value: "en_proceso", label: "En proceso" },
  { value: "resuelta", label: "Resueltas" },
  { value: "cerrada", label: "Cerradas" },
];

const PRIORITY_FILTERS = [
  { value: "", label: "Todas" },
  { value: "baja", label: "Baja" },
  { value: "media", label: "Media" },
  { value: "alta", label: "Alta" },
  { value: "critica", label: "Crítica" },
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

export default function AdminIncidentsScreen({ navigation, route }) {
  const { user, logout } = useAuth();
  const [incidents, setIncidents] = useState([]);
  const [locations, setLocations] = useState([]);
  const [users, setUsers] = useState([]);
  const [categories, setCategories] = useState([]);
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [assignmentTarget, setAssignmentTarget] = useState(null);
  const [historyByIncident, setHistoryByIncident] = useState({});
  const [expandedHistoryId, setExpandedHistoryId] = useState(null);
  const [historyLoadingId, setHistoryLoadingId] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const nextPageRef = useRef(1);
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

  const loadIncidents = useCallback(async (append = false) => {
    setError("");
    const page = append ? nextPageRef.current : 1;
    if (append) {
      setLoadingMore(true);
    }
    try {
      const params = { page };
      if (locationFilter) {
        params.location = locationFilter;
      }
      if (statusFilter) {
        params.status = statusFilter;
      }
      if (priorityFilter) {
        params.priority = priorityFilter;
      }
      if (categoryFilter) {
        params.category = categoryFilter;
      }
      const { data } = await api.get("/incidents/", { params });
      setIncidents((current) => append ? [...current, ...data.results] : data.results);
      setHasMore(Boolean(data.next));
      nextPageRef.current = page + 1;
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      if (append) {
        setLoadingMore(false);
      } else {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [locationFilter, statusFilter, priorityFilter, categoryFilter]);

  useFocusEffect(
    useCallback(() => {
      loadIncidents();
    }, [loadIncidents]),
  );

  useEffect(() => {
    let active = true;
    Promise.all([
      fetchAllPages("/locations/"),
      fetchAllPages("/users/"),
      fetchAllPages("/categories/"),
    ])
      .then(([locationResults, userResults, categoryResults]) => {
        if (active) {
          setLocations(locationResults);
          setUsers(userResults.filter((account) => account.is_active));
          setCategories(categoryResults.filter((category) => category.is_active));
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
      setHistoryByIncident((current) => {
        const updated = { ...current };
        delete updated[incident.id];
        return updated;
      });
      setExpandedHistoryId((current) => current === incident.id ? null : current);
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
      setHistoryByIncident((current) => {
        const updated = { ...current };
        delete updated[incident.id];
        return updated;
      });
      setExpandedHistoryId((current) => current === incident.id ? null : current);
      await loadIncidents();
    } catch (requestError) {
      setActionError(getApiErrorMessage(requestError));
    } finally {
      setBusyIncidentId(null);
    }
  }

  async function toggleHistory(incidentId) {
    if (expandedHistoryId === incidentId) {
      setExpandedHistoryId(null);
      setHistoryError("");
      return;
    }
    setExpandedHistoryId(incidentId);
    setHistoryError("");
    if (historyByIncident[incidentId]) {
      return;
    }

    setHistoryLoadingId(incidentId);
    try {
      const events = await fetchAllPages(`/incidents/${incidentId}/events/`);
      setHistoryByIncident((current) => ({ ...current, [incidentId]: events }));
    } catch (requestError) {
      setHistoryError(getApiErrorMessage(requestError));
    } finally {
      setHistoryLoadingId(null);
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
    const history = historyByIncident[item.id] ?? [];
    const statusNames = {
      pendiente: "Pendiente",
      en_proceso: "En proceso",
      resuelta: "Resuelta",
      cerrada: "Cerrada",
    };

    function describeEvent(event) {
      if (event.event_type === "created") {
        return "Se creó el reporte.";
      }
      if (event.event_type === "status_changed") {
        const from = statusNames[event.old_value?.status] ?? event.old_value?.status;
        const to = statusNames[event.new_value?.status] ?? event.new_value?.status;
        return `Estado: ${from ?? "—"} → ${to ?? "—"}.`;
      }
      if (event.event_type === "assigned") {
        const from = usersById.get(event.old_value?.assigned_to)?.username ?? "Sin asignar";
        const to = usersById.get(event.new_value?.assigned_to)?.username ?? "Sin asignar";
        return `Asignación: ${from} → ${to}.`;
      }
      return "Actualización registrada.";
    }

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

        <ActionButton
          compact
          disabled={busy || optionsError !== ""}
          onPress={() =>
            setAssignmentTarget(assignmentTarget === item.id ? null : item.id)
          }
          title={assignmentTarget === item.id ? "Cancelar asignación" : "Asignar técnico"}
          variant="secondary"
        />

        {assignmentTarget === item.id ? (
          <View style={styles.assignmentOptions}>
            {siteTechnicians.map((technician) => (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: item.assigned_to === technician.id }}
                disabled={busy || item.assigned_to === technician.id}
                key={technician.id}
                onPress={() => assignTechnician(item, technician.id)}
                style={({ pressed }) => [
                  styles.choice,
                  item.assigned_to === technician.id && styles.selectedChoice,
                  busy && styles.disabled,
                  pressed && styles.pressed,
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
                style={({ pressed }) => [
                  styles.choice,
                  busy && styles.disabled,
                  pressed && styles.pressed,
                ]}
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
          <ActionButton
            compact
            disabled={busy}
            onPress={() => changeStatus(item)}
            title={nextStatusLabel}
          />
        ) : null}
        <ActionButton
          compact
          onPress={() => toggleHistory(item.id)}
          title={expandedHistoryId === item.id ? "Ocultar historial" : "Ver historial"}
          variant="quiet"
        />
        {expandedHistoryId === item.id ? (
          <View style={styles.history}>
            {historyLoadingId === item.id ? (
              <ActivityIndicator color="#0b6b63" />
            ) : history.length ? (
              history.map((event) => (
                <View key={event.id} style={styles.historyEvent}>
                  <Text style={styles.historyText}>{describeEvent(event)}</Text>
                  <Text style={styles.historyMeta}>
                    {event.actor_username} · {new Date(event.created_at).toLocaleString()}
                  </Text>
                </View>
              ))
            ) : (
              <Text style={styles.helper}>No hay eventos de historial.</Text>
            )}
            {historyError ? (
              <Text accessibilityRole="alert" style={styles.error}>{historyError}</Text>
            ) : null}
          </View>
        ) : null}
      </View>
    );
  }

  return (
    <View style={styles.page}>
      <View style={styles.header}>
        <View>
          <Text style={styles.welcome}>Hola, {user.username}</Text>
          <Text style={styles.role}>
            {route?.params?.organizationName
              ? `Incidencias · ${route.params.organizationName}`
              : "Administración de incidencias"}
          </Text>
        </View>
        <ActionButton
          compact
          fullWidth={false}
          onPress={handleLogout}
          title="Salir"
          variant="quiet"
        />
      </View>

      <View style={styles.topActions}>
        {user.role === "organization_admin" ? (
          <ActionButton
            compact
            onPress={() => navigation.navigate("ManageEmergencyAlerts")}
            title="Emitir alerta de emergencia"
            variant="primary"
          />
        ) : null}
        <ActionButton
          compact
          onPress={() => navigation.navigate("ManageInvitations")}
          title="Invitar usuarios"
          variant="primary"
        />
        <ActionButton
          compact
          onPress={() => navigation.navigate("JoinOrganization")}
          title="Unirse a otra organización"
          variant="quiet"
        />
        <ActionButton
          compact
          onPress={() => navigation.navigate("Emergencies")}
          title="Protocolos de emergencia"
          variant="secondary"
        />
        <ActionButton
          compact
          onPress={() => navigation.navigate("CreateUser")}
          title="Crear usuario"
          variant="secondary"
        />
        <ActionButton
          compact
          onPress={() => navigation.navigate("Categories")}
          title="Administrar categorías"
          variant="secondary"
        />
      </View>

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

      <Text style={styles.filterLabel}>Prioridad</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow}>
        {PRIORITY_FILTERS.map((priority) => (
          <FilterChip
            key={priority.value || "all"}
            label={priority.label}
            onPress={() => setPriorityFilter(priority.value)}
            selected={priorityFilter === priority.value}
          />
        ))}
      </ScrollView>

      <Text style={styles.filterLabel}>Categoría</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow}>
        <FilterChip
          label="Todas"
          onPress={() => setCategoryFilter("")}
          selected={!categoryFilter}
        />
        {categories.map((category) => (
          <FilterChip
            key={category.id}
            label={category.name}
            onPress={() => setCategoryFilter(String(category.id))}
            selected={categoryFilter === String(category.id)}
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
          ListFooterComponent={
            hasMore ? (
              <ActionButton
                disabled={loadingMore}
                onPress={() => loadIncidents(true)}
                title={loadingMore ? "Cargando…" : "Cargar más incidencias"}
                variant="secondary"
              />
            ) : null
          }
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
      style={({ pressed }) => [
        styles.filterChip,
        selected && styles.selectedFilterChip,
        pressed && styles.pressed,
      ]}
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
  topActions: {
    gap: 8,
    marginBottom: 4,
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
    minHeight: 40,
    alignItems: "center",
    justifyContent: "center",
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
    borderColor: "#e0eae7",
    borderRadius: 18,
    backgroundColor: "#ffffff",
    elevation: 3,
    shadowColor: "#173d35",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
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
  assignmentOptions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  history: {
    gap: 10,
    marginTop: 10,
    padding: 12,
    borderRadius: 10,
    backgroundColor: "#f4f7f6",
  },
  historyEvent: {
    gap: 3,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#dce6e3",
  },
  historyText: {
    color: "#263238",
  },
  historyMeta: {
    color: "#52615e",
    fontSize: 12,
  },
  choice: {
    flexShrink: 0,
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
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
  pressed: {
    opacity: 0.8,
    transform: [{ scale: 0.98 }],
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
