// The demo writes nothing. Each button says what it would do in production.
export const notifications = {
  log: (name) => `In production, this creates a Salesforce Task for ${name} with your note. Nothing was sent in this demo.`,
  snooze: (name) => `In production, ${name} leaves your list until next Monday. Nothing was saved in this demo.`,
  flag: (name, reason) =>
    `In production, "${reason}" goes to the monthly playbook review with ${name}'s signals. Nothing was saved in this demo.`,
  source: (source) => `In production, this opens the record in ${source}. This demo uses mock data.`,
};
