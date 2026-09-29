# Laboratorio SIEM con Wazuh

> **Resumen** — Arquitectura de referencia de un SIEM Wazuh de un solo nodo para proteger a una empresa
> ficticia de 40 personas: telemetría de Windows (Sysmon), Linux (auditd) y del firewall, ocho casos de uso de
> detección mapeados a MITRE ATT&CK, herramientas con versiones fijadas y un sistema de medición probado.
> **Entregable: diseño de referencia, listo para construir.**

| | |
|---|---|
| **Rol asumido** | Ingeniero de seguridad de una empresa de 40 personas sin SOC |
| **Entorno** | Proxmox VE, 5 VM, red de laboratorio aislada (3 VLAN) |
| **Herramientas** | Wazuh 4.14.8, Sysmon (sysmon-modular), auditd, OPNsense, Python |
| **Entregable** | Arquitectura, plan de detección, scripts de construcción fijados, herramientas de reporte probadas |

---

## 1. Problema

- **Contexto:** una empresa ficticia de servicios profesionales con 40 personas tiene un dominio Windows, un
  servidor Linux y un firewall perimetral. Los registros se quedan en cada máquina y nadie los revisa.
- **Por qué importa:** el robo de credenciales, la persistencia y el abuso de privilegios pasarían
  inadvertidos durante semanas. La empresa no puede pagar un SIEM comercial ni un SOC 24/7.
- **Objetivos:**
    1. Centralizar la telemetría de Windows, Linux y el firewall en un SIEM de código abierto.
    2. Detectar 8 comportamientos de atacantes relevantes para una empresa de este tamaño, mapeados a MITRE ATT&CK.
    3. Mantener un volumen de alertas que una sola persona a tiempo parcial pueda revisar a diario.
    4. Hacer que todo el laboratorio sea reproducible desde el repositorio.
- **Alcance y restricciones:** solo herramientas de código abierto; licencias de evaluación para Windows; todo
  se ejecuta en un laboratorio aislado sin ruta hacia ninguna red de producción.
- **Criterios de éxito:** cada caso de uso tiene un resultado de detección registrado; el volumen diario de
  alertas se mide antes y después del ajuste; la construcción es reproducible con los scripts del repositorio.

## 2. Arquitectura

| Host | SO | Función | IP | Recursos |
|---|---|---|---|---|
| wazuh01 | Ubuntu 24.04 | Indexador + servidor + dashboard de Wazuh | 10.10.20.10 | 4 vCPU, 8 GB RAM, 80 GB |
| dc01 | Windows Server 2022 (evaluación) | Controlador de dominio `corp.internal`; agente + Sysmon | 10.10.20.11 | 2 vCPU, 4 GB, 60 GB |
| srv01 | Ubuntu 24.04 | Servidor Linux; agente + auditd | 10.10.20.12 | 1 vCPU, 2 GB, 20 GB |
| ws01 | Windows 11 (evaluación) | Estación unida al dominio; agente + Sysmon | 10.10.30.21 | 2 vCPU, 4 GB, 60 GB |
| fw01 | OPNsense 26.7 | Firewall entre VLAN (fw-hq del Lab 02); syslog hacia wazuh01 | 10.10.99.1 | 2 vCPU, 4 GB, 32 GB |

- **Flujos de datos:** agentes → wazuh01 por 1514/tcp (protocolo cifrado del agente); fw01 → wazuh01 por
  syslog 514/udp; analista → dashboard de Wazuh por 443/tcp, solo desde la VLAN de gestión.

| Decisión | Alternativas consideradas | Por qué esta |
|---|---|---|
| Wazuh de un solo nodo, instalación nativa | Elastic Security; Wazuh en Docker | Gratuito; incluye agentes, FIM, SCA y respuesta activa; la instalación nativa es como la operaría una empresa pequeña |
| Versión fijada (4.14.8) con verificación del instalador | Instalador "latest" | Construcciones reproducibles; un cambio inesperado del proveedor detiene la instalación en lugar de producir un resultado distinto |
| Sysmon con sysmon-modular | Configuración de SwiftOnSecurity; sin Sysmon | Mantenida, modular y etiquetada con técnicas ATT&CK |
| OPNsense como firewall | Prueba de FortiGate-VM; pfSense CE | La prueba gratuita de FortiGate es demasiado limitada (ver lecciones); OPNsense se construye y documenta en el [Lab 02](https://github.com/santorest/lab-02-segmented-network); la ruta de syslog no cambia si más adelante se usa un FortiGate con licencia |

## 3. Construcción

1. **Requisitos** — host Proxmox con ≥32 GB de RAM; bridge/VLAN aisladas 20, 30 y 99; ISO de evaluación de
   Windows Server 2022 y Windows 11; ISO de Ubuntu 24.04; el firewall OPNsense del [Lab 02](https://github.com/santorest/lab-02-segmented-network).
2. **Servidor Wazuh** — en wazuh01 ejecuta [`scripts/deploy/install-wazuh.sh`](scripts/deploy/install-wazuh.sh).
   Descarga el instalador oficial 4.14.8, **verifica su SHA-256** e instala el indexador, el servidor y el
   dashboard. Guarda la contraseña de administrador generada en un gestor de contraseñas.
3. **Agentes** — inscribe dc01, ws01 y srv01 siguiendo la documentación oficial de agentes de Wazuh 4.14; la
   configuración de recolección está en [`configs/agents/`](configs/agents/).
4. **Sysmon** — instálalo en dc01 y ws01 con la configuración fijada de sysmon-modular
   ([`configs/sysmon/README.md`](configs/sysmon/README.md)).
5. **Registros del firewall** — configura el syslog remoto de OPNsense hacia wazuh01 (Lab 02, guía 08).
6. **Línea base** — deja el laboratorio funcionando con actividad normal durante una semana y exporta el conteo
   diario de alertas con [`scripts/report/export_alert_metrics.py`](scripts/report/export_alert_metrics.py).

> **Notas de construcción:** los imprevistos y sus soluciones se registran en [`docs/build-notes.md`](docs/build-notes.md).

## 4. Plan de detección

Cada caso de uso indica el host donde se ejecuta, el comportamiento a detectar y la telemetría que lo hace
visible. Los casos de uso se ejecutan únicamente dentro del laboratorio aislado (snapshot de la VM antes y
reversión después), siguiendo la documentación oficial de Atomic Red Team para la versión fijada; los resultados
se registran en [`tests/test-plan.md`](tests/test-plan.md).

| # | Host | ATT&CK | Comportamiento | Telemetría |
|---|---|---|---|---|
| T1 | ws01 | T1059.001 | PowerShell ofuscado | Creación de procesos (Sysmon), registro de bloques de script de PowerShell |
| T2 | ws01 | T1003.001 | Acceso a credenciales en LSASS | Acceso a procesos (Sysmon) |
| T3 | ws01 | T1547.001 | Persistencia mediante claves Run del registro | Eventos de registro (Sysmon) |
| T4 | dc01 | T1136.002 / T1098 | Nueva cuenta de dominio añadida a un grupo privilegiado | Eventos de gestión de cuentas de Windows Security |
| T5 | dc01 | T1070.001 | Borrado del registro de seguridad | Eventos del registro de Windows Security |
| T6 | srv01 | T1110.001 | Adivinación de contraseñas por SSH | Registros de autenticación de sshd |
| T7 | srv01 | T1098.004 | Modificación de `authorized_keys` de SSH | Monitoreo de integridad de archivos + auditd |
| T8 | fw01 | T1046 | Descubrimiento de servicios de red (escaneo) | Registros del firewall vía syslog |

## 5. Entregables y medición

**Entregado en este repositorio:**

- Arquitectura y dimensionamiento de un laboratorio de cinco VM y tres VLAN ([diagrama](diagrams/architecture.svg)).
- Plan de detección: ocho casos de uso mapeados a MITRE ATT&CK y a la telemetría que necesita cada uno.
- Un instalador de Wazuh 4.14.8 con versión fijada que verifica el checksum del proveedor antes de ejecutarse.
- Un sistema de reportes probado en CI: [`export_alert_metrics.py`](scripts/report/export_alert_metrics.py)
  exporta el conteo diario de alertas del indexador de Wazuh y [`coverage_table.py`](scripts/report/coverage_table.py)
  convierte el plan de pruebas y esas exportaciones en las tablas de resultados.

**Cómo se miden los resultados** (`python scripts/report/coverage_table.py`):

| Métrica | Definición |
|---|---|
| Cobertura de detección | Casos de uso que generaron una alerta ÷ casos de uso probados, antes y después del ajuste |
| Volumen de alertas | Alertas promedio por día durante una semana de línea base frente a una semana después del ajuste |
| Reducción | Cambio relativo del volumen diario de alertas entre la línea base y el ajuste |

La cobertura solo se reporta cuando todos los casos de uso tienen un resultado registrado, de modo que nunca
se puede calcular a partir de un subconjunto favorable de pruebas.

## 6. Lecciones de diseño y hoja de ruta

- **Fija las versiones y verifica lo que descargas.** Un instalador "latest" hace imposible reproducir un
  laboratorio meses después. Fijar Wazuh 4.14.8 y comprobar el SHA-256 del instalador convierte un cambio
  silencioso del proveedor en una detención visible.
- **Revisa los límites de licencia antes de diseñar alrededor de un producto.** La prueba gratuita de
  FortiGate-VM solo permite tres interfaces, políticas y rutas, y no recibe actualizaciones de FortiGuard; por
  eso la fuente de registros del firewall usa OPNsense ([Lab 02](https://github.com/santorest/lab-02-segmented-network)), que no tiene esos límites. La ruta de syslog no
  cambia si más adelante se usa un FortiGate con licencia.
- **Planifica la telemetría antes que las reglas.** La mayoría de los casos de uso de Windows dependen de que
  Sysmon, la política de auditoría avanzada y el registro de bloques de script de PowerShell estén activos; sin
  ellos, una regla no tiene nada que detectar. Por eso cada caso de uso indica su fuente de telemetría.
- **Dimensiona primero el SIEM.** Solo el indexador de Wazuh necesita 8 GB de RAM y el laboratorio completo
  unos 19 GB, lo que define el requisito de un host con ≥32 GB.
- **Define las métricas antes de recolectar datos.** Escribir las definiciones de cobertura y volumen de
  alertas (y la regla de no reportar resultados parciales) antes de cualquier prueba mantiene los resultados
  honestos.

**Hoja de ruta:** construir el laboratorio a partir de este diseño, recolectar una semana de línea base, ejecutar
los ocho casos de uso, escribir reglas personalizadas para las brechas, ajustar y publicar aquí los resultados
medidos de cobertura y volumen de alertas.

## 7. Reprodúcelo tú mismo

- Clonar: `git clone https://github.com/santorest/lab-01-wazuh-siem.git`
- Descargar el paquete: desde el sitio del portafolio (el SHA-256 aparece junto a la descarga).
- Tiempo estimado: 1–2 días de construcción, más una semana de línea base.
- Limpieza: elimina las VM del laboratorio y el bridge aislado; no se usan recursos en la nube.

## 8. Mapeo

| Control / técnica | Marco | Cómo lo aborda este proyecto |
|---|---|---|
| 8.2 Recolectar registros de auditoría · 8.9 Centralizar registros | CIS Controls v8 | Los agentes y el syslog envían toda la telemetría a wazuh01 |
| 8.11 Revisar los registros de auditoría | CIS Controls v8 | Flujo de revisión diaria dimensionado con la métrica de volumen de alertas |
| T1059.001, T1003.001, T1547.001, T1136.002, T1098, T1070.001, T1110.001, T1098.004, T1046 | MITRE ATT&CK | Un caso de uso cada uno (sección 4) |

---

*Todas las pruebas se realizan en un entorno de laboratorio aislado de mi propiedad. No se incluyen datos,
nombres de host ni configuraciones de ninguna organización real.*
