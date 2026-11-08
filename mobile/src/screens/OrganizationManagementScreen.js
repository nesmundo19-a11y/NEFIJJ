import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Button,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";

import api, { saveActiveOrganization } from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

async function fetchOrganizations() {
  const organizations = [];
  let page = 1;
  let summary = null;
  while (true) {
    const { data } = await api.get("/organizations/", { params: { page } });
    if (page === 1) {
      summary = data.summary;
    }
    organizations.push(...data.results);
    if (!data.next) {
      return { organizations, summary };
    }
    page += 1;
  }
}

export default function OrganizationManagementScreen({ navigation }) {
  const { user, logout } = useAuth();
  const [organizations, setOrganizations] = useState([]);
  const [summary, setSummary] = useState({ total: 0, active: 0, suspended: 0 });
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyOrganizationId, setBusyOrganizationId] = useState(null);
  const [error, setError] = useState("");

  const loadOrganizations = useCallback(async () => {
    setError("");
    try {
      const result = await fetchOrganizations();
      setOrganizations(result.organizations);
      setSummary(result.summary);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadOrganizations();
    }, [loadOrganizations]),
  );

  async function createOrganization() {
    if (!name.trim() || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug.trim())) {
      setError("Ingresa el nombre y un identificador en minúsculas separado por guiones.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api.post("/organizations/", {
        name: name.trim(),
        slug: slug.trim(),
      });
      setName("");
      setSlug("");
      await loadOrganizations();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function setOrganizationStatus(organization, isActive) {
    setBusyOrganizationId(organization.id);
    setError("");
    try {
      await api.patch(`/organizations/${organization.id}/status/`, {
        status: isActive ? "active" : "suspended",
      });
      await loadOrganizations();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setBusyOrganizationId(null);
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  return (
    <View style={styles.page}>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.title}>Gestión de empresas</Text>
          <Text style={styles.subtitle}>Superadministrador: {user.username}</Text>
        </View>
        <Button onPress={handleLogout} title="Salir" />
      </View>
      <View style={styles.form}>
        <Text style={styles.formTitle}>Registrar organización</Text>
        <TextInput
          accessibilityLabel="Nombre de la organización"
          editable={!saving}
          onChangeText={setName}
          placeholder="Nombre de la organización"
          style={styles.input}
          value={name}
        />
        <TextInput
          accessibilityLabel="Identificador de la organización"
          autoCapitalize="none"
          editable={!saving}
          onChangeText={setSlug}
          placeholder="identificador-con-guiones"
          style={styles.input}
          value={slug}
        />
        <Pressable
          accessibilityRole="button"
          disabled={saving}
          onPress={createOrganization}
          style={[styles.createButton, saving && styles.disabled]}
        >
          <Text style={styles.createButtonText}>
            {saving ? "Guardando…" : "Crear organización"}
          </Text>
        </Pressable>
      </View>
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {loading ? (
        <ActivityIndicator color="#0b6b63" size="large" style={styles.loading} />
      ) : (
        <>
          <View accessibilityLabel="Resumen de organizaciones" style={styles.summary}>
            <View style={styles.summaryCard}>
              <Text style={styles.summaryValue}>{summary.total}</Text>
              <Text style={styles.summaryLabel}>Registradas</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={styles.summaryValue}>{summary.active}</Text>
              <Text style={styles.summaryLabel}>Activas</Text>
            </View>
            <View style={styles.summaryCard}>
              <Text style={styles.summaryValue}>{summary.suspended}</Text>
              <Text style={styles.summaryLabel}>Suspendidas</Text>
            </View>
          </View>
          <FlatList
            contentContainerStyle={organizations.length ? styles.list : styles.emptyList}
            data={organizations}
            keyExtractor={(item) => String(item.id)}
            refreshControl={
              <RefreshControl
                onRefresh={() => {
                  setRefreshing(true);
                  loadOrganizations();
                }}
                refreshing={refreshing}
              />
            }
            ListEmptyComponent={
              <Text style={styles.empty}>No hay organizaciones registradas.</Text>
            }
            renderItem={({ item }) => {
              const isActive = item.status === "active";
              return (
                <View style={styles.organization}>
                  <View style={styles.organizationText}>
                    <Text style={styles.organizationName}>{item.name}</Text>
                    <Text style={styles.organizationSlug}>ID {item.id} · {item.slug}</Text>
                    <Text style={styles.status}>
                      {isActive ? "Activa" : "Suspendida"}
                    </Text>
                    <Pressable
                      accessibilityRole="button"
                      onPress={() =>
                        navigation.navigate("CreateUser", {
                          organizationId: item.id,
                          organizationName: item.name,
                        })
                      }
                      style={styles.userButton}
                    >
                      <Text style={styles.userButtonText}>Crear usuario</Text>
                    </Pressable>
                    {isActive ? (
                      <Pressable
                        accessibilityRole="button"
                        onPress={async () => {
                          await saveActiveOrganization(item.id);
                          navigation.navigate("AdminIncidents", {
                            organizationId: item.id,
                            organizationName: item.name,
                          });
                        }}
                        style={[styles.userButton, styles.incidentsButton]}
                      >
                        <Text style={[styles.userButtonText, styles.incidentsButtonText]}>
                          Ver incidencias
                        </Text>
                      </Pressable>
                    ) : null}
                    {isActive ? (
                      <Pressable
                        accessibilityRole="button"
                        onPress={() =>
                          navigation.navigate("ManageInvitations", {
                            organizationId: item.id,
                            organizationName: item.name,
                          })
                        }
                        style={styles.userButton}
                      >
                        <Text style={styles.userButtonText}>Crear invitación QR</Text>
                      </Pressable>
                    ) : null}
                    {isActive ? (
                      <Pressable
                        accessibilityRole="button"
                        onPress={() =>
                          navigation.navigate("Categories", {
                            organizationId: item.id,
                            organizationName: item.name,
                          })
                        }
                        style={styles.userButton}
                      >
                        <Text style={styles.userButtonText}>Administrar categorías</Text>
                      </Pressable>
                    ) : null}
                  </View>
                  <Switch
                    accessibilityLabel={`Estado de ${item.name}`}
                    disabled={busyOrganizationId === item.id}
                    onValueChange={(value) => setOrganizationStatus(item, value)}
                    value={isActive}
                  />
                </View>
              );
            }}
          />
        </>
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
    gap: 8,
    paddingVertical: 16,
  },
  headerText: {
    flex: 1,
  },
  title: {
    color: "#172321",
    fontSize: 21,
    fontWeight: "700",
  },
  subtitle: {
    marginTop: 4,
    color: "#52615e",
  },
  form: {
    gap: 10,
    marginBottom: 12,
    padding: 14,
    borderRadius: 12,
    backgroundColor: "#ffffff",
  },
  summary: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 12,
  },
  summaryCard: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: "#ffffff",
  },
  summaryValue: {
    color: "#172321",
    fontSize: 20,
    fontWeight: "700",
  },
  summaryLabel: {
    marginTop: 3,
    color: "#52615e",
    fontSize: 12,
    textAlign: "center",
  },
  formTitle: {
    color: "#172321",
    fontWeight: "700",
  },
  input: {
    minHeight: 44,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 8,
    color: "#172321",
  },
  createButton: {
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    backgroundColor: "#0b6b63",
  },
  createButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.6,
  },
  organization: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 10,
    padding: 14,
    borderRadius: 10,
    backgroundColor: "#ffffff",
  },
  organizationText: {
    flex: 1,
  },
  organizationName: {
    color: "#172321",
    fontWeight: "700",
  },
  organizationSlug: {
    marginTop: 3,
    color: "#52615e",
  },
  status: {
    marginTop: 5,
    color: "#52615e",
  },
  userButton: {
    alignSelf: "flex-start",
    marginTop: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#e1efec",
  },
  userButtonText: {
    color: "#0b6b63",
    fontWeight: "600",
  },
  incidentsButton: {
    backgroundColor: "#0b6b63",
    borderColor: "#0b6b63",
  },
  incidentsButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  list: {
    paddingBottom: 24,
  },
  emptyList: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  empty: {
    color: "#52615e",
    textAlign: "center",
  },
  error: {
    marginVertical: 6,
    color: "#a42323",
  },
  loading: {
    marginTop: 32,
  },
});
