/**
 * Tests for src/app/page.js (Homepage)
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import Home from "@/app/page";

jest.mock("@/components/Nav", () => function MockNav() { return <nav data-testid="nav" />; });
jest.mock("@/components/HomeDiplomaCheck", () => function MockDiplomaCheck() { return <div data-testid="diploma-check" />; });

jest.mock("next/link", () => {
  return function MockLink({ href, children, className }) {
    return <a href={href} className={className}>{children}</a>;
  };
});

describe("Homepage — Hero", () => {
  beforeEach(() => render(<Home />));

  it("renders the main title", () => {
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Vind vacatures zo dicht mogelijk bij huis"
    );
  });

  it("renders subtitle over loondienst en cao", () => {
    expect(
      screen.getByText("Alleen loondienst · kinderopvang cao · alle grote organisaties")
    ).toBeInTheDocument();
  });

  it("renders gratis voor werkzoekenden badge", () => {
    expect(
      screen.getByText("Volledig gratis voor werkzoekenden")
    ).toBeInTheDocument();
  });

  it("renders Bekijk alle vacatures CTA linking to /jobs", () => {
    const link = screen.getByRole("link", { name: "Bekijk alle vacatures" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/jobs");
  });

  it("renders In mijn buurt zoeken CTA linking to /map", () => {
    const link = screen.getByRole("link", { name: /In mijn buurt zoeken/ });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/map");
  });

  it("does NOT render old Plaats gratis vacature CTA", () => {
    expect(screen.queryByText("Plaats gratis vacature")).not.toBeInTheDocument();
  });

  it("does NOT render old werkgevers sectie", () => {
    expect(screen.queryByText(/Bereik de juiste professionals/i)).not.toBeInTheDocument();
  });
});

describe("Homepage — Voordelen badges", () => {
  beforeEach(() => render(<Home />));

  it("renders vacatures op afstand badge", () => {
    expect(
      screen.getByText(/Vacatures gesorteerd op afstand/i)
    ).toBeInTheDocument();
  });

  it("renders grote organisaties badge", () => {
    expect(
      screen.getByText(/Partou.*Kinderdam.*alle grote organisaties/i)
    ).toBeInTheDocument();
  });

  it("renders automatisch gesynchroniseerd badge", () => {
    expect(
      screen.getByText(/automatisch gesynchroniseerd/i)
    ).toBeInTheDocument();
  });
});

describe("Homepage — Hoe het werkt", () => {
  beforeEach(() => render(<Home />));

  it("renders Hoe het werkt heading", () => {
    expect(
      screen.getByText("In drie stappen naar jouw nieuwe baan")
    ).toBeInTheDocument();
  });

  it("renders stap 1 — Registreer gratis", () => {
    expect(screen.getByText("Registreer gratis")).toBeInTheDocument();
  });

  it("renders stap 2 — Zoek dichtbij huis", () => {
    expect(screen.getByText("Zoek dichtbij huis")).toBeInTheDocument();
  });

  it("renders stap 3 — Solliciteer direct", () => {
    expect(screen.getByText("Solliciteer direct")).toBeInTheDocument();
  });

  it("renders Gratis registreren CTA", () => {
    const link = screen.getByRole("link", { name: /Gratis registreren/i });
    expect(link).toHaveAttribute("href", "/register");
  });
});

describe("Homepage — Stats", () => {
  beforeEach(() => render(<Home />));

  it("renders 500+ actuele vacatures stat", () => {
    expect(screen.getByText("500+")).toBeInTheDocument();
    expect(screen.getByText("Actuele vacatures")).toBeInTheDocument();
  });

  it("renders 100% gratis stat", () => {
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("Gratis voor werkzoekenden")).toBeInTheDocument();
  });
});

describe("Homepage — Waarom wij bestaan", () => {
  beforeEach(() => render(<Home />));

  it("renders the mission heading", () => {
    expect(
      screen.getByText("Wij lossen het personeelstekort in de kinderopvang op")
    ).toBeInTheDocument();
  });

  it("renders Bekijk vacatures CTA", () => {
    const links = screen.getAllByRole("link", { name: /Bekijk vacatures/i });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0]).toHaveAttribute("href", "/jobs");
  });

  it("renders diplomacheck CTA", () => {
    const link = screen.getByRole("link", { name: /Doe de diplomacheck/i });
    expect(link).toHaveAttribute("href", "/diplomacheck");
  });
});

describe("Homepage — Nav", () => {
  it("renders the Nav component", () => {
    render(<Home />);
    expect(screen.getByTestId("nav")).toBeInTheDocument();
  });
});
