import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { events } from "./data";
import {
  defaultPreferences, defaultProfile, seedNotifications, recommend,
} from "./userData";

const UserContext = createContext(null);

function usePersisted(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* ignore */ }
  }, [key, value]);
  return [value, setValue];
}

export function UserProvider({ children }) {
  const [savedIds, setSavedIds] = usePersisted("hr:saved", ["1", "2"]);
  const [profile, setProfile] = usePersisted("hr:profile", defaultProfile);
  const [preferences, setPreferences] = usePersisted("hr:prefs", defaultPreferences);
  const [notifications, setNotifications] = usePersisted("hr:notifications", seedNotifications);

  const isSaved = useCallback((id) => savedIds.includes(id), [savedIds]);
  const toggleSaved = useCallback(
    (id) => setSavedIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id])),
    [setSavedIds]
  );

  const updateProfile = useCallback((patch) => setProfile((p) => ({ ...p, ...patch })), [setProfile]);
  const updatePreferences = useCallback(
    (patch) => setPreferences((p) => ({ ...p, ...(typeof patch === "function" ? patch(p) : patch) })),
    [setPreferences]
  );
  const resetPreferences = useCallback(() => setPreferences(defaultPreferences), [setPreferences]);

  const markRead = useCallback(
    (id) => setNotifications((n) => n.map((x) => (x.id === id ? { ...x, read: true } : x))),
    [setNotifications]
  );
  const markAllRead = useCallback(
    () => setNotifications((n) => n.map((x) => ({ ...x, read: true }))),
    [setNotifications]
  );
  const dismissNotification = useCallback(
    (id) => setNotifications((n) => n.filter((x) => x.id !== id)),
    [setNotifications]
  );

  const savedEvents = useMemo(
    () => savedIds.map((id) => events.find((e) => e.id === id)).filter(Boolean),
    [savedIds]
  );
  const unreadCount = notifications.filter((n) => !n.read).length;
  const recommendations = useMemo(() => recommend(events, preferences), [preferences]);

  const completeness = useMemo(() => {
    const checks = [
      profile.name, profile.email, profile.organization, profile.location,
      profile.bio, profile.github || profile.linkedin,
      profile.skills.length > 0, preferences.interests.length > 0,
    ];
    return Math.round((checks.filter(Boolean).length / checks.length) * 100);
  }, [profile, preferences]);

  const value = {
    savedIds, savedEvents, isSaved, toggleSaved,
    profile, updateProfile, completeness,
    preferences, updatePreferences, resetPreferences,
    notifications, unreadCount, markRead, markAllRead, dismissNotification,
    recommendations,
  };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used inside <UserProvider>");
  return ctx;
}
