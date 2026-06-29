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

export function WarmBright() {
  return (
    <div style={{
      width: "100%", height: "100vh",
      background: "#0d1520",
      backgroundImage: "radial-gradient(ellipse at 50% 0%, rgba(20,50,100,0.6) 0%, transparent 65%)",
      display: "flex", flexDirection: "column",
      fontFamily: "'Cinzel', 'Palatino Linotype', serif",
      color: "#f0e6cc",
    }}>
      <div style={{
        padding: "14px 40px 16px",
        background: "linear-gradient(to bottom, rgba(5,12,28,0.9) 0%, rgba(5,12,28,0.4) 100%)",
        borderBottom: "1px solid rgba(240,180,60,0.35)",
      }}>
        <div style={{ fontSize: "0.7rem", color: "#f0c060", marginBottom: 4, letterSpacing: "0.08em" }}>← Home</div>
        <h1 style={{ margin: 0, fontSize: "1.6rem", letterSpacing: "0.12em", color: "#f5d070", textTransform: "uppercase", fontWeight: 700 }}>
          Middle Ages
        </h1>
        <p style={{ margin: "4px 0 0", fontSize: "0.78rem", color: "rgba(220,200,160,0.85)" }}>
          The period from collapse of Rome in 500AD to renaissance in 1500AD.
        </p>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ width: 220, background: "rgba(5,12,28,0.75)", borderRight: "1px solid rgba(240,180,60,0.25)", flexShrink: 0 }}>
          {groups.map((g, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center",
              height: 60, padding: "0 10px",
              borderBottom: "1px solid rgba(240,180,60,0.12)",
              borderLeft: `4px solid ${g.colour}`,
            }}>
              <span style={{
                fontSize: "0.78rem", fontWeight: 600,
                color: "#f0c060", letterSpacing: "0.04em",
              }}>{g.label}</span>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, position: "relative", overflow: "hidden", background: "rgba(13,21,32,0.4)" }}>
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 28,
            background: "rgba(5,12,28,0.9)", borderBottom: "2px solid rgba(240,180,60,0.45)",
            display: "flex", alignItems: "center", paddingLeft: 8, gap: "11%",
          }}>
            {["1000","1050","1100","1150","1200","1250","1300","1350","1400"].map(y => (
              <span key={y} style={{ fontSize: "0.72rem", color: "#e8b840", fontWeight: 600, letterSpacing: "0.03em" }}>{y}</span>
            ))}
          </div>

          {groups.map((_, gi) => (
            <div key={gi} style={{
              position: "absolute", left: 0, right: 0,
              top: 28 + gi * 60, height: 60,
              borderBottom: "1px solid rgba(240,180,60,0.1)",
            }}>
              {events.filter(e => e.group === gi).map((ev, ei) => (
                <div key={ei} style={{
                  position: "absolute",
                  left: ev.left, width: ev.width,
                  top: "50%", transform: "translateY(-50%)",
                  height: 32,
                  background: "rgba(20,35,60,0.92)",
                  border: "1px solid rgba(200,155,40,0.6)",
                  borderRadius: 4,
                  display: "flex", alignItems: "center", paddingLeft: 6,
                  fontSize: "0.72rem", color: "#f0e6cc",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.5), 0 0 0 0.5px rgba(240,180,60,0.15)",
                  whiteSpace: "nowrap", overflow: "hidden",
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
        color: "rgba(240,180,60,0.55)", textAlign: "center",
        letterSpacing: "0.08em",
        borderTop: "1px solid rgba(240,180,60,0.18)",
      }}>
        WARM & BRIGHT — mixed-case labels · navy base · crisper gold
      </div>
    </div>
  );
}
