import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";

import api from "../api/client";
import { getApiErrorMessage } from "../api/errors";

export default function EmergenciesScreen() {
  const [protocols, setProtocols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadProtocols = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get("/emergencies/");
      setProtocols(data.results);
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

  return (
    <View style={styles.page}>
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      {loading ? (
        <ActivityIndicator color="#0b6b63" size="large" style={styles.loading} />
      ) : (
        <FlatList
          contentContainerStyle={protocols.length ? styles.list : styles.emptyList}
          data={protocols}
          keyExtractor={(item) => String(item.id)}
          ListHeaderComponent={
            <View style={styles.notice}>
              <Text style={styles.noticeTitle}>Información preventiva</Text>
              <Text style={styles.noticeText}>
                Estos protocolos son información de referencia, no alertas en tiempo real.
                Ante un peligro inmediato, sigue las indicaciones de los servicios oficiales.
              </Text>
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
