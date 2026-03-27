/**
 * Tests for src/components/HomeDiplomaCheck.jsx
 */
import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import HomeDiplomaCheck from "@/components/HomeDiplomaCheck";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
  },
}));

jest.mock("next/link", () => {
  return function MockLink({ href, children, className }) {
    return <a href={href} className={className}>{children}</a>;
  };
});

import { api } from "@/lib/api";

const MOCK_SUGGESTION = {
  id: 1,
  name: "Pedagogisch Werk",
  crebo: "25697",
  level: "mbo4",
  level_display: "MBO niveau 4",
};

const MOCK_DETAIL_DIRECT = {
  id: 1,
  name: "Pedagogisch Werk",
  level: "mbo4",
  level_display: "MBO niveau 4",
  kdv_status: "direct",
  bso_status: "direct",
  crebo: "25697",
};

const MOCK_DETAIL_BSO_ONLY = {
  id: 2,
  name: "Agogisch medewerker GGZ",
  level: "mbo4",
  level_display: "MBO niveau 4",
  kdv_status: "not_qualified",
  bso_status: "direct",
  crebo: "",
};

const MOCK_DETAIL_NOT_QUALIFIED = {
  id: 3,
  name: "Acteur",
  level: "mbo4",
  level_display: "MBO niveau 4",
  kdv_status: "not_qualified",
  bso_status: "not_qualified",
  crebo: "",
};

beforeEach(() => {
  api.get.mockReset();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe("HomeDiplomaCheck — basis rendering", () => {
  it("toont zoekbalk", () => {
    render(<HomeDiplomaCheck />);
    expect(screen.getByPlaceholderText(/Typ je diplomanaam/i)).toBeInTheDocument();
  });

  it("toont Diplomacheck badge", () => {
    render(<HomeDiplomaCheck />);
    expect(screen.getByText("Diplomacheck")).toBeInTheDocument();
  });

  it("toont header tekst", () => {
    render(<HomeDiplomaCheck />);
    expect(screen.getByText(/Ontdek waar jij kunt werken/i)).toBeInTheDocument();
  });

  it("toont link naar volledige diplomacheck", () => {
    render(<HomeDiplomaCheck />);
    expect(screen.getByText(/Ga naar de volledige diplomacheck/i)).toBeInTheDocument();
  });
});

describe("HomeDiplomaCheck — zoeken en suggesties", () => {
  it("doet geen API call bij minder dan 2 tekens", async () => {
    render(<HomeDiplomaCheck />);
    fireEvent.change(screen.getByPlaceholderText(/Typ je diplomanaam/i), {
      target: { value: "P" },
    });
    await act(async () => { jest.runAllTimers(); });
    expect(api.get).not.toHaveBeenCalled();
  });

  it("toont suggesties na zoeken", async () => {
    api.get.mockResolvedValueOnce([MOCK_SUGGESTION]);
    render(<HomeDiplomaCheck />);

    fireEvent.change(screen.getByPlaceholderText(/Typ je diplomanaam/i), {
      target: { value: "Ped" },
    });
    await act(async () => { jest.runAllTimers(); });

    await waitFor(() => {
      expect(screen.getByText("Pedagogisch Werk")).toBeInTheDocument();
    });
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("diplomacheck/search/?q=Ped"));
  });

  it("toont 'Geen diploma gevonden' als zoekresultaat leeg is", async () => {
    api.get.mockResolvedValueOnce([]);
    render(<HomeDiplomaCheck />);

    fireEvent.change(screen.getByPlaceholderText(/Typ je diplomanaam/i), {
      target: { value: "xyz" },
    });
    await act(async () => { jest.runAllTimers(); });

    await waitFor(() => {
      expect(screen.getByText(/Geen diploma gevonden/i)).toBeInTheDocument();
    });
  });
});

describe("HomeDiplomaCheck — resultaat na selectie", () => {
  async function searchAndSelect(detail) {
    api.get
      .mockResolvedValueOnce([MOCK_SUGGESTION])
      .mockResolvedValueOnce(detail);

    render(<HomeDiplomaCheck />);
    fireEvent.change(screen.getByPlaceholderText(/Typ je diplomanaam/i), {
      target: { value: "Ped" },
    });
    await act(async () => { jest.runAllTimers(); });
    await waitFor(() => screen.getByText("Pedagogisch Werk"));

    await act(async () => {
      fireEvent.click(screen.getByText("Pedagogisch Werk"));
    });
  }

  it("toont KDV en BSO kaarten na selectie", async () => {
    await searchAndSelect(MOCK_DETAIL_DIRECT);
    await waitFor(() => {
      expect(screen.getByText("KDV")).toBeInTheDocument();
      expect(screen.getByText("BSO")).toBeInTheDocument();
    });
  });

  it("toont CTA link naar registratie als bevoegd (kdv+bso direct)", async () => {
    await searchAndSelect(MOCK_DETAIL_DIRECT);
    await waitFor(() => {
      expect(screen.getByText(/Gratis profiel/i)).toBeInTheDocument();
    });
    const link = screen.getByText(/Gratis profiel/i).closest("a");
    expect(link.href).toContain("/register");
    expect(link.href).toContain("opvangtype=kdv");
  });

  it("registreer-URL bevat bso als alleen BSO direct bevoegd", async () => {
    await searchAndSelect(MOCK_DETAIL_BSO_ONLY);
    await waitFor(() => {
      const link = screen.getByText(/Gratis profiel/i).closest("a");
      expect(link.href).toContain("opvangtype=bso");
    });
  });

  it("toont 'niet direct' bericht als niet bevoegd", async () => {
    await searchAndSelect(MOCK_DETAIL_NOT_QUALIFIED);
    await waitFor(() => {
      expect(screen.getByText(/kwalificeert niet direct/i)).toBeInTheDocument();
    });
  });
});
