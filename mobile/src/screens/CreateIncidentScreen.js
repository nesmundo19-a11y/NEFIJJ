import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";

const PRIORITIES = ["baja", "media", "alta", "critica"];

export default function CreateIncidentScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [categories, setCategories] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState(null);
  const [priority, setPriority] = useState("media");
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api
      .get("/categories/")
      .then(({ data }) => {
        if (active) {
          setCategories(data.results);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) {
          setLoadingCategories(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit() {
    if (!title.trim() || !description.trim() || !categoryId) {
      setError("Completa el título, la descripción y la categoría.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await api.post("/incidents/", {
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId,
        priority,
      });
      navigation.goBack();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView
      contentContainerStyle={[styles.page, { paddingBottom: Math.max(insets.bottom, 24) }]}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.label}>Título</Text>
      <TextInput
        accessibilityLabel="Título"
        editable={!submitting}
        maxLength={200}
        onChangeText={setTitle}
        placeholder="Describe brevemente el problema"
        style={styles.input}
        value={title}
      />
      <Text style={styles.label}>Descripción</Text>
      <TextInput
        accessibilityLabel="Descripción"
        editable={!submitting}
        multiline
        onChangeText={setDescription}
        placeholder="Indica dónde ocurre y qué está sucediendo"
        style={[styles.input, styles.multiline]}
        textAlignVertical="top"
        value={description}
      />
      <Text style={styles.label}>Categoría</Text>
      {loadingCategories ? (
        <ActivityIndicator color="#0b6b63" />
      ) : (
        <View style={styles.options}>
          {categories.map((category) => (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: categoryId === category.id }}
              key={category.id}
              onPress={() => setCategoryId(category.id)}
              style={[styles.chip, categoryId === category.id && styles.selectedChip]}
            >
              <Text style={[styles.chipText, categoryId === category.id && styles.selectedChipText]}>
                {category.name}
              </Text>
            </Pressable>
          ))}
          {!categories.length ? (
            <Text style={styles.helper}>No hay categorías activas. Contacta al administrador.</Text>
          ) : null}
        </View>
      )}
      <Text style={styles.label}>Prioridad</Text>
      <View style={styles.options}>
        {PRIORITIES.map((value) => (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: priority === value }}
            key={value}
            onPress={() => setPriority(value)}
            style={[styles.chip, priority === value && styles.selectedChip]}
          >
            <Text style={[styles.chipText, priority === value && styles.selectedChipText]}>
              {value}
            </Text>
          </Pressable>
        ))}
      </View>
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Pressable
        accessibilityRole="button"
        disabled={submitting || loadingCategories || categories.length === 0}
        onPress={handleSubmit}
        style={({ pressed }) => [
          styles.submit,
          pressed && styles.pressed,
          (submitting || loadingCategories || categories.length === 0) && styles.disabled,
        ]}
      >
        <Text style={styles.submitText}>{submitting ? "Enviando…" : "Enviar reporte"}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    gap: 10,
    padding: 18,
    backgroundColor: "#f4f7f6",
  },
  label: {
    marginTop: 8,
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
  multiline: {
    minHeight: 120,
    paddingTop: 12,
  },
  options: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 20,
    backgroundColor: "#ffffff",
  },
  selectedChip: {
    borderColor: "#0b6b63",
    backgroundColor: "#0b6b63",
  },
  chipText: {
    color: "#263238",
    textTransform: "capitalize",
  },
  selectedChipText: {
    color: "#ffffff",
  },
  helper: {
    color: "#52615e",
  },
  error: {
    color: "#a42323",
  },
  submit: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 16,
    borderRadius: 8,
    backgroundColor: "#0b6b63",
  },
  submitText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  pressed: {
    opacity: 0.8,
  },
  disabled: {
    opacity: 0.5,
  },
});
