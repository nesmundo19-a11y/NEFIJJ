import { StyleSheet, Text, View } from "react-native";

const STATUS_STYLES = {
  pendiente: { label: "Pendiente", color: "#835500", backgroundColor: "#fff2cc" },
  en_proceso: { label: "En proceso", color: "#145a8d", backgroundColor: "#e1f1ff" },
  resuelta: { label: "Resuelta", color: "#17633d", backgroundColor: "#e2f5e9" },
  cerrada: { label: "Cerrada", color: "#4b5563", backgroundColor: "#e9edf0" },
};

const PRIORITY_STYLES = {
  baja: { label: "Baja", color: "#17633d", backgroundColor: "#e2f5e9" },
  media: { label: "Media", color: "#835500", backgroundColor: "#fff2cc" },
  alta: { label: "Alta", color: "#a34600", backgroundColor: "#ffeadb" },
  critica: { label: "Crítica", color: "#a42323", backgroundColor: "#fde5e5" },
};

function Badge({ value, styles }) {
  const badge = styles[value] ?? {
    label: value,
    color: "#4b5563",
    backgroundColor: "#e9edf0",
  };
  return (
    <Text style={[componentStyles.badge, { color: badge.color, backgroundColor: badge.backgroundColor }]}>
      {badge.label}
    </Text>
  );
}

export function IncidentBadges({ priority, status }) {
  return (
    <View style={componentStyles.row}>
      <Badge value={status} styles={STATUS_STYLES} />
      <Badge value={priority} styles={PRIORITY_STYLES} />
    </View>
  );
}

const componentStyles = StyleSheet.create({
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 7,
    marginTop: 10,
  },
  badge: {
    overflow: "hidden",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 16,
    fontSize: 12,
    fontWeight: "700",
  },
});
