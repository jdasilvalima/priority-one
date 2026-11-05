export const TIERS = {
  Critical: { color: "#E8590C", subtitle: "Act today" },
  High: { color: "#F0B000", subtitle: "Act this week" },
  Medium: { color: "#3CC25A", subtitle: "This month" },
  Low: { color: "#CDD5E0", subtitle: "Routine" },
};

export const EFFORT_STYLES = {
  Quick: { color: "#00602F", background: "#E9F9EF" },
  Medium: { color: "#0B4F9C", background: "#E8F1FC" },
  Heavy: { color: "#8A3B00", background: "#FFF1E0" },
};

export function TierPill({ tier }) {
  return (
    <span className="ds-pill" style={{ background: TIERS[tier].color }}>
      {tier}
    </span>
  );
}
