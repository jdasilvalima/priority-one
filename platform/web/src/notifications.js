// What the Account Manager sees after each action. Everything here is saved in the database.
export const notifications = {
  log: (name) => `Saved for ${name}. With a real connection, this also creates the Salesforce Task.`,
  snooze: (name) => `${name} leaves your list until next Monday.`,
  undo: (name) => `${name} is back on your list.`,
  flag: (name, reason) => `Saved: "${reason}". It goes to the monthly playbook review for ${name}.`,
  source: (source) => `With a real connection, this opens the record in ${source}. This stack uses fake sources.`,
};
