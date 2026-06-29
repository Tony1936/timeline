const groups = [
  { label: "King of England", colour: "#f87171" },
  { label: "Queen of England", colour: "#fb923c" },
  { label: "Archbishop of Canterbury", colour: "#60a5fa" },
  { label: "Pope", colour: "#c084fc" },
  { label: "King of France", colour: "#34d399" },
  { label: "Welsh Events", colour: "#facc15" },
  { label: "Major Events", colour: "#f87171" },
  { label: "Irish Events", colour: "#4ade80" },
];

const events = [
  { group: 0, label: "William I", left: "12%", width: "14%" },
  { group: 1, label: "Birth of Matilda of Flanders", left: "8%", width: "18%" },
  { group: 1, label: "Death of Eleanor of Aquitane", left: "50%", width: "20%" },
  { group: 2, label: "Langfranc appointed", left: "18%", width: "13%" },
  { group: 2, label: "Birth of Thomas Becket", left: "34%", width: "14%" },
  { group: 3, label: "Paschal II", left: "28%", width: "10%" },
  { group: 4, label: "Philip I Birth", left: "20%", width: "12%" },
  { group: 5, label: "Dynastic Disarray", left: "22%", width: "13%" },
  { group: 7, label: "Battle of Clontarf", left: "6%", width: "14%" },
];

export function SansSerif() {
  return (
    <div style={{
      width: "100%", height: "100vh",
      background: "#111827",
      backgroundImage: "radial-gradient(ellipse at 50% 0%, rgba(30,58,100,0.5) 0%, transparent 60%)",
      display: "flex", flexDirection: "column",
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      color: "#e5e7eb",
    }}>
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" />

      <div style={{
        padding: "14px 40px 16px",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.25) 100%)",
        borderBottom: "1px solid rgba(250,180,50,0.3)",
      }}>
        <div style={{ fontSize: "0.7rem", color: "#fbbf24", marginBottom: 4, letterSpacing: "0.02em", fontWeight: 500 }}>← Home</div>
        <h1 style={{ margin: 0, fontSize: "1.55rem", letterSpacing: "0.05em", color: "#fde68a", fontWeight: 700, textTransform: "uppercase" }}>
          Middle Ages
        </h1>
        <p style={{ margin: "4px 0 0", fontSize: "0.82rem", color: "rgba(209,213,219,0.85)", fontWeight: 400 }}>
          The period from collapse of Rome in 500AD to renaissance in 1500AD.
        </p>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ width: 230, background: "rgba(0,0,0,0.55)", borderRight: "1px solid rgba(250,180,50,0.2)", flexShrink: 0 }}>
          {groups.map((g, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center",
              height: 60, padding: "0 12px",
              borderBottom: "1px solid rgba(255,255,255,0.06)",
              borderLeft: `4px solid ${g.colour}`,
            }}>
              <span style={{
                fontSize: "0.8rem", fontWeight: 600,
                color: "#fde68a", letterSpacing: "0.01em",
              }}>{g.label}</span>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 28,
            background: "rgba(0,0,0,0.7)", borderBottom: "2px solid rgba(250,180,50,0.4)",
            display: "flex", alignItems: "center", paddingLeft: 8, gap: "11%",
          }}>
            {["1000","1050","1100","1150","1200","1250","1300","1350","1400"].map(y => (
              <span key={y} style={{ fontSize: "0.72rem", color: "#fbbf24", fontWeight: 600, letterSpacing: "0.02em" }}>{y}</span>
            ))}
          </div>

          {groups.map((_, gi) => (
            <div key={gi} style={{
              position: "absolute", left: 0, right: 0,
              top: 28 + gi * 60, height: 60,
              borderBottom: "1px solid rgba(255,255,255,0.06)",
            }}>
              {events.filter(e => e.group === gi).map((ev, ei) => (
                <div key={ei} style={{
                  position: "absolute",
                  left: ev.left, width: ev.width,
                  top: "50%", transform: "translateY(-50%)",
                  height: 32,
                  background: "rgba(30,41,59,0.95)",
                  border: "1px solid rgba(250,180,50,0.45)",
                  borderRadius: 5,
                  display: "flex", alignItems: "center", paddingLeft: 8,
                  fontSize: "0.73rem", fontWeight: 500, color: "#f1f5f9",
                  boxShadow: "0 1px 6px rgba(0,0,0,0.5)",
                  whiteSpace: "nowrap", overflow: "hidden",
                  letterSpacing: "0.01em",
                }}>
                  {ev.label}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div style={{
        padding: "6px 16px", fontSize: "0.65rem",
        color: "rgba(250,180,50,0.5)", textAlign: "center",
        letterSpacing: "0.05em", fontWeight: 500,
        borderTop: "1px solid rgba(250,180,50,0.15)",
      }}>
        SANS-SERIF — mixed-case labels · Inter font · slate base
      </div>
    </div>
  );
}
