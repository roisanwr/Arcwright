import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { gsap } from 'gsap'

const NODES = [
  { id: 39, label: 'Node 1',  x: -4,  y: 1.5,  z: -6,  color: '#4fc3f7' },
  { id: 30, label: 'Node 2',  x: 6,   y: -0.5,  z: -5,  color: '#4fc3f7' },
  { id: 58, label: 'Node 3',  x: 8,   y: 1.5,   z: 2,   color: '#4fc3f7' },
  { id: 61, label: 'Node 4',  x: -2,  y: 0.5,   z: 8,   color: '#4fc3f7' },
  { id: 62, label: 'Node 5',  x: -7,  y: -0.5,  z: 7,   color: '#4fc3f7' },
]

const EDGES = [
  { from: 39, to: 30 },
  { from: 30, to: 58 },
  { from: 58, to: 61 },
  { from: 58, to: 62 },
]

export default function App() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const W = window.innerWidth, H = window.innerHeight
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0b1a2e')

    // Kamera dari tengah, lurus ke depan (tidak ke bawah)
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 200)
    camera.position.set(0, 0, 14)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    containerRef.current.appendChild(renderer.domElement)

    // Lights
    scene.add(new THREE.AmbientLight(0x404060))
    const dl = new THREE.DirectionalLight(0xffffff, 2)
    dl.position.set(10, 20, 10)
    scene.add(dl)
    const fl = new THREE.DirectionalLight(0x4fc3f7, 0.4)
    fl.position.set(-10, 5, -10)
    scene.add(fl)

    // Tetesan Air 3D
    const dropMat = new THREE.MeshPhongMaterial({
      color: 0xaaddff, emissive: 0x0288d1,
      transparent: true, opacity: 1,
    })
    const drop = new THREE.Mesh(new THREE.SphereGeometry(0.4, 32, 32), dropMat)
    drop.position.set(0, 8, 0)
    scene.add(drop)

    // Ring ripple
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x4fc3f7, transparent: true, opacity: 0, side: THREE.DoubleSide,
    })
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.3, 0.5, 32), ringMat)
    ring.rotation.x = -Math.PI / 2
    ring.position.set(0, 0, 0)
    ring.scale.set(0, 0, 0)
    scene.add(ring)

    // Partikel splash
    const SPLASH_COUNT = 30
    const splashMesh = new THREE.InstancedMesh(
      new THREE.SphereGeometry(0.06, 8, 8),
      new THREE.MeshPhongMaterial({ color: 0xb3e5fc, transparent: true, opacity: 0 }),
      SPLASH_COUNT
    )
    splashMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
    scene.add(splashMesh)

    const splashVel = []
    for (let i = 0; i < SPLASH_COUNT; i++) {
      const a = Math.random() * Math.PI * 2
      const s = 1 + Math.random() * 3
      splashVel.push({ vx: Math.cos(a) * s * 0.5, vy: 2 + Math.random() * 3, vz: Math.sin(a) * s * 0.5, sc: 0.3 + Math.random() * 0.7 })
    }
    const dummy = new THREE.Object3D()

    // BORN Core
    const coreMat = new THREE.MeshPhongMaterial({
      color: 0xffffff, emissive: 0x00aaff, emissiveIntensity: 0.5,
      transparent: true, opacity: 0,
    })
    const core = new THREE.Mesh(new THREE.SphereGeometry(0.5, 24, 24), coreMat)
    core.position.set(0, 0, 0)
    scene.add(core)

    const glowMat = new THREE.MeshBasicMaterial({
      color: 0x00aaff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending,
    })
    const glow = new THREE.Mesh(new THREE.SphereGeometry(0.8, 24, 24), glowMat)
    glow.position.set(0, 0, 0)
    scene.add(glow)

    // Graph Nodes (di sekitar pusat, height rata-rata 0)
    const gNodes = NODES.map(d => {
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.5, 20, 20),
        new THREE.MeshPhongMaterial({ color: d.color, emissive: 0x0288d1,
          emissiveIntensity: 0.2, transparent: true, opacity: 0 }))
      m.position.set(d.x, d.y, d.z)
      m.userData = d
      scene.add(m)

      const g = new THREE.Mesh(new THREE.SphereGeometry(0.8, 20, 20),
        new THREE.MeshBasicMaterial({ color: 0x00aaff, transparent: true, opacity: 0,
          blending: THREE.AdditiveBlending }))
      g.position.copy(m.position)
      scene.add(g)
      return { mesh: m, glow: g, data: d }
    })

    // Graph Edges
    const gEdges = EDGES.map(e => {
      const f = NODES.find(n => n.id === e.from), t = NODES.find(n => n.id === e.to)
      if (!f || !t) return null
      const s = new THREE.Vector3(f.x, f.y, f.z), en = new THREE.Vector3(t.x, t.y, t.z)
      const d = new THREE.Vector3().subVectors(en, s), len = d.length()
      d.normalize()
      const mid = new THREE.Vector3().addVectors(s, en).multiplyScalar(0.5)
      const m = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, len, 6, 1),
        new THREE.MeshPhongMaterial({ color: 0x4fc3f7, emissive: 0x0288d1,
          emissiveIntensity: 0.3, transparent: true, opacity: 0 }))
      m.position.copy(mid)
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d)
      scene.add(m)
      return m
    }).filter(Boolean)

    // GSAP Timeline
    const tl = gsap.timeline()

    // ACT 1: Air jatuh
    tl.to(drop.position, { y: 0, duration: 1.2, ease: 'power2.in',
      onUpdate: () => {
        const p = 1 - (drop.position.y / 8)
        drop.scale.set(1 - p * 0.3, 1 + p * 0.6, 1 - p * 0.3)
      }
    })

    // Splash
    tl.to(drop.scale, { x: 3, y: 0.05, z: 3, duration: 0.2 }, 'splash')
    tl.to(dropMat, { opacity: 0, duration: 0.15 }, 'splash')
    tl.to(ring.scale, { x: 5, z: 5, duration: 0.6 }, 'splash')
    tl.to(ringMat, { opacity: 0.5, duration: 0.3 }, 'splash')
    tl.to(ringMat, { opacity: 0, duration: 0.4 }, 'splash+=0.3')
    splashMesh.material.opacity = 1

    let splashT = 0, splashOn = false
    tl.call(() => { splashOn = true; splashT = 0 })

    // Dark pause
    tl.to({}, { duration: 1.5 })

    // BORN muncul
    tl.to(coreMat, { opacity: 1, duration: 1 })
    tl.to(glowMat, { opacity: 0.5, duration: 0.8 }, '-=0.3')

    // Kedip
    tl.to(glowMat, { opacity: 0.8, duration: 0.4 })
    tl.to(glowMat, { opacity: 0.3, duration: 0.4 })
    tl.to(glowMat, { opacity: 0.7, duration: 0.4 })
    tl.to(glowMat, { opacity: 0.4, duration: 0.4 })

    // Zoom out kamera tetap lurus
    tl.to(camera.position, { z: 18, duration: 2, ease: 'power2.inOut' })

    // Node 39 + edge
    const n1 = gNodes[0], e1 = gEdges[0]
    tl.to(n1.mesh.material, { opacity: 1, duration: 0.8 })
    tl.to(n1.glow.material, { opacity: 0.3, duration: 0.4 }, '-=0.4')
    tl.to(e1.material, { opacity: 0.6, duration: 1 }, '-=0.3')

    // Node 30
    const n2 = gNodes[1]
    tl.to(n2.mesh.material, { opacity: 1, duration: 0.8 }, '-=0.5')
    tl.to(n2.glow.material, { opacity: 0.3, duration: 0.4 }, '-=0.4')

    // Kamera rotasi pelan di sumbu Y (tetap dari tengah)
    tl.to(camera.position, { x: 3, duration: 3, ease: 'power1.inOut' }, '-=1')

    // Node 58 + edge
    const n3 = gNodes[2], e2 = gEdges[1]
    tl.to(e2.material, { opacity: 0.6, duration: 1 })
    tl.to(n3.mesh.material, { opacity: 1, duration: 0.8 }, '-=0.5')
    tl.to(n3.glow.material, { opacity: 0.3, duration: 0.4 }, '-=0.4')

    tl.to(camera.position, { x: -2, z: 20, duration: 3, ease: 'power1.inOut' }, '-=1')

    // Node 61 & 62 bareng
    const n4 = gNodes[3], n5 = gNodes[4], e3 = gEdges[2], e4 = gEdges[3]
    tl.to([e3.material, e4.material], { opacity: 0.6, duration: 1 })
    tl.to([n4.mesh.material, n5.mesh.material], { opacity: 1, duration: 0.8 }, '-=0.5')
    tl.to([n4.glow.material, n5.glow.material], { opacity: 0.3, duration: 0.4 }, '-=0.4')

    // Final
    tl.to(camera.position, { x: 0, z: 24, duration: 4, ease: 'power2.inOut' })

    // ── Render ──
    const clock = new THREE.Clock()
    function animate() {
      reqId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()
      const dt = clock.getDelta()

      camera.lookAt(0, 0, 0)

      // Splash particles
      if (splashOn) {
        splashT += 0.016
        if (splashT < 1.2) {
          for (let i = 0; i < SPLASH_COUNT; i++) {
            const v = splashVel[i]
            dummy.position.set(v.vx * splashT, (v.vy * splashT) - (0.5 * 12 * splashT * splashT), v.vz * splashT)
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

      // Kedip BORN
      if (coreMat.opacity > 0.5) glowMat.opacity = 0.3 + Math.abs(Math.sin(t * 2.5)) * 0.4

      // Kedip node
      gNodes.forEach(s => {
        if (s.mesh.material.opacity > 0.5)
          s.glow.material.opacity = 0.15 + Math.abs(Math.sin(t * 2 + s.data.id)) * 0.25
      })

      renderer.render(scene, camera)
    }
    let reqId = requestAnimationFrame(animate)

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(reqId)
      window.removeEventListener('resize', onResize)
      if (containerRef.current) containerRef.current.innerHTML = ''
    }
  }, [])

  return (
    <div className="w-full h-screen bg-[#0b1a2e] overflow-hidden relative">
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 text-center pointer-events-none z-10">
        <h1 className="text-2xl font-bold text-white/80 uppercase tracking-[0.3em]">Arwright</h1>
        <p className="text-sm text-[#4fc3f7]/60 tracking-[0.2em] mt-1">The Journey of Connected Thoughts</p>
      </div>
    </div>
  )
}
