import axios from "axios";
import * as SecureStore from "expo-secure-store";

const baseURL = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, "");

if (!baseURL) {
  throw new Error("Configura EXPO_PUBLIC_API_URL en mobile/.env.local.");
}

const authClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

let sessionExpiredHandler;

export function registerSessionExpiredHandler(handler) {
  sessionExpiredHandler = handler;
  return () => {
    if (sessionExpiredHandler === handler) {
      sessionExpiredHandler = undefined;
    }
  };
}

async function invalidateSession() {
  await clearSession();
  sessionExpiredHandler?.();
}

const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

export async function saveSession({ access, refresh }) {
  await Promise.all([
    SecureStore.setItemAsync("access_token", access),
    SecureStore.setItemAsync("refresh_token", refresh),
  ]);
}

export async function clearSession() {
  await Promise.all([
    SecureStore.deleteItemAsync("access_token"),
    SecureStore.deleteItemAsync("refresh_token"),
    SecureStore.deleteItemAsync("user"),
    SecureStore.deleteItemAsync("active_organization_id"),
  ]);
}

export async function saveUser(user) {
  await SecureStore.setItemAsync("user", JSON.stringify(user));
}

export async function saveActiveOrganization(organizationId) {
  if (organizationId === null || organizationId === undefined) {
    await SecureStore.deleteItemAsync("active_organization_id");
    return;
  }
  await SecureStore.setItemAsync("active_organization_id", String(organizationId));
}

let refreshInFlight;

async function refreshAccessToken(refresh) {
  if (!refreshInFlight) {
    refreshInFlight = authClient
      .post("/auth/token/refresh/", { refresh })
      .then(async ({ data }) => {
        await saveSession({
          access: data.access,
          refresh: data.refresh ?? refresh,
        });
        return data.access;
      })
      .finally(() => {
        refreshInFlight = undefined;
      });
  }

  return refreshInFlight;
}

api.interceptors.request.use(async (config) => {
  const [access, organizationId] = await Promise.all([
    SecureStore.getItemAsync("access_token"),
    SecureStore.getItemAsync("active_organization_id"),
  ]);
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  if (organizationId) {
    config.headers["X-Organization-ID"] = organizationId;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const isAuthenticationRequest = request?.url?.startsWith("/auth/");
    if (
      error.response?.status !== 401 ||
      !request ||
      request._retry ||
      isAuthenticationRequest
    ) {
      return Promise.reject(error);
    }

    request._retry = true;
    const refresh = await SecureStore.getItemAsync("refresh_token");
    if (!refresh) {
      await invalidateSession();
      return Promise.reject(error);
    }

    try {
      const access = await refreshAccessToken(refresh);
      request.headers.Authorization = `Bearer ${access}`;
      return api(request);
    } catch (refreshError) {
      await invalidateSession();
      return Promise.reject(refreshError);
    }
  },
);

export async function authenticate(username, password) {
  const { data } = await authClient.post("/auth/token/", { username, password });
  try {
    await saveSession(data);
    await saveUser(data.user);
  } catch (error) {
    await clearSession();
    throw error;
  }
  return data.user;
}

export default api;
