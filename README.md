# NeuralEyeTracker – Projekt Struktúra és Architektúra

Ez a dokumentum a **NeuralEyeTracker** szakdolgozati alkalmazás könyvtárszerkezetét, főbb moduljait és a projekt felépítését foglalja össze. A dokumentáció célja, hogy átlátható képet adjon a forráskódról, a kísérleti erőforrásokról, a webes felületről, valamint a telepítőcsomag készítéséhez tartozó könyvtárakról.

---

## 1. Tisztított könyvtárszerkezet

Az alábbi fa a projekt érdemi szerkezetét mutatja be (a generált fájlok, gyorsítótárak és harmadik féltől származó függőségek részletezése nélkül):

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
├── build-installer/         # [Generált] Ideiglenes build fájlok (pl. PyInstaller)
└── dist-installer/          # [Generált] Elkészült végleges telepítő/bináris kimenet
```

---

## 2. Modulok és könyvtárak részletes leírása

### Alkalmazásmag (Python)

| Könyvtár | Feladatkör |
| :--- | :--- |
| **`config/`** | Globális beállítások, paraméterek, elérési utak és futásidejű konfigurációk tárolása. |
| **`core/`** | A rendszer magja: szemkövetési algoritmusok, adatfeldolgozás, neurális/analitikai feldolgozó réteg és kísérletvezérlés. |
| **`ui/`** | Az asztali felhasználói felület komponensei, ablakok, nézetek és interakciós logika. |
| **`utils/`** | Újrafelhasználható segédmodulok (pl. fájlkezelés, naplózás, adatformázás, validáció). |
| **`resources/`** | A felülethez és a működéshez szükséges statikus erőforrások (képek, ikonok, sablonok). |

### Kísérleti adatbázis (`stimuli/`)

A könyvtár a szemkövetéses vizsgálatok során megjelenített ingereket csoportosítja affektív/érzelmi kategóriák mentén:
* **`neutral/`** – Kontrollként szolgáló, érzelmileg semleges ingerek.
* **`positive/`** – Pozitív érzelmi töltetű ingerek.
* **`negative/`** – Általános negatív érzelmi töltetű ingerek.
* **`threat/`** – Fenyegetettséget vagy veszélyt kiváltó ingerek.
* **`trauma/`** – Specifikus, traumával összefüggő kísérleti ingerek.

### Webes komponens (`web/`)

A könyvtár egy modern frontend alkalmazást foglal magában az alábbi technológiai stackkel (a `node_modules` alapján):
* **Keretrendszer:** React (`react`, `react-dom`)
* **Nyelv:** TypeScript (`typescript`)
* **Build eszköz:** Vite (`vite`, `@vitejs/plugin-react`, `esbuild`, `rollup`)
* **Főbb almappák:**
  * `web/src/` – A komponensek és a kliensoldali logika forráskódja.
  * `web/dist/` – A `vite build` parancs által előállított, optimalizált kimeneti fájlok (`assets/`).

### Csomagolás, telepítés és dokumentáció

| Könyvtár | Feladatkör |
| :--- | :--- |
| **`packaging/`** | A Python alkalmazás binárissá fordításához szükséges specifikációk és szkriptek. |
| **`installer/`** | A végfelhasználói telepítő (pl. Inno Setup / NSIS) konfigurációs fájljai. |
| **`Docs/`** | Rendszertervek, fejlesztői jegyzetek és a szakdolgozathoz tartozó mellékletek. |

---

## 3. Generált könyvtárak és verziókezelési javaslat

Az alábbi könyvtárak automatikusan jönnek létre fejlesztés vagy build során, ezért **nem javasolt** őket verziókezelőbe (Git) feltölteni:

* `**/__pycache__/` – Python bájtkód gyorsítótár.
* `.venv/` – Helyi Python virtuális környezet (helyette `requirements.txt` vagy `pyproject.toml` ajánlott).
* `web/node_modules/` – Telepített npm csomagok (helyette `package.json` és `package-lock.json` kezelendő).
* `web/dist/` – Fordított frontend kimenet.
* `build-installer/` és `dist-installer/` – Telepítő készítésekor keletkező átmeneti és végleges build termékek.

### Ajánlott `.gitignore` részlet

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