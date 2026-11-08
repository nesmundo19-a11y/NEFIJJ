import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import ActionButton from "../components/ActionButton";
import { registerPushDevice } from "../notifications/push";

export default function EmergenciesScreen() {
  const [protocols, setProtocols] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState("");
  const [error, setError] = useState("");

  const loadProtocols = useCallback(async () => {
    setError("");
    try {
      const [protocolResponse, alertResponse] = await Promise.all([
        api.get("/emergencies/"),
        api.get("/emergency-alerts/"),
      ]);
      setProtocols(protocolResponse.data.results);
      setAlerts(alertResponse.data.results);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadProtocols();
    }, [loadProtocols]),
  );

  async function enableNotifications() {
    setRegistering(true);
    setNotificationMessage("");
    setError("");
    try {
      const result = await registerPushDevice();
      setNotificationMessage(
        result.status === "registered"
          ? "Este dispositivo quedó registrado para recibir alertas."
          : "No se activaron las notificaciones. Puedes habilitarlas en los ajustes del dispositivo.",
      );
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setRegistering(false);
    }
  }

  return (
    <View style={styles.page}>
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {notificationMessage ? (
        <Text accessibilityRole="status" style={styles.notificationMessage}>
          {notificationMessage}
        </Text>
      ) : null}
      {loading ? (
        <ActivityIndicator color="#0b6b63" size="large" style={styles.loading} />
      ) : (
        <FlatList
          contentContainerStyle={protocols.length ? styles.list : styles.emptyList}
          data={protocols}
          keyExtractor={(item) => String(item.id)}
          ListHeaderComponent={
            <View>
              <View style={styles.notice}>
                <Text style={styles.noticeTitle}>Alertas de emergencia</Text>
                <Text style={styles.noticeText}>
                  Las notificaciones dependen de internet y del servicio push; no se garantiza
                  su entrega. Ante un peligro inmediato, sigue las indicaciones de los
                  servicios oficiales.
                </Text>
                <ActionButton
                  compact
                  disabled={registering}
                  onPress={enableNotifications}
                  title={registering ? "Activando…" : "Activar notificaciones en este dispositivo"}
                  variant="secondary"
                />
              </View>
              <Text style={styles.sectionTitle}>Alertas recibidas</Text>
              {alerts.map((alert) => (
                <View key={alert.id} style={styles.card}>
                  <Text style={styles.title}>{alert.title}</Text>
                  <Text style={styles.content}>{alert.message}</Text>
                  <Text style={styles.meta}>
                    {alert.status === "cancelled" ? "Cancelada" : "Activa"} ·{" "}
                    {new Date(alert.created_at).toLocaleString()}
                  </Text>
                </View>
              ))}
              <View style={styles.notice}>
                <Text style={styles.noticeTitle}>Protocolos preventivos</Text>
                <Text style={styles.noticeText}>
                  Estos protocolos son información de referencia, no alertas en tiempo real.
                  Ante un peligro inmediato, sigue las indicaciones de los servicios oficiales.
                </Text>
              </View>
            </View>
          }
          ListEmptyComponent={
            <Text style={styles.empty}>No hay protocolos activos para esta sede.</Text>
          }
          refreshControl={
            <RefreshControl
              onRefresh={() => {
                setRefreshing(true);
                loadProtocols();
              }}
              refreshing={refreshing}
            />
          }
          renderItem={({ item }) => (
            <View style={styles.card}>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.content}>{item.content}</Text>
              <Text style={styles.phone}>Contacto: {item.contact_phone}</Text>
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    padding: 16,
    backgroundColor: "#f4f7f6",
  },
  list: {
    paddingBottom: 24,
  },
  notice: {
    marginBottom: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e7c56d",
    borderRadius: 14,
    backgroundColor: "#fff8e6",
  },
  noticeTitle: {
    color: "#684800",
    fontSize: 15,
    fontWeight: "800",
  },
  noticeText: {
    marginTop: 6,
    color: "#684800",
    lineHeight: 20,
  },
  sectionTitle: {
    marginBottom: 10,
    color: "#172321",
    fontSize: 17,
    fontWeight: "700",
  },
  emptyList: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  card: {
    marginBottom: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#e2eae7",
    borderRadius: 16,
    backgroundColor: "#ffffff",
    elevation: 2,
  },
  title: {
    color: "#172321",
    fontSize: 17,
    fontWeight: "700",
  },
  content: {
    marginTop: 8,
    color: "#34433f",
    lineHeight: 21,
  },
  phone: {
    marginTop: 12,
    color: "#0b6b63",
    fontWeight: "700",
  },
  meta: {
    marginTop: 10,
    color: "#52615e",
    fontSize: 12,
  },
  notificationMessage: {
    marginVertical: 8,
    color: "#0b6b63",
  },
  loading: {
    marginTop: 32,
  },
  empty: {
    color: "#52615e",
    textAlign: "center",
  },
  error: {
    marginVertical: 8,
    color: "#a42323",
  },
});
