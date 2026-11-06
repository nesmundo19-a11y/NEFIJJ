import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as SecureStore from "expo-secure-store";

import {
  authenticate,
  clearSession,
  registerSessionExpiredHandler,
  saveActiveOrganization,
} from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [activeOrganizationId, setActiveOrganizationId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initializationError, setInitializationError] = useState(null);

  const restoreSession = useCallback(async () => {
    setLoading(true);
    setInitializationError(null);
    try {
      const [access, refresh, storedUser, storedOrganizationId] = await Promise.all([
        SecureStore.getItemAsync("access_token"),
        SecureStore.getItemAsync("refresh_token"),
        SecureStore.getItemAsync("user"),
        SecureStore.getItemAsync("active_organization_id"),
      ]);
      if (!access || !refresh || !storedUser) {
        await clearSession();
        setUser(null);
        setActiveOrganizationId(null);
      } else {
        const restoredUser = JSON.parse(storedUser);
        if (!Array.isArray(restoredUser.organizations)) {
          await clearSession();
          setUser(null);
          setActiveOrganizationId(null);
          return;
        }
        const activeMemberships = (restoredUser.organizations ?? []).filter(
          (membership) => membership.organization_status === "active",
        );
        const storedMembership = activeMemberships.find(
          (membership) => String(membership.organization_id) === storedOrganizationId,
        );
        const selectedOrganizationId =
          storedMembership?.organization_id ??
          (activeMemberships.length === 1 ? activeMemberships[0].organization_id : null);
        await saveActiveOrganization(selectedOrganizationId);
        setUser(restoredUser);
        setActiveOrganizationId(
          selectedOrganizationId === null ? null : String(selectedOrganizationId),
        );
      }
    } catch {
      setInitializationError("No se pudo restaurar la sesión segura. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(
    () =>
      registerSessionExpiredHandler(() => {
        setUser(null);
        setActiveOrganizationId(null);
      }),
    [],
  );

  const login = useCallback(async (username, password) => {
    const authenticatedUser = await authenticate(username, password);
    const activeMemberships = (authenticatedUser.organizations ?? []).filter(
      (membership) => membership.organization_status === "active",
    );
    const selectedOrganizationId =
      activeMemberships.length === 1 ? activeMemberships[0].organization_id : null;
    try {
      await saveActiveOrganization(selectedOrganizationId);
    } catch (error) {
      await clearSession();
      throw error;
    }
    setUser(authenticatedUser);
    setActiveOrganizationId(
      selectedOrganizationId === null ? null : String(selectedOrganizationId),
    );
    return authenticatedUser;
  }, []);

  const selectOrganization = useCallback(
    async (organizationId) => {
      const membership = (user?.organizations ?? []).find(
        (item) =>
          String(item.organization_id) === String(organizationId) &&
          item.organization_status === "active",
      );
      if (!membership) {
        throw new Error("No tienes acceso a una organización activa con ese identificador.");
      }
      await saveActiveOrganization(membership.organization_id);
      setActiveOrganizationId(String(membership.organization_id));
    },
    [user],
  );

  const logout = useCallback(async () => {
    await clearSession();
    setUser(null);
    setActiveOrganizationId(null);
  }, []);

  const activeMembership = useMemo(
    () =>
      (user?.organizations ?? []).find(
        (membership) =>
          String(membership.organization_id) === activeOrganizationId &&
          membership.organization_status === "active",
      ) ?? null,
    [user, activeOrganizationId],
  );
  const scopedUser = useMemo(
    () =>
      user
        ? {
            ...user,
            role:
              activeMembership?.role ??
              (user.role === "superadmin" ? "superadmin" : "member"),
            location_id: activeMembership
              ? activeMembership.location_id
              : user.location_id,
            active_organization_id: activeMembership?.organization_id ?? null,
          }
        : null,
    [user, activeMembership],
  );

  const value = useMemo(
    () => ({
      user: scopedUser,
      activeMembership,
      selectOrganization,
      loading,
      initializationError,
      login,
      logout,
      retryRestore: restoreSession,
    }),
    [
      scopedUser,
      activeMembership,
      selectOrganization,
      loading,
      initializationError,
      login,
      logout,
      restoreSession,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider.");
  }
  return context;
}
