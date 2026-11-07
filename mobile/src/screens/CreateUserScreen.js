import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

const USER_ROLES = [
  { value: "user", label: "Usuario" },
  { value: "technician", label: "Técnico" },
  { value: "organization_admin", label: "Administrador" },
];

async function fetchAllLocations(requestConfig) {
  const locations = [];
  let page = 1;
  while (true) {
    const { data } = await api.get("/locations/", {
      ...requestConfig,
      params: { page },
    });
    locations.push(...data.results);
    if (!data.next) {
      return locations;
    }
    page += 1;
  }
}

export default function CreateUserScreen({ navigation, route }) {
  const { user } = useAuth();
  const organizationId = route.params?.organizationId;
  const organizationName = route.params?.organizationName;
  const isPlatformAdmin = user.role === "superadmin";
  const requestConfig = useMemo(
    () =>
      organizationId
        ? { headers: { "X-Organization-ID": String(organizationId) } }
        : {},
    [organizationId],
  );
  const availableRoles = isPlatformAdmin
    ? USER_ROLES
    : USER_ROLES.filter((role) => role.value !== "organization_admin");

  const [locations, setLocations] = useState([]);
  const [loadingLocations, setLoadingLocations] = useState(true);
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [role, setRole] = useState("user");
  const [locationId, setLocationId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchAllLocations(requestConfig)
      .then((results) => {
        if (active) {
          setLocations(results);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) {
          setLoadingLocations(false);
        }
      });
    return () => {
      active = false;
    };
  }, [requestConfig]);

  async function handleSubmit() {
    const needsLocation = role !== "organization_admin";
    if (
      !username.trim() ||
      !email.trim() ||
      !password ||
      !passwordConfirmation ||
      (needsLocation && !locationId)
    ) {
      setError("Completa el usuario, correo, contraseña y sede requerida.");
      return;
    }
    if (password !== passwordConfirmation) {
      setError("La confirmación de contraseña no coincide.");
      return;
    }
    if (password.length < 12) {
      setError("La contraseña debe tener al menos 12 caracteres.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await api.post(
        "/users/",
        {
          username: username.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          password,
          role,
          ...(needsLocation ? { location_id: Number(locationId) } : {}),
        },
        requestConfig,
      );
      Alert.alert("Usuario creado", "La cuenta ya puede iniciar sesión.");
      navigation.goBack();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <Text style={styles.description}>
        {organizationName
          ? `Organización: ${organizationName}`
          : "La cuenta se agregará a la organización activa."}
      </Text>
      <TextInput
        accessibilityLabel="Nombre de usuario"
        autoCapitalize="none"
        autoCorrect={false}
        editable={!submitting}
        onChangeText={setUsername}
        placeholder="Nombre de usuario"
        style={styles.input}
        value={username}
      />
      <TextInput
        accessibilityLabel="Nombres"
        editable={!submitting}
        onChangeText={setFirstName}
        placeholder="Nombres"
        style={styles.input}
        value={firstName}
      />
      <TextInput
        accessibilityLabel="Apellidos"
        editable={!submitting}
        onChangeText={setLastName}
        placeholder="Apellidos"
        style={styles.input}
        value={lastName}
      />
      <TextInput
        accessibilityLabel="Correo electrónico"
        autoCapitalize="none"
        editable={!submitting}
        keyboardType="email-address"
        onChangeText={setEmail}
        placeholder="Correo electrónico"
        style={styles.input}
        value={email}
      />
      <TextInput
        accessibilityLabel="Contraseña inicial"
        autoCapitalize="none"
        editable={!submitting}
        onChangeText={setPassword}
        placeholder="Contraseña inicial (mínimo 12 caracteres)"
        secureTextEntry
        style={styles.input}
        value={password}
      />
      <TextInput
        accessibilityLabel="Confirmar contraseña inicial"
        autoCapitalize="none"
        editable={!submitting}
        onChangeText={setPasswordConfirmation}
        placeholder="Confirmar contraseña inicial"
        secureTextEntry
        style={styles.input}
        value={passwordConfirmation}
      />

      <Text style={styles.label}>Rol</Text>
      <View style={styles.options}>
        {availableRoles.map((item) => (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: role === item.value }}
            key={item.value}
            onPress={() => setRole(item.value)}
            style={[styles.chip, role === item.value && styles.selectedChip]}
          >
            <Text style={[styles.chipText, role === item.value && styles.selectedChipText]}>
              {item.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {role !== "organization_admin" ? (
        <>
          <Text style={styles.label}>Sede</Text>
          {loadingLocations ? (
            <ActivityIndicator color="#0b6b63" />
          ) : locations.length ? (
            <View style={styles.options}>
              {locations.map((location) => (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ selected: String(location.id) === locationId }}
                  key={location.id}
                  onPress={() => setLocationId(String(location.id))}
                  style={[
                    styles.chip,
                    String(location.id) === locationId && styles.selectedChip,
                  ]}
                >
                  <Text
                    style={[
                      styles.chipText,
                      String(location.id) === locationId && styles.selectedChipText,
                    ]}
                  >
                    {location.name}
                  </Text>
                </Pressable>
              ))}
            </View>
          ) : (
            <Text style={styles.description}>No hay sedes activas disponibles.</Text>
          )}
        </>
      ) : null}

      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Pressable
        accessibilityRole="button"
        disabled={submitting || loadingLocations || (role !== "organization_admin" && !locations.length)}
        onPress={handleSubmit}
        style={[styles.button, submitting && styles.disabled]}
      >
        {submitting ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.buttonText}>Crear usuario</Text>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    gap: 12,
    padding: 18,
    backgroundColor: "#f4f7f6",
  },
  description: {
    color: "#52615e",
  },
  input: {
    minHeight: 46,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 8,
    backgroundColor: "#ffffff",
    color: "#172321",
  },
  label: {
    marginTop: 4,
    color: "#263238",
    fontWeight: "700",
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
  },
  selectedChipText: {
    color: "#ffffff",
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
  buttonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.6,
  },
});
