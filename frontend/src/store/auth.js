import { create } from "zustand";
import api from "../api/client";

// If no token is stored, we know immediately the user is not logged in.
// This avoids blocking the whole app on a network call for unauthenticated visitors.
const hasToken = () => Boolean(localStorage.getItem("access_token"));

const useAuthStore = create((set) => ({
  user: null,
  // Only show loading spinner if we have a token and need to verify it.
  loading: hasToken(),

  login: async (email, password) => {
    const { data } = await api.post("/auth/token/", { email, password });
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    const me = await api.get("/auth/me/");
    set({ user: me.data });
  },

  googleLogin: async (credential) => {
    const { data } = await api.post("/auth/google/", { credential });
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    set({ user: data.user });
  },

  googleComplete: async (credential, org_name) => {
    const { data } = await api.post("/auth/google/complete/", { credential, org_name });
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    set({ user: data.user });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, loading: false });
  },

  fetchMe: async () => {
    if (!hasToken()) {
      // No token — resolve immediately without a network call.
      set({ user: null, loading: false });
      return;
    }
    try {
      const { data } = await api.get("/auth/me/");
      set({ user: data, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
}));

export default useAuthStore;
