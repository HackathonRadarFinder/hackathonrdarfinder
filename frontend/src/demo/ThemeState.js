import { createContext, useContext } from 'react';
export const ThemeContext = createContext({ theme: 'light', setTheme: () => {}, toggleTheme: () => {}, isDark: false });
export const useTheme = () => useContext(ThemeContext);
