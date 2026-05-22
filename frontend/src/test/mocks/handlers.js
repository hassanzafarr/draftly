import { http, HttpResponse } from "msw";

export const API_BASE = "/api";

export const defaultUser = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "test@example.com",
  role: "admin",
  org: {
    id: "00000000-0000-0000-0000-000000000099",
    name: "Test Org",
    subscription_tier: "starter",
    doc_quota: 50,
    proposal_quota: 50,
    created_at: "2026-01-01T00:00:00Z",
  },
  created_at: "2026-01-01T00:00:00Z",
};

export const handlers = [
  http.post(`${API_BASE}/auth/token/`, async () => {
    return HttpResponse.json({
      access: "fake-access-token",
      refresh: "fake-refresh-token",
    });
  }),

  http.get(`${API_BASE}/auth/me/`, ({ request }) => {
    const auth = request.headers.get("authorization");
    if (!auth || !auth.startsWith("Bearer ")) {
      return new HttpResponse(null, { status: 401 });
    }
    return HttpResponse.json(defaultUser);
  }),
];
