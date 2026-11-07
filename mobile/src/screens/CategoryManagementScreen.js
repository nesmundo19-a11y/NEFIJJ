import { useCallback, useState } from "react";
import {
  ActivityIndicator,
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

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

async function fetchCategories(organizationId) {
  const categories = [];
  let page = 1;
  const config = organizationId
    ? { headers: { "X-Organization-ID": String(organizationId) } }
    : undefined;
  while (true) {
    const { data } = await api.get("/categories/", {
      ...config,
      params: { page },
    });
    categories.push(...data.results);
    if (!data.next) {
      return categories;
    }
    page += 1;
  }
}

export default function CategoryManagementScreen({ route }) {
  const { user } = useAuth();
  const organizationId = route.params?.organizationId ?? user.active_organization_id;
  const [categories, setCategories] = useState([]);
  const [editingCategory, setEditingCategory] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyCategoryId, setBusyCategoryId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadCategories = useCallback(async () => {
    setError("");
    try {
      setCategories(await fetchCategories(organizationId));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [organizationId]);

  useFocusEffect(
    useCallback(() => {
      loadCategories();
    }, [loadCategories]),
  );

  function resetForm() {
    setEditingCategory(null);
    setName("");
    setDescription("");
  }

  async function saveCategory() {
    if (!name.trim()) {
      setError("Escribe el nombre de la categoría.");
      return;
    }
    if (!organizationId) {
      setError("Selecciona una organización activa antes de administrar categorías.");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    const config = { headers: { "X-Organization-ID": String(organizationId) } };
    const payload = { name: name.trim(), description: description.trim() };
    try {
      if (editingCategory) {
        await api.patch(`/categories/${editingCategory.id}/`, payload, config);
        setSuccess("Categoría actualizada.");
      } else {
        await api.post("/categories/", payload, config);
        setSuccess("Categoría creada.");
      }
      resetForm();
      await loadCategories();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  function editCategory(category) {
    setEditingCategory(category);
    setName(category.name);
    setDescription(category.description ?? "");
    setError("");
    setSuccess("");
  }

  async function changeCategoryStatus(category, isActive) {
    setBusyCategoryId(category.id);
    setError("");
    setSuccess("");
    try {
      await api.patch(
        `/categories/${category.id}/`,
        { is_active: isActive },
        { headers: { "X-Organization-ID": String(organizationId) } },
      );
      setSuccess(`Categoría ${isActive ? "activada" : "desactivada"}.`);
      await loadCategories();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setBusyCategoryId(null);
    }
  }

  return (
    <View style={styles.page}>
      <FlatList
        contentContainerStyle={categories.length ? styles.list : styles.emptyList}
        data={categories}
        keyExtractor={(item) => String(item.id)}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            onRefresh={() => {
              setRefreshing(true);
              loadCategories();
            }}
            refreshing={refreshing}
          />
        }
        ListHeaderComponent={
          <View style={styles.form}>
            <Text style={styles.title}>
              {editingCategory ? "Editar categoría" : "Nueva categoría"}
            </Text>
            <Text style={styles.helper}>
              Las categorías organizan los reportes de esta organización.
            </Text>
            <TextInput
              accessibilityLabel="Nombre de la categoría"
              editable={!saving}
              maxLength={150}
              onChangeText={setName}
              placeholder="Nombre"
              style={styles.input}
              value={name}
            />
            <TextInput
              accessibilityLabel="Descripción de la categoría"
              editable={!saving}
              multiline
              onChangeText={setDescription}
              placeholder="Descripción (opcional)"
              style={[styles.input, styles.multiline]}
              textAlignVertical="top"
              value={description}
            />
            <View style={styles.formActions}>
              <Pressable
                accessibilityRole="button"
                disabled={saving}
                onPress={saveCategory}
                style={[styles.primaryButton, saving && styles.disabled]}
              >
                <Text style={styles.primaryButtonText}>
                  {saving ? "Guardando…" : editingCategory ? "Guardar cambios" : "Crear categoría"}
                </Text>
              </Pressable>
              {editingCategory ? (
                <Pressable
                  accessibilityRole="button"
                  disabled={saving}
                  onPress={resetForm}
                  style={styles.cancelButton}
                >
                  <Text style={styles.cancelButtonText}>Cancelar</Text>
                </Pressable>
              ) : null}
            </View>
            {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
            {success ? <Text accessibilityRole="alert" style={styles.success}>{success}</Text> : null}
            <Text style={styles.sectionTitle}>Categorías de la organización</Text>
          </View>
        }
        ListEmptyComponent={
          loading ? (
            <ActivityIndicator color="#0b6b63" size="large" style={styles.loading} />
          ) : (
            <Text style={styles.empty}>Aún no hay categorías. Puedes crear la primera arriba.</Text>
          )
        }
        renderItem={({ item }) => (
          <View style={styles.categoryCard}>
            <View style={styles.categoryText}>
              <Text style={styles.categoryName}>{item.name}</Text>
              {item.description ? (
                <Text style={styles.description}>{item.description}</Text>
              ) : null}
              <Text style={[styles.status, item.is_active ? styles.active : styles.inactive]}>
                {item.is_active ? "Activa" : "Inactiva"}
              </Text>
              <Pressable
                accessibilityRole="button"
                onPress={() => editCategory(item)}
                style={styles.editButton}
              >
                <Text style={styles.editButtonText}>Editar</Text>
              </Pressable>
            </View>
            <Switch
              accessibilityLabel={`${item.is_active ? "Desactivar" : "Activar"} ${item.name}`}
              disabled={busyCategoryId === item.id}
              onValueChange={(value) => changeCategoryStatus(item, value)}
              value={item.is_active}
            />
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#f4f7f6",
  },
  list: {
    padding: 16,
    paddingBottom: 32,
  },
  emptyList: {
    flexGrow: 1,
    padding: 16,
  },
  form: {
    gap: 12,
    marginBottom: 18,
    padding: 18,
    borderRadius: 16,
    backgroundColor: "#ffffff",
  },
  title: {
    color: "#172321",
    fontSize: 21,
    fontWeight: "800",
  },
  helper: {
    color: "#52615e",
    lineHeight: 20,
  },
  input: {
    minHeight: 48,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 10,
    backgroundColor: "#ffffff",
    color: "#172321",
  },
  multiline: {
    minHeight: 90,
    paddingTop: 12,
  },
  formActions: {
    gap: 8,
  },
  primaryButton: {
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 10,
    backgroundColor: "#0b6b63",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  cancelButton: {
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelButtonText: {
    color: "#52615e",
    fontWeight: "700",
  },
  sectionTitle: {
    marginTop: 8,
    color: "#172321",
    fontSize: 16,
    fontWeight: "700",
  },
  categoryCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 10,
    padding: 16,
    borderRadius: 14,
    backgroundColor: "#ffffff",
  },
  categoryText: {
    flex: 1,
  },
  categoryName: {
    color: "#172321",
    fontSize: 16,
    fontWeight: "700",
  },
  description: {
    marginTop: 5,
    color: "#52615e",
  },
  status: {
    marginTop: 6,
    fontSize: 12,
    fontWeight: "700",
  },
  active: {
    color: "#17633d",
  },
  inactive: {
    color: "#6b7280",
  },
  editButton: {
    alignSelf: "flex-start",
    marginTop: 8,
    paddingVertical: 5,
    paddingRight: 12,
  },
  editButtonText: {
    color: "#075b55",
    fontWeight: "700",
  },
  error: {
    color: "#a42323",
  },
  success: {
    color: "#17633d",
  },
  empty: {
    padding: 20,
    color: "#52615e",
    textAlign: "center",
  },
  loading: {
    margin: 20,
  },
  disabled: {
    opacity: 0.6,
  },
});
