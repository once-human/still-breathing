// again.. studio: real-time three.js view of the simulated tee, matched to the Cycles render setup so the
// path-traced turntable frames can take over whenever the view lands on one of them.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";

const ASSET = "tee/fred/";
const STILLS = (tee) => `tee/fred-b-${tee}/turntable/`;
const ANGLES = Array.from({ length: 12 }, (_, i) => i * 30);
// reference = the exact light rig of render.py (Blender, Z-up) converted to three (Y-up): (x, y, z) -> (x, z, -y)
const REF = { lens: 85, ev: 0, keyTemp: 5600, keyAz: -38, fill: 3.6, rim: true };
const TARGET = new THREE.Vector3(0, 1.10, 0);
const CAM0 = new THREE.Vector3(0.18, 1.22, 2.55);
const SENSOR = 36;            // mm, Blender default; fits the taller side of a portrait frame

const stage = document.getElementById("stage");
const canvas = document.getElementById("gl");
const still = document.getElementById("still");
const modeEl = document.getElementById("mode");
const readout = document.getElementById("readout");
const loadstate = document.getElementById("loadstate");
const ticks = document.getElementById("ticks");

const state = { ...REF, tee: "black", yaw: 0, knit: true, dragging: false };
export const studio = { state, setTee: null };

// ---------- renderer ----------
// no WebGL (old phone, GPU blocked): fall back to flipping through the path-traced frames
let renderer = null;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" }); }
catch (e) { console.warn("WebGL unavailable, stills mode", e); }
const NOGL = !renderer;
if (NOGL) {
  canvas.remove(); loadstate.textContent = "no WebGL · rendered frames";
  renderer = { setClearColor() {}, render() {}, setPixelRatio() {}, setSize() {}, capabilities: { getMaxAnisotropy: () => 1 }, toneMappingExposure: 1 };
}
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;     // = Khronos PBR Neutral, the same view transform as the stills
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(24, 880 / 1120, 0.05, 30);
RectAreaLightUniformsLib.init();

// ---------- light rig ----------
function kelvin(t) {           // blackbody colour, Tanner Helland fit, returned linear 0..1
  t /= 100; let r, g, b;
  r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
  g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
  b = t >= 66 ? 255 : t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  const c = new THREE.Color().setRGB(...[r, g, b].map((v) => Math.min(255, Math.max(0, v)) / 255), THREE.SRGBColorSpace);
  return c;
}
const K_REF = kelvin(REF.keyTemp);
function area(w, h) { const l = new THREE.RectAreaLight(0xffffff, 1, w, h); scene.add(l); return l; }
const key = area(1.4, 1.8), fill = area(1.2, 1.6), rim = area(1.0, 1.0);
const KEY_TINT = new THREE.Color(1, 0.98, 0.95), FILL_TINT = new THREE.Color(0.95, 0.97, 1);
fill.position.set(1.9, 1.3, 1.4); rim.position.set(0.6, 2.4, -1.4);
scene.add(new THREE.HemisphereLight(0xf4f2ee, 0x6d6a64, 0.12));
const POWER = { black: 1.0, cream: 0.42 };     // render.py lowers the rig for the light tee so folds don't burn out
function applyLights() {
  const p = POWER[state.tee];
  const az = THREE.MathUtils.degToRad(state.keyAz), r = Math.hypot(1.5, 1.9);
  key.position.set(r * Math.sin(az), 2.1, r * Math.cos(az));
  const shift = kelvin(state.keyTemp); const k = KEY_TINT.clone();
  k.r *= shift.r / K_REF.r; k.g *= shift.g / K_REF.g; k.b *= shift.b / K_REF.b;
  key.color.copy(k); key.intensity = 28 * p;          // calibrated by eye against the Cycles frames
  fill.color.copy(FILL_TINT); fill.intensity = (28 * p) / state.fill;
  rim.intensity = state.rim ? 17 * p : 0;
  for (const l of [key, fill, rim]) l.lookAt(0, 1.12, 0);
}

// ---------- camera (lens + dolly keeps the framing, like stepping back with a longer lens) ----------
function applyCamera() {
  camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(SENSOR / 2 / state.lens));
  const dir = CAM0.clone().sub(TARGET); camera.position.copy(TARGET).addScaledVector(dir, state.lens / 85);
  camera.lookAt(TARGET); camera.updateProjectionMatrix();
  renderer.toneMappingExposure = Math.pow(2, state.ev);
  // 10 cm scale bar at the garment plane
  const d = camera.position.distanceTo(TARGET), viewH = 2 * d * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  stage.style.setProperty("--tencm", `${(0.10 / viewH) * stage.clientHeight}px`);
}

// ---------- the tee ----------
const tex = new THREE.TextureLoader();
function load(url, srgb) {
  return new Promise((res, rej) => tex.load(ASSET + url, (t) => {
    t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy(); res(t);
  }, undefined, rej));
}
const maps = {};
async function teeMaps(tee) {
  if (!maps[tee]) maps[tee] = Promise.all([load(`color-${tee}.jpg`, true), load(`orm-${tee}.png`, false)]);
  return maps[tee];
}
const FABRIC = { black: 0x151515, cream: 0xfffae7 };
let outer, inner, tris = 0;
const knitU = { knitMap: { value: null }, knitRepeat: { value: new THREE.Vector2(200 / 1.14, 76 / 1.11) }, knitScale: { value: 0.55 } };
function makeOuter(normal, knit) {
  const m = new THREE.MeshPhysicalMaterial({
    normalMap: normal, normalScale: new THREE.Vector2(1, 1), roughness: 1, metalness: 0,
    aoMapIntensity: 0.85, sheen: 0.35, sheenRoughness: 0.3, sheenColor: new THREE.Color(1, 1, 1), specularIntensity: 0.5,
  });
  knitU.knitMap.value = knit; knit.wrapS = knit.wrapT = THREE.RepeatWrapping;
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, knitU);
    sh.fragmentShader = "uniform sampler2D knitMap; uniform vec2 knitRepeat; uniform float knitScale;\n" + sh.fragmentShader
      // jersey loops on top of the construction normals (stitches, rib, hems): whiteout blend
      .replace("#include <normal_fragment_maps>", `
        vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0; mapN.xy *= normalScale;
        vec3 kN = texture2D( knitMap, vNormalMapUv * knitRepeat ).xyz * 2.0 - 1.0; kN.xy *= knitScale;
        mapN = normalize( vec3( mapN.xy + kN.xy, mapN.z * kN.z ) );
        normal = normalize( tbn * mapN );`)
      // cotton fuzz (sheen) only where there is no ink; over the print it reads as a white haze
      .replace("#include <lights_physical_fragment>", `#include <lights_physical_fragment>
        material.sheenColor *= 1.0 - texture2D( roughnessMap, vRoughnessMapUv ).b;`);
  };
  return m;
}
async function setTee(t) {
  state.tee = t;
  if (outer) {
    const [color, orm] = await teeMaps(t);
    outer.map = color; outer.roughnessMap = orm; outer.aoMap = orm; outer.needsUpdate = true;
    inner.color.setHex(FABRIC[t]).convertSRGBToLinear();
  }
  applyLights(); preloadStills(); markDirty();
}
studio.setTee = setTee;

const pivot = new THREE.Group(); scene.add(pivot);
(async () => {
  if (NOGL) return;
  try {
    const draco = new DRACOLoader().setDecoderPath("https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/");
    const gl = new GLTFLoader().setDRACOLoader(draco);
    const [gltf, normal, knit, [color, orm]] = await Promise.all([
      gl.loadAsync(ASSET + "tee.glb"), load("normal.png", false), load("knit-normal.png", false), teeMaps(state.tee)]);
    outer = makeOuter(normal, knit); outer.map = color; outer.roughnessMap = orm; outer.aoMap = orm;
    inner = new THREE.MeshStandardMaterial({ roughness: 0.95, metalness: 0 }); inner.color.setHex(FABRIC[state.tee]).convertSRGBToLinear();
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      o.material = /inner/i.test(o.material?.name || "") ? inner : outer;
      tris += o.geometry.index ? o.geometry.index.count / 3 : o.geometry.attributes.position.count / 3;
    });
    pivot.add(gltf.scene);
    loadstate.textContent = `${Math.round(tris).toLocaleString("en-IN")} tris`;
    markDirty();
  } catch (e) { loadstate.textContent = "mesh failed to load"; console.error(e); }
})();

// ---------- path-traced turntable frames ----------
const stills = {};
function preloadStills() {
  ticks.innerHTML = "";
  for (const a of ANGLES) {
    const i = document.createElement("i"); ticks.appendChild(i);
    const k = `${state.tee}:${a}`;
    if (!stills[k]) { const im = new Image(); im.src = `${STILLS(state.tee)}a${a}.png`; stills[k] = im; im.onload = () => { i.classList.add("ready"); updateStill(); }; }
    else if (stills[k].complete && stills[k].naturalWidth) i.classList.add("ready");
  }
}
const atReference = () => state.lens === REF.lens && state.ev === REF.ev && state.keyTemp === REF.keyTemp && state.keyAz === REF.keyAz && state.fill === REF.fill && state.rim === REF.rim;
function updateStill() {
  const yaw = ((state.yaw % 360) + 360) % 360, near = Math.round(yaw / 30) * 30 % 360;
  [...ticks.children].forEach((t, i) => t.classList.toggle("at", ANGLES[i] === near && Math.abs(yaw - near) < 0.5 || (near === 0 && Math.abs(yaw - 360) < 0.5 && i === 0)));
  const im = stills[`${state.tee}:${near}`];
  const ok = NOGL ? !!(im && im.complete && im.naturalWidth)
    : !state.dragging && !spinning && atReference() && im && im.complete && im.naturalWidth && (Math.abs(yaw - near) < 0.5 || Math.abs(yaw - 360) < 0.5);
  if (ok) { if (still.src !== im.src) still.src = im.src; still.classList.add("show"); }
  else still.classList.remove("show");
  modeEl.classList.toggle("traced", !!ok);
  modeEl.innerHTML = ok ? "<i></i><b>PATH-TRACED</b> Cycles · 64 spp" : NOGL ? "<i></i><b>RENDERING</b> frames not ready" : "<i></i><b>REAL-TIME</b> WebGL2";
}

// ---------- turntable interaction: drag, inertia, settle on the nearest rendered angle ----------
let vel = 0, lastX = 0, lastT = 0, spinning = false, goal = null;
stage.addEventListener("pointerdown", (e) => { state.dragging = true; stage.classList.add("drag"); stage.setPointerCapture(e.pointerId); lastX = e.clientX; lastT = performance.now(); vel = 0; goal = null; updateStill(); });
stage.addEventListener("pointermove", (e) => {
  if (!state.dragging) return;
  const now = performance.now(), dx = e.clientX - lastX; state.yaw += dx * 0.45;
  vel = (dx * 0.45) / Math.max(1, now - lastT) * 16; lastX = e.clientX; lastT = now; markDirty();
});
function release() {
  if (!state.dragging) return; state.dragging = false; stage.classList.remove("drag");
  spinning = true; goal = Math.round((state.yaw + vel * 8) / 30) * 30; markDirty();
}
stage.addEventListener("pointerup", release); stage.addEventListener("pointercancel", release);
export function turnTo(deg) {   // shortest way round
  const cur = state.yaw, d = ((deg - cur) % 360 + 540) % 360 - 180; goal = cur + d; spinning = true; markDirty();
}
document.querySelectorAll(".views button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".views button").forEach((x) => x.classList.toggle("on", x === b)); turnTo(+b.dataset.yaw);
}));
stage.tabIndex = 0;
stage.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") turnTo((goal ?? state.yaw) - 30); if (e.key === "ArrowRight") turnTo((goal ?? state.yaw) + 30); });

// ---------- studio panel ----------
const $ = (id) => document.getElementById(id);
$("studioToggle").addEventListener("click", () => { const p = $("studioPanel"); p.hidden = !p.hidden; $("studioToggle").setAttribute("aria-expanded", String(!p.hidden)); });
function syncPanel() {
  $("lens").value = state.lens; $("lensOut").textContent = `${state.lens} mm`;
  document.querySelectorAll('[data-ctl="lens"] button').forEach((b) => b.classList.toggle("on", +b.textContent === state.lens));
  $("ev").value = state.ev; $("evOut").textContent = `${state.ev > 0 ? "+" : state.ev < 0 ? "−" : "±"}${Math.abs(state.ev).toFixed(1)} EV`;
  $("keyTemp").value = state.keyTemp; $("keyAz").value = state.keyAz; $("keyOut").textContent = `${state.keyTemp} K · ${Math.abs(state.keyAz)}° ${state.keyAz < 0 ? "L" : "R"}`;
  $("fill").value = state.fill; $("fillOut").textContent = `${(+state.fill).toFixed(1)} : 1`;
  $("rim").checked = state.rim; $("knit").checked = state.knit;
}
const onInput = (id, key, f = Number) => $(id).addEventListener("input", (e) => { state[key] = f(e.target.value); syncPanel(); applyCamera(); applyLights(); updateStill(); markDirty(); });
onInput("lens", "lens"); onInput("ev", "ev"); onInput("keyTemp", "keyTemp"); onInput("keyAz", "keyAz"); onInput("fill", "fill");
document.querySelectorAll('[data-ctl="lens"] button').forEach((b) => b.addEventListener("click", () => { state.lens = +b.textContent; syncPanel(); applyCamera(); updateStill(); markDirty(); }));
$("rim").addEventListener("change", (e) => { state.rim = e.target.checked; applyLights(); updateStill(); markDirty(); });
$("knit").addEventListener("change", (e) => { state.knit = e.target.checked; knitU.knitScale.value = state.knit ? 0.55 : 0; markDirty(); });
document.querySelectorAll("#papers button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#papers button").forEach((x) => x.classList.toggle("on", x === b));
  stage.style.setProperty("--backdrop", b.dataset.paper);
  const c = new THREE.Color(b.dataset.paper); stage.classList.toggle("dark", c.r + c.g + c.b < 1.2);
}));
$("reset").addEventListener("click", () => { Object.assign(state, { ...REF }); syncPanel(); applyCamera(); applyLights(); updateStill(); markDirty(); });

// ---------- loop: renders only when something changed ----------
let dirty = true, frames = 0, fpsT = performance.now(), fps = 0;
function markDirty() { dirty = true; }
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(w, h, false); applyCamera(); markDirty();
}
new ResizeObserver(resize).observe(stage);
function tick(now) {
  if (!state.dragging && spinning) {
    if (goal === null) goal = Math.round(state.yaw / 30) * 30;
    const d = goal - state.yaw; state.yaw += d * 0.14;
    if (Math.abs(d) < 0.05) { state.yaw = goal; spinning = false; goal = null; }
    dirty = true;
  }
  if (dirty) {
    pivot.rotation.y = THREE.MathUtils.degToRad(state.yaw);
    renderer.render(scene, camera); dirty = false; frames++; updateStill();
    const y = ((Math.round(state.yaw) % 360) + 360) % 360;
    readout.textContent = `${state.lens} mm · f/5.6 · 1/125 s · ISO 100 · key ${state.keyTemp} K · yaw ${String(y).padStart(3, "0")}°${fps ? ` · ${fps} fps` : ""}`;
  }
  if (now - fpsT > 1000) { fps = frames > 2 ? frames : fps; frames = 0; fpsT = now; }
  requestAnimationFrame(tick);
}
syncPanel(); applyLights(); applyCamera(); preloadStills(); requestAnimationFrame(tick);