# Návod: spouštění Brno Rain Botu přes cron-job.org

Tenhle návod je psaný tak, aby ho zvládl kdokoliv — žádné programování není potřeba,
stačí klikat podle kroků a jednou zkopírovat pár řádků textu.

## Proč vůbec cron-job.org?

Bot už umí běžet sám na GitHub Actions (každých 15 minut). Háček je v tom, že
GitHubu ten časovač „plave" — spuštění se běžně opozdí o 5 až 30 minut, někdy se
běh i úplně přeskočí. U upozornění na déšť, které má dorazit **15–30 minut předem**,
je to docela zásadní.

cron-job.org je bezplatná služba, která umí v **přesný čas** „ťuknout" na GitHub a
říct mu: *teď spusť bota*. GitHub pak workflow rozběhne okamžitě. Výsledek:
upozornění chodí spolehlivě a včas.

Princip v jedné větě: **cron-job.org každých 15 minut pošle GitHubu příkaz
„spusť workflow rain-check.yml".**

---

## Co budeme potřebovat

1. Účet na [cron-job.org](https://cron-job.org) (zdarma).
2. Jeden přístupový token z GitHubu (vyrobíme ho za chvíli, je to na 2 minuty).

---

## Krok 1 — Vyrobit přístupový token na GitHubu

Token je jako „heslo na jedno použití pro robota". Díky němu smí cron-job.org
spouštět náš workflow, ale nic jiného v repozitáři nemůže.

1. Přihlas se na GitHub a otevři:
   **https://github.com/settings/personal-access-tokens/new**
   (Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token)
2. Vyplň:
   - **Token name**: `cron-job-org-brno-bot` (jen pro tvou orientaci)
   - **Expiration**: vyber třeba `1 year` (po roce ho bude potřeba obnovit — viz konec návodu)
   - **Repository access**: zvol **Only select repositories** a vyber repozitář
     `marvisiocz/brno-bot`.
3. Sjeď dolů na **Permissions → Repository permissions**, najdi položku
   **Actions** a přepni ji na **Read and write**.
   (Tohle je jediné oprávnění, které token potřebuje.)
4. Dole klikni na **Generate token**.
5. **Zkopíruj si vygenerovaný token** (začíná `github_pat_...`) a ulož si ho někam
   stranou. GitHub ti ho ukáže jen jednou — až okno zavřeš, už se k němu nedostaneš.

---

## Krok 2 — Založit úlohu na cron-job.org

1. Zaregistruj se / přihlas na **https://cron-job.org** a klikni na
   **Create cronjob** (Vytvořit úlohu).

2. Do políčka **Title** napiš třeba `Brno Rain Bot`.

3. Do políčka **URL (address)** vlož přesně tohle:

   ```
   https://api.github.com/repos/marvisiocz/brno-bot/actions/workflows/rain-check.yml/dispatches
   ```

4. **Schedule (časový plán)** — nastav spouštění **každých 15 minut**:
   - Zvol režim, kde se dá vybrat „every 15 minutes", nebo
   - v rozšířeném (cron) zápisu nastav minuty na `0,15,30,45` a vše ostatní na „every".

5. Teď to důležité — rozklikni **Advanced (pokročilé nastavení)**. Tam nastavíme,
   *jak* se má na GitHub zavolat.

### 2a) Metoda požadavku

Přepni **Request method** na **POST**.

### 2b) Hlavičky (Headers)

Přidej tyto **tři hlavičky** (tlačítko „Add header" / „+"):

| Název (Key)             | Hodnota (Value)                      |
| ----------------------- | ------------------------------------ |
| `Accept`                | `application/vnd.github+json`        |
| `Authorization`         | `Bearer ZDE_VLOZ_SVUJ_TOKEN`         |
| `X-GitHub-Api-Version`  | `2022-11-28`                         |

> ⚠️ U hlavičky `Authorization` musí zůstat slovo **`Bearer`**, mezera, a **až za ní**
> vložíš token z Kroku 1. Tedy například:
> `Bearer github_pat_11ABCDEFG...`

### 2c) Tělo zprávy (Request body)

Najdi pole **Request body** (někdy schované pod „POST data" / „Body") a vlož do něj
přesně tento jeden řádek:

```json
{"ref":"main"}
```

To GitHubu říká: *spusť workflow nad hlavní větví `main`*. (Pokud bys bota měl na
jiné větvi, vyměníš `main` za její název — ale standardně je to `main`.)

6. Ulož úlohu tlačítkem **Create** / **Save**.

---

## Krok 3 — Vyzkoušet, že to funguje

1. Na cron-job.org u vytvořené úlohy klikni na **Run now** / **Test run**
   (spustit hned).
2. Pokud je vše správně, cron-job.org ukáže odpověď s kódem **`204`**
   (případně „success" / zelený puntík). **204 znamená úspěch** — GitHub příkaz
   přijal. Žádný text v odpovědi nečekej, 204 je „přijato, nic dalšího neposílám".
3. Na GitHubu otevři repozitář → záložka **Actions** → měl by tam naskočit nový
   běh „Brno rain alert" spuštěný přes API.

Když uvidíš nový běh v Actions, je hotovo. 🎉

### Když to nezabere — rychlá kontrola chyb

cron-job.org ti u odpovědi ukáže návratový kód. Co znamenají:

- **204** → vše OK.
- **401** (Unauthorized) → špatný nebo prošlý token, nebo chybí slovo `Bearer`
  před tokenem v hlavičce `Authorization`.
- **403** (Forbidden) → token nemá oprávnění **Actions: Read and write**, nebo
  nemá přístup k tomuhle repozitáři.
- **404** (Not Found) → překlep v URL (jméno repozitáře nebo souboru
  `rain-check.yml`), nebo token nevidí daný repozitář.
- **422** (Unprocessable) → špatné tělo zprávy. Musí být přesně `{"ref":"main"}`
  a větev `main` musí existovat.

---

## Co s původním časovačem na GitHubu?

V souboru `.github/workflows/rain-check.yml` je řádek:

```yaml
  schedule:
    - cron: "7,22,37,52 * * * *"
```

Máš dvě možnosti:

- **Nechat ho být** (doporučeno na začátek): GitHub i cron-job.org pak budou bota
  spouštět souběžně. Nevadí to — bot má v sobě pojistku proti duplicitním
  upozorněním (posílá max. jedno na začátku každého deště). Bereš cron-job.org jako
  přesnější „budík" a GitHub cron jako záchranu, kdyby cron-job.org vypadl.
- **Vypnout GitHub časovač**, ať běží jen přesný cron-job.org: smaž ty dva řádky
  `schedule:` a `- cron: ...`. Řádek `workflow_dispatch:` musí zůstat — díky němu
  jde workflow spouštět právě přes API z cron-job.org.

---

## Údržba (jednou za čas)

- **Token má platnost** (nastavili jsme 1 rok). Až vyprší, cron-job.org začne
  vracet `401`. Stačí v Kroku 1 vyrobit nový token a v Kroku 2 ho přepsat
  v hlavičce `Authorization`.
- **Token je tajný.** Nikam ho nelep veřejně, nedávej do commitů. Žije jen
  v nastavení cron-job.org.
