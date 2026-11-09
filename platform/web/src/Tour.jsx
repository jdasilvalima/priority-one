import { driver } from "driver.js";
import "driver.js/dist/driver.css";

export const TOUR_HASH = "#tour";
const SEEN_KEY = "priorityone-tour-seen";

let current = null;

// Each step points at a real part of "This week". A step whose part is missing, in an empty week, is skipped.
function steps(week) {
  return [
    {
      element: ".ds-hero h1",
      popover: {
        title: "Your list for this week",
        description: `It replaces the ${week.alerts.total} alerts you got from ${week.alerts.tools} tools. Every account here needs you.`,
      },
    },
    {
      element: ".ds-gh",
      popover: { title: "Most urgent first", description: "Critical means act today. High means act this week." },
    },
    {
      element: ".ds-card .ds-sigs",
      popover: {
        title: "Why this account is here",
        description: "Each line is a warning sign and the tool it comes from. Click the tool to open the record.",
      },
    },
    {
      element: ".ds-card .ds-nb",
      popover: { title: "What to do next", description: "One action, how long it takes, and what to prepare." },
    },
    {
      element: ".ds-card .ds-acts",
      popover: {
        title: "Done, or not now?",
        description:
          "Log to Salesforce creates a task in Salesforce. Not this week takes the account off your list until next Monday.",
      },
    },
    {
      element: ".ds-card .ds-lnk .ds-a:not(.ds-mut)",
      popover: {
        title: "How the score adds up",
        description: "Shows the points of each signal and the client size behind the score.",
      },
    },
    {
      element: ".ds-card .ds-lnk .ds-mut",
      popover: {
        title: "Disagree with the priority?",
        description: "Say why. Your reason goes to the monthly review, where the points are adjusted.",
      },
    },
    {
      element: ".ds-nav",
      popover: {
        title: "Need more?",
        description: "How scoring works lists what each issue is worth. Take the tour shows this guide again.",
      },
    },
  ].filter((step) => document.querySelector(step.element));
}

function remember() {
  try {
    localStorage.setItem(SEEN_KEY, "yes");
  } catch {
    // Storage can be blocked: the tour then shows on every visit, which is harmless.
  }
}

export function isFirstVisit() {
  try {
    return localStorage.getItem(SEEN_KEY) === null;
  } catch {
    return false;
  }
}

export function startTour(week) {
  if (current?.isActive()) return;
  remember();
  current = driver({
    steps: steps(week),
    showProgress: true,
    progressText: "{{current}} of {{total}}",
    prevBtnText: "Back",
    nextBtnText: "Next",
    doneBtnText: "Done",
    popoverClass: "ds-tour",
    stagePadding: 6,
    stageRadius: 14,
  });
  current.drive();
}
