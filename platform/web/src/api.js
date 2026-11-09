// Same address as the page: the web server passes /api to the API service, and the cookie goes along.
async function send(path, method, body) {
  const response = await fetch(`/api/${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

const account = (id) => `accounts/${encodeURIComponent(id)}`;

export const api = {
  week: () => send("week", "GET"),
  login: (password) => send("login", "POST", { password }),
  logout: () => send("logout", "POST"),
  act: (accountId, kind, reason) => send(`${account(accountId)}/actions`, "POST", { kind, reason }),
  undoSnooze: (accountId) => send(`${account(accountId)}/snooze`, "DELETE"),
};
