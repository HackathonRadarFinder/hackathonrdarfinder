import React, { useState, useEffect } from "react";

import { ThemeContext } from "./ThemeState";

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      const saved = localStorage.getItem("hr_theme");
      if (saved === "dark" || saved === "light") return saved;
      if (saved === "system") {
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
      }
    } catch {}
    return "light";
  });

  const isDark = theme === "dark";

  useEffect(() => {
    try {
      document.documentElement.setAttribute("data-theme", theme);
      document.documentElement.classList.toggle("dark", isDark);
      localStorage.setItem("hr_theme", theme);

      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      if (metaThemeColor) {
        metaThemeColor.setAttribute("content", isDark ? "#09090B" : "#ffffff");
      }
    } catch {}
  }, [theme, isDark]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (e) => {
      const saved = localStorage.getItem("hr_theme");
      if (saved === "system") {
        setThemeState(e.matches ? "dark" : "light");
      }
    };
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const setTheme = (newTheme) => {
    if (newTheme === "system") {
      const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setThemeState(systemDark ? "dark" : "light");
      try {
        localStorage.setItem("hr_theme", "system");
      } catch {}
    } else {
      setThemeState(newTheme);
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isDark }}>
      {children}
    </ThemeContext.Provider>
  );
}
