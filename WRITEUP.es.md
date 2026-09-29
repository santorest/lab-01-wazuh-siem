# Laboratorio SIEM con Wazuh

> **Resumen** — Diseño y construcción de un SIEM Wazuh de un solo nodo para una empresa ficticia de 40
> personas, que recoge telemetría de Windows (Sysmon), Linux (auditd) y del firewall, con ocho casos de uso de
> detección mapeados a MITRE ATT&CK. **Estado: en construcción; los resultados del laboratorio están
> pendientes y solo se publicarán una vez medidos.**

| | |
|---|---|
| **Rol asumido** | Ingeniero de seguridad de una empresa de 40 personas sin SOC |
| **Entorno** | Proxmox VE, 5 VM, red de laboratorio aislada (3 VLAN) |
| **Herramientas** | Wazuh 4.14.8, Sysmon (sysmon-modular), auditd, pfSense CE, Python |
| **Resultado clave** | Pendiente de la ejecución en el laboratorio |

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
| dc01 | Windows Server 2022 (evaluación) | Controlador de dominio `lab.local`; agente + Sysmon | 10.10.20.11 | 2 vCPU, 4 GB, 60 GB |
| srv01 | Ubuntu 24.04 | Servidor Linux; agente + auditd | 10.10.20.12 | 1 vCPU, 2 GB, 20 GB |
| ws01 | Windows 11 (evaluación) | Estación unida al dominio; agente + Sysmon | 10.10.30.21 | 2 vCPU, 4 GB, 60 GB |
| fw01 | pfSense CE | Firewall entre VLAN; syslog hacia wazuh01 | 10.10.99.1 | 1 vCPU, 1 GB, 16 GB |

- **Flujos de datos:** agentes → wazuh01 por 1514/tcp (protocolo cifrado del agente); fw01 → wazuh01 por
  syslog 514/udp; analista → dashboard de Wazuh por 443/tcp, solo desde la VLAN de gestión.

| Decisión | Alternativas consideradas | Por qué esta |
|---|---|---|
| Wazuh de un solo nodo, instalación nativa | Elastic Security; Wazuh en Docker | Gratuito; incluye agentes, FIM, SCA y respuesta activa; la instalación nativa es como la operaría una empresa pequeña |
| Versión fijada (4.14.8) con verificación del instalador | Instalador "latest" | Construcciones reproducibles; un cambio inesperado del proveedor detiene la instalación en lugar de producir un resultado distinto |
| Sysmon con sysmon-modular | Configuración de SwiftOnSecurity; sin Sysmon | Mantenida, modular y etiquetada con técnicas ATT&CK |
| pfSense ahora, FortiGate después | Esperar al laboratorio de FortiGate | Desbloquea la telemetría del firewall; la ruta de syslog no cambia cuando llegue FortiGate |

## 3. Construcción

1. **Requisitos** — host Proxmox con ≥32 GB de RAM; bridge/VLAN aisladas 20, 30 y 99; ISO de evaluación de
   Windows Server 2022 y Windows 11; ISO de Ubuntu 24.04; ISO de pfSense CE.
2. **Servidor Wazuh** — en wazuh01 ejecuta [`scripts/deploy/install-wazuh.sh`](scripts/deploy/install-wazuh.sh).
   Descarga el instalador oficial 4.14.8, **verifica su SHA-256** e instala el indexador, el servidor y el
   dashboard. Guarda la contraseña de administrador generada en un gestor de contraseñas.
3. **Agentes** — inscribe dc01, ws01 y srv01 siguiendo la documentación oficial de agentes de Wazuh 4.14; la
   configuración de recolección está en [`configs/agents/`](configs/agents/).
4. **Sysmon** — instálalo en dc01 y ws01 con la configuración fijada de sysmon-modular
   ([`configs/sysmon/README.md`](configs/sysmon/README.md)).
5. **Registros del firewall** — configura el syslog remoto de pfSense hacia wazuh01.
6. **Línea base** — deja el laboratorio funcionando con actividad normal durante una semana y exporta el conteo
   diario de alertas con [`scripts/report/export_alert_metrics.py`](scripts/report/export_alert_metrics.py).

> **Imprevistos:** se registran a medida que avanza la construcción en [`docs/build-notes.md`](docs/build-notes.md).

## 4. Pruebas y validación

Cada caso de uso se ejecuta únicamente dentro del laboratorio aislado (snapshot de la VM antes y reversión
después), siguiendo la documentación oficial de Atomic Red Team para la versión fijada. Los resultados se
registran en [`tests/test-plan.md`](tests/test-plan.md).

| # | Host | ATT&CK | Comportamiento | Estado |
|---|---|---|---|---|
| T1 | ws01 | T1059.001 | PowerShell ofuscado | Pendiente de ejecución |
| T2 | ws01 | T1003.001 | Acceso a credenciales en LSASS | Pendiente de ejecución |
| T3 | ws01 | T1547.001 | Persistencia mediante claves Run del registro | Pendiente de ejecución |
| T4 | dc01 | T1136.002 / T1098 | Nueva cuenta de dominio añadida a un grupo privilegiado | Pendiente de ejecución |
| T5 | dc01 | T1070.001 | Borrado del registro de seguridad | Pendiente de ejecución |
| T6 | srv01 | T1110.001 | Adivinación de contraseñas por SSH | Pendiente de ejecución |
| T7 | srv01 | T1098.004 | Modificación de `authorized_keys` de SSH | Pendiente de ejecución |
| T8 | fw01 | T1046 | Descubrimiento de servicios de red (escaneo) | Pendiente de ejecución |

## 5. Resultados

**Verificado hasta ahora (reproducible desde el repositorio):**
- El instalador está fijado a Wazuh 4.14.8 y se niega a ejecutarse si el archivo del proveedor cambia
  (verificación de checksum).
- La generación de reportes se prueba en CI: [`export_alert_metrics.py`](scripts/report/export_alert_metrics.py)
  y [`coverage_table.py`](scripts/report/coverage_table.py), incluida la regla de que los resultados faltantes
  se reportan como *Pendiente* y nunca como un porcentaje parcial.

**Métricas del laboratorio** — se completan con las exportaciones reales del laboratorio usando
`python scripts/report/coverage_table.py`:

| Métrica | Resultado |
|---|---|
| Cobertura de detección antes del ajuste | Pendiente |
| Cobertura de detección después del ajuste | Pendiente |
| Alertas promedio por día (línea base → ajustado) | Pendiente |

- **Evidencia:** se añadirán capturas depuradas en [`screenshots/`](screenshots/) después de la ejecución.
- **Lo que no funcionó / brechas conocidas:** se documentarán con honestidad después de la ejecución.

## 6. Lecciones aprendidas

Se escribirán después de la ejecución en el laboratorio.

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
