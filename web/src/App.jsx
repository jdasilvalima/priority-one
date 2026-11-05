import { useCallback, useEffect, useState } from "react";
import Card from "./Card.jsx";
import { TIERS, TierPill } from "./tiers.jsx";

// The address of the database stays on the server: the page only knows this route.
const WEEK_URL = import.meta.env.DEV ? "/week.json" : "/api/week";
const NOTIFICATION_MS = 7000;

function Header({ user }) {
  return (
    <header className="ds-top">
      <div className="ds-in ds-bar">
        <div className="ds-logo">
          <i />
          <b>PriorityOne</b>
        </div>
        <div className="ds-who">
          <span>
            {user.name} · {user.title} · {user.account_count} accounts
          </span>
          <span className="ds-av">{user.initials}</span>
        </div>
      </div>
    </header>
  );
}

function Hero({ week }) {
  return (
    <section className="ds-hero">
      <div className="ds-in">
        <p className="ds-week">{week.week_label}</p>
        <h1>{week.need_you_count} accounts need you this week.</h1>
        <p className="ds-lead">
          These are all your accounts with a Critical or High signal from the AM playbook. Each one says why, and the one
          thing to do next. This list replaces {week.alerts.total} alerts you got from {week.alerts.tools} tools last week.
        </p>
        <div className="ds-strip">
          <strong>Score =</strong>
          <span>
            signal points <em>Critical 50 · High 30 · Medium 15 · Low 5</em>
          </span>
          <b>×</b>
          <span>
            client size <em>×1 · ×1.5 · ×2</em>
          </span>
        </div>
        <div className="ds-pills">
          <span className="ds-dl">Data</span>
          {week.sources.map((source) => (
            <span className="ds-dp" key={source.label}>
              <i />
              {source.label} {source.fresh}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function CanWait({ week }) {
  return (
    <section className="ds-wait">
      <h2>Can wait</h2>
      <p className="ds-ws">Medium or Low signals. They move up only if a Critical or High signal appears.</p>
      <ul>
        {week.can_wait.map((account) => (
          <li key={account.account_id}>
            <strong>{account.name}</strong>
            <TierPill tier={account.tier} />
            <span className="ds-wt">{account.summary}</span>
            <span className="ds-wf">{account.equation}</span>
          </li>
        ))}
      </ul>
      <p className="ds-34">
        <strong>{week.healthy_count} accounts:</strong> no signal, data fresh. Nothing to do.
      </p>
    </section>
  );
}

function Notification({ text, onClose }) {
  return (
    <div className="ds-toast" role="status">
      <p>{text}</p>
      <button type="button" aria-label="Dismiss" onClick={onClose}>
        ×
      </button>
    </div>
  );
}

export default function App() {
  const [week, setWeek] = useState(null);
  const [failed, setFailed] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    fetch(WEEK_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(setWeek)
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    if (!notification) return undefined;
    const timer = setTimeout(() => setNotification(null), NOTIFICATION_MS);
    return () => clearTimeout(timer);
  }, [notification]);

  const notify = useCallback((text) => setNotification({ text }), []);

  if (failed) return <p className="ds-state">This week's list could not be loaded. Reload the page.</p>;
  if (!week) return <p className="ds-state">Loading this week's list…</p>;

  return (
    <div className="dz">
      <Header user={week.user} />
      <Hero week={week} />
      <main className="ds-in ds-m">
        <div className="ds-groups">
          {week.groups.map((group) => (
            <section key={group.tier}>
              <div className="ds-gh">
                <span className="ds-badge" style={{ background: TIERS[group.tier].color }}>
                  {group.tier}
                </span>
                <span>{TIERS[group.tier].subtitle}</span>
              </div>
              <div className="ds-list">
                {group.cards.map((card) => (
                  <Card key={card.account_id} card={card} notify={notify} />
                ))}
              </div>
            </section>
          ))}
        </div>
        <CanWait week={week} />
        <p className="ds-foot">
          Within each priority, accounts are sorted by score; effort breaks ties. Prototype with mock data, no real merchant
          information.
        </p>
      </main>
      {notification && <Notification text={notification.text} onClose={() => setNotification(null)} />}
    </div>
  );
}
