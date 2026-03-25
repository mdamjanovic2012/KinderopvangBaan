# Changelog

Alle noemenswaardige wijzigingen per productie-deploy worden hier bijgehouden.
Format: `## [datum] — korte omschrijving`

---

## [2026-03-25] — CAO functielijst + werkzoekende profiel uitgebreid

### Toegevoegd
- **CAO kinderopvang functielijst** (12 functies) als vaste keuzelijst
  - Vervangt oude `job_type` keuzes (bso/kdv/nanny/gastouder)
  - Functies: Assistent PM, PM3, PM4, Senior PM, Groepsbegeleider BSO, Coördinator BSO, Teamleider, Locatiemanager, Pedagogisch beleidsmedewerker, Gastouder, Nanny, Stagiair
- `Job.job_type` keuzes vervangen door CAO functielijst
- `WorkerProfile.cao_function` veld — medewerker kiest eigen CAO-functie
- API endpoint `GET /api/jobs/choices/` — geeft CAO functies + contract types terug
- Frontend `web/src/lib/caoFunctions.js` — gedeelde constanten
- ZZP verwijderd uit `Job.contract_type` keuzes

### Gewijzigd
- `web/src/app/jobs/page.js`: filterselectie gebruikt volledige CAO lijst
- `web/src/app/jobs/[id]/page.js`: toont CAO-functielabel via `getCaoLabel()`
- `web/src/app/dashboard/vacatures/nieuw/page.js`: functiedropdown via CAO lijst
- `web/src/app/dashboard/profiel/page.js`: CAO-functie select toegevoegd

---

## [2026-03-25] — Werkzoekende profiel uitgebreid + naam in dashboard

### Toegevoegd
- **Voornaam + achternaam** bij registratie (optionele velden)
- **Dashboard groet** gebruikt voornaam als ingevuld (anders gebruikersnaam)
- **Naam rij** in accountgegevens op dashboard
- **Werkzoekende profiel** uitgebreid:
  - Bevoegdheid checkboxes: Dagopvang, BSO, Peuterspeelzaal (vervangt VOG)
  - Postcode + huisnummer met **PDOK auto-fill** (straat + woonplaats)
  - Uren per week (gewenst)
  - Per direct beschikbaar toggle
  - Dienstverband checkboxes: Fulltime, Parttime, Flex/oproep (ZZP verwijderd)
- Nieuwe velden op `WorkerProfile`: `bevoegdheid`, `hours_per_week`, `immediate_available`, `postcode`, `house_number`, `street`
- PublicWorkerSerializer: exposeert `bevoegdheid`, `immediate_available`, `hours_per_week`; adresvelden worden niet gedeeld

### Gewijzigd
- `UserSerializer` en `RegisterSerializer`: `first_name` + `last_name` toegevoegd

---

## [2026-03-25] — Owner dashboard + database backup

### Toegevoegd
- **Owner dashboard** op `/pivce-za-zivce/` met django-unfold (moderne UI)
  - Organisaties: zoeken, filteren, LRK-verificatie, acties (activeer/deactiveer)
  - Vacatures: overzicht per organisatie, premium markering, bulk acties
  - Sollicitaties: status beheer (bekeken / geaccepteerd / afgewezen)
  - Gebruikers: rol-filter, activeer/deactiveer
  - Werkzoekende profielen: compliance overzicht (VOG, diploma, beschikbaarheid)
- **Database backup** naar Azure Blob Storage (`kbdbbackups`)
  - Management command `backup_db` met pg_dump
  - Maximaal 1x per 7 dagen, behoudt laatste 30 backups
  - Flags: `--force`, `--dry-run`
  - Automatisch bij elke deploy via `startup.sh`

### Gewijzigd
- Admin URL gewijzigd van `/admin/` naar `/pivce-za-zivce/`
- `requirements.txt`: `django-unfold==0.43.0`, `azure-storage-blob==12.24.1` toegevoegd

---

## [2026-03-24] — LRK enrichment + moeder-dochter structuur

### Toegevoegd
- **LRK enrichment** management command (`enrich_from_lrk`)
  - Download publieke CSV van landelijkregisterkinderopvang.nl
  - Verrijkt: `naam_houder`, `kvk_nummer_houder`, `gemeente`, `lrk_url`
  - Vult leeg contact (telefoon, e-mail, website) aan
  - Maximaal 1x per 30 dagen (timestamp in `/home/.lrk_last_run`)
  - Flags: `--force`, `--dry-run`, `--csv`
- **Moeder-dochter structuur** (`parent` FK op Institution)
  - Koppeling via `kvk_nummer_houder` groepering
  - Parent gekozen op naamovereenkomst of laagste pk
- Nieuwe velden op `Institution`: `lrk_url`, `kvk_nummer_houder`, `naam_houder`, `gemeente`, `parent`

### Gewijzigd
- `startup.sh`: LRK enrichment non-blocking na migraties
- Registratie: ouder-optie verwijderd, rol validatie backend

---

## [2026-03-23] — Homepage redesign + registratie flow

### Gewijzigd
- **Homepage** volledig herschreven:
  - Nieuwe titel / subtitel / extra regel
  - CTA knoppen: "Zoek vacatures" + "Plaats gratis vacature"
  - Kaart verwijderd
  - Gratis badge sectie (3 items)
  - "Waarom wij bestaan" missie sectie
  - Werkgevers sectie met voordelen en CTA
- **Registratie**: ouder-rol verwijderd, kop aangepast naar "gratis account aanmaken"

---

## [2026-03-22] — Mobiele UI + CI/CD

### Toegevoegd
- Hamburger navigatie voor mobiel
- Responsive grids (kaart toggle op mobiel)
- Azure DevOps CI/CD pipeline (5 stages, self-hosted MacLocal agent)
- Async deploy stap met smoke test

---

## [2026-03-21] — Initiële productie deploy

### Toegevoegd
- Django GeoDjango backend (PostgreSQL/PostGIS) op Azure App Service
- Next.js 16 frontend op Azure App Service
- JWT authenticatie (djangorestframework-simplejwt)
- Institutions model met LRK registratie
- Jobs model met vacatures en sollicitaties
- Kaart view met MapLibre GL
