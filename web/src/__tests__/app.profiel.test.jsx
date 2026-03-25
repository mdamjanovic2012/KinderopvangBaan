/**
 * Tests voor /dashboard/profiel — bevoegdheid, PDOK auto-fill, uren, per direct
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import WorkerProfilePage from "@/app/dashboard/profiel/page";

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

const DEFAULT_PROFILE = {
  bio: "Test bio",
  work_radius_km: 15,
  has_diploma: true,
  bevoegdheid: ["bso"],
  cao_function: "pm3",
  contract_types: ["fulltime"],
  years_experience: 3,
  hours_per_week: 32,
  immediate_available: false,
  availability: { days: ["ma", "di"], from: "2026-05-01" },
  postcode: "1234AB",
  house_number: "10",
  street: "Teststraat",
  city: "Amsterdam",
};

function setupFetch(profile = DEFAULT_PROFILE) {
  global.fetch = jest.fn((url) => {
    if (url.includes("pdok.nl")) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            response: {
              docs: [{ straatnaam: "Hoofdstraat", woonplaatsnaam: "Utrecht" }],
            },
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(profile),
    });
  });
}

async function setup(profileOverrides = {}) {
  useAuth.mockReturnValue({
    user: { username: "testworker", role: "worker" },
    loading: false,
  });
  setupFetch({ ...DEFAULT_PROFILE, ...profileOverrides });

  await act(async () => {
    render(<WorkerProfilePage />);
  });
  await waitFor(() => expect(screen.queryByText("Laden...")).not.toBeInTheDocument());
}

beforeEach(() => jest.clearAllMocks());

describe("Profiel pagina — basisweergave", () => {
  test("toont de profielpagina heading", async () => {
    await setup();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Mijn profiel");
  });

  test("laadt bio uit API", async () => {
    await setup();
    expect(screen.getByPlaceholderText(/Vertel iets/)).toHaveValue("Test bio");
  });

  test("toont jaren werkervaring", async () => {
    await setup();
    expect(screen.getByPlaceholderText("0")).toHaveValue(3);
  });
});

describe("Profiel pagina — CAO functie", () => {
  test("toont functie dropdown", async () => {
    await setup();
    expect(screen.getByText("Mijn functie")).toBeInTheDocument();
  });

  test("laadt cao_function uit API", async () => {
    await setup({ cao_function: "pm3" });
    const select = screen.getByDisplayValue("Pedagogisch medewerker (niveau 3)");
    expect(select).toBeInTheDocument();
  });

  test("verstuurt cao_function in PATCH body", async () => {
    await setup({ cao_function: "bso_begeleider" });
    const submitBtn = screen.getByRole("button", { name: "Opslaan" });
    await act(async () => {
      fireEvent.click(submitBtn);
    });
    await waitFor(() => {
      const patchCall = global.fetch.mock.calls.find((c) => c[1]?.method === "PATCH");
      const body = JSON.parse(patchCall[1].body);
      expect(body.cao_function).toBe("bso_begeleider");
    });
  });
});

describe("Profiel pagina — bevoegdheid", () => {
  test("toont bevoegdheid checkboxes", async () => {
    await setup();
    expect(screen.getByText("BSO")).toBeInTheDocument();
    expect(screen.getByText("Dagopvang")).toBeInTheDocument();
    expect(screen.getByText("Peuterspeelzaal")).toBeInTheDocument();
  });

  test("toont diploma checkbox", async () => {
    await setup();
    expect(screen.getByText("Diploma behaald")).toBeInTheDocument();
  });

  test("BSO staat aangevinkt als het in bevoegdheid zit", async () => {
    await setup({ bevoegdheid: ["bso"] });
    const checkboxDiv = screen.getByText("BSO").closest("label").querySelector("div");
    expect(checkboxDiv.className).toContain("bg-blue-700");
  });

  test("Dagopvang staat niet aangevinkt als het niet in bevoegdheid zit", async () => {
    await setup({ bevoegdheid: ["bso"] });
    const checkboxDiv = screen.getByText("Dagopvang").closest("label").querySelector("div");
    expect(checkboxDiv.className).not.toContain("bg-blue-700");
  });
});

describe("Profiel pagina — locatie en PDOK", () => {
  test("toont postcode en huisnummer velden", async () => {
    await setup();
    expect(screen.getByPlaceholderText("1234AB")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("12A")).toBeInTheDocument();
  });

  test("laadt bestaande postcode en straat", async () => {
    await setup();
    expect(screen.getByDisplayValue("1234AB")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Teststraat")).toBeInTheDocument();
  });

  test("PDOK auto-fill bij onBlur op postcode", async () => {
    await setup({ postcode: "5678CD", house_number: "5", street: "", city: "" });
    const postcodeInput = screen.getByPlaceholderText("1234AB");
    await act(async () => {
      fireEvent.blur(postcodeInput);
    });
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("pdok.nl")
      )
    );
    await waitFor(() => {
      expect(screen.getByDisplayValue("Hoofdstraat")).toBeInTheDocument();
    });
  });
});

describe("Profiel pagina — beschikbaarheid", () => {
  test("toont per direct toggle", async () => {
    await setup();
    expect(screen.getByText("Per direct beschikbaar")).toBeInTheDocument();
  });

  test("beschikbaar-vanaf veld zichtbaar als niet per direct", async () => {
    await setup({ immediate_available: false });
    expect(screen.getByText("Beschikbaar vanaf")).toBeInTheDocument();
  });

  test("beschikbaar-vanaf veld verborgen als per direct beschikbaar", async () => {
    await setup({ immediate_available: true });
    expect(screen.queryByText("Beschikbaar vanaf")).not.toBeInTheDocument();
  });

  test("toont uren per week veld", async () => {
    await setup();
    expect(screen.getByPlaceholderText("32")).toBeInTheDocument();
    expect(screen.getByDisplayValue("32")).toBeInTheDocument();
  });
});

describe("Profiel pagina — dienstverband", () => {
  test("toont contract opties zonder ZZP", async () => {
    await setup();
    expect(screen.getByText("Fulltime")).toBeInTheDocument();
    expect(screen.getByText("Parttime")).toBeInTheDocument();
    expect(screen.getByText("Flex / oproep")).toBeInTheDocument();
    expect(screen.queryByText(/ZZP/i)).not.toBeInTheDocument();
  });
});

describe("Profiel pagina — opslaan", () => {
  test("verstuurt PATCH bij opslaan", async () => {
    await setup();
    const submitBtn = screen.getByRole("button", { name: "Opslaan" });
    await act(async () => {
      fireEvent.click(submitBtn);
    });
    await waitFor(() => {
      const patchCall = global.fetch.mock.calls.find(
        (c) => c[0].includes("worker-profile") && c[1]?.method === "PATCH"
      );
      expect(patchCall).toBeTruthy();
    });
  });

  test("verstuurt bevoegdheid in PATCH body", async () => {
    await setup({ bevoegdheid: ["dagopvang", "peuterspeelzaal"] });
    const submitBtn = screen.getByRole("button", { name: "Opslaan" });
    await act(async () => {
      fireEvent.click(submitBtn);
    });
    await waitFor(() => {
      const patchCall = global.fetch.mock.calls.find(
        (c) => c[1]?.method === "PATCH"
      );
      const body = JSON.parse(patchCall[1].body);
      expect(body.bevoegdheid).toEqual(["dagopvang", "peuterspeelzaal"]);
    });
  });

  test("verstuurt immediate_available in PATCH body", async () => {
    await setup({ immediate_available: true });
    const submitBtn = screen.getByRole("button", { name: "Opslaan" });
    await act(async () => {
      fireEvent.click(submitBtn);
    });
    await waitFor(() => {
      const patchCall = global.fetch.mock.calls.find(
        (c) => c[1]?.method === "PATCH"
      );
      const body = JSON.parse(patchCall[1].body);
      expect(body.immediate_available).toBe(true);
    });
  });
});
