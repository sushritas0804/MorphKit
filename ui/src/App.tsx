import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type {
  ApplyResult,
  ParamSpec,
  Preview,
  ProjectScan,
  SegmentManifest,
} from "./types";

function defaultsFor(segment: SegmentManifest | null): Record<string, unknown> {
  if (!segment) return {};
  return Object.fromEntries(
    Object.entries(segment.params).map(([key, spec]) => [key, spec.default]),
  );
}

function ParamField({
  name,
  spec,
  value,
  onChange,
}: {
  name: string;
  spec: ParamSpec;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (spec.type === "boolean") {
    return (
      <label className="field checkbox">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span>{name}</span>
      </label>
    );
  }
  return (
    <label className="field">
      <span>{name}</span>
      <input
        type={spec.type === "integer" ? "number" : "text"}
        value={String(value ?? "")}
        min={spec.min}
        onChange={(event) =>
          onChange(
            spec.type === "integer" ? Number(event.target.value) : event.target.value,
          )
        }
      />
      {spec.description ? <small>{spec.description}</small> : null}
    </label>
  );
}

function DiffView({ diff }: { diff: string }) {
  if (!diff) return <p className="muted">No changes to show.</p>;
  return (
    <pre className="diff">
      {diff.split("\n").map((line, index) => {
        const kind = line.startsWith("+++") || line.startsWith("---")
          ? "meta"
          : line.startsWith("+")
            ? "add"
            : line.startsWith("-")
              ? "del"
              : line.startsWith("@@")
                ? "hunk"
                : "";
        return (
          <div key={index} className={`line ${kind}`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export default function App() {
  const [scan, setScan] = useState<ProjectScan | null>(null);
  const [segments, setSegments] = useState<SegmentManifest[]>([]);
  const [selected, setSelected] = useState<SegmentManifest | null>(null);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [preview, setPreview] = useState<Preview | null>(null);
  const [applied, setApplied] = useState<ApplyResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [targetIndex, setTargetIndex] = useState(0);

  const target = scan?.apps[targetIndex] ?? scan?.apps[0] ?? null;

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [nextScan, nextSegments] = await Promise.all([api.project(), api.segments()]);
      setScan(nextScan);
      setSegments(nextSegments);
      setSelected((current) => current ?? nextSegments[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    setParams(defaultsFor(selected));
    setPreview(null);
    setApplied(null);
  }, [selected]);

  useEffect(() => {
    setTargetIndex((current) =>
      Math.min(current, Math.max((scan?.apps.length ?? 1) - 1, 0)),
    );
    setPreview(null);
    setApplied(null);
  }, [scan]);

  const payload = useMemo(() => {
    if (!selected || !target) return null;
    return {
      segment: selected.name,
      params,
      app_file: target.file,
      app_var: target.app_var,
    };
  }, [selected, params, target]);

  const requestPreview = useCallback(async () => {
    if (!payload) return;
    setBusy(true);
    setError(null);
    setApplied(null);
    try {
      setPreview(await api.preview(payload));
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [payload]);

  const requestApply = useCallback(async () => {
    if (!payload) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.apply(payload);
      setApplied(result);
      setPreview(result);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [payload, refresh]);

  const onDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
    const name = event.dataTransfer.getData("application/x-morphkit-segment");
    const match = segments.find((segment) => segment.name === name);
    if (match) {
      setSelected(match);
      setPreview(null);
      setApplied(null);
    }
  };

  const alreadyApplied =
    selected && target
      ? (scan?.existing_segments[selected.name] ?? []).includes(target.file)
      : false;

  return (
    <div className="app">
      <header>
        <div>
          <h1>Morphkit</h1>
          <p className="muted">
            {scan ? scan.root : "loading..."} · {scan?.framework ?? "unknown"} ·{" "}
            {scan?.python_files.length ?? 0} Python files ·{" "}
            {scan?.has_tests ? "tests found" : "no tests"}
          </p>
        </div>
        <button className="ghost" onClick={() => void refresh()} disabled={busy}>
          Rescan
        </button>
      </header>

      {error ? <div className="banner error">{error}</div> : null}
      {scan?.warnings.map((warning) => (
        <div className="banner warn" key={warning}>
          {warning}
        </div>
      ))}

      <main>
        <section className="panel palette">
          <h2>Segments</h2>
          <p className="muted small">Drag a card onto the app, or click to select.</p>
          <div className="cards">
            {segments.map((segment) => (
              <article
                key={segment.name}
                draggable
                onDragStart={(event) => {
                  event.dataTransfer.setData("application/x-morphkit-segment", segment.name);
                  event.dataTransfer.effectAllowed = "copy";
                }}
                onClick={() => {
                  setSelected(segment);
                  setPreview(null);
                  setApplied(null);
                }}
                className={`card ${selected?.name === segment.name ? "active" : ""}`}
              >
                <div className="card-head">
                  <strong>{segment.display_name}</strong>
                  <span className="tag">{segment.stage}</span>
                </div>
                <p className="muted small">{segment.summary}</p>
                {(scan?.existing_segments[segment.name] ?? []).length > 0 ? (
                  <span className="tag done">present</span>
                ) : null}
              </article>
            ))}
            {segments.length === 0 ? <p className="muted">No segments found.</p> : null}
          </div>
        </section>

        <section className="panel canvas">
          <h2>Target</h2>
          {target ? (
            <div
              className={`dropzone ${dragOver ? "over" : ""}`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
            >
              <div className="target-file">
                {target.file}
                <span className="muted">:{target.line}</span>
              </div>
              <div className="muted small">
                app object: <code>{target.app_var}</code>
              </div>
              <div className="muted small">
                {dragOver
                  ? "Release to preview this segment."
                  : "Drop a segment here to see the exact diff."}
              </div>
              {scan && scan.apps.length > 1 ? (
                <label className="field target-picker">
                  <span>Target app object</span>
                  <select
                    value={targetIndex}
                    onChange={(event) => {
                      setTargetIndex(Number(event.target.value));
                      setPreview(null);
                      setApplied(null);
                    }}
                  >
                    {scan.apps.map((app, index) => (
                      <option key={`${app.file}:${app.line}:${app.app_var}`} value={index}>
                        {app.file}:{app.line} ({app.app_var})
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>
          ) : (
            <div className="banner warn">
              No <code>x = FastAPI(...)</code> found in this project.
            </div>
          )}

          {selected ? (
            <div className="params">
              <h3>{selected.display_name} params</h3>
              {Object.entries(selected.params).map(([name, spec]) => (
                <ParamField
                  key={name}
                  name={name}
                  spec={spec}
                  value={params[name]}
                  onChange={(value) =>
                    setParams((current) => ({ ...current, [name]: value }))
                  }
                />
              ))}
              <div className="actions">
                <button
                  className="ghost"
                  onClick={() => void requestPreview()}
                  disabled={busy || !payload}
                >
                  Preview change
                </button>
                <button
                  className="primary"
                  onClick={() => void requestApply()}
                  disabled={busy || !payload || alreadyApplied}
                >
                  {alreadyApplied ? "Already applied" : "Apply to project"}
                </button>
              </div>
              {alreadyApplied ? (
                <p className="muted small">
                  Marker found in {target?.file}. Remove it from the file to re-apply.
                </p>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className="panel preview">
          <h2>Preview</h2>
          {preview ? (
            <>
              <p className="muted small">
                {preview.file} · {preview.reason}
              </p>
              <DiffView diff={preview.diff} />
            </>
          ) : (
            <p className="muted">Drop a segment or press Preview change.</p>
          )}

          {applied?.verify ? (
            <div className="verify">
              <h3>Verification</h3>
              <p className="small">
                syntax: {applied.verify.syntax_ok ? "ok" : applied.verify.syntax_error}
              </p>
              <p className="small">
                tests:{" "}
                {applied.verify.tests.ran
                  ? applied.verify.tests.passed
                    ? "passed"
                    : "failed"
                  : applied.verify.tests.output_tail}
              </p>
              {applied.verify.tests.ran ? (
                <pre className="output">{applied.verify.tests.output_tail}</pre>
              ) : null}
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}
