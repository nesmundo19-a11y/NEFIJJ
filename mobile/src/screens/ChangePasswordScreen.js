import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from "react-native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

export default function ChangePasswordScreen() {
  const { logout } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!oldPassword || !newPassword || !confirmation) {
      setError("Completa todos los campos.");
      return;
    }
    if (newPassword !== confirmation) {
      setError("La confirmación no coincide con la nueva contraseña.");
      return;
    }
    if (newPassword.length < 12) {
      setError("La nueva contraseña debe tener al menos 12 caracteres.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await api.post("/auth/password/change/", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      await logout();
      Alert.alert("Contraseña actualizada", "Inicia sesión con tu nueva contraseña.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <Text style={styles.description}>
        Confirma tu contraseña actual. Por seguridad, tendrás que iniciar sesión de nuevo
        después del cambio.
      </Text>
      <TextInput
        accessibilityLabel="Contraseña actual"
        autoCapitalize="none"
        editable={!submitting}
        onChangeText={setOldPassword}
        placeholder="Contraseña actual"
        secureTextEntry
        style={styles.input}
        value={oldPassword}
      />
      <TextInput
        accessibilityLabel="Nueva contraseña"
        autoCapitalize="none"
        editable={!submitting}
        onChangeText={setNewPassword}
        placeholder="Nueva contraseña (mínimo 12 caracteres)"
        secureTextEntry
        style={styles.input}
        value={newPassword}
      />
      <TextInput
        accessibilityLabel="Confirmar nueva contraseña"
        autoCapitalize="none"
        editable={!submitting}
        onChangeText={setConfirmation}
        onSubmitEditing={handleSubmit}
        placeholder="Confirmar nueva contraseña"
        returnKeyType="done"
        secureTextEntry
        style={styles.input}
        value={confirmation}
      />
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Pressable
        accessibilityRole="button"
        disabled={submitting}
        onPress={handleSubmit}
        style={[styles.button, submitting && styles.disabled]}
      >
        {submitting ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.buttonText}>Actualizar contraseña</Text>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    gap: 14,
    padding: 20,
    backgroundColor: "#f4f7f6",
  },
  description: {
    color: "#52615e",
    lineHeight: 21,
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
  error: {
    color: "#a42323",
  },
  button: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    backgroundColor: "#0b6b63",
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.6,
  },
});
