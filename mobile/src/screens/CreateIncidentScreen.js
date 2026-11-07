import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";

const PRIORITIES = ["baja", "media", "alta", "critica"];
const MAX_EVIDENCE_BYTES = 10 * 1024 * 1024;

export default function CreateIncidentScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [categories, setCategories] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState(null);
  const [priority, setPriority] = useState("media");
  const [evidence, setEvidence] = useState(null);
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
      const payload = evidence ? new FormData() : {
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId,
        priority,
      };
      if (evidence) {
        payload.append("title", title.trim());
        payload.append("description", description.trim());
        payload.append("category_id", String(categoryId));
        payload.append("priority", priority);
        const imageType = evidence.mimeType || "image/jpeg";
        payload.append("evidence_image", {
          uri: evidence.uri,
          name: `evidence-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${
            imageType === "image/png" ? "png" : "jpg"
          }`,
          type: imageType,
        });
      }
      await api.post("/incidents/", payload, evidence
        ? { headers: { "Content-Type": "multipart/form-data" } }
        : undefined);
      navigation.goBack();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  async function selectEvidence(source) {
    setError("");
    try {
      const permission =
        source === "camera"
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        setError(
          source === "camera"
            ? "Permite el acceso a la cámara para tomar una foto."
            : "Permite el acceso a tus fotos para adjuntar una imagen.",
        );
        return;
      }

      const result =
        source === "camera"
          ? await ImagePicker.launchCameraAsync({
              mediaTypes: ["images"],
              allowsEditing: true,
              aspect: [4, 3],
              quality: 0.8,
            })
          : await ImagePicker.launchImageLibraryAsync({
              mediaTypes: ["images"],
              allowsEditing: true,
              aspect: [4, 3],
              quality: 0.8,
            });
      if (result.canceled) {
        return;
      }

      const selected = result.assets[0];
      if (selected.fileSize && selected.fileSize > MAX_EVIDENCE_BYTES) {
        setError("La foto debe pesar 10 MB o menos. Elige otra imagen.");
        return;
      }
      if (
        selected.mimeType &&
        !["image/jpeg", "image/png"].includes(selected.mimeType.toLowerCase())
      ) {
        setError("Elige una imagen JPG o PNG.");
        return;
      }
      setEvidence(selected);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
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
        maxLength={255}
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
      <Text style={styles.label}>Foto de evidencia (opcional)</Text>
      <View style={styles.evidenceActions}>
        <Pressable
          accessibilityRole="button"
          disabled={submitting}
          onPress={() => selectEvidence("camera")}
          style={[styles.evidenceButton, submitting && styles.disabled]}
        >
          <Text style={styles.evidenceButtonText}>Tomar foto</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          disabled={submitting}
          onPress={() => selectEvidence("library")}
          style={[styles.evidenceButton, submitting && styles.disabled]}
        >
          <Text style={styles.evidenceButtonText}>Elegir foto</Text>
        </Pressable>
      </View>
      {evidence ? (
        <View style={styles.previewContainer}>
          <Image
            accessibilityLabel="Vista previa de la foto de evidencia"
            source={{ uri: evidence.uri }}
            style={styles.preview}
          />
          <Pressable
            accessibilityRole="button"
            disabled={submitting}
            onPress={() => setEvidence(null)}
            style={styles.removeEvidence}
          >
            <Text style={styles.removeEvidenceText}>Quitar foto</Text>
          </Pressable>
        </View>
      ) : (
        <Text style={styles.helper}>JPG o PNG, máximo 10 MB.</Text>
      )}
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
  evidenceActions: {
    flexDirection: "row",
    gap: 10,
  },
  evidenceButton: {
    minHeight: 44,
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#0b6b63",
    borderRadius: 10,
    backgroundColor: "#ffffff",
  },
  evidenceButtonText: {
    color: "#075b55",
    fontWeight: "700",
  },
  previewContainer: {
    alignItems: "flex-start",
    gap: 8,
  },
  preview: {
    width: "100%",
    height: 190,
    borderRadius: 12,
    backgroundColor: "#e1e9e6",
  },
  removeEvidence: {
    paddingVertical: 6,
  },
  removeEvidenceText: {
    color: "#a42323",
    fontWeight: "700",
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
