"""
CAO kinderopvang — vaste functielijst (Collectieve Arbeidsovereenkomst).
Wordt gebruikt in Job.job_type en WorkerProfile.cao_function.
"""

CAO_FUNCTIONS = [
    ("assistent_pm",      "Assistent pedagogisch medewerker"),
    ("pm3",               "Pedagogisch medewerker (niveau 3)"),
    ("pm4",               "Pedagogisch medewerker (niveau 4)"),
    ("senior_pm",         "Senior pedagogisch medewerker"),
    ("bso_begeleider",    "Groepsbegeleider BSO"),
    ("coordinator_bso",   "Coördinator BSO"),
    ("teamleider",        "Teamleider kinderopvang"),
    ("locatiemanager",    "Locatiemanager / Vestigingsmanager"),
    ("beleidsmedewerker", "Pedagogisch beleidsmedewerker"),
    ("gastouder",         "Gastouder"),
    ("nanny",             "Nanny"),
    ("stagiair",          "Stagiair (BBL/BOL)"),
]

CAO_FUNCTION_VALUES = [v for v, _ in CAO_FUNCTIONS]
