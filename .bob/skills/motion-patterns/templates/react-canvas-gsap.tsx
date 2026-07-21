import { useEffect, useRef } from 'react';
import gsap from 'gsap';

/**
 * Pattern: Porting Vanilla HTML5 Canvas + GSAP to React
 * 
 * Use this when the user provides a raw HTML/JS canvas reference (e.g. physics, particles).
 * Do NOT attempt to recreate the exact physics in React state or Three.js unless requested.
 * Keep the animation state in plain JS objects and mutate them with GSAP.
 * Avoid mapping rapidly changing 60fps animation state to React `useState`.
 */
export default function CanvasGsapPortTemplate() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 1. Define state as plain objects (not React state)
    const state = {
      x: canvas.width / 2,
      y: -50,
      radius: 20,
      alpha: 0
    };

    // 2. Setup GSAP tweens targeting the plain objects
    gsap.to(state, {
      y: canvas.height / 2,
      alpha: 1,
      duration: 1.5,
      ease: 'power2.inOut'
    });

    let reqId: number;

    // 3. The render loop (requestAnimationFrame)
    const render = () => {
      reqId = requestAnimationFrame(render);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw using the tweened state
      ctx.globalAlpha = state.alpha;
      ctx.beginPath();
      ctx.arc(state.x, state.y, state.radius, 0, Math.PI * 2);
      ctx.fillStyle = '#4fc3f7';
      ctx.fill();
    };

    render();

    // 4. Cleanup
    return () => {
      cancelAnimationFrame(reqId);
      gsap.killTweensOf(state);
    };
  }, []);

  // Make sure canvas takes full width/height or handle resize inside useEffect
  return <canvas ref={canvasRef} className="w-full h-full block" />;
}