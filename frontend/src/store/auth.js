import { create } from "zustand";
import api from "../api/client";

const useAuthStore = create((set) => ({
  user: null,
  loading: true,

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
    localStorage.clear();
    set({ user: null });
  },

  fetchMe: async () => {
    try {
      const { data } = await api.get("/auth/me/");
      set({ user: data, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
}));

export default useAuthStore;
