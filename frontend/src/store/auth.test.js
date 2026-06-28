import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import useAuthStore from "./auth.js";
import { server } from "../test/mocks/server.js";
import { API_BASE, defaultUser } from "../test/mocks/handlers.js";

const resetStore = () => useAuthStore.setState({ user: null, loading: true });

describe("useAuthStore", () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    resetStore();
  });

  it("login stores JWT tokens in localStorage and sets user", async () => {
    await useAuthStore.getState().login("test@example.com", "TestPass123!");

    expect(localStorage.getItem("access_token")).toBe("fake-access-token");
    expect(localStorage.getItem("refresh_token")).toBe("fake-refresh-token");
    expect(useAuthStore.getState().user).toEqual(defaultUser);
  });

  it("logout clears localStorage, resets user, and sets loading false", () => {
    localStorage.setItem("access_token", "fake-access-token");
    localStorage.setItem("refresh_token", "fake-refresh-token");
    useAuthStore.setState({ user: defaultUser, loading: false });

    useAuthStore.getState().logout();

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().loading).toBe(false);
  });

  it("fetchMe skips network call and resolves immediately when no token", async () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");

    await useAuthStore.getState().fetchMe();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.loading).toBe(false);
  });

  it("fetchMe on 401 sets user null and loading false (no crash)", async () => {
    server.use(http.get(`${API_BASE}/auth/me/`, () => new HttpResponse(null, { status: 401 })));
    // Simulate having a token so fetchMe actually makes the network call
    localStorage.setItem("access_token", "expired-token");

    await useAuthStore.getState().fetchMe();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.loading).toBe(false);
  });
});
