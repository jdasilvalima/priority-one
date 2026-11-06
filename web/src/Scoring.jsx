import { Calculation } from "./Card.jsx";
import { TIERS } from "./tiers.jsx";

export const SCORING_HASH = "#scoring";

export function ScoreStrip({ scoring, children }) {
  const points = scoring.tiers.map(({ tier, points: worth }) => `${tier} ${worth}`).join(" · ");
  const sizes = scoring.sizes.map(({ multiplier }) => `×${multiplier}`).join(" · ");
  return (
    <div className="ds-strip">
      <strong>Score =</strong>
      <span>
        signal points <em>{points}</em>
      </span>
      <b>×</b>
      <span>
        client size <em>{sizes}</em>
      </span>
      {children}
    </div>
  );
}

function TierIssues({ tier }) {
  return (
    <section>
      <div className="ds-gh">
        <span className="ds-badge" style={{ background: TIERS[tier.tier].color }}>
          {tier.tier}
        </span>
        <span>{TIERS[tier.tier].subtitle}</span>
      </div>
      <ul className="ds-rule-list">
        {tier.issues.map((issue) => (
          <li className="ds-rule" key={issue.label}>
            <div className="ds-rule-text">
              <strong>{issue.label}</strong>
              <p>{issue.when}</p>
              <p className="ds-data">Data: {issue.sources}</p>
            </div>
            <span className="ds-rule-points">+{tier.points} pts</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Scoring({ week }) {
  const { scoring } = week;
  const example = week.groups[0]?.cards[0];

  return (
    <>
      <section className="ds-hero">
        <div className="ds-in">
          <p className="ds-week">How scoring works</p>
          <h1>What each issue is worth.</h1>
          <p className="ds-lead">
            Every issue found on an account adds points. The total is multiplied by the client's size. Nothing is hidden:
            you can redo every score by hand.
          </p>
          <ScoreStrip scoring={scoring} />
        </div>
      </section>
      <main className="ds-in ds-m ds-scoring">
        <div className="ds-groups">
          <section>
            <h2 className="ds-step">1. Add the points of each issue</h2>
            <p className="ds-ws">An issue counts once per account, even if it happens several times.</p>
            <div className="ds-tiers">
              {scoring.tiers.map((tier) => (
                <TierIssues key={tier.tier} tier={tier} />
              ))}
            </div>
          </section>

          <section>
            <h2 className="ds-step">2. Multiply by the client's size</h2>
            <p className="ds-ws">The same issue matters more on a larger client.</p>
            <ul className="ds-rule-list">
              {scoring.sizes.map((size) => (
                <li className="ds-rule" key={size.label}>
                  <strong>{size.label}</strong>
                  <span className="ds-rule-points">×{size.multiplier}</span>
                </li>
              ))}
            </ul>
          </section>

          {example && (
            <section>
              <h2 className="ds-step">3. Example: {example.name}</h2>
              <Calculation card={example} />
            </section>
          )}

          <section>
            <h2 className="ds-step">{example ? "4" : "3"}. How accounts are ordered</h2>
            <ol className="ds-order">
              <li>An account takes the priority of its most serious issue.</li>
              <li>Critical accounts come first, then High, so a Critical account can sit above a High one with a higher score.</li>
              <li>Within a priority, the highest score comes first. If two scores are equal, the quicker next step comes first.</li>
              <li>Medium and Low accounts go under "Can wait". Accounts with no issue stay off the page.</li>
            </ol>
          </section>
        </div>
        <p className="ds-foot">
          Disagree with a score? Use "Wrong priority?" on the account card.{" "}
          <a className="ds-back" href="#">
            ← Back to this week
          </a>
        </p>
      </main>
    </>
  );
}
