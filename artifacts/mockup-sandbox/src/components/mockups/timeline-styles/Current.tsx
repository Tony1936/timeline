const groups = [
  { label: "King of England", colour: "#e05252" },
  { label: "Queen of England", colour: "#e0a052" },
  { label: "Archbishop of Canterbury", colour: "#52a0e0" },
  { label: "Pope", colour: "#9452e0" },
  { label: "King of France", colour: "#52e0a0" },
  { label: "Welsh Events", colour: "#e0e052" },
  { label: "Major Events", colour: "#e05252" },
  { label: "Irish Events", colour: "#52e052" },
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

export function Current() {
  return (
    <div style={{
      width: "100%", height: "100vh",
      background: "#0a0906",
      backgroundImage: "radial-gradient(ellipse at 60% 0%, rgba(60,40,10,0.5) 0%, transparent 60%)",
      display: "flex", flexDirection: "column",
      fontFamily: "'Cinzel', 'Palatino Linotype', serif",
      color: "#e8dcc8",
    }}>
      <div style={{
        padding: "14px 40px 16px",
        background: "linear-gradient(to bottom, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.3) 100%)",
        borderBottom: "1px solid rgba(160,130,60,0.3)",
      }}>
        <div style={{ fontSize: "0.7rem", color: "#c8a864", marginBottom: 4, letterSpacing: "0.08em" }}>← Home</div>
        <h1 style={{ margin: 0, fontSize: "1.6rem", letterSpacing: "0.12em", color: "#d4b86a", textTransform: "uppercase", fontWeight: 700 }}>
          Middle Ages
        </h1>
        <p style={{ margin: "4px 0 0", fontSize: "0.78rem", color: "rgba(200,185,155,0.75)" }}>
          The period from collapse of Rome in 500AD to renaissance in 1500AD.
        </p>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ width: 220, background: "rgba(8,5,2,0.7)", borderRight: "1px solid rgba(160,130,60,0.3)", flexShrink: 0 }}>
          {groups.map((g, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center",
              height: 60, padding: "0 10px",
              borderBottom: "1px solid rgba(160,130,60,0.1)",
              borderLeft: `4px solid ${g.colour}`,
            }}>
              <span style={{
                fontSize: "0.78rem", fontWeight: 600,
                color: "#c8a864", letterSpacing: "0.04em",
                textTransform: "uppercase",
              }}>{g.label}</span>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 28,
            background: "rgba(8,5,2,0.8)", borderBottom: "2px solid rgba(180,148,60,0.5)",
            display: "flex", alignItems: "center", paddingLeft: 8, gap: "11%",
          }}>
            {["1000","1050","1100","1150","1200","1250","1300","1350","1400"].map(y => (
              <span key={y} style={{ fontSize: "0.72rem", color: "#b8973a", fontWeight: 600, letterSpacing: "0.03em" }}>{y}</span>
            ))}
          </div>

          {groups.map((_, gi) => (
            <div key={gi} style={{
              position: "absolute", left: 0, right: 0,
              top: 28 + gi * 60, height: 60,
              borderBottom: "1px solid rgba(160,130,60,0.1)",
            }}>
              {events.filter(e => e.group === gi).map((ev, ei) => (
                <div key={ei} style={{
                  position: "absolute",
                  left: ev.left, width: ev.width,
                  top: "50%", transform: "translateY(-50%)",
                  height: 32,
                  background: "rgba(12,8,4,0.88)",
                  border: "1px solid rgba(150,118,45,0.55)",
                  borderRadius: 3,
                  display: "flex", alignItems: "center", paddingLeft: 6,
                  fontSize: "0.72rem", color: "#e8dcc8",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.6)",
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
        color: "rgba(160,130,60,0.5)", textAlign: "center",
        letterSpacing: "0.08em",
        borderTop: "1px solid rgba(160,130,60,0.15)",
      }}>
        CURRENT — uppercase labels · dark charcoal · serif
      </div>
    </div>
  );
}
