/**
 * Tests for src/context/AuthContext.jsx
 */
import React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/context/AuthContext";

jest.mock("@/lib/auth");
import * as authLib from "@/lib/auth";

function TestConsumer({ onAction } = {}) {
  const { user, loading, login, logout, register } = useAuth();
  return (
    <div>
      <div data-testid="loading">{loading ? "loading" : "ready"}</div>
      <div data-testid="user">{user ? user.username : "none"}</div>
      <button data-testid="login-btn" onClick={() => login("u", "p").catch(() => {})}>Login</button>
      <button data-testid="logout-btn" onClick={logout}>Logout</button>
      <button
        data-testid="register-btn"
        onClick={() =>
          register({ username: "new", email: "a@b.nl", password: "pass1234", role: "worker" }).catch(() => {})
        }
      >
        Register
      </button>
    </div>
  );
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );
}

describe("AuthContext — initial state (no tokens)", () => {
  it("shows ready after mount with no tokens", async () => {
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("ready"));
  });

  it("user is null when no tokens", async () => {
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("none"));
  });
});

describe("AuthContext — session restore", () => {
  it("restores session from valid access token", async () => {
    localStorage.setItem("kb_access", "valid_access");
    localStorage.setItem("kb_refresh", "valid_refresh");
    authLib.getMeRequest.mockResolvedValueOnce({ id: 1, username: "restoreduser", role: "worker" });

    renderWithAuth();
    await waitFor(() =>
      expect(screen.getByTestId("user").textContent).toBe("restoreduser")
    );
  });

  it("refreshes when access token is expired", async () => {
    localStorage.setItem("kb_access", "expired_access");
    localStorage.setItem("kb_refresh", "valid_refresh");
    authLib.getMeRequest
      .mockRejectedValueOnce({ detail: "token_expired" })
      .mockResolvedValueOnce({ id: 1, username: "refresheduser", role: "worker" });
    authLib.refreshRequest.mockResolvedValueOnce({ access: "new_access" });

    renderWithAuth();
    await waitFor(() =>
      expect(screen.getByTestId("user").textContent).toBe("refresheduser")
    );
    expect(localStorage.getItem("kb_access")).toBe("new_access");
  });

  it("logs out when both tokens are invalid", async () => {
    localStorage.setItem("kb_access", "bad");
    localStorage.setItem("kb_refresh", "also_bad");
    authLib.getMeRequest.mockRejectedValueOnce({ detail: "expired" });
    authLib.refreshRequest.mockRejectedValueOnce({ detail: "invalid" });

    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("none"));
    expect(localStorage.getItem("kb_access")).toBeNull();
  });
});

describe("AuthContext — login", () => {
  it("stores tokens and sets user on success", async () => {
    authLib.loginRequest.mockResolvedValueOnce({ access: "acc", refresh: "ref" });
    authLib.getMeRequest.mockResolvedValueOnce({ id: 1, username: "loginuser", role: "worker" });

    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("ready"));

    await act(async () => {
      screen.getByTestId("login-btn").click();
    });
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("loginuser"));
    expect(localStorage.getItem("kb_access")).toBe("acc");
  });

  it("user remains null after failed login", async () => {
    authLib.loginRequest.mockRejectedValueOnce({ detail: "No active account" });

    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("ready"));
    await act(async () => { screen.getByTestId("login-btn").click(); });
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("none"));
  });
});

describe("AuthContext — logout", () => {
  it("clears user and tokens", async () => {
    localStorage.setItem("kb_access", "tok");
    localStorage.setItem("kb_refresh", "ref");
    authLib.getMeRequest.mockResolvedValueOnce({ id: 1, username: "u", role: "worker" });

    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("u"));

    act(() => { screen.getByTestId("logout-btn").click(); });
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("none"));
    expect(localStorage.getItem("kb_access")).toBeNull();
  });
});

describe("AuthContext — register", () => {
  it("registers and auto-logs in", async () => {
    authLib.registerRequest.mockResolvedValueOnce({ id: 2, username: "new" });
    authLib.loginRequest.mockResolvedValueOnce({ access: "acc2", refresh: "ref2" });
    authLib.getMeRequest.mockResolvedValueOnce({ id: 2, username: "new", role: "worker" });

    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("ready"));

    await act(async () => { screen.getByTestId("register-btn").click(); });
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("new"));
  });
});

describe("AuthContext — useAuth outside provider", () => {
  it("throws when used outside AuthProvider", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow();
    spy.mockRestore();
  });
});
