// Mock user data + helpers. Replace with API calls when the backend is ready.

export const INTERESTS = [
  "AI", "GenAI", "LLM", "Cloud", "Azure", "AWS", "Web",
  "Climate", "Sustainability", "Innovation", "India",
];

export const defaultProfile = {
  name: "",
  email: "",
  organization: "",
  role: "Student",
  location: "",
  bio: "",
  github: "",
  linkedin: "",
  skills: ["React", "Python"],
};

export const defaultPreferences = {
  interests: ["AI", "Cloud"],
  mode: "Any",              // Any | Remote | Hybrid
  eligibility: "Students",  // Students | Developers | Professionals
  minConfidence: "Medium",  // All | Medium | High  (predictions)
  notify: { deadlines: true, newEvents: true, predictions: true, digest: false },
  channels: { email: true, push: true },
  digestFrequency: "Weekly", // Daily | Weekly
};

export const seedNotifications = [
  { id: "n1", type: "deadline", title: "Smart India Hackathon registration closes soon", body: "Registration deadline is Feb 28, 2027.", time: "2 hours ago", read: false, link: "/event/3" },
  { id: "n2", type: "prediction", title: "New prediction signal: Microsoft", body: "Microsoft AI Innovation Challenge · 91% confidence for Jan 15 – Feb 28, 2027.", time: "5 hours ago", read: false, link: "/predictions" },
  { id: "n3", type: "event", title: "New event verified: Hack for Earth", body: "UN Environment Programme listed a new sustainability hackathon.", time: "1 day ago", read: false, link: "/event/6" },
  { id: "n4", type: "event", title: "AWS Generative AI Hackathon details updated", body: "Dates and prize information were refreshed from the source.", time: "3 days ago", read: true, link: "/event/4" },
  { id: "n5", type: "system", title: "Complete your profile", body: "Add your skills and interests to get better recommendations.", time: "4 days ago", read: true, link: "/profile" },
];

export function getInitials(name) {
  const letters = (name || "").trim().split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join("");
  return (letters || "NK").toUpperCase();
}

export function daysLeft(deadline) {
  const d = new Date(deadline);
  if (isNaN(d)) return null;
  return Math.ceil((d - new Date()) / 86400000);
}

const tokens = (...parts) =>
  parts.flat().join(" ").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);

export function matchesInterests(text, interests) {
  const t = tokens(text);
  return interests.filter((i) => t.includes(i.toLowerCase()));
}

export function recommend(events, prefs) {
  return events
    .map((e) => {
      const reasons = [];
      let score = 20;

      const hits = matchesInterests([e.tags, e.theme, e.title], prefs.interests);
      if (hits.length) {
        score += Math.min(hits.length, 3) * 18;
        reasons.push(`Matches your interest in ${hits.slice(0, 2).join(" & ")}`);
      }
      if (prefs.mode !== "Any" && e.mode === prefs.mode) {
        score += 12;
        reasons.push(`${e.mode} event, as you prefer`);
      }
      const elig = e.eligibility.toLowerCase();
      if (elig === "everyone" || elig.includes(prefs.eligibility.toLowerCase().replace(/s$/, ""))) {
        score += 12;
        reasons.push(`Open to ${prefs.eligibility.toLowerCase()}`);
      }
      if (e.status === "Official") {
        score += 6;
        reasons.push("Officially verified");
      }
      return { event: e, score: Math.min(score, 98), reasons };
    })
    .sort((a, b) => b.score - a.score);
}
