import { useEffect, useRef } from 'react'
import gsap from 'gsap'

export default function App() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let W = canvas.width = window.innerWidth
    let H = canvas.height = window.innerHeight

    const BLUE       = '#4fc3f7'
    const BLUE_LIGHT = '#b3e5fc'
    let floorY       = H * 0.6

    // Koordinat pusat — SEMUA referensi di tengah
    const CENTER_X = W / 2

    // Tetesan & Born di tengah
    let mainDrop = { x: CENTER_X, y: -40, r: 16, alpha: 0 }
    let ripples: any[] = []
    let splashParts: any[] = []
    let miniDrops: any[] = []
    
    let phase = 'idle'

    let bornObj = { 
      x: CENTER_X, 
      y: floorY, 
      r: 0, 
      alpha: 0, 
      glow: 0, 
      textAlpha: 0,
      zoom: 1, 
      pulseAmp: 4 
    }

    let journeyObj = {
      progress: 0,
      lineLength: 0,
      dx: 0,           // Seberapa banyak garis miring ke kanan
      targetAlpha: 0,
      targetScale: 0,
      cameraSway: 0,   // Posisi kamera (sway geser)
      cameraZoom: 1,
      ready: false
    }

    // Target Node — miring ke kanan atas
    const TARGET_X = W * 0.65
    const TARGET_Y = H * 0.2

    let reqId: number
    const startTime = Date.now()

    const handleResize = () => {
      W = canvas.width = window.innerWidth
      H = canvas.height = window.innerHeight
      floorY = H * 0.6
      CENTER_X = W / 2
      mainDrop.x = CENTER_X
      bornObj.x = CENTER_X
    }
    window.addEventListener('resize', handleResize)

    function drawDrop(x: number, y: number, r: number, alpha: number, scaleX = 1, scaleY = 1) {
      if (alpha <= 0 || r <= 0) return
      ctx!.save()
      ctx!.globalAlpha = Math.min(1, alpha)
      ctx!.translate(x, y)
      ctx!.scale(scaleX, scaleY)

      ctx!.beginPath()
      ctx!.moveTo(-r * 0.55, -r * 0.25)
      ctx!.quadraticCurveTo(0, -r * 2.4, r * 0.55, -r * 0.25)
      ctx!.quadraticCurveTo(0, r * 0.6, -r * 0.55, -r * 0.25)
      ctx!.fillStyle = BLUE
      ctx!.fill()

      ctx!.beginPath()
      ctx!.arc(0, 0, r, 0, Math.PI * 2)
      ctx!.fillStyle = BLUE
      ctx!.fill()

      const g = ctx!.createRadialGradient(-r * 0.25, -r * 0.25, r * 0.05, 0, 0, r)
      g.addColorStop(0, 'rgba(255,255,255,0.45)')
      g.addColorStop(1, 'rgba(2,136,209,0.0)')
      ctx!.beginPath()
      ctx!.arc(0, 0, r, 0, Math.PI * 2)
      ctx!.fillStyle = g
      ctx!.fill()

      ctx!.restore()
    }

    function drawRipple(rp: any) {
      if (rp.alpha <= 0) return
      ctx!.save()
      ctx!.globalAlpha = rp.alpha * 0.7
      ctx!.strokeStyle = BLUE
      ctx!.lineWidth = 1.5
      ctx!.beginPath()
      ctx!.ellipse(rp.x, rp.y, rp.rx, rp.ry, 0, 0, Math.PI * 2)
      ctx!.stroke()
      ctx!.restore()
    }

    function drawParticle(p: any) {
      if (p.alpha <= 0 || p.r <= 0) return
      ctx!.save()
      ctx!.globalAlpha = p.alpha
      ctx!.fillStyle = BLUE_LIGHT
      ctx!.beginPath()
      ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx!.fill()
      ctx!.restore()
    }

    function drawScene(time: number) {
      ctx!.save()
      
      const progress = journeyObj.progress
      
      const startX = bornObj.x
      const startY = bornObj.y
      
      const endX = startX + journeyObj.dx
      const endY = startY - journeyObj.lineLength
      
      const camX = endX + journeyObj.cameraSway
      const camY = endY
      const camZoom = journeyObj.cameraZoom

      // Kamera translate
      ctx!.translate(W / 2, H / 2)
      ctx!.scale(camZoom, camZoom)
      ctx!.translate(-camX, -camY)

      // Grid referensi
      ctx!.strokeStyle = 'rgba(79,195,247,0.07)'
      ctx!.lineWidth = 1
      for (let gx = -500; gx < 1500; gx += 80) {
        ctx!.beginPath()
        ctx!.moveTo(gx, -500)
        ctx!.lineTo(gx, 500)
        ctx!.stroke()
      }
      for (let gy = -500; gy < 500; gy += 80) {
        ctx!.beginPath()
        ctx!.moveTo(-500, gy)
        ctx!.lineTo(1500, gy)
        ctx!.stroke()
      }

      // ===== NODE BORN (Tengah) =====
      if (bornObj.alpha > 0) {
        ctx!.save()
        ctx!.globalAlpha = bornObj.alpha
        
        ctx!.beginPath()
        ctx!.arc(startX, startY, bornObj.r, 0, Math.PI * 2)
        ctx!.fillStyle = '#ffffff'
        ctx!.fill()

        const pulse = Math.abs(Math.sin(time * 3))
        const glowR = bornObj.r * 2 + (pulse * bornObj.pulseAmp)
        const glowAlpha = bornObj.glow * (0.4 + pulse * 0.3)
        
        ctx!.globalAlpha = glowAlpha
        ctx!.beginPath()
        ctx!.arc(startX, startY, glowR, 0, Math.PI * 2)
        ctx!.fillStyle = '#00aaff'
        ctx!.fill()

        if (bornObj.textAlpha > 0) {
          ctx!.globalAlpha = bornObj.textAlpha
          ctx!.font = '600 24px sans-serif'
          ctx!.fillStyle = '#ffffff'
          ctx!.textAlign = 'center'
          ctx!.letterSpacing = '8px'
          ctx!.fillText('BORN', startX, startY + 60)
        }
        ctx!.restore()
      }

      // ===== GARIS JOURNEY =====
      if (phase === 'journey') {
        ctx!.globalAlpha = 0.9
        ctx!.strokeStyle = '#4fc3f7'
        ctx!.lineWidth = 3
        ctx!.setLineDash([10, 6])
        ctx!.beginPath()
        ctx!.moveTo(startX, startY)
        ctx!.lineTo(endX, endY)
        ctx!.stroke()
        ctx!.setLineDash([])
        
        ctx!.strokeStyle = 'rgba(0,170,255,0.3)'
        ctx!.lineWidth = 8
        ctx!.beginPath()
        ctx!.moveTo(startX, startY)
        ctx!.lineTo(endX, endY)
        ctx!.stroke()

        // Spark
        ctx!.beginPath()
        ctx!.arc(endX, endY, 7, 0, Math.PI * 2)
        ctx!.fillStyle = '#ffffff'
        ctx!.fill()

        const sparkGlow = ctx!.createRadialGradient(endX, endY, 0, endX, endY, 35)
        sparkGlow.addColorStop(0, 'rgba(255,255,255,0.9)')
        sparkGlow.addColorStop(1, 'rgba(0,170,255,0)')
        ctx!.beginPath()
        ctx!.arc(endX, endY, 35, 0, Math.PI * 2)
        ctx!.fillStyle = sparkGlow
        ctx!.fill()

        // Target Node
        if (journeyObj.targetAlpha > 0) {
          ctx!.save()
          ctx!.globalAlpha = journeyObj.targetAlpha
          
          ctx!.translate(TARGET_X, TARGET_Y)
          ctx!.scale(journeyObj.targetScale, journeyObj.targetScale)
          
          ctx!.strokeStyle = 'rgba(79,195,247,0.5)'
          ctx!.lineWidth = 3
          ctx!.beginPath()
          ctx!.arc(0, 0, 100, 0, Math.PI * 2)
          ctx!.stroke()
          
          ctx!.strokeStyle = 'rgba(255,255,255,0.4)'
          ctx!.lineWidth = 2
          ctx!.beginPath()
          ctx!.arc(0, 0, 60, 0, Math.PI * 2)
          ctx!.stroke()
          
          ctx!.beginPath()
          ctx!.arc(0, 0, 25, 0, Math.PI * 2)
          ctx!.fillStyle = 'rgba(255,255,255,0.9)'
          ctx!.fill()
          
          const bigGlow = ctx!.createRadialGradient(0, 0, 0, 0, 0, 150)
          bigGlow.addColorStop(0, 'rgba(0,170,255,0.4)')
          bigGlow.addColorStop(1, 'rgba(0,170,255,0)')
          ctx!.beginPath()
          ctx!.arc(0, 0, 150, 0, Math.PI * 2)
          ctx!.fillStyle = bigGlow
          ctx!.fill()
          
          ctx!.restore()
        }
      }

      ctx!.restore()
    }

    function triggerSplash() {
      phase = 'impact'

      for (let i = 0; i < 4; i++) {
        ripples.push({
          x: CENTER_X, y: floorY,
          rx: 6 + i * 4, ry: 2.5 + i,
          vx: 5 + i * 5, vy: 1.8 + i * 0.6,
          alpha: 0.9 - i * 0.15
        })
      }

      for (let i = 0; i < 28; i++) {
        const angle = (Math.PI * 2 * i / 28) - Math.PI / 2
        const speed = 2 + Math.random() * 5
        splashParts.push({
          x:  CENTER_X + Math.cos(angle) * 6,
          y:  floorY,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed - 5 - Math.random() * 4,
          r:  1.5 + Math.random() * 4,
          alpha: 0.9
        })
      }

      for (let i = 0; i < 6; i++) {
        const ang = -Math.PI / 2 + (i - 2.5) * 0.38
        miniDrops.push({
          x:     CENTER_X + Math.cos(ang) * 10,
          y:     floorY,
          vx:    Math.cos(ang) * (1.5 + Math.random() * 2.5),
          vy:    -6 - Math.random() * 4,
          r:     3 + Math.random() * 4,
          alpha: 0.9
        })
      }

      gsap.to(mainDrop, { alpha: 0, duration: 0.3, ease: 'power2.in' })

      setTimeout(() => {
        phase = 'darkness'
        setTimeout(() => {
          phase = 'born'
          gsap.to(bornObj, {
            alpha: 1, glow: 1, r: 10,
            duration: 1.5, ease: 'power2.out'
          })
          gsap.to(bornObj, {
            textAlpha: 1,
            duration: 1.5, delay: 0.5, ease: 'power2.out'
          })

          setTimeout(() => {
            phase = 'journey'
            
            const tl = gsap.timeline()
            
            tl.to(journeyObj, {
              dx: TARGET_X - bornObj.x,
              lineLength: bornObj.y - TARGET_Y,
              cameraSway: 200,
              cameraZoom: 0.7,
              duration: 4.5,
              ease: 'power2.inOut'
            })
            
            tl.to(journeyObj, {
              targetAlpha: 1,
              targetScale: 1,
              duration: 1.5,
              ease: 'elastic.out(1, 0.4)'
            })
            
            tl.to(journeyObj, {
              cameraSway: 180,
              duration: 1,
              ease: 'power2.out'
            })

          }, 3000)
        }, 2000)
      }, 1500)
    }

    function startAnim() {
      ripples = []
      splashParts = []
      miniDrops = []
      mainDrop = { x: CENTER_X, y: -40, r: 16, alpha: 0 }
      bornObj = { x: CENTER_X, y: floorY, r: 0, alpha: 0, glow: 0, textAlpha: 0, zoom: 1, pulseAmp: 4 }
      journeyObj = { progress: 0, lineLength: 0, dx: 0, targetAlpha: 0, targetScale: 0, cameraSway: 0, cameraZoom: 1, ready: false }
      phase = 'falling'

      gsap.to(mainDrop, { alpha: 1, duration: 0.3 })
      gsap.to(mainDrop, {
        y: floorY - mainDrop.r * 0.5,
        duration: 1.3,
        ease: 'power2.in',
        onComplete: triggerSplash
      })
    }

    function loop() {
      reqId = requestAnimationFrame(loop)
      ctx!.clearRect(0, 0, W, H)
      
      const currentTime = (Date.now() - startTime) / 1000

      ripples.forEach(rp => {
        rp.rx += rp.vx
        rp.ry += rp.vy
        rp.alpha -= 0.010
        drawRipple(rp)
      })
      ripples = ripples.filter(r => r.alpha > 0)

      splashParts.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        p.vy += 0.22
        p.alpha -= 0.020
        p.r *= 0.985
        drawParticle(p)
      })
      splashParts = splashParts.filter(p => p.alpha > 0)

      miniDrops.forEach(d => {
        d.x += d.vx
        d.y += d.vy
        d.vy += 0.20
        if (d.y > floorY) d.alpha -= 0.06
        d.r *= 0.990
        drawDrop(d.x, d.y, d.r, d.alpha)
      })
      miniDrops = miniDrops.filter(d => d.alpha > 0)

      if (phase === 'falling' || phase === 'impact') {
        const fallProgress = Math.max(0, (mainDrop.y + 40) / (floorY + 40))
        const stretchY = 1 + fallProgress * 0.35
        const squishX = phase === 'impact' ? 0.6 : 1
        const squishY = phase === 'impact' ? 0.55 : stretchY
        drawDrop(mainDrop.x, mainDrop.y, mainDrop.r, mainDrop.alpha, squishX, squishY)
      }

      if (phase === 'born' || phase === 'journey') {
        drawScene(currentTime)
      }
    }

    loop()
    const startTimer = setTimeout(startAnim, 500)

    return () => {
      clearTimeout(startTimer)
      cancelAnimationFrame(reqId)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  return (
    <div className="w-full h-screen bg-[#0b1a2e] relative overflow-hidden">
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  )
}
