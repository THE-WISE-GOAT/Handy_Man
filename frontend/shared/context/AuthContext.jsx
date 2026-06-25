import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiClient } from "@shared/api/client";
import {
  getDefaultCustomerPath,
  getDefaultWorkerPath,
} from "@shared/config/viewRoutes";

const AuthContext = createContext(null);
const TOKEN_KEY = "handy_man_access_token";
const TOKEN_TYPE_KEY = "handy_man_token_type";
const USERNAME_KEY = "handy_man_username";
const USER_KEY = "handy_man_user";

const decodeTokenPayload = (token) => {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) return null;

    const normalized = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
};

const hasTokenExpired = (token) => {
  const payload = decodeTokenPayload(token);
  if (!payload || !payload.exp) return false;
  const nowInSeconds = Math.floor(Date.now() / 1000);
  return nowInSeconds >= payload.exp;
};

const safeParseJSON = (value) => {
  if (!value) return null;

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
};

const normalizeUserProfile = (profile, fallbackUsername = "") => {
  if (!profile) {
    return null;
  }

  const roleNames = Array.isArray(profile.roles)
    ? profile.roles.map((role) => role.name)
    : [];

  const primaryRole = roleNames.length > 0 ? roleNames[0] : null;

  return {
    ...profile,
    roles: roleNames,
    role: primaryRole,
    username: profile.username || fallbackUsername,
    email: profile.email || "",
    firstName:
      profile.firstName ||
      profile.first_name ||
      profile.username?.split(" ")?.[0] ||
      fallbackUsername,
    lastName:
      profile.lastName ||
      profile.last_name ||
      profile.username?.split(" ")?.[1] ||
      "",
    locationLabel:
      profile.locationLabel ||
      profile.location_label ||
      "System Location Active",
    accountType:
      primaryRole === "worker"
        ? "Service Specialist"
        : primaryRole === "technician"
          ? "Service Specialist"
          : primaryRole === "provider"
            ? "Service Specialist"
            : "Customer",
  };
};

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState("");
  const [tokenType, setTokenType] = useState("bearer");
  const [username, setUsername] = useState("");
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const bootstrapUserSession = async ({
    token,
    type = "bearer",
    usernameValue = "",
  }) => {
    const responseBody = await apiClient.get(`/users/me`, {
      token,
      tokenType: type,
    });

    const profile = normalizeUserProfile(responseBody, usernameValue);

    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TOKEN_TYPE_KEY, type);
    if (usernameValue) {
      localStorage.setItem(USERNAME_KEY, usernameValue);
    }
    if (profile) {
      localStorage.setItem(USER_KEY, JSON.stringify(profile));
    }

    setAccessToken(token);
    setTokenType(type);
    setUsername(profile?.username || usernameValue || "");
    setUser(profile);

    return profile;
  };

  useEffect(() => {
    try {
      const storedToken = localStorage.getItem(TOKEN_KEY) || "";
      const storedTokenType = localStorage.getItem(TOKEN_TYPE_KEY) || "bearer";
      const storedUsername = localStorage.getItem(USERNAME_KEY) || "";
      const storedUser = safeParseJSON(localStorage.getItem(USER_KEY));

      if (storedToken && !hasTokenExpired(storedToken)) {
        setAccessToken(storedToken);
        setTokenType(storedTokenType);
        setUsername(storedUsername);
        setUser(storedUser);
      } else {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TOKEN_TYPE_KEY);
        localStorage.removeItem(USERNAME_KEY);
        localStorage.removeItem(USER_KEY);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async ({ token, type = "bearer", usernameValue = "" }) => {
    return bootstrapUserSession({ token, type, usernameValue });
  };

  const logoutLocal = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_TYPE_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(USER_KEY);
    setAccessToken("");
    setTokenType("bearer");
    setUsername("");
    setUser(null);
  };

  const logout = async () => {
    try {
      await apiClient.post("/service-tasks/logout", {}, { skipAuth: false });
    } catch (error) {
      console.warn("Logout API call failed:", error);
    }
    logoutLocal();
  };

  const isAuthenticated = Boolean(accessToken) && !hasTokenExpired(accessToken);
  const roles = Array.isArray(user?.roles) ? user.roles : [];
  const normalizedRoles = roles.map((role) => String(role).toLowerCase());
  const hasRole = (roleName) =>
    normalizedRoles.includes(String(roleName).toLowerCase());
  const canAccessWorker = ["worker", "technician", "provider"].some(
    (roleName) => hasRole(roleName),
  );
  const defaultHomePath = canAccessWorker
    ? getDefaultWorkerPath()
    : getDefaultCustomerPath("dashboard");

  const value = useMemo(
    () => ({
      accessToken,
      tokenType,
      username,
      user,
      roles,
      isLoading,
      isAuthenticated,
      canAccessWorker,
      defaultHomePath,
      hasRole,
      login,
      logout,
    }),
    [
      accessToken,
      tokenType,
      username,
      user,
      roles,
      isLoading,
      isAuthenticated,
      canAccessWorker,
      defaultHomePath,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
