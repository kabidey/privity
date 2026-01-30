// Simple cache utility for page data
const CACHE_PREFIX = 'privity_cache_';
const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

export const cache = {
  // Set data with TTL
  set: (key, data, ttl = DEFAULT_TTL) => {
    try {
      const cacheData = {
        data,
        expiry: Date.now() + ttl,
        timestamp: Date.now()
      };
      localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(cacheData));
    } catch (e) {
      console.warn('Cache set failed:', e);
    }
  },

  // Get data if not expired
  get: (key) => {
    try {
      const cached = localStorage.getItem(CACHE_PREFIX + key);
      if (!cached) return null;
      
      const { data, expiry } = JSON.parse(cached);
      if (Date.now() > expiry) {
        localStorage.removeItem(CACHE_PREFIX + key);
        return null;
      }
      return data;
    } catch (e) {
      console.warn('Cache get failed:', e);
      return null;
    }
  },

  // Remove specific cache
  remove: (key) => {
    try {
      localStorage.removeItem(CACHE_PREFIX + key);
    } catch (e) {
      console.warn('Cache remove failed:', e);
    }
  },

  // Clear all cache
  clear: () => {
    try {
      Object.keys(localStorage)
        .filter(k => k.startsWith(CACHE_PREFIX))
        .forEach(k => localStorage.removeItem(k));
    } catch (e) {
      console.warn('Cache clear failed:', e);
    }
  },

  // Invalidate cache on data mutation
  invalidate: (patterns) => {
    try {
      const keys = Object.keys(localStorage).filter(k => k.startsWith(CACHE_PREFIX));
      patterns.forEach(pattern => {
        keys.filter(k => k.includes(pattern)).forEach(k => localStorage.removeItem(k));
      });
    } catch (e) {
      console.warn('Cache invalidate failed:', e);
    }
  }
};

// Cache keys
export const CACHE_KEYS = {
  STOCKS: 'stocks_list',
  CLIENTS: 'clients_list',
  VENDORS: 'vendors_list',
  USERS: 'users_list',
  RESEARCH_REPORTS: 'research_reports',
  DASHBOARD_STATS: 'dashboard_stats',
};

export default cache;
