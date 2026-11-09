import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Card from "./Card.jsx";
import Login from "./Login.jsx";
import { notifications } from "./notifications.js";
import Scoring, { SCORING_HASH, ScoreStrip } from "./Scoring.jsx";
import { TOUR_HASH, isFirstVisit, startTour } from "./Tour.jsx";
import { TIERS, TierPill } from "./tiers.jsx";

const NOTIFICATION_MS = 7000;

function Header({ user, hash, onLogout }) {
  const page = hash === SCORING_HASH ? SCORING_HASH : "#";
  return (
    <header className="ds-top">
      <div className="ds-in ds-bar">
        <div className="ds-logo">
          <i />
          <b>PriorityOne</b>
        </div>
        <nav className="ds-nav" aria-label="Main">
          <a href="#" aria-current={page === "#" ? "page" : undefined}>
            This week
          </a>
          <a href={SCORING_HASH} aria-current={page === SCORING_HASH ? "page" : undefined}>
            How scoring works
          </a>
          <a href={TOUR_HASH}>Take the tour</a>
        </nav>
        <div className="ds-who">
          <span>
            {user.name} · {user.title} · {user.account_count} accounts
          </span>
          <span className="ds-av">{user.initials}</span>
          <button type="button" className="ds-logout" onClick={onLogout}>
            Log out
          </button>
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
        <ScoreStrip scoring={week.scoring}>
          <a className="ds-how" href={SCORING_HASH}>
            See what each issue is worth →
          </a>
        </ScoreStrip>
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

function Snoozed({ week, act }) {
  if (week.snoozed.length === 0) return null;
  return (
    <section className="ds-wait">
      <h2>Not this week</h2>
      <p className="ds-ws">Back on your list next Monday.</p>
      <ul>
        {week.snoozed.map((account) => (
          <li key={account.account_id}>
            <strong>{account.name}</strong>
            <button
              type="button"
              className="ds-a"
              onClick={() => act(() => api.undoSnooze(account.account_id), notifications.undo(account.name))}
            >
              Undo
            </button>
          </li>
        ))}
      </ul>
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

function useHash() {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    function follow() {
      setHash(window.location.hash);
      window.scrollTo(0, 0);
    }
    window.addEventListener("hashchange", follow);
    return () => window.removeEventListener("hashchange", follow);
  }, []);

  return hash;
}

export default function App() {
  const hash = useHash();
  const [week, setWeek] = useState(null);
  const [failed, setFailed] = useState(false);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [notification, setNotification] = useState(null);

  const load = useCallback(async () => {
    try {
      setWeek(await api.week());
      setNeedsLogin(false);
      setFailed(false);
    } catch (error) {
      if (error.status === 401) setNeedsLogin(true);
      else setFailed(true);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!notification) return undefined;
    const timer = setTimeout(() => setNotification(null), NOTIFICATION_MS);
    return () => clearTimeout(timer);
  }, [notification]);

  const notify = useCallback((text) => setNotification({ text }), []);

  // The tour starts on the first visit, and again from "Take the tour" in the menu.
  useEffect(() => {
    if (!week || hash === SCORING_HASH) return;
    if (hash === TOUR_HASH) {
      window.location.hash = "";
      startTour(week);
    } else if (isFirstVisit()) {
      startTour(week);
    }
  }, [week, hash]);

  const act = useCallback(
    async (request, message) => {
      try {
        await request();
        await load();
        notify(message);
      } catch (error) {
        if (error.status === 401) setNeedsLogin(true);
        else notify("That could not be saved. Nothing changed, try again.");
      }
    },
    [load, notify],
  );

  async function logout() {
    await api.logout();
    setWeek(null);
    setNeedsLogin(true);
  }

  if (needsLogin) return <Login onDone={load} />;
  if (failed) return <p className="ds-state">This week's list could not be loaded. Reload the page.</p>;
  if (!week) return <p className="ds-state">Loading this week's list…</p>;

  if (hash === SCORING_HASH) {
    return (
      <div className="dz">
        <Header user={week.user} hash={hash} onLogout={logout} />
        <Scoring week={week} />
      </div>
    );
  }

  return (
    <div className="dz">
      <Header user={week.user} hash={hash} onLogout={logout} />
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
                  <Card key={card.account_id} card={card} notify={notify} act={act} />
                ))}
              </div>
            </section>
          ))}
        </div>
        <Snoozed week={week} act={act} />
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
