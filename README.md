<div align="center">

  <img src="docs/logo.png" alt="NeuralEyeTracker Logo" width="420" />

  <p><sub>Adaptive oculometric &amp; pupillometric research application — Project structure &amp; architecture overview</sub></p>

  <p>
    <img src="https://img.shields.io/badge/Core-Python_3-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Web_UI-React_%2B_TypeScript-61DAFB?logo=react&logoColor=white" alt="React + TypeScript" />
    <img src="https://img.shields.io/badge/Bundler-Vite-646CFF?logo=vite&logoColor=white" alt="Vite" />
    <img src="https://img.shields.io/badge/Stimuli-5_Affective_Sets-ff8c00" alt="Stimuli" />
    <img src="https://img.shields.io/badge/Target-Thesis_Build-lightgrey" alt="Thesis" />
  </p>

  <p><strong>A NeuralEyeTracker szakdolgozati alkalmazás könyvtárszerkezete, moduljai és build-környezete.</strong></p>

</div>

---

## Projektáttekintés

A **NeuralEyeTracker** a szakdolgozathoz kapcsolódó kísérleti és analitikai szoftverrendszer, amely egy asztali Python alkalmazásmagot, egy kísérleti vizuális inger-állományt (`stimuli/`), egy modern React + TypeScript + Vite webes modult (`web/`), valamint a telepítőcsomag előállításához tartozó könyvtárakat (`packaging/`, `installer/`, `dist-installer/`) foglalja magában.

A projekt felépítésének célja, hogy egyértelműen elkülönítse a konfigurációt, az üzleti/feldolgozási logikát, a felhasználói felületeket, a vizuális ingerkategóriákat és a build-termékeket, miközben áttekinthető alapot biztosít a kísérletek futtatásához és a csomagoláshoz.

## Tisztított könyvtárszerkezet

Az alábbi fa a projekt érdemi szerkezetét mutatja be (a generált fájlok, bájtkód-gyorsítótárak és harmadik féltől származó függőségek részletezése nélkül):

```text
NeuralEyeTracker/
├── config/                  # Alkalmazás- és környezeti konfigurációk
├── core/                    # Központi üzleti logika, szemkövetési és feldolgozási motor
├── ui/                      # Asztali felhasználói felület (Python GUI modulok)
├── utils/                   # Segédfüggvények, közös eszközök és kiegészítő modulok
├── resources/               # Statikus erőforrások (ikonok, stílusok, médiafájlok)
├── stimuli/                 # Kísérleti vizuális ingerek érzelmi kategóriák szerint
│   ├── neutral/             # Semleges ingerek
│   ├── positive/            # Pozitív ingerek
│   ├── negative/            # Negatív ingerek
│   ├── threat/              # Fenyegető ingerek
│   └── trauma/              # Traumához kapcsolódó ingerek
├── web/                     # Webes modul (React + TypeScript + Vite)
│   ├── src/                 # Webes alkalmazás forráskódja
│   └── dist/                # Buildelt, éles webes kimenet (assets/)
├── packaging/               # Csomagolási konfigurációk és build szkriptek
├── installer/               # Telepítőcsomag (installer) forrásai és beállításai
├── Docs/                    # Projekt- és szakdolgozati dokumentációk
├── .venv/                   # [Generált] Python virtuális környezet
├── build-installer/         # [Generált] Ideiglenes build fájlok
└── dist-installer/          # [Generált] Elkészült végleges telepítő/bináris kimenet
```

## Modulok és könyvtárak

### Alkalmazásmag (Python)

| Könyvtár | Feladatkör |
|---|---|
| **`config/`** | Globális beállítások, paraméterek, elérési utak és futásidejű konfigurációk tárolása |
| **`core/`** | A rendszer magja: szemkövetési és adatfeldolgozási logika, modell- és kísérletvezérlés |
| **`ui/`** | Az asztali felhasználói felület moduljai, ablakai és interakciós elemei |
| **`utils/`** | Újrafelhasználható segédfüggvények (fájlkezelés, formázás, naplózás, validáció) |
| **`resources/`** | A működéshez és a felülethez szükséges statikus erőforrások |

### Kísérleti adatbázis (`stimuli/`)

A könyvtár a szemkövetéses vizsgálatok során megjelenített ingereket csoportosítja affektív kategóriák mentén:

- **`neutral/`** – Kontrollként szolgáló, érzelmileg semleges ingerek
- **`positive/`** – Pozitív érzelmi töltetű ingerek
- **`negative/`** – Általános negatív érzelmi töltetű ingerek
- **`threat/`** – Fenyegetettséget vagy veszélyt kiváltó ingerek
- **`trauma/`** – Specifikus, traumával összefüggő kísérleti ingerek

### Webes komponens (`web/`)

A webes modul modern frontend stackre épül (`react`, `react-dom`, `typescript`, `vite`, `@vitejs/plugin-react`, `esbuild`, `rollup`):

- **`web/src/`** – A komponensek és a kliensoldali logika forráskódja
- **`web/dist/`** – A `vite build` parancs által előállított, optimalizált kimeneti állományok (`assets/`)

### Csomagolás, telepítés és dokumentáció

| Könyvtár | Feladatkör |
|---|---|
| **`packaging/`** | A Python alkalmazás binárissá csomagolásához szükséges specifikációk és szkriptek |
| **`installer/`** | A végfelhasználói telepítőcsomag forrásai és konfigurációs beállításai |
| **`Docs/`** | Rendszerleírások, fejlesztői jegyzetek és a szakdolgozathoz tartozó dokumentáció |

## Generált könyvtárak és verziókezelés

Az alábbi könyvtárak automatikusan keletkeznek a fejlesztés vagy a buildelés során, ezért **nem javasolt** őket verziókezelőbe (Git) feltölteni:

- `**/__pycache__/` – Python bájtkód gyorsítótár
- `.venv/` – Helyi Python virtuális környezet (helyette `requirements.txt` vagy `pyproject.toml` ajánlott)
- `web/node_modules/` – Telepített npm csomagok (helyette `package.json` és `package-lock.json` kezelendő)
- `web/dist/` – Fordított frontend kimenet
- `build-installer/` és `dist-installer/` – Telepítő készítésekor keletkező átmeneti és végleges build termékek

Ajánlott `.gitignore` beállítások:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/

# Build és telepítő kimenetek
build-installer/
dist-installer/

# Web / Node.js
web/node_modules/
web/dist/
web/.vite/
```

---

<div align="center">

**NeuralEyeTracker**

*Kísérleti okulometriai architektúra · Projektstruktúra-áttekintés*

</div>