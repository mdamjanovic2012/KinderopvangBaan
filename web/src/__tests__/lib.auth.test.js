/**
 * Tests for src/lib/auth.js
 */
import { loginRequest, registerRequest, getMeRequest, refreshRequest } from "@/lib/auth";

const mockFetch = (data, ok = true) => {
  global.fetch.mockResolvedValueOnce({
    ok,
    json: async () => data,
  });
};

describe("loginRequest", () => {
  it("posts to token endpoint", async () => {
    mockFetch({ access: "acc_token", refresh: "ref_token" });
    const result = await loginRequest("user1", "pass123");
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toContain("/auth/token/");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({ username: "user1", password: "pass123" });
    expect(result.access).toBe("acc_token");
  });

  it("throws on failure", async () => {
    mockFetch({ detail: "No active account" }, false);
    await expect(loginRequest("x", "y")).rejects.toEqual({ detail: "No active account" });
  });
});

describe("registerRequest", () => {
  it("posts to register endpoint", async () => {
    mockFetch({ id: 1, username: "newuser" });
    await registerRequest({ username: "newuser", email: "a@b.nl", password: "pass1234", role: "worker" });
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toContain("/auth/register/");
    expect(opts.method).toBe("POST");
    const body = JSON.parse(opts.body);
    expect(body.username).toBe("newuser");
    expect(body.role).toBe("worker");
  });

  it("throws on validation error", async () => {
    mockFetch({ username: ["This field is required."] }, false);
    await expect(registerRequest({})).rejects.toEqual({ username: ["This field is required."] });
  });
});

describe("getMeRequest", () => {
  it("sends Authorization header", async () => {
    mockFetch({ id: 1, username: "me", role: "worker" });
    const result = await getMeRequest("my_access_token");
    const [, opts] = fetch.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer my_access_token");
    expect(result.username).toBe("me");
  });

  it("throws on 401", async () => {
    mockFetch({ detail: "Token is invalid" }, false);
    await expect(getMeRequest("bad_token")).rejects.toEqual({ detail: "Token is invalid" });
  });
});

describe("refreshRequest", () => {
  it("posts refresh token", async () => {
    mockFetch({ access: "new_access_token" });
    const result = await refreshRequest("my_refresh");
    const [url, opts] = fetch.mock.calls[0];
    expect(url).toContain("/auth/token/refresh/");
    expect(JSON.parse(opts.body)).toEqual({ refresh: "my_refresh" });
    expect(result.access).toBe("new_access_token");
  });

  it("throws on expired refresh", async () => {
    mockFetch({ code: "token_not_valid" }, false);
    await expect(refreshRequest("old_refresh")).rejects.toEqual({ code: "token_not_valid" });
  });
});
