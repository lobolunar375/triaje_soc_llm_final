Realiza en un solo paso el triaje completo del incidente con el expediente y las salidas de las herramientas (MITRE ATT&CK e historial).

Decide la clase del incidente (TP, BP o FP). Distingue con cuidado BP de TP: un BP tratado como amenaza consume tiempo del analista y un TP descartado deja pasar un ataque. Pondera el historial de los detectores, las técnicas y tácticas, los veredictos automáticos y el rol de las entidades.

Asigna además la prioridad operativa:
- P1 (crítica): TP con táctica avanzada (ejecución, movimiento lateral, exfiltración, impacto) o con entidades impactadas.
- P2 (alta): TP en etapa temprana o incidente con confianza baja y señales maliciosas.
- P3 (media): BP o FP con señales que merecen una verificación.
- P4 (baja): BP o FP sin señales de riesgo.

Devuelve:
- clase: TP, BP o FP.
- confianza: número entre 0 y 1.
- prioridad: P1, P2, P3 o P4.
- escalar: true si el incidente debe pasar al nivel 2.
- justificacion: entre 40 y 120 palabras que expliquen la clase y nombren la clase asignada.
- evidencias: identificadores del expediente que sustentan la decisión (al menos uno).
