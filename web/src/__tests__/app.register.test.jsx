/**
 * Tests for src/app/register/page.js
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RegisterPage from "@/app/register/page";

jest.mock("@/context/AuthContext", () => ({
  useAuth: jest.fn(),
}));

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
}));

jest.mock("next/link", () => {
  return function MockLink({ href, children, className }) {
    return <a href={href} className={className}>{children}</a>;
  };
});

import { useAuth } from "@/context/AuthContext";

function setupAuth(overrides = {}) {
  useAuth.mockReturnValue({
    register: jest.fn(),
    ...overrides,
  });
}

describe("RegisterPage — stap 1: Wie ben jij?", () => {
  beforeEach(() => {
    setupAuth();
    render(<RegisterPage />);
  });

  it("renders gratis account heading", () => {
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/gratis/i);
  });

  it("renders 'Wie ben jij?' subtitle", () => {
    expect(screen.getByText("Wie ben jij?")).toBeInTheDocument();
  });

  it("renders professional option", () => {
    expect(
      screen.getByText("Ik ben een kinderopvang professional")
    ).toBeInTheDocument();
  });

  it("renders organisatie option", () => {
    expect(
      screen.getByText("Ik ben een kinderopvangorganisatie")
    ).toBeInTheDocument();
  });

  it("does NOT render ouder option", () => {
    expect(screen.queryByText("Ouder")).not.toBeInTheDocument();
    expect(screen.queryByText("Ik zoek kinderopvang voor mijn kind")).not.toBeInTheDocument();
  });

  it("renders exactly 2 role options", () => {
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
  });

  it("renders worker desc text", () => {
    expect(
      screen.getByText("Ik zoek een baan in de kinderopvang")
    ).toBeInTheDocument();
  });

  it("renders institution desc text", () => {
    expect(
      screen.getByText("Ik wil gratis vacatures plaatsen en professionals vinden")
    ).toBeInTheDocument();
  });

  it("renders Inloggen link", () => {
    expect(screen.getByRole("link", { name: "Inloggen" })).toHaveAttribute(
      "href",
      "/login"
    );
  });
});

describe("RegisterPage — stap 2: gegevens formulier", () => {
  beforeEach(() => {
    setupAuth();
    render(<RegisterPage />);
    fireEvent.click(screen.getByText("Ik ben een kinderopvang professional"));
  });

  it("shows gegevens form after role selection", () => {
    expect(screen.getByText("Jouw gegevens")).toBeInTheDocument();
  });

  it("shows selected role in header", () => {
    expect(
      screen.getByText("Ik ben een kinderopvang professional")
    ).toBeInTheDocument();
  });

  it("shows Terug button", () => {
    expect(screen.getByText(/Terug/i)).toBeInTheDocument();
  });

  it("clicking Terug returns to step 1", () => {
    fireEvent.click(screen.getByText(/Terug/i));
    expect(screen.getByText("Wie ben jij?")).toBeInTheDocument();
  });

  it("shows username input", () => {
    expect(screen.getByPlaceholderText("jouwgebruikersnaam")).toBeInTheDocument();
  });

  it("shows email input", () => {
    expect(screen.getByPlaceholderText("jouw@email.nl")).toBeInTheDocument();
  });

  it("shows Account aanmaken button", () => {
    expect(
      screen.getByRole("button", { name: "Account aanmaken" })
    ).toBeInTheDocument();
  });

  it("shows password mismatch error", async () => {
    fireEvent.change(screen.getByPlaceholderText("jouwgebruikersnaam"), {
      target: { value: "testuser" },
    });
    fireEvent.change(screen.getByPlaceholderText("jouw@email.nl"), {
      target: { value: "test@test.nl" },
    });
    fireEvent.change(screen.getByPlaceholderText("Minimaal 8 tekens"), {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "different123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Account aanmaken" }));
    await waitFor(() => {
      expect(
        screen.getByText("Wachtwoorden komen niet overeen.")
      ).toBeInTheDocument();
    });
  });

  it("calls register with correct role on submit", async () => {
    const mockRegister = jest.fn().mockResolvedValue({});
    setupAuth({ register: mockRegister });
    render(<RegisterPage />);
    fireEvent.click(screen.getAllByText("Ik ben een kinderopvang professional")[0]);

    fireEvent.change(screen.getAllByPlaceholderText("jouwgebruikersnaam")[0], {
      target: { value: "newworker" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("jouw@email.nl")[0], {
      target: { value: "new@test.nl" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("Minimaal 8 tekens")[0], {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("••••••••")[0], {
      target: { value: "password123" },
    });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Account aanmaken" })[0]
    );
    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        expect.objectContaining({ role: "worker" })
      );
    });
  });
});
