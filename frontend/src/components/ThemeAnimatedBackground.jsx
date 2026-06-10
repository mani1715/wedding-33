import React, { useEffect, useRef, memo } from 'react';
import './ThemeAnimatedBackground.css';

/**
 * ThemeAnimatedBackground — Performance-optimized themed particle background.
 *
 * Optimizations (Phase 4):
 *   - Reduced particle counts (desktop 10-14, mobile 4-8)
 *   - DPR capped at min(devicePixelRatio, 1.5)
 *   - Pauses animation when:
 *       • document.hidden (tab switched away)
 *       • canvas offscreen (IntersectionObserver)
 *       • user prefers-reduced-motion
 *   - Throttled scroll (~150ms) and touch (~80ms) handlers
 *   - Caches RAF-allocated objects to avoid GC churn
 *   - Removes expensive shadow blur (kept only as a single inexpensive shadow color)
 *   - Cleans up ALL listeners + RAF + observers on unmount
 *
 * Visual quality is preserved — fewer particles but the motion remains.
 */

const isMobile = () => typeof window !== 'undefined' && window.innerWidth <= 768;
const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Theme particle dictionaries (kept identical visually — only counts reduced)
const THEME_CONFIGS = {
  temple: {
    desktop: 12, mobile: 6,
    colors: ['#FF69B4', '#FF1493', '#FFB6C1', '#FFC0CB', '#DB7093'],
    shapes: ['🌸', '🌺', '🏵️', '🌼', '🌷'],
    speed: 0.5, size: { min: 20, max: 40 },
  },
  beach: {
    desktop: 10, mobile: 5,
    colors: ['#4FC3F7', '#29B6F6', '#03A9F4', '#81D4FA', '#B3E5FC'],
    shapes: ['💧', '🌊', '💦', '🐚', '⭐'],
    speed: 0.3, size: { min: 15, max: 35 },
  },
  mughal: {
    desktop: 12, mobile: 6,
    colors: ['#FFD700', '#FFA500', '#FF8C00', '#FFE4B5', '#FAFAD2'],
    shapes: ['🪔', '✨', '💫', '⭐', '🌟'],
    speed: 0.4, size: { min: 18, max: 38 },
  },
  nature: {
    desktop: 12, mobile: 6,
    colors: ['#8BC34A', '#4CAF50', '#81C784', '#AED581', '#C5E1A5'],
    shapes: ['🍃', '🌿', '🍂', '🌱', '🌾'],
    speed: 0.45, size: { min: 20, max: 35 },
  },
  minimal: {
    desktop: 8, mobile: 4,
    colors: ['#E0E0E0', '#BDBDBD', '#9E9E9E', '#F5F5F5', '#EEEEEE'],
    shapes: ['●', '○', '◆', '◇', '■'],
    speed: 0.25, size: { min: 10, max: 25 },
  },
  kerala_backwaters: {
    desktop: 10, mobile: 5,
    colors: ['#00BCD4', '#0097A7', '#006064', '#80DEEA', '#B2EBF2'],
    shapes: ['🚣', '🌴', '🦜', '🌊', '☀️'],
    speed: 0.35, size: { min: 18, max: 32 },
  },
  bengali: {
    desktop: 12, mobile: 6,
    colors: ['#E91E63', '#FF4081', '#F50057', '#FF80AB', '#FFB2C1'],
    shapes: ['🌸', '🎊', '🪔', '🌺', '✨'],
    speed: 0.5, size: { min: 20, max: 38 },
  },
  bollywood: {
    desktop: 14, mobile: 8,
    colors: ['#FF6B9D', '#FEC260', '#4ECDC4', '#F06292', '#FFD54F'],
    shapes: ['🎬', '🎵', '⭐', '✨', '💃'],
    speed: 0.6, size: { min: 22, max: 42 },
  },
  christian: {
    desktop: 10, mobile: 5,
    colors: ['#FFFFFF', '#E8F5E9', '#C8E6C9', '#F0F4C3', '#FFF9C4'],
    shapes: ['🕊️', '✝️', '🕯️', '💒', '🌹'],
    speed: 0.3, size: { min: 18, max: 35 },
  },
  muslim: {
    desktop: 10, mobile: 5,
    colors: ['#4CAF50', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9'],
    shapes: ['☪️', '🕌', '🌙', '⭐', '✨'],
    speed: 0.4, size: { min: 18, max: 36 },
  },
  punjabi: {
    desktop: 12, mobile: 6,
    colors: ['#FF9800', '#FFA726', '#FFB74D', '#FFCC80', '#FFE0B2'],
    shapes: ['🥁', '🎵', '🌾', '🎊', '💃'],
    speed: 0.5, size: { min: 20, max: 40 },
  },
};

const getThemeConfig = (themeName) => {
  const cfg = THEME_CONFIGS[themeName] || THEME_CONFIGS.temple;
  // 2026-05 perf overhaul — Desktop 24 / Tablet 14 / Mobile 8.
  // Override the per-theme desktop/mobile defaults so every page gets a
  // cheap canvas across the whole app.
  const w = typeof window !== 'undefined' ? window.innerWidth : 1280;
  let count;
  if (w <= 768) count = 8;
  else if (w <= 1024) count = 14;
  else count = Math.min(24, cfg.desktop);
  return { ...cfg, particleCount: count };
};

const ThemeAnimatedBackground = memo(function ThemeAnimatedBackground({
  theme = 'temple',
}) {
  // 🚨 Mobile perf bail-out (Feb 2026): the fullscreen canvas was repainting
  // ~2.6 million pixels per frame on real Android devices (360×696 viewport
  // × DPR 2.6²). Even with only 8 particles the per-frame fillText+rotate+
  // sqrt loop saturated the main thread, and Android Chrome silently dropped
  // touch-scroll gestures whenever the main thread couldn't keep up.
  // Symptom reported by users: "page scrolls a little, then locks".
  //
  // The canvas adds ~5% visual delight for ~95% of the perf cost on mobile —
  // every page already has cinematic CSS gradients + the design backdrop
  // layer. So on mobile (and for users with prefers-reduced-motion) we
  // return null entirely. Desktop keeps the full effect.
  const skip = (typeof window !== 'undefined') && (
    window.innerWidth <= 1024 ||
    (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) ||
    // Coarse pointer = touch-primary device; another reliable mobile signal.
    (window.matchMedia && window.matchMedia('(pointer: coarse)').matches)
  );
  const canvasRef = useRef(null);
  const stateRef = useRef({
    particles: [],
    touches: [],
    mouseX: 0,
    mouseY: 0,
    running: false,
    visible: true,
    tabVisible: true,
    rafId: null,
    lastScroll: 0,
    lastTouch: 0,
    dpr: 1,
  });

  useEffect(() => {
    if (skip) return;          // mobile / reduced-motion / coarse-pointer: no canvas at all
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Respect prefers-reduced-motion — render no animation at all
    if (prefersReducedMotion()) {
      return undefined;
    }

    const ctx = canvas.getContext('2d', { alpha: true });
    const config = getThemeConfig(theme);
    const state = stateRef.current;

    // Cap DPR to 1.5 for cheap rendering on retina/mobile
    const dpr = Math.min(typeof window !== 'undefined' ? window.devicePixelRatio : 1, 1.5);
    state.dpr = dpr;

    // ── Particle factory (plain objects, no class — cheaper to construct) ──
    const makeParticle = (overrides = {}) => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const size =
        Math.random() * (config.size.max - config.size.min) + config.size.min;
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        size,
        speedX: (Math.random() - 0.5) * config.speed,
        speedY: (Math.random() - 0.5) * config.speed,
        shape: config.shapes[Math.floor(Math.random() * config.shapes.length)],
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.02,
        opacity: Math.random() * 0.5 + 0.3,
        wobble: Math.random() * Math.PI * 2,
        wobbleSpeed: Math.random() * 0.03 + 0.01,
        ...overrides,
      };
    };

    const resize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // scale once
    };
    resize();

    // Seed particles
    state.particles = Array.from({ length: config.particleCount }, () => makeParticle());

    // ── Animation loop (single allocation, reuse particle objects) ──
    let lastTime = performance.now();
    const animate = () => {
      // Bail if paused
      if (!state.running || !state.visible || !state.tabVisible) {
        state.rafId = null;
        return;
      }

      const now = performance.now();
      const deltaTime = Math.min((now - lastTime) / 16, 3); // clamp for tab-pause spikes
      lastTime = now;

      const w = canvas.clientWidth;
      const h = canvas.clientHeight;

      ctx.clearRect(0, 0, w, h);

      // Cache mouse position locally
      const mx = state.mouseX;
      const my = state.mouseY;

      // Update + draw each particle
      for (let i = 0; i < state.particles.length; i++) {
        const p = state.particles[i];

        // Soft mouse repulsion
        const dx = mx - p.x;
        const dy = my - p.y;
        const distSq = dx * dx + dy * dy;
        if (distSq < 22500) {
          // 150 * 150
          const dist = Math.sqrt(distSq) || 1;
          const force = (150 - dist) / 150;
          p.x -= (dx / dist) * force * 2;
          p.y -= (dy / dist) * force * 2;
        }

        p.wobble += p.wobbleSpeed;
        p.x += p.speedX * deltaTime + Math.sin(p.wobble) * 0.5;
        p.y += p.speedY * deltaTime + Math.cos(p.wobble) * 0.3;
        p.rotation += p.rotationSpeed * deltaTime;

        if (p.x < -p.size) p.x = w + p.size;
        else if (p.x > w + p.size) p.x = -p.size;
        if (p.y < -p.size) p.y = h + p.size;
        else if (p.y > h + p.size) p.y = -p.size;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.globalAlpha = p.opacity;
        ctx.font = p.size + 'px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        // shadowBlur is EXPENSIVE — removed for perf, fillText still readable
        ctx.fillText(p.shape, 0, 0);
        ctx.restore();
      }

      // Touch ripples
      const touches = state.touches;
      for (let i = touches.length - 1; i >= 0; i--) {
        const t = touches[i];
        t.life -= 0.02 * deltaTime;
        if (t.life <= 0) {
          touches.splice(i, 1);
          continue;
        }
        ctx.save();
        ctx.globalAlpha = t.life;
        ctx.strokeStyle = config.colors[1] || config.colors[0];
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(t.x, t.y, (1 - t.life) * 100, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      state.rafId = requestAnimationFrame(animate);
    };

    const startLoop = () => {
      if (state.rafId != null) return;
      lastTime = performance.now();
      state.running = true;
      state.rafId = requestAnimationFrame(animate);
    };
    const stopLoop = () => {
      if (state.rafId != null) {
        cancelAnimationFrame(state.rafId);
        state.rafId = null;
      }
    };

    // ── Visibility & viewport pausing ──
    const handleVisibilityChange = () => {
      state.tabVisible = !document.hidden;
      if (state.tabVisible && state.visible) startLoop();
      else stopLoop();
    };

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          state.visible = e.isIntersecting;
        }
        if (state.visible && state.tabVisible) startLoop();
        else stopLoop();
      },
      { threshold: 0 }
    );
    io.observe(canvas);

    // ── Throttled event handlers ──
    // 2026-05 perf overhaul: mousemove ONLY on desktop. touchstart + scroll
    // listeners REMOVED — they were the single biggest source of scroll
    // jank because each scroll/tap was injecting new particles into the
    // canvas loop.
    const isDesktopWidth =
      typeof window !== 'undefined' && window.innerWidth > 1024;
    const handleMouseMove = (e) => {
      state.mouseX = e.clientX;
      state.mouseY = e.clientY;
    };

    // ── Wire up ──
    if (isDesktopWidth) {
      window.addEventListener('mousemove', handleMouseMove, { passive: true });
    }
    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    state.tabVisible = !document.hidden;
    startLoop();

    // ── Cleanup ──
    return () => {
      stopLoop();
      io.disconnect();
      if (isDesktopWidth) {
        window.removeEventListener('mousemove', handleMouseMove);
      }
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      state.particles = [];
      state.touches = [];
    };
  }, [theme, skip]);

  // Don't render the canvas at all on mobile/reduced-motion — saves the
  // entire RAF loop + the GPU layer.
  if (skip) return null;

  return (
    <canvas
      ref={canvasRef}
      className="theme-animated-background"
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1,
      }}
      data-testid="theme-animated-background"
    />
  );
});

export default ThemeAnimatedBackground;
