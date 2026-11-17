import { useCallback, useEffect, useMemo, useState } from "react";

type TrackerState = {
  status: string;
  error: string | null;
  running: boolean;
  tracking: boolean;
  model_trained: boolean;
  camera_index: number;
  fps: number;
  confidence: number | null;
  cx: number | null;
  cy: number | null;
  pupil_size: number | null;
  radius_px: number | null;
  neural_az: number | null;
  neural_el: number | null;
  raw_data: Record<string, unknown> | null;
};

const EMPTY_STATE: TrackerState = {
  status: "offline", error: null, running: false, tracking: false,
  model_trained: false, camera_index: 0, fps: 0, confidence: null,
  cx: null, cy: null, pupil_size: null, radius_px: null,
  neural_az: null, neural_el: null, raw_data: null,
};

const shown = (number: number | null, digits = 2, unit = "") =>
  number === null ? "—" : `${number.toFixed(digits)}${unit}`;

export default function App() {
  const [tracker, setTracker] = useState<TrackerState>(EMPTY_STATE);
  const [camera, setCamera] = useState("0");
  const [frame, setFrame] = useState(Date.now());
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/state", { cache: "no-store" });
      if (!response.ok) throw new Error("A tracker állapota nem érhető el.");
      setTracker(await response.json() as TrackerState);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "A Python API nem érhető el.");
    }
  }, []);

  const start = useCallback(async () => {
    try {
      const response = await fetch(`/api/start?camera=${encodeURIComponent(camera)}`, { method: "POST" });
      const result = await response.json() as { ok: boolean; error?: string };
      if (!result.ok) setError(result.error ?? "A tracker nem indítható.");
      await refresh();
    } catch {
      setError("A Python tracker API nem érhető el.");
    }
  }, [camera, refresh]);

  const stop = useCallback(async () => {
    await fetch("/api/stop", { method: "POST" });
    await refresh();
  }, [refresh]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 500);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!tracker.running) return;
    const timer = window.setInterval(() => setFrame(Date.now()), 160);
    return () => window.clearInterval(timer);
  }, [tracker.running]);

  const statusText = useMemo(() => {
    if (tracker.status === "tracking") return "Detektor: Stabil";
    if (tracker.status === "waiting") return "Detektor: Keresés";
    if (tracker.status === "error") return "Detektor: Hiba";
    return "Detektor: Készenlét";
  }, [tracker.status]);

  const activeError = error ?? tracker.error;

  return (
    <main className="clinical-app">
      <header className="app-header">
        <div className="top-navigation">
          <div className="brand-group">
            <div className="brand-icon" aria-hidden="true">◉</div>
            <strong>Neural Eye Tracker</strong>
            <span className="clinical-badge">Klinikai Munkaterület</span>
            <nav className="main-nav">
              <button>Fájl</button><button>Páciens</button><button>Szerkesztés</button>
              <button className="active">Klinikai</button><button>Eszközök</button><button>Súgó</button>
            </nav>
          </div>
          <div className="header-actions">
            <span className={`telemetry-pill ${tracker.tracking ? "good" : ""}`}>
              <i className="status-dot" />{statusText} ({shown(tracker.confidence, 2)})
            </span>
            <span className="telemetry-pill mono">{shown(tracker.fps, 0)} FPS</span>
            <label className="camera-pill">Forrás:
              <input value={camera} onChange={(event) => setCamera(event.target.value)} aria-label="Kamera index" />
            </label>
            {tracker.running
              ? <button className="action-button outline" onClick={() => void stop()}>Leállítás</button>
              : <button className="action-button primary" onClick={() => void start()}>Rögzítés</button>}
          </div>
        </div>
        <div className="quickbar">
          <div className="quick-search"><span>⌕</span><input placeholder="Gyorskeresés: Páciens, vizsgálat vagy riport keresése..." /></div>
          <div className="quick-meta"><span>Forrás: <b>Kamera {camera}</b></span><span>Mód: <b>Élő követés</b></span><b className="ready-badge">{tracker.running ? "Élő" : "Kész"}</b></div>
        </div>
      </header>

      <section className="patient-banner">
        <div className="patient-main">
          <div className="patient-avatar">—</div>
          <div><h1>Nincs kijelölt páciens</h1><p><i className="status-dot" /> Munkamenet előkészítve <span>•</span> Neurokognitív szemkövetés</p></div>
          <div className="patient-fields"><div><small>Születési dátum / Kor</small><b>—</b></div><div><small>Nem</small><b>—</b></div><div><small>Vizsgálat</small><b className="blue">Élő mérés</b></div></div>
        </div>
        <div className="alert-cards">
          <div className="alert-card rose"><small>Allergiák / Mellékhatások</small><b>—</b></div>
          <div className="alert-card amber"><small>Figyelmeztetések</small><b>{tracker.model_trained ? "Nincs" : "Kalibráció szükséges"}</b></div>
        </div>
        <div className="tabs"><button className="selected">▦ &nbsp; Összegzés</button><button>⌁ &nbsp; Aktuális kezelés</button><button>◷ &nbsp; Kórtörténet</button><button>▤ &nbsp; Leletek</button><button>▱ &nbsp; Dokumentumok</button><button>▣ &nbsp; Számlázás</button></div>
      </section>

      <section className="work-area">
        <aside className="left-column">
          <Card title="Aktuális vizit" badge="Aktív">
            <div className="select-grid"><Field label="Szerepkör" value="Kutató" /><Field label="Vizit típusa" value="Élő mérés" /></div>
            <textarea placeholder="Panaszok, státusz, diagnózis és terápia..." />
            <div className="quick-buttons"><button>Előzmény</button><button>Vizsgálat</button><button>Jegyzet</button></div>
          </Card>
          <Card title="Élő biometria" right={<span className="sync-label"><i className="status-dot" /> Szinkron</span>}>
            <div className="biometric-grid">
              <Bio label="Konfidencia" value={shown(tracker.confidence, 2)} progress={tracker.confidence} />
              <Bio label="Mintavétel" value={shown(tracker.fps, 0, " Hz")} />
              <Bio label="Átmérő" value={shown(tracker.radius_px === null ? null : tracker.radius_px * 2, 1, " px")} blue />
              <Bio label="Sugár" value={shown(tracker.radius_px, 1, " px")} />
              <Bio label="Centrum X" value={shown(tracker.cx, 0, " px")} />
              <Bio label="Centrum Y" value={shown(tracker.cy, 0, " px")} />
            </div>
          </Card>
          <Card title="Munkamenet" badge={tracker.running ? "Fut" : "Kész"}>
            <div className="session-rows"><DataRow label="Forrás" value={`Kamera ${tracker.camera_index}`} /><DataRow label="Állapot" value={tracker.status} /></div>
          </Card>
        </aside>

        <section className="center-column">
          <Card title="Vizsgálati munkaterület" subtitle="Valós idejű kamerakép, pupillometria és vizsgálati jegyzet" className="investigation-card">
            <div className="work-buttons"><button>◉ &nbsp; Élő hőtérkép</button><button className="primary-small">▤ &nbsp; Riport</button></div>
            <div className="report-strip"><span>▧ &nbsp; Élő tracker adatfolyam</span><span>{tracker.running ? "Kamera csatlakoztatva" : "Nincs elindított mérés"}</span></div>
            <div className="camera-view">
              {tracker.running ? <img src={`/api/frame.jpg?ts=${frame}`} alt="Élő kamera és detektor kép" /> : <div className="camera-placeholder"><b>Élő kamerakép</b><span>A mérés indításához kattints a Rögzítés gombra.</span></div>}
            </div>
            <div className="interpretation"><h3><span>5</span> Szakmai értelmezés</h3><p>Az értelmezés csak kalibrált, érvényes neurális modell esetén jelenik meg.</p><div className="notice">A rendszer nem generál klinikai következtetést hiányos vagy kalibrálatlan mérésből.</div></div>
          </Card>
        </section>

        <aside className="right-column">
          <Card title="Valós idejű állapot" right={<span className="live-tag">LIVE</span>}>
            <div className="state-box"><DataRow label="Detektálás" value={tracker.tracking ? "Érvényes" : "Várakozás"} /><DataRow label="Centrum X" value={shown(tracker.cx, 2, " px")} /><DataRow label="Centrum Y" value={shown(tracker.cy, 2, " px")} /><DataRow label="Konfidencia" value={shown(tracker.confidence, 3)} /></div>
            <div className="gaze-box"><span>Tekintetirány</span><b>{shown(tracker.neural_az, 1, "°")} / {shown(tracker.neural_el, 1, "°")}</b><small>Azimut / Eleváció</small></div>
          </Card>
          <Card title="Rendszer állapota">
            <Diagnostic label="Python tracker API" ok={!activeError} detail={activeError ?? "Elérhető"} />
            <Diagnostic label="Kameraforrás" ok={tracker.running} detail={`Kamera ${tracker.camera_index}`} />
            <Diagnostic label="Pupilladetektor" ok={tracker.tracking} detail={tracker.tracking ? "Stabil" : "Várakozás"} />
            <Diagnostic label="Neurális modell" ok={tracker.model_trained} detail={tracker.model_trained ? "Aktív" : "Kalibráció szükséges"} />
          </Card>
          <Card title="Mért nyers adatok" className="raw-card"><pre>{tracker.raw_data ? JSON.stringify(tracker.raw_data, null, 2) : "Nincs mérési adat."}</pre></Card>
        </aside>
      </section>
    </main>
  );
}

function Card({ title, badge, right, subtitle, className = "", children }: { title: string; badge?: string; right?: React.ReactNode; subtitle?: string; className?: string; children: React.ReactNode }) {
  return <div className={`card ${className}`}><div className="card-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{right ?? (badge && <span className="card-badge">{badge}</span>)}</div>{children}</div>;
}
function Field({ label, value }: { label: string; value: string }) { return <label className="field"><small>{label}</small><select value={value} onChange={() => undefined}><option>{value}</option></select></label>; }
function Bio({ label, value, progress, blue = false }: { label: string; value: string; progress?: number | null; blue?: boolean }) { return <div className="bio"><small>{label}</small><b className={blue ? "blue" : ""}>{value}</b>{progress !== undefined && <span className="progress"><i style={{ width: `${Math.max(0, Math.min(100, (progress ?? 0) * 100))}%` }} /></span>}</div>; }
function DataRow({ label, value }: { label: string; value: string }) { return <div className="data-row"><span>{label}</span><b className="mono">{value}</b></div>; }
function Diagnostic({ label, ok, detail }: { label: string; ok: boolean; detail: string }) { return <div className="diagnostic"><i className={`status-dot ${ok ? "on" : ""}`} /><div><b>{label}</b><small>{detail}</small></div></div>; }
