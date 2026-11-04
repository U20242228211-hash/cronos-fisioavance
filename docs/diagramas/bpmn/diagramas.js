// Los cuatro diagramas de proceso de Cronos en BPMN 2.0. Uso: node diagramas.js <carpeta-salida>
const fs = require("fs");
const path = require("path");
const { construir, cx } = require("./motor.js");

const salida = process.argv[2] || ".";
fs.mkdirSync(salida, { recursive: true });

// ------------------------------------------------------------------ 1. Proceso actual (AS-IS)
const asIs = {
  id: "AsIs", columnas: 6,
  pools: [
    { id: "Pac", nombre: "Paciente o acudiente", proceso: "Proceso_Paciente", alto: 330, filas: { a: 52, m: 160, b: 270 }, separacion: 60 },
    {
      id: "Ips", nombre: "Fisioavance IPS", proceso: "Proceso_Ips",
      lanes: [
        { id: "L_Rec", nombre: "Recepción", alto: 150 },
        { id: "L_Coo", nombre: "Representante legal o coordinación", alto: 180 },
      ],
    },
  ],
  nodos: [
    { id: "Ini_Pac", tipo: "inicio", nombre: "Quiere decir algo sobre la atención", pool: "Pac", col: 0, fila: "m" },
    { id: "Gw_Como", tipo: "xor", nombre: "¿Cómo lo hace?", pool: "Pac", col: 1, fila: "m", etq: { pos: "izq", w: 80, dy: -36, dx: 4 } },
    { id: "Fin_NoDice", tipo: "fin", nombre: "La IPS no se entera", pool: "Pac", col: 1, fila: "a", etq: { pos: "izq", w: 110 } },
    { id: "T_Qr", tipo: "tarea", nombre: "Escanear el QR y llenar el formulario (PQRSF o encuesta)", pool: "Pac", col: 2, fila: "m" },
    { id: "Fin_Form", tipo: "fin", def: "mensaje", nombre: "Formulario enviado", pool: "Pac", col: 3, fila: "m", etq: { pos: "der", w: 90 } },
    { id: "T_Buzon", tipo: "tarea", nombre: "Escribir la sugerencia y depositarla en el buzón", pool: "Pac", col: 1, fila: "b" },
    { id: "Fin_Papel", tipo: "fin", def: "mensaje", nombre: "Papel en el buzón", pool: "Pac", col: 2, fila: "b", etq: { pos: "der", w: 80 } },
    { id: "Ini_Rec", tipo: "inicio", def: "temporizador", nombre: "Cada 2 días", lane: "L_Rec", col: 1, etq: { pos: "arr", w: 80 } },
    { id: "T_Abrir", tipo: "manual", nombre: "Abrir el buzón y recoger los papeles", lane: "L_Rec", col: 2 },
    { id: "T_Leer", tipo: "usuario", nombre: "Leer las sugerencias y las respuestas del formulario", lane: "L_Coo", col: 3 },
    { id: "T_Atender", tipo: "usuario", nombre: "Atender cada caso", lane: "L_Coo", col: 4 },
    { id: "Fin_Ips", tipo: "fin", nombre: "Caso atendido", lane: "L_Coo", col: 5 },
  ],
  flujos: [
    { de: "Ini_Pac", a: "Gw_Como" },
    { de: "Gw_Como", a: "Fin_NoDice", nombre: "No lo dice", etq: { w: 60 } },
    { de: "Gw_Como", a: "T_Qr", nombre: "Código QR", etq: { w: 60 } },
    { de: "Gw_Como", a: "T_Buzon", nombre: "Buzón", etq: { w: 40 } },
    { de: "T_Qr", a: "Fin_Form" },
    { de: "T_Buzon", a: "Fin_Papel" },
    { de: "Ini_Rec", a: "T_Abrir" },
    { de: "T_Abrir", a: "T_Leer", ruta: "vh" },
    { de: "T_Leer", a: "T_Atender" },
    { de: "T_Atender", a: "Fin_Ips" },
  ],
  mensajes: [
    { de: "Fin_Papel", a: "T_Abrir" },
    { de: "Fin_Form", a: "T_Leer", nombre: "Respuestas del formulario", etq: { w: 90, dy: 8 } },
  ],
  notas: [
    { a: "Fin_NoDice", texto: "Punto crítico 2: muchos pacientes llegan de afán y no escanean el código.", en: "Pac", x: cx(1) + 40, y: 26, w: 290, h: 52, desde: "izq", hacia: "der" },
    { a: "Ini_Rec", texto: "Punto crítico 1: el buzón se abre cada 2 días y un reclamo de riesgo vital se debe resolver en 24 horas.", en: "L_Coo", x: 80, y: 60, w: 330, h: 56, desde: "arr", px: cx(1) - 80, hacia: "aba" },
    { a: "T_Atender", texto: "No se indagó cómo se responde ni cómo se controla el término.", en: "L_Rec", x: cx(4) - 60, y: 20, w: 250, h: 48, desde: "aba", px: 60, hacia: "arr" },
  ],
};

// ------------------------------------------------------------------ 2. Radicación y clasificación (TO-BE)
const radicacion = {
  id: "Radicacion", columnas: 6,
  pools: [
    { id: "Pac", nombre: "Paciente o acudiente", alto: 60, separacion: 80 },
    {
      id: "Ips", nombre: "Fisioavance IPS", proceso: "Proceso_Radicacion",
      lanes: [
        { id: "L_Rec", nombre: "Recepción", alto: 140 },
        { id: "L_Cro", nombre: "Cronos (sistema)", alto: 170 },
        { id: "L_Ate", nombre: "Atención al usuario", alto: 160 },
      ],
    },
  ],
  nodos: [
    { id: "Ini_Buzon", tipo: "inicio", def: "temporizador", nombre: "Todos los días", lane: "L_Rec", col: 1, etq: { pos: "arr", w: 80 } },
    { id: "T_Registrar", tipo: "usuario", nombre: "Abrir el buzón y registrar cada PQRSF en el panel", lane: "L_Rec", col: 2 },
    { id: "Ini_Portal", tipo: "inicio", def: "mensaje", nombre: "PQRSF radicada en el portal", lane: "L_Cro", col: 0, etq: { w: 90 } },
    { id: "Gw_Une", tipo: "xor", lane: "L_Cro", col: 2 },
    { id: "T_Radicar", tipo: "servicio", nombre: "Radicar, proponer la clasificación y calcular el término", lane: "L_Cro", col: 3 },
    { id: "T_Avisar", tipo: "envio", nombre: "Avisar por correo a atención al usuario", lane: "L_Cro", col: 4 },
    { id: "T_Confirmar", tipo: "usuario", nombre: "Confirmar la clasificación y asignar el responsable", lane: "L_Ate", col: 4 },
    { id: "Fin_Rad", tipo: "fin", nombre: "PQRSF en trámite", lane: "L_Ate", col: 5, etq: { w: 80 } },
  ],
  flujos: [
    { de: "Ini_Buzon", a: "T_Registrar" },
    { de: "T_Registrar", a: "Gw_Une" },
    { de: "Ini_Portal", a: "Gw_Une" },
    { de: "Gw_Une", a: "T_Radicar" },
    { de: "T_Radicar", a: "T_Avisar" },
    { de: "T_Avisar", a: "T_Confirmar" },
    { de: "T_Confirmar", a: "Fin_Rad" },
  ],
  mensajes: [
    { de: "Pac", a: "Ini_Portal", nombre: "PQRSF por el QR, el enlace de WhatsApp o la tableta", etq: { w: 150 } },
    { de: "Pac", a: "T_Registrar", nombre: "Papel en el buzón", etq: { w: 90 } },
    { de: "T_Radicar", a: "Pac", nombre: "Constancia con radicado y fecha límite", etq: { w: 140 } },
  ],
  notas: [
    { a: "T_Avisar", texto: "Si es de riesgo vital, el correo también le llega a la dirección.", en: "L_Rec", x: cx(4) - 55, y: 18, w: 260, h: 46, desde: "aba", px: 55, hacia: "arr" },
    { a: "T_Radicar", texto: "El término corre desde la radicación: 8, 24, 48 o 72 horas corridas, o días hábiles con festivos.", en: "L_Ate", x: 200, y: 30, w: 320, h: 52, desde: "arr", px: 300, hacia: "aba", tx: cx(3) - 30 },
  ],
};

// ------------------------------------------------------------------ 3. Atención, respuesta y cierre (TO-BE)
const atencion = {
  id: "Atencion", columnas: 7,
  pools: [
    { id: "Pac", nombre: "Paciente o acudiente", alto: 60, separacion: 80 },
    {
      id: "Ips", nombre: "Fisioavance IPS", proceso: "Proceso_Atencion",
      lanes: [
        { id: "L_Cro", nombre: "Cronos (sistema)", alto: 140 },
        { id: "L_Ate", nombre: "Atención al usuario", alto: 250, filas: { m: 80, b: 190 } },
        { id: "L_Dir", nombre: "Dirección", alto: 140 },
      ],
    },
  ],
  nodos: [
    { id: "Ini_Caso", tipo: "inicio", nombre: "PQRSF en trámite", lane: "L_Ate", col: 0, etq: { w: 80 } },
    { id: "T_Gestionar", tipo: "usuario", nombre: "Gestionar el caso y responder", lane: "L_Ate", col: 1 },
    { id: "B_Alerta", tipo: "borde", def: "temporizador", nombre: "Al 50 % y al 80 % del término", unido: "T_Gestionar", lado: "arriba", etq: { pos: "der", w: 110, dx: 4, dy: -40 } },
    { id: "B_Vence", tipo: "borde", def: "temporizador", nombre: "Al vencerse el término", unido: "T_Gestionar", lado: "abajo", etq: { pos: "der", w: 90, dy: 14 } },
    { id: "T_Alerta", tipo: "servicio", nombre: "Enviar la alerta por correo al responsable", lane: "L_Cro", col: 1 },
    { id: "Fin_Alerta", tipo: "fin", nombre: "Alerta enviada", lane: "L_Cro", col: 2, etq: { w: 80 } },
    { id: "T_Escalar", tipo: "usuario", nombre: "Hacer seguimiento al caso vencido", lane: "L_Dir", col: 1 },
    { id: "Fin_Escala", tipo: "fin", nombre: "Escalamiento atendido", lane: "L_Dir", col: 2, etq: { w: 90 } },
    { id: "Gw_Anonima", tipo: "xor", nombre: "¿Es anónima?", lane: "L_Ate", col: 2, etq: { pos: "arr", w: 80 } },
    { id: "T_Enviar", tipo: "envio", nombre: "Enviar la respuesta por WhatsApp o correo", lane: "L_Ate", col: 3 },
    { id: "T_Aviso", tipo: "usuario", nombre: "Imprimir el aviso para la cartelera", lane: "L_Ate", col: 3, fila: "b" },
    { id: "Gw_Une", tipo: "xor", lane: "L_Ate", col: 4 },
    { id: "T_Cerrar", tipo: "usuario", nombre: "Cerrar el caso", lane: "L_Ate", col: 5 },
    { id: "Fin_Caso", tipo: "fin", nombre: "Caso cerrado", lane: "L_Ate", col: 6, etq: { w: 80 } },
  ],
  flujos: [
    { de: "Ini_Caso", a: "T_Gestionar" },
    { de: "T_Gestionar", a: "Gw_Anonima" },
    { de: "B_Alerta", a: "T_Alerta" },
    { de: "T_Alerta", a: "Fin_Alerta" },
    { de: "B_Vence", a: "T_Escalar" },
    { de: "T_Escalar", a: "Fin_Escala" },
    { de: "Gw_Anonima", a: "T_Enviar", nombre: "No", etq: { w: 24 } },
    { de: "Gw_Anonima", a: "T_Aviso", nombre: "Sí", ruta: "vh", etq: { w: 20 } },
    { de: "T_Enviar", a: "Gw_Une" },
    { de: "T_Aviso", a: "Gw_Une", ruta: "hv" },
    { de: "Gw_Une", a: "T_Cerrar" },
    { de: "T_Cerrar", a: "Fin_Caso" },
  ],
  mensajes: [
    { de: "T_Enviar", a: "Pac", nombre: "Respuesta fechada, con la advertencia de la Superintendencia", etq: { w: 170 } },
  ],
  notas: [
    { a: "T_Aviso", texto: "Cronos publica el aviso en el portal durante 5 días hábiles.", en: "L_Dir", x: cx(3) - 55, y: 25, w: 250, h: 44, desde: "arr", px: 55, hacia: "aba" },
    { a: "T_Cerrar", texto: "Si el paciente no queda conforme, el caso se puede reabrir.", en: "L_Cro", x: cx(5) - 50, y: 20, w: 250, h: 46, desde: "aba", px: 50, hacia: "arr" },
  ],
};

// ------------------------------------------------------------------ 4. Encuesta de satisfacción (TO-BE)
const encuesta = {
  id: "Encuesta", columnas: 6,
  pools: [
    { id: "Pac", nombre: "Paciente o acudiente", alto: 60, separacion: 70 },
    {
      id: "Ips", nombre: "Fisioavance IPS", proceso: "Proceso_Encuesta", separacion: 60,
      lanes: [
        { id: "L_Rec", nombre: "Recepción", alto: 140 },
        { id: "L_Cro", nombre: "Cronos (sistema)", alto: 150 },
        { id: "L_Ate", nombre: "Atención al usuario", alto: 230, filas: { m: 70, b: 175 } },
      ],
    },
    { id: "Min", nombre: "Ministerio de Salud y Protección Social (PISIS)", alto: 60 },
  ],
  nodos: [
    { id: "Ini_Termina", tipo: "inicio", nombre: "El paciente terminó su tratamiento", lane: "L_Rec", col: 0, etq: { w: 100 } },
    { id: "T_Invitar", tipo: "envio", nombre: "Crear la invitación y enviarla por WhatsApp", lane: "L_Rec", col: 1 },
    { id: "C_Respondida", tipo: "captura", def: "mensaje", nombre: "Encuesta respondida", lane: "L_Cro", col: 2, etq: { w: 80 } },
    { id: "T_Guardar", tipo: "servicio", nombre: "Guardar las respuestas", lane: "L_Cro", col: 3 },
    { id: "Gw_Mala", tipo: "xor", nombre: "¿Alguna calificación de 2 o menos?", lane: "L_Cro", col: 4, etq: { pos: "arr", w: 140 } },
    { id: "Fin_Guardada", tipo: "fin", nombre: "Encuesta guardada", lane: "L_Cro", col: 5, etq: { w: 90 } },
    { id: "T_Revisar", tipo: "usuario", nombre: "Revisar la encuesta y decidir si se registra una queja", lane: "L_Ate", col: 4 },
    { id: "Fin_Revisada", tipo: "fin", nombre: "Encuesta revisada", lane: "L_Ate", col: 5, etq: { w: 90 } },
    { id: "Ini_Trimestre", tipo: "inicio", def: "temporizador", nombre: "Cada trimestre", lane: "L_Ate", col: 0, fila: "b", etq: { w: 80 } },
    { id: "T_Reportar", tipo: "usuario", nombre: "Descargar el Excel de la Resolución 256 y reportarlo", lane: "L_Ate", col: 1, fila: "b" },
    { id: "Fin_Reporte", tipo: "fin", nombre: "Reporte enviado", lane: "L_Ate", col: 2, fila: "b", etq: { w: 80 } },
  ],
  flujos: [
    { de: "Ini_Termina", a: "T_Invitar" },
    { de: "T_Invitar", a: "C_Respondida", ruta: "vh" },
    { de: "C_Respondida", a: "T_Guardar" },
    { de: "T_Guardar", a: "Gw_Mala" },
    { de: "Gw_Mala", a: "Fin_Guardada", nombre: "No", etq: { w: 24 } },
    { de: "Gw_Mala", a: "T_Revisar", nombre: "Sí", etq: { w: 20 } },
    { de: "T_Revisar", a: "Fin_Revisada" },
    { de: "Ini_Trimestre", a: "T_Reportar" },
    { de: "T_Reportar", a: "Fin_Reporte" },
  ],
  mensajes: [
    { de: "T_Invitar", a: "Pac", nombre: "Invitación con el enlace de la encuesta", etq: { w: 130 } },
    { de: "Pac", a: "C_Respondida", nombre: "Respuestas: cinco caritas y un comentario", etq: { w: 140 } },
    { de: "T_Reportar", a: "Min", nombre: "Conteos del trimestre", etq: { w: 120, y: 655 } },
  ],
  notas: [
    { a: "C_Respondida", texto: "También se responde por el código QR o en la tableta de recepción, sin invitación.", en: "L_Rec", x: cx(2) + 90, y: 20, w: 290, h: 50, desde: "aba", px: 20, hacia: "arr", tx: cx(2) + 12 },
    { a: "T_Revisar", texto: "Cronos le avisa por correo a atención al usuario.", en: "L_Ate", x: cx(4) - 90, y: 170, w: 240, h: 44, desde: "arr", px: 90, hacia: "aba" },
    { a: "Ini_Trimestre", texto: "Dentro de los 30 días siguientes al cierre de cada trimestre (Resolución 256).", en: "L_Ate", x: 80, y: 20, w: 300, h: 50, desde: "aba", px: 70, hacia: "arr" },
  ],
};

for (const [nombre, spec] of [["09-bpmn-as-is", asIs], ["10-bpmn-to-be-radicacion", radicacion], ["11-bpmn-to-be-atencion", atencion], ["12-bpmn-to-be-encuesta", encuesta]]) {
  const { xml } = construir(spec);
  fs.writeFileSync(path.join(salida, nombre + ".bpmn"), xml);
  console.log("escrito", nombre + ".bpmn");
}
