import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

const DEMO_ACCOUNTS = [
  {
    key: "superadmin",
    roleLabel: "👑 Superadministrador",
    badge: "GLOBAL",
    badgeColor: "#6c2bd9",
    description: "Gestión global de empresas y usuarios",
    username: "demo_superadmin",
    password: "NefijjAdmin2026*",
  },
  {
    key: "admin",
    roleLabel: "🏢 Admin Organizacional",
    badge: "EMPRESA",
    badgeColor: "#0b6b63",
    description: "Administra incidencias, asigna técnicos y alertas",
    username: "demo_admin",
    password: "NefijjAdmin2026*",
  },
  {
    key: "technician",
    roleLabel: "🔧 Técnico",
    badge: "OPERATIVO",
    badgeColor: "#b45309",
    description: "Atiende y resuelve incidencias asignadas",
    username: "demo_tecnico_a",
    password: "NefijjAdmin2026*",
  },
  {
    key: "student",
    roleLabel: "🎓 Usuario / Estudiante",
    badge: "REPORTE",
    badgeColor: "#1d4ed8",
    description: "Reporta incidencias con foto y consulta estado",
    username: "demo_estudiante_a",
    password: "NefijjAdmin2026*",
  },
];

export default function LoginScreen() {
  const { login } = useAuth();
  const insets = useSafeAreaInsets();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeQuickKey, setActiveQuickKey] = useState(null);

  async function performLogin(targetUsername, targetPassword) {
    if (!targetUsername.trim() || !targetPassword) {
      setError("Ingresa tu usuario y contraseña.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await login(targetUsername.trim(), targetPassword);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
      setActiveQuickKey(null);
    }
  }

  async function handleSubmit() {
    await performLogin(username, password);
  }

  async function handleQuickLogin(account) {
    setActiveQuickKey(account.key);
    setUsername(account.username);
    setPassword(account.password);
    await performLogin(account.username, account.password);
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={[styles.page, { paddingTop: insets.top, paddingBottom: insets.bottom }]}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
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
            style={({ pressed }) => [styles.button, pressed && styles.pressed, submitting && styles.disabled]}
          >
            {submitting && !activeQuickKey ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.buttonText}>Ingresar</Text>
            )}
          </Pressable>

          <View style={styles.dividerContainer}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>o entra con 1 toque (DEMO)</Text>
            <View style={styles.dividerLine} />
          </View>

          <View style={styles.quickGrid}>
            {DEMO_ACCOUNTS.map((account) => {
              const isCurrentSubmitting = submitting && activeQuickKey === account.key;
              return (
                <Pressable
                  key={account.key}
                  accessibilityRole="button"
                  disabled={submitting}
                  onPress={() => handleQuickLogin(account)}
                  style={({ pressed }) => [
                    styles.quickCard,
                    pressed && styles.quickCardPressed,
                    submitting && styles.quickCardDisabled,
                  ]}
                >
                  <View style={styles.quickCardHeader}>
                    <Text style={styles.quickRoleText}>{account.roleLabel}</Text>
                    <View style={[styles.badge, { backgroundColor: account.badgeColor }]}>
                      <Text style={styles.badgeText}>{account.badge}</Text>
                    </View>
                  </View>
                  <Text style={styles.quickDescText}>{account.description}</Text>
                  <View style={styles.quickFooter}>
                    <Text style={styles.quickUserText}>Usuario: {account.username}</Text>
                    {isCurrentSubmitting ? (
                      <ActivityIndicator color="#0b6b63" size="small" />
                    ) : (
                      <Text style={styles.quickActionText}>Ingresar →</Text>
                    )}
                  </View>
                </Pressable>
              );
            })}
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#eaf1ef",
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 20,
  },
  card: {
    padding: 24,
    borderRadius: 16,
    backgroundColor: "#ffffff",
    gap: 10,
    elevation: 3,
    shadowColor: "#000000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
  },
  title: {
    color: "#0b6b63",
    fontSize: 32,
    fontWeight: "700",
    textAlign: "center",
  },
  subtitle: {
    marginBottom: 6,
    color: "#52615e",
    lineHeight: 20,
    textAlign: "center",
    fontSize: 14,
  },
  label: {
    color: "#263238",
    fontWeight: "600",
    fontSize: 14,
  },
  input: {
    minHeight: 46,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 10,
    color: "#172321",
    backgroundColor: "#ffffff",
    fontSize: 15,
  },
  error: {
    color: "#a42323",
    fontSize: 13,
  },
  button: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 6,
    borderRadius: 10,
    backgroundColor: "#0b6b63",
  },
  pressed: {
    opacity: 0.8,
  },
  disabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 16,
  },
  dividerContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 14,
    gap: 8,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: "#d5dedc",
  },
  dividerText: {
    color: "#6b7d78",
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
  },
  quickGrid: {
    gap: 10,
  },
  quickCard: {
    borderWidth: 1,
    borderColor: "#dbe5e2",
    borderRadius: 12,
    padding: 12,
    backgroundColor: "#f7faf9",
    gap: 4,
  },
  quickCardPressed: {
    backgroundColor: "#e8f2ef",
    borderColor: "#0b6b63",
  },
  quickCardDisabled: {
    opacity: 0.6,
  },
  quickCardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  quickRoleText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#172321",
  },
  badge: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeText: {
    color: "#ffffff",
    fontSize: 10,
    fontWeight: "800",
  },
  quickDescText: {
    fontSize: 12,
    color: "#52615e",
  },
  quickFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 4,
    paddingTop: 4,
    borderTopWidth: 1,
    borderTopColor: "#e6eee9",
  },
  quickUserText: {
    fontSize: 11,
    color: "#6b7d78",
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
  },
  quickActionText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#0b6b63",
  },
});
