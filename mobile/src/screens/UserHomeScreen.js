import { ScrollView, StyleSheet, Text, View } from "react-native";

import { useAuth } from "../auth/AuthContext";
import ActionButton from "../components/ActionButton";

export default function UserHomeScreen({ navigation }) {
  const { user, activeMembership, logout } = useAuth();

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.welcomeCard}>
        <Text style={styles.brand}>NEFIJJ</Text>
        <Text style={styles.greeting}>Hola, {user.username}</Text>
        <Text style={styles.organization}>
          {activeMembership?.organization_name ?? "Organización activa"}
        </Text>
        {activeMembership?.location_name ? (
          <Text style={styles.location}>{activeMembership.location_name}</Text>
        ) : null}
      </View>

      <Text style={styles.sectionTitle}>¿Qué necesitas hacer?</Text>
      <ActionButton
        onPress={() => navigation.navigate("CreateIncident")}
        title="Reportar una incidencia"
      />
      <ActionButton
        onPress={() => navigation.navigate("MyReports")}
        title="Consultar mis reportes"
        variant="secondary"
      />
      <ActionButton
        onPress={() => navigation.navigate("Emergencies")}
        title="Protocolos de emergencia"
        variant="quiet"
      />
      <ActionButton
        onPress={() => navigation.navigate("JoinOrganization")}
        title="Unirme a otra organización"
        variant="quiet"
      />
      <ActionButton
        onPress={logout}
        title="Cerrar sesión"
        variant="secondary"
      />
      <Text style={styles.note}>
        La fecha y hora del reporte las registra el servidor. No solicitamos tu
        ubicación GPS.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    gap: 14,
    padding: 18,
    backgroundColor: "#f4f7f6",
  },
  welcomeCard: {
    gap: 5,
    marginBottom: 8,
    padding: 18,
    borderRadius: 16,
    backgroundColor: "#ffffff",
  },
  brand: {
    color: "#0b6b63",
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 1.2,
  },
  greeting: {
    marginTop: 4,
    color: "#172321",
    fontSize: 23,
    fontWeight: "700",
  },
  organization: {
    marginTop: 5,
    color: "#34433f",
    fontWeight: "600",
  },
  location: {
    color: "#52615e",
  },
  sectionTitle: {
    marginTop: 6,
    color: "#172321",
    fontSize: 17,
    fontWeight: "700",
  },
  note: {
    marginTop: 4,
    color: "#52615e",
    fontSize: 13,
    lineHeight: 19,
  },
});
