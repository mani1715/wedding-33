import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import "@/styles/luxury.css";
import "@/styles/luxury-overrides.css";
import "@/styles/mobile-fixes.css";
import App from "@/App";

// Mobile scroll perf: ensure all scroll/touch listeners default to passive.
// This prevents 3rd-party libs (or framer-motion subscribers) from
// blocking the main thread on touch/scroll on Android Chrome.
if (typeof window !== 'undefined' && 'EventTarget' in window) {
  const PASSIVE_EVENTS = new Set(['scroll', 'touchmove', 'touchstart', 'wheel', 'mousewheel']);
  const originalAddEventListener = window.EventTarget.prototype.addEventListener;
  window.EventTarget.prototype.addEventListener = function (type, fn, options) {
    if (PASSIVE_EVENTS.has(type)) {
      if (typeof options === 'object' && options !== null) {
        if (options.passive === undefined) options.passive = true;
      } else if (options === undefined || typeof options === 'boolean') {
        options = { capture: !!options, passive: true };
      }
    }
    return originalAddEventListener.call(this, type, fn, options);
  };
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
