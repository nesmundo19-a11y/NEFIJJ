import { Pressable, StyleSheet, Text } from "react-native";

const styles = StyleSheet.create({
  button: {
    width: "100%",
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1,
    borderRadius: 14,
  },
  fitContent: {
    width: "auto",
    flexShrink: 0,
  },
  primary: {
    borderColor: "#075b55",
    backgroundColor: "#0b6b63",
    elevation: 3,
    shadowColor: "#075b55",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 6,
  },
  secondary: {
    borderColor: "#c5ddd7",
    backgroundColor: "#eaf4f1",
  },
  quiet: {
    borderColor: "#dce6e3",
    backgroundColor: "#ffffff",
  },
  compact: {
    minHeight: 40,
    paddingHorizontal: 14,
    borderRadius: 12,
  },
  text: {
    flexShrink: 1,
    flexWrap: "wrap",
    textAlign: "center",
    fontSize: 14,
    fontWeight: "700",
  },
  primaryText: {
    color: "#ffffff",
  },
  secondaryText: {
    color: "#075b55",
  },
  quietText: {
    color: "#34433f",
  },
  pressed: {
    opacity: 0.82,
    transform: [{ scale: 0.98 }],
  },
  disabled: {
    opacity: 0.5,
  },
});

const VARIANT_STYLES = {
  primary: {
    button: styles.primary,
    text: styles.primaryText,
  },
  secondary: {
    button: styles.secondary,
    text: styles.secondaryText,
  },
  quiet: {
    button: styles.quiet,
    text: styles.quietText,
  },
};

export default function ActionButton({
  title,
  onPress,
  variant = "primary",
  disabled = false,
  compact = false,
  fullWidth = true,
}) {
  const variantStyles = VARIANT_STYLES[variant] ?? VARIANT_STYLES.primary;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        !fullWidth && styles.fitContent,
        variantStyles.button,
        compact && styles.compact,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <Text style={[styles.text, variantStyles.text]}>{title}</Text>
    </Pressable>
  );
}
