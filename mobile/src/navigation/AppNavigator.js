import { ActivityIndicator, Button, StyleSheet, Text, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";

import AdminIncidentsScreen from "../screens/AdminIncidentsScreen";
import { useAuth } from "../auth/AuthContext";
import CategoryManagementScreen from "../screens/CategoryManagementScreen";
import ChangePasswordScreen from "../screens/ChangePasswordScreen";
import CreateIncidentScreen from "../screens/CreateIncidentScreen";
import CreateUserScreen from "../screens/CreateUserScreen";
import EmergenciesScreen from "../screens/EmergenciesScreen";
import EmergencyAlertManagementScreen from "../screens/EmergencyAlertManagementScreen";
import IncidentsScreen from "../screens/IncidentsScreen";
import JoinOrganizationScreen from "../screens/JoinOrganizationScreen";
import LoginScreen from "../screens/LoginScreen";
import InvitationManagementScreen from "../screens/InvitationManagementScreen";
import OrganizationManagementScreen from "../screens/OrganizationManagementScreen";
import OrganizationSelectScreen from "../screens/OrganizationSelectScreen";
import UserHomeScreen from "../screens/UserHomeScreen";

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  const { user, logout, loading, initializationError, retryRestore } = useAuth();

  if (loading) {
    return (
      <SafeAreaProvider>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#0b6b63" />
          <Text style={styles.message}>Cargando sesión segura…</Text>
        </View>
      </SafeAreaProvider>
    );
  }

  if (initializationError) {
    return (
      <SafeAreaProvider>
        <View style={styles.center}>
          <Text style={styles.message}>{initializationError}</Text>
          <Button title="Reintentar" onPress={retryRestore} />
        </View>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator
          key={
            user
              ? `${user.role}:${user.active_organization_id ?? ""}`
              : "logged-out"
          }
        >
          {user ? (
            <>
              <Stack.Screen
                name="Home"
                component={
                  user.role === "superadmin"
                    ? OrganizationManagementScreen
                    : user.role === "member"
                      ? OrganizationSelectScreen
                      : user.role === "organization_admin"
                        ? AdminIncidentsScreen
                        : user.role === "user"
                        ? UserHomeScreen
                        : IncidentsScreen
                }
                options={({ navigation }) => ({
                  title:
                    user.role === "superadmin"
                      ? "Gestión de empresas"
                      : user.role === "member"
                        ? "Organización"
                        : user.role === "organization_admin"
                          ? "Administrar incidencias"
                          : user.role === "user"
                            ? "Inicio"
                            : "Mis incidencias",
                  headerRight:
                    () => (
                      <View style={styles.headerActions}>
                        {user.role !== "superadmin" &&
                        (user.organizations ?? []).filter(
                          (membership) => membership.organization_status === "active",
                        ).length > 1 ? (
                          <Button
                            onPress={() => navigation.navigate("SelectOrganization")}
                            title="Empresa"
                          />
                        ) : null}
                        <Button
                          onPress={() => navigation.navigate("AccountSettings")}
                          title="Cuenta"
                        />
                        <Button
                          color="#a42323"
                          onPress={() => logout()}
                          title="Salir"
                        />
                      </View>
                    ),
                })}
              />
              {user.role !== "superadmin" &&
              user.role !== "member" &&
              (user.organizations ?? []).filter(
                (membership) => membership.organization_status === "active",
              ).length > 1 ? (
                <Stack.Screen
                  name="SelectOrganization"
                  component={OrganizationSelectScreen}
                  options={{ title: "Seleccionar organización" }}
                />
              ) : null}
              {user.role === "user" ? (
                <Stack.Screen
                  name="CreateIncident"
                  component={CreateIncidentScreen}
                  options={{ title: "Reportar incidencia" }}
                />
              ) : null}
              {user.role === "user" ? (
                <Stack.Screen
                  name="MyReports"
                  component={IncidentsScreen}
                  options={{ title: "Mis reportes" }}
                />
              ) : null}
              {user.role !== "superadmin" ? (
                <Stack.Screen
                  name="Emergencies"
                  component={EmergenciesScreen}
                  options={{ title: "Emergencias" }}
                />
              ) : null}
              {user.role === "organization_admin" || user.role === "superadmin" ? (
                <Stack.Screen
                  name="CreateUser"
                  component={CreateUserScreen}
                  options={{ title: "Crear usuario" }}
                />
              ) : null}
              {user.role === "organization_admin" || user.role === "superadmin" ? (
                <Stack.Screen
                  name="Categories"
                  component={CategoryManagementScreen}
                  options={{ title: "Administrar categorías" }}
                />
              ) : null}
              {user.role === "organization_admin" || user.role === "superadmin" ? (
                <Stack.Screen
                  name="ManageInvitations"
                  component={InvitationManagementScreen}
                  options={{ title: "Invitaciones de organización" }}
                />
              ) : null}
              {user.role === "organization_admin" ? (
                <Stack.Screen
                  name="ManageEmergencyAlerts"
                  component={EmergencyAlertManagementScreen}
                  options={{ title: "Alertas de emergencia" }}
                />
              ) : null}
              {user.role !== "superadmin" ? (
                <Stack.Screen
                  name="JoinOrganization"
                  component={JoinOrganizationScreen}
                  options={{ title: "Unirse a una organización" }}
                />
              ) : null}
              <Stack.Screen
                name="AccountSettings"
                component={ChangePasswordScreen}
                options={{ title: "Cambiar contraseña" }}
              />
            </>
          ) : (
            <Stack.Screen
              name="Login"
              component={LoginScreen}
              options={{ title: "Iniciar sesión" }}
            />
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#f4f7f6",
  },
  message: {
    marginVertical: 16,
    color: "#263238",
    textAlign: "center",
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
  },
});
