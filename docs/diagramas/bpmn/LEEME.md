# Diagramas de proceso en BPMN 2.0

Los cuatro `.bpmn` se abren y se editan en <https://demo.bpmn.io> o en Camunda Modeler. Se generan desde
`diagramas.js` (qué va en cada diagrama) con `motor.js` (ubica cada elemento en una cuadrícula y traza los flujos
con tramos rectos), y se dibujan con bpmn-js:

```bash
npm install bpmn-js@18.30.1
node diagramas.js .
node dibujar.mjs <puerto de Chrome con --remote-debugging-port> .
```

| Archivo | Qué muestra |
|---|---|
| `09-bpmn-as-is` | Proceso actual de Fisioavance, con sus dos puntos críticos |
| `10-bpmn-to-be-radicacion` | Cómo entra una PQRSF con Cronos y quién confirma la clasificación |
| `11-bpmn-to-be-atencion` | Gestión, alertas por tiempo, respuesta y cierre |
| `12-bpmn-to-be-encuesta` | Encuesta de satisfacción y reporte trimestral |
