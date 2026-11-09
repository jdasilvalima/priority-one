import { useState } from "react";
import { api } from "./api.js";
import { notifications } from "./notifications.js";
import { EFFORT_STYLES, TierPill } from "./tiers.jsx";

const FLAG_REASONS = [
  "Already handling it",
  "Data is wrong or out of date",
  "I know something the data can't see",
  "Wrong next step",
];

export function Calculation({ card }) {
  return (
    <div className="ds-box">
      <div className="ds-scroll">
        <table>
          <thead>
            <tr>
              <th>Signal</th>
              <th>Priority</th>
              <th>Data</th>
              <th className="r">Points</th>
            </tr>
          </thead>
          <tbody>
            {card.signals.map((signal) => (
              <tr key={signal.label}>
                <td className="b">{signal.label}</td>
                <td>
                  {signal.tier} · {signal.points} pts
                </td>
                <td className="ds-data">
                  {signal.source} · {signal.fresh}
                </td>
                <td className="r b">{signal.points}</td>
              </tr>
            ))}
            <tr>
              <td colSpan="3" className="ds-size">
                × client size: {card.size_label}
              </td>
              <td className="r b">×{card.size_multiplier}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="ds-tot">
        <strong>{card.equation}</strong>
      </p>
      <p className="ds-note">
        Points are starting assumptions from the AM playbook. Each month we check them against what really happened: did
        the account lose more than 20% of its volume within 90 days? Signals that predict it well gain points; the others
        lose points.
      </p>
    </div>
  );
}

function FlagForm({ card, act, onClose }) {
  const [reason, setReason] = useState(FLAG_REASONS[0]);
  const selectId = `reason-${card.account_id}`;

  function send() {
    act(() => api.act(card.account_id, "flagged", reason), notifications.flag(card.name, reason));
    onClose();
  }

  return (
    <div className="ds-box ds-flag">
      <div className="ds-sel">
        <label htmlFor={selectId}>Why is this wrong?</label>
        <select id={selectId} value={reason} onChange={(event) => setReason(event.target.value)}>
          {FLAG_REASONS.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      </div>
      <button type="button" className="ds-send" onClick={send}>
        Send
      </button>
    </div>
  );
}

export default function Card({ card, notify, act }) {
  const [showCalculation, setShowCalculation] = useState(card.rank === 1);
  const [flagging, setFlagging] = useState(false);

  return (
    <article className="ds-card">
      <div className="ds-row">
        <div className="ds-rank">{card.rank}</div>
        <div className="ds-body">
          <div className="ds-nl">
            <h2>{card.name}</h2>
            <span className="ds-meta">{card.meta}</span>
          </div>
          <p className="ds-hl">{card.headline}</p>
          <ul className="ds-sigs">
            {card.signals.map((signal) => (
              <li key={signal.label}>
                <span className="ds-sig">
                  <TierPill tier={signal.tier} />
                  <span>{signal.evidence}</span>
                </span>
                <button type="button" className="ds-src" onClick={() => notify(notifications.source(signal.source))}>
                  {signal.source} · {signal.fresh} ↗
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="ds-score">
          <p className="ds-sl">Score</p>
          <p className="ds-sn">{card.score}</p>
          <p className="ds-sf">{card.formula}</p>
        </div>
      </div>

      <div className="ds-next">
        <div className="ds-nb">
          <p className="ds-dn">
            <span>Do next</span>
            <span className="ds-eff" style={EFFORT_STYLES[card.effort_band]}>
              {card.effort}
            </span>
          </p>
          <p className="ds-nt">{card.action_text}</p>
          <p className="ds-rd">To prepare: {card.prepare}</p>
        </div>
        <div className="ds-acts">
          <button
            type="button"
            className="ds-log"
            disabled={card.logged}
            onClick={() => act(() => api.act(card.account_id, "logged"), notifications.log(card.name))}
          >
            {card.logged ? "Logged ✓" : "Log to Salesforce"}
          </button>
          <button
            type="button"
            className="ds-snz"
            onClick={() => act(() => api.act(card.account_id, "snoozed"), notifications.snooze(card.name))}
          >
            Not this week
          </button>
        </div>
      </div>

      <div className="ds-lnk">
        <button
          type="button"
          className="ds-a"
          aria-expanded={showCalculation}
          onClick={() => setShowCalculation(!showCalculation)}
        >
          {showCalculation ? "Hide the calculation" : "How is this score calculated?"}
        </button>
        <button type="button" className="ds-a ds-mut" aria-expanded={flagging} onClick={() => setFlagging(!flagging)}>
          {flagging ? "Cancel" : "Wrong priority?"}
        </button>
      </div>

      {card.flagged && <p className="ds-flagged">You flagged this: {card.flagged}</p>}
      {showCalculation && <Calculation card={card} />}
      {flagging && <FlagForm card={card} act={act} onClose={() => setFlagging(false)} />}
    </article>
  );
}
