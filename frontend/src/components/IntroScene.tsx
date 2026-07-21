/**
 * IntroScene — Three.js water-drop + graph-node animation.
 * Ported from original App.tsx. onReady fires when the
 * animation completes so Landing can fade-in the hero overlay.
 */
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { gsap } from 'gsap'

const NODES = [
  { id: 39, x: -4,  y: 1.5,  z: -6  },
  { id: 30, x:  6,  y: -0.5, z: -5  },
  { id: 58, x:  8,  y: 1.5,  z:  2  },
  { id: 61, x: -2,  y: 0.5,  z:  8  },
  { id: 62, x: -7,  y: -0.5, z:  7  },
]
const EDGES = [
  { from: 39, to: 30 },
  { from: 30, to: 58 },
  { from: 58, to: 61 },
  { from: 58, to: 62 },
]

const ACCENT = 0x2dd4bf  // teal accent — matches --accent

interface Props {
  onReady?: () => void
  ambient?: boolean  // if true, skip animation, go straight to ambient state
}

export default function IntroScene({ onReady, ambient = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const container = containerRef.current

    const W = window.innerWidth, H = window.innerHeight
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#080e18')

    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 200)
    camera.position.set(0, 0, ambient ? 24 : 14)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    container.appendChild(renderer.domElement)

    // Lights
    scene.add(new THREE.AmbientLight(0x203040, 2))
    const dl = new THREE.DirectionalLight(0xffffff, 1.5)
    dl.position.set(10, 20, 10)
    scene.add(dl)
    const fl = new THREE.DirectionalLight(ACCENT, 0.5)
    fl.position.set(-10, 5, -10)
    scene.add(fl)

    // ── Water drop ────────────────────────────────────────────────────────────
    const dropMat = new THREE.MeshPhongMaterial({ color: 0xaaddff, emissive: 0x00aabb, transparent: true, opacity: ambient ? 0 : 1 })
    const drop = new THREE.Mesh(new THREE.SphereGeometry(0.4, 32, 32), dropMat)
    drop.position.set(0, 8, 0)
    scene.add(drop)

    const ringMat = new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: 0, side: THREE.DoubleSide })
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.3, 0.5, 32), ringMat)
    ring.rotation.x = -Math.PI / 2
    ring.scale.set(0, 0, 0)
    scene.add(ring)

    const SPLASH = 30
    const splashMesh = new THREE.InstancedMesh(
      new THREE.SphereGeometry(0.06, 8, 8),
      new THREE.MeshPhongMaterial({ color: 0x90e4d4, transparent: true, opacity: 0 }),
      SPLASH
    )
    splashMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
    scene.add(splashMesh)

    const splashVel = Array.from({ length: SPLASH }, () => {
      const a = Math.random() * Math.PI * 2
      const s = 1 + Math.random() * 3
      return { vx: Math.cos(a) * s * 0.5, vy: 2 + Math.random() * 3, vz: Math.sin(a) * s * 0.5, sc: 0.3 + Math.random() * 0.7 }
    })
    const dummy = new THREE.Object3D()
    let splashT = 0, splashOn = false

    // ── BORN core ─────────────────────────────────────────────────────────────
    const coreMat = new THREE.MeshPhongMaterial({ color: 0xffffff, emissive: 0x00ccbb, emissiveIntensity: 0.6, transparent: true, opacity: ambient ? 1 : 0 })
    const core = new THREE.Mesh(new THREE.SphereGeometry(0.5, 24, 24), coreMat)
    scene.add(core)

    const glowMat = new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: ambient ? 0.4 : 0, blending: THREE.AdditiveBlending })
    const glow = new THREE.Mesh(new THREE.SphereGeometry(0.85, 24, 24), glowMat)
    scene.add(glow)

    // ── Graph nodes ───────────────────────────────────────────────────────────
    const gNodes = NODES.map(d => {
      const mat = new THREE.MeshPhongMaterial({ color: ACCENT, emissive: 0x008877, emissiveIntensity: 0.3, transparent: true, opacity: ambient ? 1 : 0 })
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.5, 20, 20), mat)
      m.position.set(d.x, d.y, d.z)
      scene.add(m)

      const gm = new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: ambient ? 0.25 : 0, blending: THREE.AdditiveBlending })
      const g = new THREE.Mesh(new THREE.SphereGeometry(0.85, 20, 20), gm)
      g.position.copy(m.position)
      scene.add(g)
      return { mesh: m, glow: g, data: d }
    })

    // ── Graph edges ───────────────────────────────────────────────────────────
    const gEdges = EDGES.map(e => {
      const f = NODES.find(n => n.id === e.from)!
      const t = NODES.find(n => n.id === e.to)!
      const s = new THREE.Vector3(f.x, f.y, f.z)
      const en = new THREE.Vector3(t.x, t.y, t.z)
      const d = new THREE.Vector3().subVectors(en, s)
      const len = d.length()
      d.normalize()
      const mid = new THREE.Vector3().addVectors(s, en).multiplyScalar(0.5)
      const em = new THREE.MeshPhongMaterial({ color: ACCENT, emissive: 0x007766, emissiveIntensity: 0.4, transparent: true, opacity: ambient ? 0.5 : 0 })
      const m = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, len, 6), em)
      m.position.copy(mid)
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d)
      scene.add(m)
      return m
    })

    // ── GSAP timeline (skip if ambient) ───────────────────────────────────────
    if (!ambient) {
      const tl = gsap.timeline({ onComplete: () => onReady?.() })

      tl.to(drop.position, { y: 0, duration: 1.2, ease: 'power2.in', onUpdate: () => {
        const p = 1 - drop.position.y / 8
        drop.scale.set(1 - p * 0.3, 1 + p * 0.6, 1 - p * 0.3)
      }})
      tl.to(drop.scale, { x: 3, y: 0.05, z: 3, duration: 0.2 }, 'splash')
      tl.to(dropMat, { opacity: 0, duration: 0.15 }, 'splash')
      tl.to(ring.scale, { x: 5, z: 5, duration: 0.6 }, 'splash')
      tl.to(ringMat, { opacity: 0.5, duration: 0.3 }, 'splash')
      tl.to(ringMat, { opacity: 0, duration: 0.4 }, 'splash+=0.3')
      splashMesh.material.opacity = 1
      tl.call(() => { splashOn = true; splashT = 0 })

      tl.to({}, { duration: 1.2 })
      tl.to(coreMat, { opacity: 1, duration: 0.9 })
      tl.to(glowMat, { opacity: 0.5, duration: 0.7 }, '-=0.3')
      tl.to(glowMat, { opacity: 0.8, duration: 0.3 })
      tl.to(glowMat, { opacity: 0.3, duration: 0.3 })
      tl.to(glowMat, { opacity: 0.6, duration: 0.3 })
      tl.to(camera.position, { z: 18, duration: 1.8, ease: 'power2.inOut' })

      const [n1, n2, n3, n4, n5] = gNodes
      const [e1, e2, e3, e4] = gEdges

      tl.to(n1.mesh.material, { opacity: 1, duration: 0.7 })
      tl.to(n1.glow.material, { opacity: 0.3, duration: 0.4 }, '-=0.3')
      tl.to(e1.material,      { opacity: 0.5, duration: 0.8 }, '-=0.2')
      tl.to(n2.mesh.material, { opacity: 1, duration: 0.7 }, '-=0.4')
      tl.to(n2.glow.material, { opacity: 0.3, duration: 0.4 }, '-=0.3')
      tl.to(camera.position,  { x: 3, duration: 2.5, ease: 'power1.inOut' }, '-=0.8')
      tl.to(e2.material,      { opacity: 0.5, duration: 0.8 })
      tl.to(n3.mesh.material, { opacity: 1, duration: 0.7 }, '-=0.4')
      tl.to(n3.glow.material, { opacity: 0.3, duration: 0.4 }, '-=0.3')
      tl.to(camera.position,  { x: -2, z: 20, duration: 2.5, ease: 'power1.inOut' }, '-=0.8')
      tl.to([e3.material, e4.material], { opacity: 0.5, duration: 0.8 })
      tl.to([n4.mesh.material, n5.mesh.material], { opacity: 1, duration: 0.7 }, '-=0.4')
      tl.to([n4.glow.material, n5.glow.material], { opacity: 0.25, duration: 0.4 }, '-=0.3')
      tl.to(camera.position, { x: 0, z: 24, duration: 3, ease: 'power2.inOut' })
    }

    // ── Render loop ───────────────────────────────────────────────────────────
    const clock = new THREE.Clock()
    let reqId: number
    function animate() {
      reqId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()

      camera.lookAt(0, 0, 0)

      if (splashOn) {
        splashT += 0.016
        if (splashT < 1.2) {
          for (let i = 0; i < SPLASH; i++) {
            const v = splashVel[i]
            dummy.position.set(v.vx * splashT, v.vy * splashT - 6 * splashT * splashT, v.vz * splashT)
            const s = Math.max(0, v.sc * (1 - splashT / 1.2))
            dummy.scale.set(s, s, s)
            dummy.updateMatrix()
            splashMesh.setMatrixAt(i, dummy.matrix)
          }
          splashMesh.instanceMatrix.needsUpdate = true
          splashMesh.material.opacity = Math.max(0, 1 - splashT * 1.2)
        } else {
          splashOn = false
          splashMesh.material.opacity = 0
        }
      }

      if (coreMat.opacity > 0.5) glowMat.opacity = 0.25 + Math.abs(Math.sin(t * 2.2)) * 0.35
      gNodes.forEach(s => {
        if (s.mesh.material.opacity > 0.5)
          s.glow.material.opacity = 0.1 + Math.abs(Math.sin(t * 1.8 + s.data.id * 0.4)) * 0.2
      })

      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(reqId)
      window.removeEventListener('resize', onResize)
      gsap.killTweensOf([drop.position, drop.scale, dropMat, ringMat, ring.scale,
        coreMat, glowMat, camera.position,
        ...gNodes.map(n => n.mesh.material),
        ...gNodes.map(n => n.glow.material),
        ...gEdges.map(e => e.material)])
      renderer.dispose()
      container.innerHTML = ''
    }
  }, [ambient, onReady])

  return <div ref={containerRef} className="w-full h-full" />
}
