// Arma un archivo BPMN 2.0 (modelo + coordenadas) a partir de una descripción en cuadrícula.
// Las piscinas van una debajo de otra; cada elemento se ubica por columna y por fila de su carril,
// y los flujos se trazan con tramos rectos (horizontal, vertical o en L).

const S = 160; // separación entre columnas
const CX0 = 150; // centro de la primera columna
const TAREA = { w: 130, h: 90 };
const EVENTO = 36;
const COMPUERTA = 50;

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/\n/g, "&#10;");
const cx = (col) => CX0 + col * S;

function construir(spec) {
  const anchoPool = cx(spec.columnas - 1) + TAREA.w / 2 + 40;
  // ---------- piscinas y carriles ----------
  let y = 0;
  const pools = {}, lanes = {};
  for (const p of spec.pools) {
    const alto = p.lanes ? p.lanes.reduce((s, l) => s + l.alto, 0) : p.alto;
    pools[p.id] = { ...p, x: 0, y, w: anchoPool, h: alto };
    if (p.lanes) {
      let ly = y;
      for (const l of p.lanes) {
        lanes[l.id] = { ...l, pool: p.id, x: 30, y: ly, w: anchoPool - 30, h: l.alto, nodos: [] };
        ly += l.alto;
      }
    }
    y += alto + (p.separacion ?? 70);
  }
  const filaY = (n) => {
    const cont = n.lane ? lanes[n.lane] : pools[n.pool];
    const filas = cont.filas || { m: cont.h / 2 };
    return cont.y + filas[n.fila || "m"];
  };

  // ---------- elementos ----------
  const nodos = {};
  for (const n of spec.nodos) {
    if (n.tipo === "borde") continue;
    const c = cx(n.col) + (n.dx || 0), m = filaY(n);
    const t = ["inicio", "fin", "captura"].includes(n.tipo) ? EVENTO : n.tipo === "xor" ? COMPUERTA : null;
    const w = t || TAREA.w, h = t || TAREA.h;
    nodos[n.id] = { ...n, cx: c, cy: m, x: c - w / 2, y: m - h / 2, w, h, entra: [], sale: [] };
    if (n.lane) lanes[n.lane].nodos.push(n.id);
  }
  for (const n of spec.nodos.filter((n) => n.tipo === "borde")) {
    const t = nodos[n.unido];
    const c = t.cx + (n.dx || 0), m = n.lado === "arriba" ? t.y : t.y + t.h;
    nodos[n.id] = { ...n, cx: c, cy: m, x: c - EVENTO / 2, y: m - EVENTO / 2, w: EVENTO, h: EVENTO, entra: [], sale: [], lane: t.lane, pool: t.pool };
    if (t.lane) lanes[t.lane].nodos.push(n.id);
  }
  const procesoDe = (id) => {
    const n = nodos[id];
    return pools[n.lane ? lanes[n.lane].pool : n.pool].proceso;
  };

  // ---------- flujos de secuencia ----------
  const lados = {
    der: (n) => [n.x + n.w, n.cy], izq: (n) => [n.x, n.cy], arr: (n) => [n.cx, n.y], aba: (n) => [n.cx, n.y + n.h],
  };
  const flujos = spec.flujos.map((f, i) => {
    const a = nodos[f.de], b = nodos[f.a];
    let pts;
    const ruta = f.ruta || (Math.abs(a.cy - b.cy) < 1 ? "h" : Math.abs(a.cx - b.cx) < 1 ? "v" : "vh");
    if (a.tipo === "borde") {
      const desde = a.lado === "arriba" ? lados.arr(a) : lados.aba(a);
      if (Math.abs(a.cx - b.cx) < 1) pts = [desde, b.cy < a.cy ? lados.aba(b) : lados.arr(b)];
      else pts = [desde, [a.cx, b.cy], b.cx > a.cx ? lados.izq(b) : lados.der(b)];
    } else if (ruta === "h") pts = [b.cx > a.cx ? lados.der(a) : lados.izq(a), b.cx > a.cx ? lados.izq(b) : lados.der(b)];
    else if (ruta === "v") pts = [b.cy > a.cy ? lados.aba(a) : lados.arr(a), b.cy > a.cy ? lados.arr(b) : lados.aba(b)];
    else if (ruta === "vh") pts = [b.cy > a.cy ? lados.aba(a) : lados.arr(a), [a.cx, b.cy], b.cx > a.cx ? lados.izq(b) : lados.der(b)];
    else if (ruta === "hv") pts = [b.cx > a.cx ? lados.der(a) : lados.izq(a), [b.cx, a.cy], b.cy > a.cy ? lados.arr(b) : lados.aba(b)];
    const id = f.id || `Flujo_${i + 1}`;
    a.sale.push(id); b.entra.push(id);
    let etiqueta = null;
    if (f.nombre) {
      const [x1, y1] = pts[0], [x2, y2] = pts[1];
      const vertical = Math.abs(x1 - x2) < 1;
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      etiqueta = vertical
        ? { x: mx + 6 + (f.etq?.dx || 0), y: my - 8 + (f.etq?.dy || 0), w: f.etq?.w || 70, h: 16 }
        : { x: mx - (f.etq?.w || 70) / 2 + (f.etq?.dx || 0), y: my - 20 + (f.etq?.dy || 0), w: f.etq?.w || 70, h: 16 };
    }
    return { ...f, id, pts, etiqueta, proceso: procesoDe(f.de) };
  });

  // ---------- flujos de mensaje ----------
  const extremo = (ref, haciaAbajo, x) => {
    if (pools[ref]) return [x, haciaAbajo ? pools[ref].y + pools[ref].h : pools[ref].y];
    const n = nodos[ref];
    return [x, haciaAbajo ? n.y + n.h : n.y];
  };
  const centroY = (ref) => (pools[ref] ? pools[ref].y + pools[ref].h / 2 : nodos[ref].cy);
  const mensajes = spec.mensajes.map((m, i) => {
    const x = m.x ?? (nodos[m.de] ? nodos[m.de].cx : nodos[m.a].cx);
    const abajo = centroY(m.a) > centroY(m.de);
    const p1 = extremo(m.de, abajo, x), p2 = extremo(m.a, !abajo, x);
    const pts = [p1, p2];
    const etiqueta = m.nombre ? { x: x + 8 + (m.etq?.dx || 0), y: (m.etq?.y ?? (Math.min(p1[1], p2[1]) + 10)) + (m.etq?.dy || 0), w: m.etq?.w || 150, h: 28 } : null;
    return { ...m, id: m.id || `Mensaje_${i + 1}`, pts, etiqueta };
  });

  // ---------- anotaciones ----------
  const notas = (spec.notas || []).map((n, i) => {
    const t = nodos[n.a];
    const base = n.en ? (lanes[n.en] || pools[n.en]).y : 0;
    const caja = { x: n.x, y: base + n.y, w: n.w, h: n.h };
    const desdeNota = { izq: [caja.x, caja.y + caja.h / 2], arr: [caja.x + (n.px ?? caja.w / 2), caja.y], aba: [caja.x + (n.px ?? caja.w / 2), caja.y + caja.h] }[n.desde || "izq"];
    const haciaNodo = n.hacia === "arr" ? [n.tx ?? t.cx, t.y] : n.hacia === "aba" ? [n.tx ?? t.cx, t.y + t.h] : n.hacia === "izq" ? [t.x, t.cy] : [t.x + t.w, t.cy];
    return { ...n, id: `Nota_${i + 1}`, asoc: `Asociacion_${i + 1}`, caja, pts: [desdeNota, haciaNodo] };
  });

  // ---------- XML del modelo ----------
  const tipoXml = { inicio: "startEvent", fin: "endEvent", captura: "intermediateCatchEvent", borde: "boundaryEvent", xor: "exclusiveGateway", tarea: "task", usuario: "userTask", servicio: "serviceTask", envio: "sendTask", manual: "manualTask" };
  const defXml = (d) => (d === "temporizador" ? "<bpmn:timerEventDefinition />" : d === "mensaje" ? "<bpmn:messageEventDefinition />" : "");
  const procesos = spec.pools.filter((p) => p.proceso);
  let xml = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definiciones_${spec.id}" targetNamespace="https://github.com/U20242228211-hash/cronos-fisioavance" exporter="Cronos (generado)" exporterVersion="1.0">
  <bpmn:collaboration id="Colaboracion_${spec.id}">
`;
  for (const p of spec.pools) xml += `    <bpmn:participant id="${p.id}" name="${esc(p.nombre)}"${p.proceso ? ` processRef="${p.proceso}"` : ""} />\n`;
  for (const m of mensajes) xml += `    <bpmn:messageFlow id="${m.id}"${m.nombre ? ` name="${esc(m.nombre)}"` : ""} sourceRef="${m.de}" targetRef="${m.a}" />\n`;
  for (const n of notas) xml += `    <bpmn:textAnnotation id="${n.id}"><bpmn:text>${esc(n.texto)}</bpmn:text></bpmn:textAnnotation>\n    <bpmn:association id="${n.asoc}" associationDirection="None" sourceRef="${n.a}" targetRef="${n.id}" />\n`;
  xml += "  </bpmn:collaboration>\n";
  for (const p of procesos) {
    xml += `  <bpmn:process id="${p.proceso}" isExecutable="false">\n`;
    const misLanes = Object.values(lanes).filter((l) => l.pool === p.id);
    if (misLanes.length) {
      xml += `    <bpmn:laneSet id="Carriles_${p.proceso}">\n`;
      for (const l of misLanes) xml += `      <bpmn:lane id="${l.id}" name="${esc(l.nombre)}">\n${l.nodos.map((id) => `        <bpmn:flowNodeRef>${id}</bpmn:flowNodeRef>\n`).join("")}      </bpmn:lane>\n`;
      xml += "    </bpmn:laneSet>\n";
    }
    for (const n of Object.values(nodos).filter((n) => procesoDe(n.id) === p.proceso)) {
      const attrs = n.tipo === "borde" ? ` attachedToRef="${n.unido}" cancelActivity="${n.interrumpe ? "true" : "false"}"` : "";
      const nombre = n.nombre ? ` name="${esc(n.nombre)}"` : "";
      xml += `    <bpmn:${tipoXml[n.tipo]} id="${n.id}"${nombre}${attrs}>\n${n.entra.map((f) => `      <bpmn:incoming>${f}</bpmn:incoming>\n`).join("")}${n.sale.map((f) => `      <bpmn:outgoing>${f}</bpmn:outgoing>\n`).join("")}${n.def ? `      ${defXml(n.def)}\n` : ""}    </bpmn:${tipoXml[n.tipo]}>\n`;
    }
    for (const f of flujos.filter((f) => f.proceso === p.proceso)) xml += `    <bpmn:sequenceFlow id="${f.id}"${f.nombre ? ` name="${esc(f.nombre)}"` : ""} sourceRef="${f.de}" targetRef="${f.a}" />\n`;
    xml += "  </bpmn:process>\n";
  }

  // ---------- XML de las coordenadas ----------
  const caja = (b) => `<dc:Bounds x="${Math.round(b.x)}" y="${Math.round(b.y)}" width="${Math.round(b.w)}" height="${Math.round(b.h)}" />`;
  const pts = (ps) => ps.map(([x, y]) => `<di:waypoint x="${Math.round(x)}" y="${Math.round(y)}" />`).join("");
  xml += `  <bpmndi:BPMNDiagram id="Diagrama_${spec.id}">\n    <bpmndi:BPMNPlane id="Plano_${spec.id}" bpmnElement="Colaboracion_${spec.id}">\n`;
  for (const p of Object.values(pools)) xml += `      <bpmndi:BPMNShape id="${p.id}_di" bpmnElement="${p.id}" isHorizontal="true">${caja(p)}</bpmndi:BPMNShape>\n`;
  for (const l of Object.values(lanes)) xml += `      <bpmndi:BPMNShape id="${l.id}_di" bpmnElement="${l.id}" isHorizontal="true">${caja(l)}</bpmndi:BPMNShape>\n`;
  const etiquetaNodo = (n) => {
    if (!n.nombre || ["tarea", "usuario", "servicio", "envio", "manual"].includes(n.tipo)) return "";
    const w = n.etq?.w || 110, h = n.etq?.h || 30;
    const pos = n.etq?.pos || "aba";
    let x = n.cx - w / 2, yy = n.y + n.h + 5;
    if (pos === "arr") yy = n.y - h - 4;
    if (pos === "der") { x = n.x + n.w + 6; yy = n.cy - h / 2; }
    if (pos === "izq") { x = n.x - w - 6; yy = n.cy - h / 2; }
    x += n.etq?.dx || 0; yy += n.etq?.dy || 0;
    return `<bpmndi:BPMNLabel>${caja({ x, y: yy, w, h })}</bpmndi:BPMNLabel>`;
  };
  for (const n of Object.values(nodos)) {
    xml += `      <bpmndi:BPMNShape id="${n.id}_di" bpmnElement="${n.id}"${n.tipo === "xor" ? ' isMarkerVisible="true"' : ""}>${caja(n)}${etiquetaNodo(n)}</bpmndi:BPMNShape>\n`;
  }
  for (const n of notas) xml += `      <bpmndi:BPMNShape id="${n.id}_di" bpmnElement="${n.id}">${caja(n.caja)}</bpmndi:BPMNShape>\n`;
  for (const f of flujos) xml += `      <bpmndi:BPMNEdge id="${f.id}_di" bpmnElement="${f.id}">${pts(f.pts)}${f.etiqueta ? `<bpmndi:BPMNLabel>${caja(f.etiqueta)}</bpmndi:BPMNLabel>` : ""}</bpmndi:BPMNEdge>\n`;
  for (const m of mensajes) xml += `      <bpmndi:BPMNEdge id="${m.id}_di" bpmnElement="${m.id}">${pts(m.pts)}${m.etiqueta ? `<bpmndi:BPMNLabel>${caja(m.etiqueta)}</bpmndi:BPMNLabel>` : ""}</bpmndi:BPMNEdge>\n`;
  for (const n of notas) xml += `      <bpmndi:BPMNEdge id="${n.asoc}_di" bpmnElement="${n.asoc}">${pts([n.pts[1], n.pts[0]])}</bpmndi:BPMNEdge>\n`;
  xml += "    </bpmndi:BPMNPlane>\n  </bpmndi:BPMNDiagram>\n</bpmn:definitions>\n";
  return { xml, pools, lanes, nodos };
}

module.exports = { construir, cx, S };
