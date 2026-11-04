// Dibuja cada .bpmn con bpmn-js en Chrome sin ventana y guarda SVG y PNG a doble resolución.
// Uso: node dibujar.mjs <puerto> <carpeta con .bpmn>
import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
const [, , puerto, carpeta] = process.argv;
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
async function json(ruta) {
  for (let i = 0; i < 60; i++) { try { return await (await fetch(`http://127.0.0.1:${puerto}${ruta}`)).json(); } catch { await espera(500); } }
  throw new Error("Chrome no respondió");
}
function conectar(url) {
  const ws = new WebSocket(url); let id = 0; const pend = new Map(); const oyentes = new Set();
  ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { const { ok, ko } = pend.get(m.id); pend.delete(m.id); m.error ? ko(new Error(JSON.stringify(m.error))) : ok(m.result); } else if (m.method) oyentes.forEach((f) => f(m)); });
  const abierta = new Promise((r) => ws.addEventListener("open", r, { once: true }));
  const cdp = (method, params = {}) => new Promise((ok, ko) => { const i = ++id; pend.set(i, { ok, ko }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evento = (n) => new Promise((ok) => { const f = (m) => { if (m.method === n) { oyentes.delete(f); ok(m.params); } }; oyentes.add(f); });
  return { ws, abierta, cdp, evento };
}
const version = await json("/json/version");
const pagina = (await json("/json/list")).find((t) => t.type === "page");
const { ws, abierta, cdp, evento } = conectar(pagina.webSocketDebuggerUrl);
await abierta; await cdp("Page.enable");
const ir = async (url) => { const c = evento("Page.loadEventFired"); await cdp("Page.navigate", { url }); await c; };
const base = "file://" + resolve(".");
for (const archivo of readdirSync(carpeta).filter((f) => f.endsWith(".bpmn")).sort()) {
  const xml = readFileSync(join(carpeta, archivo), "utf8");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 2200, height: 1600, deviceScaleFactor: 1, mobile: false });
  await ir(base + "/vista.html");
  const { result, exceptionDetails } = await cdp("Runtime.evaluate", { expression: `cargar(${JSON.stringify(xml)})`, awaitPromise: true, returnByValue: true });
  if (exceptionDetails) { console.log("ERROR", archivo, JSON.stringify(exceptionDetails).slice(0, 600)); continue; }
  const { avisos, svg } = result.value;
  const nombre = archivo.replace(/\.bpmn$/, "");
  writeFileSync(join(carpeta, nombre + ".svg"), svg);
  const w = Math.ceil(parseFloat(svg.match(/width="([\d.]+)"/)[1])), h = Math.ceil(parseFloat(svg.match(/height="([\d.]+)"/)[1]));
  await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 2, mobile: false });
  await ir("file://" + resolve(join(carpeta, nombre + ".svg")));
  await espera(300);
  const { data } = await cdp("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(carpeta, nombre + ".png"), Buffer.from(data, "base64"));
  console.log(nombre, `${w}x${h}`, avisos.length ? "AVISOS: " + avisos.join(" | ") : "sin avisos");
}
ws.close();
const nav = conectar(version.webSocketDebuggerUrl); await nav.abierta; await nav.cdp("Browser.close").catch(() => {}); nav.ws.close();
