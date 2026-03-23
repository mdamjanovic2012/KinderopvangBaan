/**
 * Tests for src/components/Nav.jsx
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Nav from "@/components/Nav";

// Mock the entire AuthContext module
jest.mock("@/context/AuthContext", () => ({
  useAuth: jest.fn(),
}));

// Mock next/link
jest.mock("next/link", () => {
  return function MockLink({ href, children, className }) {
    return <a href={href} className={className}>{children}</a>;
  };
});

import { useAuth } from "@/context/AuthContext";

function setupMock(overrides = {}) {
  useAuth.mockReturnValue({
    user: null,
    loading: false,
    logout: jest.fn(),
    ...overrides,
  });
}

describe("Nav — unauthenticated", () => {
  beforeEach(() => setupMock());

  it("renders the brand name", () => {
    render(<Nav />);
    expect(screen.getByText("KinderopvangBaan")).toBeInTheDocument();
  });

  it("shows Inloggen link when not authenticated", () => {
    render(<Nav />);
    expect(screen.getByText("Inloggen")).toBeInTheDocument();
  });

  it("shows Registreren link when not authenticated", () => {
    render(<Nav />);
    expect(screen.getByText("Registreren")).toBeInTheDocument();
  });

  it("shows Kaart navigation link", () => {
    render(<Nav />);
    expect(screen.getByText("Kaart")).toBeInTheDocument();
  });

  it("shows Vacatures navigation link", () => {
    render(<Nav />);
    expect(screen.getByText("Vacatures")).toBeInTheDocument();
  });

  it("shows Medewerkers navigation link", () => {
    render(<Nav />);
    expect(screen.getByText("Medewerkers")).toBeInTheDocument();
  });
});

describe("Nav — loading", () => {
  it("does not show auth buttons while loading", () => {
    setupMock({ loading: true });
    render(<Nav />);
    expect(screen.queryByText("Inloggen")).not.toBeInTheDocument();
    expect(screen.queryByText("Registreren")).not.toBeInTheDocument();
  });
});

describe("Nav — authenticated", () => {
  const mockLogout = jest.fn();

  beforeEach(() => {
    setupMock({ user: { username: "janedoe", role: "worker" }, logout: mockLogout });
  });

  it("shows username initial in avatar", () => {
    render(<Nav />);
    expect(screen.getByText("J")).toBeInTheDocument();
  });

  it("shows username", () => {
    render(<Nav />);
    expect(screen.getByText("janedoe")).toBeInTheDocument();
  });

  it("shows role label", () => {
    render(<Nav />);
    expect(screen.getByText("Medewerker")).toBeInTheDocument();
  });

  it("shows Uitloggen button", () => {
    render(<Nav />);
    expect(screen.getByText("Uitloggen")).toBeInTheDocument();
  });

  it("does not show Inloggen when authenticated", () => {
    render(<Nav />);
    expect(screen.queryByText("Inloggen")).not.toBeInTheDocument();
  });

  it("calls logout when Uitloggen is clicked", () => {
    const logout = jest.fn();
    setupMock({ user: { username: "janedoe", role: "worker" }, logout });
    render(<Nav />);
    fireEvent.click(screen.getByText("Uitloggen"));
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it("shows correct role label for institution", () => {
    setupMock({ user: { username: "bso1", role: "institution" }, logout: jest.fn() });
    render(<Nav />);
    expect(screen.getByText("Instelling")).toBeInTheDocument();
  });

  it("shows correct role label for parent", () => {
    setupMock({ user: { username: "mom1", role: "parent" }, logout: jest.fn() });
    render(<Nav />);
    expect(screen.getByText("Ouder")).toBeInTheDocument();
  });
});
