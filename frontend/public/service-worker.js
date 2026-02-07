// Service Worker for PRIVITY PWA
// VERSION: 6.3.0 - Update this on each deployment to force cache refresh
const SW_VERSION = '6.3.0';
const CACHE_NAME = `privity-cache-${SW_VERSION}`;
const STATIC_CACHE_NAME = `privity-static-${SW_VERSION}`;
const DYNAMIC_CACHE_NAME = `privity-dynamic-${SW_VERSION}`;

console.log(`[ServiceWorker] Version ${SW_VERSION} loading...`);

// Static assets to cache immediately (minimal - only truly static files)
const STATIC_ASSETS = [
  '/manifest.json',
  '/privity-logo.png',
];

// Patterns that should ALWAYS fetch from network (never serve stale)
const ALWAYS_NETWORK_PATTERNS = [
  /\/static\/js\//,      // React JS bundles
  /\/static\/css\//,     // React CSS bundles  
  /\.chunk\.(js|css)$/,  // Code-split chunks
  /main\.[a-f0-9]+\.(js|css)$/,  // Main bundles with hash
  /index\.html$/,        // Always get fresh index.html
];

// API endpoints to cache with network-first strategy
const API_CACHE_PATTERNS = [
  '/api/dashboard',
  '/api/stocks',
  '/api/clients',
  '/api/kill-switch/status',
];

// Install event - cache static assets and force activation
self.addEventListener('install', (event) => {
  console.log(`[ServiceWorker ${SW_VERSION}] Installing...`);
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('[ServiceWorker] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[ServiceWorker] Skip waiting to activate immediately');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up ALL old caches aggressively
self.addEventListener('activate', (event) => {
  console.log(`[ServiceWorker ${SW_VERSION}] Activating...`);
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            // Delete ANY cache that doesn't match current version
            return name.startsWith('privity-') && 
                   !name.includes(SW_VERSION);
          })
          .map((name) => {
            console.log('[ServiceWorker] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      console.log('[ServiceWorker] Claiming all clients');
      return self.clients.claim();
    }).then(() => {
      // Notify all clients to refresh
      return self.clients.matchAll().then(clients => {
        clients.forEach(client => {
          client.postMessage({
            type: 'SW_UPDATED',
            version: SW_VERSION
          });
        });
      });
    })
  );
});

// Check if request should always go to network
function shouldAlwaysFetchFromNetwork(url) {
  const pathname = url.pathname;
  return ALWAYS_NETWORK_PATTERNS.some(pattern => pattern.test(pathname));
}

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip WebSocket and external requests
  if (url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // API requests - Network first, fallback to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // JS/CSS bundles and index.html - ALWAYS network first (critical for updates)
  if (shouldAlwaysFetchFromNetwork(url)) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // Other static assets (images, fonts) - Cache first for performance
  event.respondWith(cacheFirstStrategy(request));
});

// Cache-first strategy for static assets
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Return offline page if available
    const offlineResponse = await caches.match('/');
    if (offlineResponse) {
      return offlineResponse;
    }
    throw error;
  }
}

// Network-first strategy for API calls
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      // Cache successful API responses
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Fallback to cache if network fails
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return error response for API calls
    return new Response(
      JSON.stringify({ error: 'You are offline. Please check your connection.' }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle push notifications (for future use)
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New notification from PRIVITY',
    icon: '/privity-logo.png',
    badge: '/privity-logo.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      { action: 'open', title: 'Open PRIVITY' },
      { action: 'close', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('PRIVITY', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Background sync (for future offline actions)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-data') {
    console.log('[ServiceWorker] Syncing data...');
    // Future: sync offline actions when back online
  }
});

console.log('[ServiceWorker] Loaded');
