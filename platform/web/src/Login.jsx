import { useState } from "react";
import { api } from "./api.js";

const ERRORS = {
  401: "Wrong password.",
  429: "Too many attempts. Wait a minute, then try again.",
};

export default function Login({ onDone }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);

  async function submit(event) {
    event.preventDefault();
    try {
      await api.login(password);
      onDone();
    } catch (failure) {
      setError(ERRORS[failure.status] ?? "Sign-in is not available. Try again.");
    }
  }

  return (
    <main className="dz ds-login">
      <form onSubmit={submit}>
        <div className="ds-logo">
          <i />
          <b>PriorityOne</b>
        </div>
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          autoFocus
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button type="submit" className="ds-log">
          Sign in
        </button>
        {error && (
          <p className="ds-login-error" role="alert">
            {error}
          </p>
        )}
        <p className="ds-note">Single sign-on replaces this password in production.</p>
      </form>
    </main>
  );
}
