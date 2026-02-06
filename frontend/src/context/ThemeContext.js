import { createContext, useContext, useEffect, useState } from 'react';

// Available themes with their display info
export const THEMES = {
  light: { name: 'Light', icon: '☀️', description: 'Clean white theme' },
  dark: { name: 'Dark', icon: '🌙', description: 'Easy on the eyes' },
  ocean: { name: 'Ocean', icon: '🌊', description: 'Deep blue vibes' },
  sunset: { name: 'Sunset', icon: '🌅', description: 'Warm orange glow' },
  forest: { name: 'Forest', icon: '🌲', description: 'Natural greens' },
  lavender: { name: 'Lavender', icon: '💜', description: 'Soft purple tones' },
  rose: { name: 'Rose', icon: '🌸', description: 'Gentle pink hues' },
  midnight: { name: 'Midnight', icon: '🌌', description: 'Deep purple night' },
  coral: { name: 'Coral', icon: '🪸', description: 'Vibrant coral reef' },
  mint: { name: 'Mint', icon: '🍃', description: 'Fresh mint green' },
};

const ThemeContext = createContext({
  theme: 'light',
  setTheme: () => {},
  toggleTheme: () => {},
  cycleTheme: () => {},
  isDark: false,
});

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme');
      if (saved && THEMES[saved]) return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });

  // Determine if current theme is a dark variant
  const isDark = ['dark', 'midnight', 'ocean'].includes(theme);

  useEffect(() => {
    const root = window.document.documentElement;
    
    // Remove all theme classes
    Object.keys(THEMES).forEach(t => root.classList.remove(t));
    
    // Add current theme class
    root.classList.add(theme);
    
    // Also add dark class for dark-variant themes (for compatibility)
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    
    localStorage.setItem('theme', theme);
  }, [theme, isDark]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const cycleTheme = () => {
    const themeKeys = Object.keys(THEMES);
    const currentIndex = themeKeys.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themeKeys.length;
    setTheme(themeKeys[nextIndex]);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, cycleTheme, isDark, themes: THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeProvider;
