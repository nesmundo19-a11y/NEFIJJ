import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import ActionButton from "../components/ActionButton";

async function fetchAllAlerts() {
  const alerts = [];
  let page = 1;
  while (true) {
    const { data } = await api.get("/emergency-alerts/", { params: { page } });
    alerts.push(...data.results);
    if (!data.next) {
      return alerts;
    }
    page += 1;
  }
}

export default function EmergencyAlertManagementScreen() {
  const [alerts, setAlerts] = useState([]);
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadAlerts = useCallback(async () => {
    setError("");
    try {
      setAlerts(await fetchAllAlerts());
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadAlerts();
    }, [loadAlerts]),
  );

  async function createAlert() {
    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      const { data } = await api.post("/emergency-alerts/", {
        title: title.trim(),
        message: message.trim(),
      });
      setTitle("");
      setMessage("");
      setNotice(
        data.pending_deliveries
          ? "Alerta registrada. Las notificaciones están pendientes; la entrega no está garantizada."
          : "Alerta registrada, pero no hay dispositivos activos con notificaciones push en la organización.",
      );
      await loadAlerts();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  function confirmCreateAlert() {
    if (!title.trim() || !message.trim()) {
      setError("Completa el título y el mensaje antes de emitir la alerta.");
      return;
    }
    Alert.alert(
      "Enviar alerta a toda la organización",
      "La alerta se enviará a los dispositivos activos registrados. La entrega push no se garantiza y no puede retirarse de dispositivos que ya la recibieron.",
      [
        { text: "Volver", style: "cancel" },
        { text: "Enviar alerta", style: "destructive", onPress: createAlert },
      ],
    );
  }

  function cancelAlert(alert) {
    Alert.alert(
      "Cancelar alerta",
      "Se detendrán los reintentos pendientes y se programará un aviso de cancelación para toda la organización.",
      [
        { text: "Volver", style: "cancel" },
        {
          text: "Cancelar alerta",
          style: "destructive",
          onPress: async () => {
            setError("");
            setNotice("");
            try {
              await api.post(`/emergency-alerts/${alert.id}/cancel/`);
              setNotice("Alerta cancelada; los avisos de cancelación quedaron programados.");
              await loadAlerts();
            } catch (requestError) {
              setError(getApiErrorMessage(requestError));
            }
          },
        },
      ],
    );
  }

  function renderAlert(item) {
    return (
      <View style={styles.alertCard}>
        <Text style={styles.alertTitle}>{item.title}</Text>
        <Text style={styles.body}>{item.message}</Text>
        <Text style={styles.meta}>
          {item.status === "cancelled" ? "Cancelada" : "Activa"} ·{" "}
          {new Date(item.created_at).toLocaleString()}
        </Text>
        <Text style={styles.delivery}>
          Push aceptadas por el servicio: {item.accepted_deliveries} · pendientes:{" "}
          {item.pending_deliveries} · fallidas: {item.failed_deliveries}
        </Text>
        <Text style={styles.disclaimer}>
          “Aceptada” indica que Expo recibió la solicitud, no que el dispositivo la mostró.
        </Text>
        {item.delivery_errors?.length ? (
          <Text style={styles.error}>
            Fallos recientes: {item.delivery_errors.join("; ")}
          </Text>
        ) : null}
        {item.status === "active" ? (
          <ActionButton
            compact
            onPress={() => cancelAlert(item)}
            title="Cancelar alerta"
            variant="quiet"
          />
        ) : null}
      </View>
    );
  }

  return (
    <View style={styles.page}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            onRefresh={() => {
              setRefreshing(true);
              loadAlerts();
            }}
            refreshing={refreshing}
          />
        }
      >
        <View style={styles.warning}>
          <Text style={styles.warningTitle}>Uso para emergencias reales</Text>
          <Text style={styles.warningText}>
            Solo administradores de organización pueden emitir o cancelar. El aviso se dirige
            a todos los miembros activos con un dispositivo registrado. No sustituye los
            canales oficiales y la entrega push no se garantiza.
          </Text>
        </View>

        <Text style={styles.label}>Título</Text>
        <TextInput
          accessibilityLabel="Título de la alerta"
          maxLength={150}
          onChangeText={setTitle}
          placeholder="Ej.: Evacuación preventiva"
          style={styles.input}
          value={title}
        />
        <Text style={styles.label}>Mensaje</Text>
        <TextInput
          accessibilityLabel="Mensaje de la alerta"
          maxLength={2000}
          multiline
          onChangeText={setMessage}
          placeholder="Indica qué ocurre y qué deben hacer las personas."
          style={[styles.input, styles.messageInput]}
          textAlignVertical="top"
          value={message}
        />
        <ActionButton
          disabled={submitting}
          onPress={confirmCreateAlert}
          title={submitting ? "Enviando…" : "Revisar y emitir alerta"}
        />
        {notice ? <Text accessibilityRole="status" style={styles.notice}>{notice}</Text> : null}
        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}

        <Text style={styles.sectionTitle}>Alertas de la organización</Text>
        {loading ? (
          <ActivityIndicator color="#0b6b63" size="large" style={styles.loading} />
        ) : alerts.length ? (
          alerts.map((alert) => <View key={alert.id}>{renderAlert(alert)}</View>)
        ) : (
          <Text style={styles.empty}>Todavía no hay alertas de emergencia.</Text>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#f4f7f6",
  },
  content: {
    gap: 10,
    padding: 16,
    paddingBottom: 28,
  },
  warning: {
    padding: 14,
    borderWidth: 1,
    borderColor: "#e7c56d",
    borderRadius: 14,
    backgroundColor: "#fff8e6",
  },
  warningTitle: {
    color: "#684800",
    fontWeight: "800",
  },
  warningText: {
    marginTop: 6,
    color: "#684800",
    lineHeight: 20,
  },
  label: {
    marginTop: 4,
    color: "#263238",
    fontWeight: "700",
  },
  input: {
    minHeight: 48,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: "#b8c6c2",
    borderRadius: 12,
    backgroundColor: "#ffffff",
    color: "#172321",
  },
  messageInput: {
    minHeight: 110,
  },
  sectionTitle: {
    marginTop: 10,
    color: "#172321",
    fontSize: 18,
    fontWeight: "700",
  },
  alertCard: {
    gap: 8,
    marginBottom: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#e2eae7",
    borderRadius: 14,
    backgroundColor: "#ffffff",
  },
  alertTitle: {
    color: "#172321",
    fontSize: 16,
    fontWeight: "700",
  },
  body: {
    color: "#34433f",
    lineHeight: 20,
  },
  meta: {
    color: "#52615e",
    fontSize: 12,
  },
  delivery: {
    color: "#34433f",
    fontSize: 13,
  },
  disclaimer: {
    color: "#684800",
    fontSize: 12,
  },
  empty: {
    paddingVertical: 10,
    color: "#52615e",
  },
  loading: {
    marginTop: 20,
  },
  notice: {
    color: "#0b6b63",
  },
  error: {
    color: "#a42323",
  },
});
