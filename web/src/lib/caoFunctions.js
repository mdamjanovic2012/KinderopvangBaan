/**
 * CAO kinderopvang — vaste functielijst.
 * Gesynchroniseerd met backend/jobs/constants.py :: CAO_FUNCTIONS
 */
export const CAO_FUNCTIONS = [
  { value: "assistent_pm",      label: "Assistent pedagogisch medewerker" },
  { value: "pm3",               label: "Pedagogisch medewerker (niveau 3)" },
  { value: "pm4",               label: "Pedagogisch medewerker (niveau 4)" },
  { value: "senior_pm",         label: "Senior pedagogisch medewerker" },
  { value: "bso_begeleider",    label: "Groepsbegeleider BSO" },
  { value: "coordinator_bso",   label: "Coördinator BSO" },
  { value: "teamleider",        label: "Teamleider kinderopvang" },
  { value: "locatiemanager",    label: "Locatiemanager / Vestigingsmanager" },
  { value: "beleidsmedewerker", label: "Pedagogisch beleidsmedewerker" },
  { value: "gastouder",         label: "Gastouder" },
  { value: "nanny",             label: "Nanny" },
  { value: "stagiair",          label: "Stagiair (BBL/BOL)" },
];

/** Geeft het label terug voor een gegeven waarde, of de waarde zelf als fallback. */
export function getCaoLabel(value) {
  return CAO_FUNCTIONS.find((f) => f.value === value)?.label ?? value;
}
