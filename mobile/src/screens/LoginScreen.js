import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

export default function LoginScreen() {
  const { login } = useAuth();
  const insets = useSafeAreaInsets();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!username.trim() || !password) {
      setError("Ingresa tu usuario y contraseña.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await login(username.trim(), password);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={[styles.page, { paddingTop: insets.top }]}
    >
      <View style={styles.card}>
        <Text style={styles.title}>NEFIJJ</Text>
        <Text style={styles.subtitle}>Gestión de incidencias institucionales</Text>
        <Text style={styles.label}>Usuario</Text>
        <TextInput
          accessibilityLabel="Usuario"
          autoCapitalize="none"
          autoCorrect={false}
          editable={!submitting}
          onChangeText={setUsername}
          onSubmitEditing={handleSubmit}
          placeholder="Nombre de usuario"
          returnKeyType="next"
          style={styles.input}
          value={username}
        />
        <Text style={styles.label}>Contraseña</Text>
        <TextInput
          accessibilityLabel="Contraseña"
          autoCapitalize="none"
          editable={!submitting}
          onChangeText={setPassword}
          onSubmitEditing={handleSubmit}
          placeholder="Contraseña"
          returnKeyType="done"
          secureTextEntry
          style={styles.input}
          value={password}
        />
        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
        <Pressable
          accessibilityRole="button"
          disabled={submitting}
          onPress={handleSubmit}
          style={({ pressed }) => [styles.button, pressed && styles.pressed]}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.buttonText}>Ingresar</Text>
          )}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#eaf1ef",
  },
  card: {
    padding: 24,
    borderRadius: 16,
    backgroundColor: "#ffffff",
    gap: 12,
  },
  title: {
    color: "#0b6b63",
    fontSize: 32,
    fontWeight: "700",
    textAlign: "center",
  },
  subtitle: {
    marginBottom: 12,
    color: "#52615e",
    textAlign: "center",
  },
  label: {
    color: "#263238",
    fontWeight: "600",
  },
  input: {
    minHeight: 48,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 8,
    color: "#172321",
  },
  error: {
    color: "#a42323",
  },
  button: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
    borderRadius: 8,
    backgroundColor: "#0b6b63",
  },
  pressed: {
    opacity: 0.8,
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
});
