/**
 * Tests voor /dashboard — voornaam groet en accountgegevens
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/dashboard/page";

jest.mock("@/components/Nav", () => () => <nav data-testid="nav" />);
jest.mock("next/link", () =>
  function MockLink({ href, children }) {
    return <a href={href}>{children}</a>;
  }
);
jest.mock("next/navigation", () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
}));
jest.mock("@/context/AuthContext", () => ({
  useAuth: jest.fn(),
}));

const { useAuth } = require("@/context/AuthContext");

function setup(userOverrides = {}) {
  const user = {
    username: "testuser",
    email: "test@test.nl",
    role: "worker",
    first_name: "",
    last_name: "",
    ...userOverrides,
  };
  useAuth.mockReturnValue({ user, loading: false });
  render(<DashboardPage />);
  return user;
}

describe("Dashboard — groet met voornaam", () => {
  beforeEach(() => jest.clearAllMocks());

  test("toont voornaam als first_name is ingevuld", () => {
    setup({ first_name: "Miki", last_name: "Janssen" });
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Welkom terug, Miki!");
  });

  test("valt terug op gebruikersnaam als geen first_name", () => {
    setup({ username: "testuser123", first_name: "" });
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Welkom terug, testuser123!");
  });

  test("toont volledige naam in accountgegevens als beide ingevuld", () => {
    setup({ first_name: "Anna", last_name: "de Vries" });
    expect(screen.getByText("Anna de Vries")).toBeInTheDocument();
  });

  test("toont geen naam rij als first_name en last_name leeg zijn", () => {
    setup({ first_name: "", last_name: "" });
    expect(screen.queryByText("Naam")).not.toBeInTheDocument();
  });

  test("toont alleen voornaam in naam rij als achternaam ontbreekt", () => {
    setup({ first_name: "Sofie", last_name: "" });
    expect(screen.getByText("Sofie")).toBeInTheDocument();
  });

  test("avatar initiaal gebruikt voornaam", () => {
    setup({ first_name: "Miki", username: "testuser" });
    const avatar = screen.getByText("M");
    expect(avatar).toBeInTheDocument();
  });

  test("avatar initiaal gebruikt gebruikersnaam als geen voornaam", () => {
    setup({ first_name: "", username: "anna123" });
    const avatar = screen.getByText("A");
    expect(avatar).toBeInTheDocument();
  });

  test("toont accounttype als Pedagogisch medewerker voor worker", () => {
    setup({ role: "worker" });
    expect(screen.getByText("Pedagogisch medewerker")).toBeInTheDocument();
  });

  test("toont accounttype als Instelling voor institution", () => {
    setup({ role: "institution" });
    expect(screen.getByText("Instelling")).toBeInTheDocument();
  });
});
