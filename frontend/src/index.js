import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";
import * as serviceWorkerRegistration from './serviceWorkerRegistration';
import { getVersion } from './version';

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Log version on startup
console.log(`PRIVITY ${getVersion()} starting...`);

// Register service worker for PWA functionality
serviceWorkerRegistration.register({
  onSuccess: () => {
    console.log(`PRIVITY ${getVersion()} is now available offline!`);
  },
  onUpdate: (registration) => {
    console.log(`New version of PRIVITY available (${getVersion()}). Refreshing...`);
    // Force update when new version is available
    if (registration && registration.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      // Reload the page to get the new version
      window.location.reload(true);
    }
  }
});
