/**
 * Tests for src/app/page.js (Homepage)
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import Home from "@/app/page";

jest.mock("@/components/Nav", () => function MockNav() { return <nav data-testid="nav" />; });

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

  it("renders the subtitel", () => {
    expect(
      screen.getByText("Alleen voor loondienst binnen de kinderopvang cao")
    ).toBeInTheDocument();
  });

  it("renders the gratis extra regel", () => {
    expect(
      screen.getByText("Volledig gratis voor werkzoekenden en werkgevers")
    ).toBeInTheDocument();
  });

  it("renders Zoek vacatures CTA linking to /jobs", () => {
    const link = screen.getByRole("link", { name: "Zoek vacatures" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/jobs");
  });

  it("renders Plaats gratis vacature CTA", () => {
    const link = screen.getByRole("link", { name: "Plaats gratis vacature" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/dashboard/vacatures/nieuw");
  });

  it("does NOT render old Bekijk de kaart CTA", () => {
    expect(screen.queryByText("Bekijk de kaart")).not.toBeInTheDocument();
  });

  it("does NOT render old Alle vacatures CTA", () => {
    expect(screen.queryByText("Alle vacatures")).not.toBeInTheDocument();
  });
});

describe("Homepage — Gratis badge", () => {
  beforeEach(() => render(<Home />));

  it("renders gratis voor werkzoekenden badge item", () => {
    expect(
      screen.getByText("Volledig gratis en ruim aanbod voor werkzoekenden")
    ).toBeInTheDocument();
  });

  it("renders gratis vacatures plaatsen badge item", () => {
    expect(
      screen.getByText("Vacatures plaatsen is volledig gratis")
    ).toBeInTheDocument();
  });

  it("renders live in minuten badge item", () => {
    expect(
      screen.getByText(
        "Heb je al vacatures? Wij zetten ze voor je live in minuten."
      )
    ).toBeInTheDocument();
  });
});

describe("Homepage — Waarom wij bestaan", () => {
  beforeEach(() => render(<Home />));

  it("renders the mission heading", () => {
    expect(
      screen.getByText(
        "Wij lossen het personeelstekort in de kinderopvang op"
      )
    ).toBeInTheDocument();
  });

  it("renders the Waarom wij bestaan CTA button", () => {
    const link = screen.getByRole("link", { name: "Waarom wij bestaan" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/over-ons");
  });

  it("renders personeelstekort mission bullet", () => {
    expect(
      screen.getByText(/personeelstekort.*wij helpen dat op te lossen/i)
    ).toBeInTheDocument();
  });

  it("renders gratis stat block", () => {
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("Gratis voor iedereen")).toBeInTheDocument();
  });
});

describe("Homepage — Werkgevers sectie", () => {
  beforeEach(() => render(<Home />));

  it("renders werkgevers heading", () => {
    expect(
      screen.getByText("Bereik de juiste professionals — gratis")
    ).toBeInTheDocument();
  });

  it("renders Gratis vacature plaatsen CTA linking to /register", () => {
    const link = screen.getByRole("link", { name: "Gratis vacature plaatsen" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/register");
  });

  it("renders werkenbij-pagina mention", () => {
    expect(
      screen.getAllByText(/werkenbij-pagina/i).length
    ).toBeGreaterThan(0);
  });

  it("renders Neem contact op CTA", () => {
    const link = screen.getByRole("link", { name: "Neem contact op" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/contact");
  });
});

describe("Homepage — Nav", () => {
  it("renders the Nav component", () => {
    render(<Home />);
    expect(screen.getByTestId("nav")).toBeInTheDocument();
  });
});
