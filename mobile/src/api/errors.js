export function getApiErrorMessage(error) {
  const data = error.response?.data;
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (data && typeof data === "object") {
    const firstError = Object.values(data).flat().find((value) => typeof value === "string");
    if (firstError) {
      return firstError;
    }
  }

  if (error.code === "ECONNABORTED") {
    return "La solicitud tardó demasiado. Inténtalo nuevamente.";
  }

  if (error.response?.status === 404) {
    return "El servidor respondió, pero no encontró la ruta. Verifica que EXPO_PUBLIC_API_URL termine en /api/v1.";
  }

  if (error.response?.status === 400) {
    return "El servidor rechazó la solicitud. Verifica DJANGO_ALLOWED_HOSTS y la configuración del backend.";
  }

  if (!error.response) {
    return "No se alcanzó el backend. Verifica que Django esté activo en 0.0.0.0:8000, que el teléfono use la misma red Wi-Fi y que la IP de EXPO_PUBLIC_API_URL siga vigente.";
  }

  return "No fue posible completar la solicitud. Inténtalo de nuevo.";
}
