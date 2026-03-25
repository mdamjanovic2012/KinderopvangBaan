/**
 * Tests voor /instellingen/[id] — moeder-dochter structuur
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { api } from "@/lib/api";
import Page from "@/app/instellingen/[id]/page";

jest.mock("@/lib/api");
jest.mock("@/components/Nav", () => () => <nav data-testid="nav" />);
jest.mock("next/dynamic", () => () => () => <div data-testid="map" />);
jest.mock("next/link", () =>
  function MockLink({ href, children, ...props }) {
    return <a href={href} {...props}>{children}</a>;
  }
);

const BASE_INST = {
  id: 1,
  name: "Test BSO Noord",
  institution_type: "bso",
  lrk_verified: true,
  is_claimed: false,
  avg_rating: null,
  street: "Teststraat",
  house_number: "1",
  postcode: "1000AA",
  city: "Amsterdam",
  province: "",
  description: "",
  capacity: null,
  available_spots: null,
  lrk_number: "12345",
  phone: "",
  email: "",
  website: "",
  opening_hours: null,
  parent: null,
  parent_info: null,
  locations: [],
  location: { type: "Point", coordinates: [4.9, 52.3] },
};

async function renderPage(institutionOverrides = {}) {
  const institution = { ...BASE_INST, ...institutionOverrides };
  api.institution.mockResolvedValue(institution);
  api.reviews.mockResolvedValue([]);
  api.jobs.mockResolvedValue({ results: [] });

  render(<Page params={{ id: "1" }} />);
  await waitFor(() => expect(screen.queryByText("Laden...")).not.toBeInTheDocument());
  return institution;
}

describe("Instellingen detail — moeder-dochter", () => {
  beforeEach(() => jest.clearAllMocks());

  test("geen organisatiestructuur sectie als standalone", async () => {
    await renderPage();
    expect(screen.queryByText(/Onderdeel van/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Andere locaties/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Locaties/i)).not.toBeInTheDocument();
  });

  test("toont 'Onderdeel van' link als institution een parent heeft", async () => {
    await renderPage({
      parent: 99,
      parent_info: {
        id: 99,
        name: "Gro-up Moeder",
        naam_houder: "Gro-up",
        city: "Amsterdam",
        institution_type: "bso",
      },
      locations: [],
    });
    expect(screen.getByText(/Onderdeel van/i)).toBeInTheDocument();
    const link = screen.getByText("Gro-up");
    expect(link.closest("a")).toHaveAttribute("href", "/instellingen/99");
  });

  test("toont naam_houder in parent link als aanwezig", async () => {
    await renderPage({
      parent: 10,
      parent_info: {
        id: 10,
        name: "Gro-up BSO Hoofd",
        naam_houder: "Gro-up Kinderopvang",
        city: "Amsterdam",
        institution_type: "bso",
      },
      locations: [],
    });
    expect(screen.getByText("Gro-up Kinderopvang")).toBeInTheDocument();
  });

  test("toont 'Andere locaties' als institution een parent heeft met siblings", async () => {
    await renderPage({
      parent: 99,
      parent_info: { id: 99, name: "Moeder", naam_houder: "Moeder", city: "Amsterdam", institution_type: "bso" },
      locations: [
        { id: 2, name: "BSO Zuid", city: "Amsterdam", institution_type: "bso", active_job_count: 0 },
      ],
    });
    expect(screen.getByText(/Andere locaties/i)).toBeInTheDocument();
    expect(screen.getByText("BSO Zuid")).toBeInTheDocument();
  });

  test("toont 'Locaties' als institution een moeder is", async () => {
    await renderPage({
      parent: null,
      parent_info: null,
      locations: [
        { id: 3, name: "Locatie Noord", city: "Amsterdam", institution_type: "bso", active_job_count: 2 },
        { id: 4, name: "Locatie Zuid", city: "Rotterdam", institution_type: "kdv", active_job_count: 0 },
      ],
    });
    expect(screen.getByText(/^Locaties/i)).toBeInTheDocument();
    expect(screen.getByText("Locatie Noord")).toBeInTheDocument();
    expect(screen.getByText("Locatie Zuid")).toBeInTheDocument();
  });

  test("toont vacature badge als locatie vacatures heeft", async () => {
    await renderPage({
      parent: null,
      parent_info: null,
      locations: [
        { id: 5, name: "BSO Met Jobs", city: "Utrecht", institution_type: "bso", active_job_count: 3 },
      ],
    });
    expect(screen.getByText(/3 vacatures/i)).toBeInTheDocument();
  });

  test("geen vacature badge als geen vacatures", async () => {
    await renderPage({
      parent: null,
      parent_info: null,
      locations: [
        { id: 6, name: "BSO Geen Jobs", city: "Leiden", institution_type: "bso", active_job_count: 0 },
      ],
    });
    // Alleen de badge met aantallen mag niet aanwezig zijn (niet de CTA-knop)
    expect(screen.queryByText(/\d+ vacatures?/i)).not.toBeInTheDocument();
  });

  test("locatie link verwijst naar juiste pagina", async () => {
    await renderPage({
      parent: null,
      parent_info: null,
      locations: [
        { id: 7, name: "Locatie X", city: "Haarlem", institution_type: "bso", active_job_count: 1 },
      ],
    });
    const link = screen.getByText("Locatie X").closest("a");
    expect(link).toHaveAttribute("href", "/instellingen/7");
  });

  test("toont naam van instelling als h1 op pagina", async () => {
    await renderPage({ name: "Mijn Kinderdagverblijf" });
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Mijn Kinderdagverblijf");
  });
});
