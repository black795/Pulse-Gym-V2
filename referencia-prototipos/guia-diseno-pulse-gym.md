# PULSE GYM — PROTOTIPO INTERACTIVO DE ALTA FIDELIDAD

## 1. OBJETIVO DEL PROYECTO

Quiero crear un **MOCKUP / PROTOTIPO INTERACTIVO DE ALTA FIDELIDAD** para un sistema de gestión de gimnasio llamado **Pulse Gym**.

El objetivo de este proyecto es representar visualmente el producto y permitir recorrer sus principales flujos como si fuera una primera versión del sistema.

### MUY IMPORTANTE

Este proyecto es un **PROTOTIPO**, no una implementación completa de producción.

Quiero priorizar:

1. Calidad visual.
2. Fidelidad al sistema de diseño especificado.
3. Navegación entre pantallas.
4. Interacciones simuladas.
5. Consistencia de datos y componentes.
6. Experiencia responsive.
7. Facilidad para demostrar el prototipo.

### NO implementar todavía

No es necesario implementar:

* Backend real.
* Base de datos real.
* APIs externas.
* Autenticación real.
* Pagos reales.
* Integración real con modelos de IA.
* Sensores IoT.
* Integración real con cámaras.
* Reconocimiento/clasificación real de imágenes.
* Sistema real de notificaciones.
* Servicios externos.

Cuando una funcionalidad requiera backend o servicios externos, **simúlala en el frontend utilizando datos mock y estados locales**.

El resultado debe sentirse como un producto real, pero debe ser entendido como un **prototipo navegable**.

---

# 2. REGLAS GENERALES DEL PROTOTIPO

## 2.1 Navegación

Todas las pantallas principales deben poder recorrerse desde la interfaz.

Los botones, enlaces, tabs, filtros y elementos interactivos importantes deben tener comportamiento dentro del prototipo.

Ejemplos:

* "Ver clientes" debe llevar a la lista de clientes.
* "+ Nuevo cliente" debe llevar al formulario de nuevo cliente.
* Una fila de cliente puede abrir su ficha.
* Las pestañas de la ficha deben cambiar el contenido.
* Los filtros pueden modificar visualmente la información mostrada.
* Los botones de acción pueden mostrar estados simulados.
* El login puede simular un inicio de sesión exitoso.
* El registro puede simular la creación de una cuenta.
* El Entrenador IA debe mostrar una conversación predefinida.
* La cámara debe simular el flujo de captura.
* La clasificación de una máquina debe mostrar un resultado predefinido.

## 2.2 Datos

Utilizar datos ficticios pero consistentes en todo el prototipo.

No generar datos aleatorios diferentes cada vez que se cambia de pantalla.

Mantener los mismos personajes y datos para que todo el sistema parezca una única aplicación real.

### Staff

* Carlos — dueño.
* Pati — recepcionista.
* Javier — entrenador.
* Rosa — entrenadora.
* Iván — entrenador.

### Clientes

* Daniela Vargas — cliente principal del prototipo.
* Emerson Choque.
* Valeria Prado.
* Ronald Quispe — pago vencido.
* Fátima Delgado.
* Bruno Salazar — lesión lumbar pendiente.

Daniela Vargas debe ser el principal hilo narrativo del prototipo porque tiene una lesión de rodilla activa.

---

# 3. SISTEMA DE DISEÑO

## 3.1 Paleta de colores

Utilizar exactamente estos valores:

| Token            | Valor     | Uso                                                                                           |
| ---------------- | --------- | --------------------------------------------------------------------------------------------- |
| `--primary`      | `#16A34A` | Botones primarios, badges de éxito, estados activos                                           |
| `--primary-dark` | `#15803D` | Texto e iconos sobre tintes verdes                                                            |
| `--primary-tint` | `#DCFCE7` | Fondos de badges y chips                                                                      |
| `--neon`         | `#B6FF45` | Acento principal de marca, CTAs destacados, pulso, línea activa del sidebar, tarjetas premium |
| `--sidebar`      | `#0A120D` | Sidebar y tarjetas oscuras/hero                                                               |
| `--black-2`      | `#101A14` | Segundo tono de degradados oscuros                                                            |
| `--ink`          | `#0B1410` | Texto principal                                                                               |
| `--muted`        | `#5F6F66` | Texto secundario                                                                              |
| `--muted-2`      | `#8A968D` | Placeholders y texto terciario                                                                |
| `--surface`      | `#FFFFFF` | Tarjetas                                                                                      |
| `--bg`           | `#F4F7F4` | Fondo general                                                                                 |
| `--border`       | `#DCE6DE` | Bordes y separadores                                                                          |
| `--danger`       | `#DC2626` | Errores, lesiones y vencidos                                                                  |
| `--danger-tint`  | `#FEE2E2` | Fondo de estados de peligro                                                                   |
| `--warning`      | `#B45309` | Alertas y pendientes                                                                          |
| `--warning-tint` | `#FEF3C7` | Fondo de advertencias                                                                         |

### Regla importante

El color `--neon` `#B6FF45` es un **acento de marca**, no debe utilizarse para textos largos.

---

# 4. TIPOGRAFÍA

Utilizar:

### Sora

Pesos:

* 600
* 700
* 800

Usar Sora para:

* títulos;
* nombre de marca;
* navegación;
* botones;
* valores KPI;
* nombres de clientes;
* nombres de máquinas;
* planes;
* roles.

### Manrope

Pesos:

* 400
* 500
* 600
* 700
* 800

Usar Manrope para:

* cuerpo;
* formularios;
* tablas;
* texto general.

Carga recomendada:

`Manrope:wght@400;500;600;700;800`
`Sora:wght@600;700;800`

---

# 5. ICONOGRAFÍA

No utilizar emojis.

Utilizar iconos SVG consistentes, preferentemente inline.

Características:

* `stroke="currentColor"`
* `stroke-width` entre 1.8 y 2.2
* `stroke-linecap="round"`
* `stroke-linejoin="round"`
* sin relleno.

Conceptos:

* Dashboard → grid.
* Clientes → usuarios.
* Membresías → tarjeta.
* Asistencia → check.
* Máquinas → mancuerna.
* Rutinas → lista.
* Mediciones → pulso cardíaco.
* Roles → escudo.
* Pagos → billete.
* Reportes → documento.

---

# 6. COMPONENTES BASE

## Sidebar administrativo

Ancho aproximado: **264px**.

Fondo:

`--sidebar`

Debe contener:

### Logo

Icono de pulso + texto:

**Pulse Gym**

"Pulse" en blanco.

"Gym" en `--neon`.

Subtítulo:

**Panel administrador**

### Navegación

Agrupar por:

#### GESTIÓN

* Clientes
* Membresías
* Pagos
* Asistencia

#### ENTRENAMIENTO

* Máquinas
* Rutinas
* Mediciones y lesiones

#### CONFIGURACIÓN

* Reportes
* Roles y permisos

El elemento activo debe tener:

* fondo verde con aproximadamente 22% de opacidad;
* texto `#7BE3A0`;
* indicador visual de selección.

---

# 7. TOPBAR

La topbar debe ser sticky en todas las pantallas administrativas.

Debe contener:

* buscador global;
* campana de notificaciones;
* badge rojo de notificaciones;
* avatar circular;
* inicial **C**;
* fondo `--sidebar`;
* texto `--neon`;
* chevron.

La búsqueda y las notificaciones pueden ser simuladas.

---

# 8. CARDS

Utilizar:

```text
border: 1px solid var(--border)
border-radius: 14px
box-shadow: sutil
```

Las tarjetas deben sentirse limpias, modernas y consistentes.

---

# 9. BOTONES

## Primario

Fondo:

`--primary`

Texto blanco.

## Outline

Fondo blanco.

Borde:

`--border`

---

# 10. BADGES

Los estados deben utilizar badges tipo pill.

### Éxito

Verde.

### Advertencia

Ámbar.

### Peligro

Rojo.

Texto en negrita.

---

# 11. TABLAS

Utilizar:

* encabezados en mayúsculas;
* 11px aproximadamente;
* color `--muted`;
* filas con borde inferior;
* avatar circular + nombre en la primera columna.

---

# 12. ACCESIBILIDAD

Agregar soporte para:

`@media (prefers-reduced-motion: reduce)`

Cuando esté activo, reducir o desactivar animaciones y transiciones.

---

# 13. ASSETS / IMÁGENES

Utilizar imágenes reales como assets si están disponibles.

Los siguientes nombres representan los assets conceptuales:

| Asset                 | Uso                          |
| --------------------- | ---------------------------- |
| `login-hero-training` | Hero de Login                |
| `wellbeing`           | Rail de Registro             |
| `progress-visual`     | Banner del Dashboard         |
| `client-daniela`      | Avatar de Daniela Vargas     |
| `nutrition-lifestyle` | Card de nutrición            |
| `roles-community`     | Banner de Roles              |
| `strength-equipment`  | Máquinas y experiencia móvil |

### Regla

Daniela Vargas es la única cliente que debe utilizar fotografía real.

Los demás clientes deben utilizar iniciales/avatar visual.

No repetir indiscriminadamente la misma fotografía para todas las máquinas.

---

# 14. ESTRUCTURA GENERAL

El prototipo tendrá cuatro grandes áreas:

## FASE 1

Panel administrador.

## FASE 2

Acceso público para clientes.

## FASE 3

Operación del negocio.

## FASE 4

Experiencia móvil del cliente.

---

# FASE 1 — PANEL ADMINISTRADOR

## 15. DASHBOARD

Pantalla principal administrativa.

### Hero

Banner oscuro de aproximadamente 236px.

Utilizar degradado:

`--sidebar` → `--black-2`

Mostrar:

**Hola, Carlos**

Mostrar fecha.

Utilizar `progress-visual` desde el lado derecho con efecto de desvanecido.

### Accesos rápidos

* * Nuevo cliente
* Ver clientes
* Rutinas
* Máquinas

### KPIs

Mostrar 4 tarjetas:

* Clientes activos.
* Membresías vigentes.
* Asistencia de hoy.
* Entrenadores activos.

### Contenido inferior

Dos columnas.

#### Actividad reciente

Feed de eventos.

#### Alertas operativas

Mostrar ejemplos como:

* lesiones sin rutina;
* membresías por vencer;
* catálogo incompleto.

---

# 16. CLIENTES — LISTA

Ruta conceptual:

**Clientes**

Debe incluir:

### Buscador

Buscar clientes por nombre u otros datos.

### Filtros

Chips:

* Todos
* Activos
* Inactivos
* Por vencer

### Tabla

Columnas:

* Nombre
* Teléfono
* Plan
* Última visita
* Estado
* Acciones

Mostrar los 6 clientes ficticios definidos anteriormente.

Agregar paginación visual.

Las acciones deben permitir navegar hacia la ficha del cliente.

---

# 17. CLIENTES — NUEVO

Formulario para registrar un cliente.

Dividir en:

### Datos personales

* Nombre.
* Apellido.
* Teléfono.
* Otros datos personales relevantes.

### Datos físicos y objetivo

* Peso.
* Altura.
* Objetivo.

### Plan y membresía

* Selección de plan.
* Información de membresía.

### Columna lateral

Mostrar card utilizando:

`nutrition-lifestyle`

Agregar notas de ayuda explicando que el sistema puede generar una rutina automáticamente.

El botón de guardar debe simular el registro.

---

# 18. CLIENTES — FICHA

Utilizar Daniela Vargas como ejemplo principal.

### Cabecera

Mostrar:

* fotografía de Daniela;
* avatar de aproximadamente 80px;
* nombre;
* badge de estado;
* acciones.

### Tabs

Debe haber cuatro pestañas realmente interactivas:

1. Datos personales.
2. Mediciones.
3. Rutina asignada.
4. Historial físico.

No utilizar solamente CSS para aparentar tabs.

El contenido debe cambiar realmente cuando el usuario seleccione cada pestaña.

### Lesión

La pestaña de mediciones debe mostrar una alerta visible indicando la lesión activa de rodilla.

---

# 19. MEMBRESÍAS

Mostrar 3 tarjetas de planes.

### Mensual

**Bs 150**

### Trimestral

**Bs 400**

Este debe ser el plan destacado.

Utilizar fondo oscuro y acento `--neon`.

### Semestral

**Bs 700**

Cada tarjeta debe tener:

**Elegir plan**

### Tabla

Mostrar asignaciones activas con estados:

* Vigente.
* Por vencer.
* Vencida.

---

# 20. ROLES Y PERMISOS

Mostrar banner utilizando:

`roles-community`

Altura aproximada:

180px.

### Roles

Crear 4 tarjetas:

* Dueño.
* Recepcionista.
* Entrenador.
* Cliente.

Cada tarjeta debe listar permisos.

### Staff

Mostrar tabla de usuarios del staff:

* Carlos.
* Pati.
* Javier.
* Rosa.
* Iván.

---

# 21. MÁQUINAS

Crear grid de máquinas.

Mostrar diferentes equipos:

* Prensa.
* Banco.
* Polea.
* Extensión.
* Caminadora.
* Elíptica.

Cada máquina debe tener su propio thumbnail.

Una tarjeta debe utilizar:

`strength-equipment`

Las máquinas sin fotografía deben mostrar un placeholder oscuro con icono.

**No repetir una misma foto genérica para todas las máquinas.**

---

# 22. RUTINAS

Mostrar la rutina semanal de Daniela.

### Tabs

Un tab por día de entrenamiento.

### Ejercicios

Cada ejercicio debe mostrar su información.

Mostrar disponibilidad:

* ● Disponible
* ● Ocupada

### Progreso

El primer ejercicio debe mostrar:

**68 kg · +8 kg en 4 semanas**

### Ejercicio especial

Para:

**Remo en polea baja**

En lugar de mostrar las series normales, mostrar:

## Plan B automático del Entrenador IA

Mostrar 3 opciones:

1. Máquina similar disponible.
2. Alternativa en calistenia.
3. Saltar al siguiente.

Agregar una nota indicando que Daniela verá las mismas opciones desde su celular.

---

# FASE 2 — ACCESO PÚBLICO

## 23. LOGIN

Sin sidebar.

Layout dividido:

**55% imagen / 45% formulario**

### Panel izquierdo

Utilizar:

`login-hero-training`

Con degradado oscuro.

Título:

**Tu mejor versión empieza aquí**

### Panel derecho

Tarjeta blanca.

Campos:

* Correo.
* Contraseña.

Opciones:

* Recordarme.
* Olvidé contraseña.

Botón:

**Iniciar sesión**

No utilizar login social.

Agregar microcopy de seguridad.

Agregar enlace:

**Registro**

El login debe ser simulado.

---

# 24. REGISTRO

Layout partido.

### Rail izquierdo

Utilizar:

`wellbeing`

Mostrar 3 beneficios con iconos/check.

### Formulario

Dividir en 4 bloques.

## Bloque 1 — Datos personales

Campos correspondientes.

Agregar:

### Foto de perfil

Opcional.

Placeholder con icono de cámara.

Agregar fecha de nacimiento.

---

## Bloque 2 — Datos físicos

Campos:

* Peso.
* Altura.
* Días disponibles.

### IMC

Debe calcularse visualmente a partir del peso y altura.

**No mostrarlo como campo editable.**

Agregar nota:

El IMC es únicamente un dato de referencia.

---

## Bloque 3 — Salud y seguridad

Campos:

* Lesiones/limitaciones.
* Alergias.
* Contacto de emergencia.
* Observaciones.

Agregar caja de alerta explicando que una lesión registrada será visible en:

* Ficha.
* Rutinas.

---

## Bloque 4 — Objetivo

Mostrar 5 categorías:

* Pérdida de grasa.
* Fuerza.
* Masa muscular.
* Acondicionamiento.
* Salud general.

CTA principal:

**Crear cuenta y generar mi rutina**

CTA secundario:

**Cancelar**

La acción debe ser simulada.

---

# FASE 3 — OPERACIÓN DEL NEGOCIO

# 25. ASISTENCIA

Crear barra de check-in manual.

Elementos:

* Buscar cliente.
* Registrar entrada.

### KPIs

* Asistencias hoy.
* Pico del día.
* Promedio semanal.

### Tabla

Entradas del día.

Métodos:

* QR.
* Manual.

---

# 26. MEDICIONES Y LESIONES

Vista consolidada para entrenadores.

No obligar a entrar cliente por cliente.

### KPIs

* Lesiones activas.
* Mediciones de la semana.
* Clientes sin medición reciente.

### Tabla de lesiones activas

Columnas:

* Cliente.
* Lesión.
* Fecha.
* Rutina ajustada.
* Entrenador asignado.

### Mediciones

Mostrar últimas mediciones de peso.

Mostrar indicador de cambio.

---

# 27. PAGOS

Crear barra de cobro rápido.

Campos:

* Cliente.
* Plan.
* Método de pago.

### KPIs

* Ingresos del mes.
* Pagos de hoy.
* Pagos pendientes.

### Historial

Mostrar:

* Fecha.
* Cliente.
* Método.
* Estado.

Métodos:

* Efectivo.
* QR.
* Tarjeta.

Estados:

* Pagado.
* Pendiente.

Los pagos son únicamente simulados.

---

# 28. REPORTES

Selector:

* Semana.
* Mes.
* Año.

### KPIs

* Ingresos.
* Clientes activos.
* Retención.
* Ticket promedio.

### Gráfico

Mostrar gráfico de barras CSS con ingresos de los últimos 6 meses.

### Desempeño por plan

Mostrar barras de progreso con porcentajes.

### Ocupación

Mostrar gráfico de barras por horario.

Resaltar visualmente el pico:

**6–8pm**

Utilizar el estilo negro Pulse para el pico.

---

# FASE 4 — EXPERIENCIA MÓVIL DEL CLIENTE

## 29. CONCEPTO GENERAL

La experiencia móvil es diferente del panel administrativo.

Ancho de referencia:

**390px**

No utilizar sidebar.

Utilizar navegación inferior con 5 íconos:

1. Inicio.
2. Rutina.
3. IA.
4. Progreso.
5. Perfil.

---

# 30. MOBILE LOGIN

Versión móvil del Login.

### Parte superior

Imagen de aproximadamente 280px.

Mostrar:

* marca;
* titular.

### Parte inferior

Hoja blanca.

Formulario compacto.

Inputs:

48px.

Botón:

50px.

---

# 31. MOBILE HOME

Mostrar:

### Header

* Saludo.
* Avatar.

### Tarjeta "Hoy"

Utilizar imagen:

`strength-equipment`

Mostrar:

* nombre del entrenamiento;
* botón **Comenzar entrenamiento**.

### Stats

Mostrar:

* Peso.
* Racha.
* Sesiones del mes.

### Entrenador IA

Tarjeta oscura para acceder al Entrenador IA.

### Semana

Mostrar días completados.

### Navegación

Barra inferior con:

* Inicio.
* Rutina.
* IA.
* Progreso.
* Perfil.

---

# 32. MOBILE — ENTRENAMIENTO ACTIVO

Inspiración visual:

apps modernas de tracking como Hevy/Strong.

### Header

Botón:

**Finalizar**

### Stats

* Duración.
* Volumen.
* Series.

### Ejercicio

Tarjeta con tabla:

* Serie.
* Anterior.
* Kg.
* Reps.

Los valores deben poder editarse visualmente.

Agregar checks de completado.

Mostrar pill de progreso de peso.

### Máquina ocupada

La segunda tarjeta debe mostrar:

**Máquina ocupada**

Mostrar las mismas opciones del Plan B:

1. Máquina similar.
2. Calistenia.
3. Saltar.

Una opción debe aparecer preseleccionada.

Mostrar un tercer ejercicio parcialmente visible debajo para sugerir scroll.

---

# 33. MOBILE — ENTRENADOR IA

Crear interfaz de chat.

### Burbujas

Diferenciar:

* IA.
* Usuario.

### Conversación

Utilizar como contexto la lesión de rodilla registrada de Daniela.

La IA debe explicar mediante mensajes simulados que está ajustando la rutina debido a esa lesión.

No implementar IA real.

### Acciones rápidas

Agregar chips de respuesta.

### Input

Mostrar:

* campo de mensaje;
* micrófono;
* cámara.

---

# 34. MOBILE — AGREGAR MÁQUINA / CÁMARA

Crear un visor de cámara simulado.

Pantalla completa.

Fondo negro.

### Elementos

* guías de encuadre en las esquinas;
* carrete de fotografías tomadas;
* contador;
* galería;
* disparador;
* flash.

No utilizar cámara real.

El disparador debe simular una fotografía tomada.

---

# 35. MOBILE — AGREGAR MÁQUINA / CONFIRMAR

Mostrar fotografía recién tomada.

Mostrar resultado simulado de clasificación:

**Prensa de piernas**

**92% de confianza**

**Grupo: Piernas**

Permitir editar visualmente los campos en caso de clasificación incorrecta.

Botones:

**Guardar y agregar otra**

**Guardar y terminar**

No utilizar IA real.

---

# 36. FLUJOS PRINCIPALES QUE DEBE PODER DEMOSTRAR EL PROTOTIPO

El prototipo debe permitir demostrar al menos estos flujos:

## Flujo 1 — Administrador

Dashboard → Clientes → Daniela → Ficha → Rutina.

## Flujo 2 — Crear cliente

Clientes → Nuevo cliente → Completar formulario → Guardar.

## Flujo 3 — Membresía

Membresías → Seleccionar plan → Estado simulado.

## Flujo 4 — Asistencia

Asistencia → Buscar cliente → Registrar entrada.

## Flujo 5 — Pago

Pagos → Seleccionar cliente → Seleccionar plan → Método → Registrar pago.

## Flujo 6 — Lesión

Daniela → Mediciones → Ver lesión → Rutina ajustada.

## Flujo 7 — Rutina

Rutinas → Daniela → Día → Ejercicio → Máquina ocupada → Plan B.

## Flujo 8 — Cliente

Login → Home → Entrenamiento → Ejercicio → Máquina ocupada → Alternativa.

## Flujo 9 — Entrenador IA

Home → Entrenador IA → Conversación → Ajuste de rutina.

## Flujo 10 — Agregar máquina

Home/Perfil → Agregar máquina → Cámara simulada → Capturar → Confirmar clasificación → Guardar.

---

# 37. CONSISTENCIA NARRATIVA

Daniela Vargas debe funcionar como el principal caso de demostración.

Su información debe mantenerse coherente:

* Tiene una lesión de rodilla activa.
* Su rutina debe reflejar esa lesión.
* El ejercicio "Remo en polea baja" puede mostrar disponibilidad de máquina.
* El Plan B debe aparecer tanto en el panel administrativo como en el móvil.
* El Entrenador IA debe utilizar la lesión como contexto.
* La experiencia debe demostrar que el sistema adapta la rutina según las condiciones registradas.

---

# 38. RESPONSIVE DESIGN

El prototipo debe funcionar correctamente en:

### Desktop

Panel administrativo completo.

### Tablet

Adaptar grids y tablas.

### Mobile

Utilizar la experiencia móvil definida en la Fase 4.

No simplemente reducir la versión desktop.

La experiencia móvil debe utilizar su propia navegación inferior y estructura.

---

# 39. ESTADOS VISUALES

El prototipo debe representar diferentes estados:

### Éxito

* Pagado.
* Activo.
* Disponible.
* Registrado.

### Advertencia

* Por vencer.
* Pendiente.
* Máquina ocupada.

### Peligro

* Vencido.
* Lesión activa.

Utilizar los colores definidos anteriormente.

---

# 40. QUÉ NO DEBE HACER LOVABLE

No convertir este proyecto en una implementación de producción innecesariamente compleja.

No agregar:

* funcionalidades que no estén especificadas;
* módulos administrativos adicionales;
* sistemas de IA reales;
* sistemas de pago reales;
* bases de datos reales;
* APIs externas;
* sensores;
* funcionalidades IoT;
* autenticación externa.

Si alguna funcionalidad necesita backend para funcionar, **simularla visualmente**.

No inventar nuevos flujos importantes sin necesidad.

No modificar arbitrariamente los colores, nombres, personajes o estructura descritos en este documento.

---

# 41. RESULTADO ESPERADO

El resultado final debe ser un:

## **PROTOTIPO INTERACTIVO DE ALTA FIDELIDAD DE PULSE GYM**

Debe verse como un producto moderno y listo para ser presentado, pero debe quedar claro por su implementación que se trata de un prototipo.

Debe permitir:

* recorrer las pantallas;
* demostrar los principales casos de uso;
* visualizar el panel administrativo;
* visualizar la experiencia del cliente;
* demostrar el flujo de rutina;
* demostrar el flujo relacionado con lesiones;
* demostrar el Plan B del Entrenador IA;
* demostrar el flujo móvil;
* demostrar la cámara y clasificación como simulación.

La prioridad absoluta es:

**DISEÑO + NAVEGACIÓN + INTERACCIÓN + CONSISTENCIA**

y no la implementación de backend.

---

# 42. PENDIENTES QUE PUEDEN QUEDAR FUERA DEL PROTOTIPO

Estas funcionalidades no necesitan implementarse ahora:

* Progreso mediante fotografías antes/después.
* Mapa real de ocupación de máquinas.
* Sistema real de logros/insignias.
* Búsqueda contextual real del topbar.
* Determinación real de si una máquina está ocupada.

En particular, el mecanismo real para determinar si una máquina está ocupada queda abierto para una futura fase:

* sensor IoT;
* check-in manual;
* otro mecanismo.

Para este prototipo simplemente **simular el estado de máquina ocupada**.

---

# 43. INSTRUCCIÓN FINAL

Antes de implementar cada pantalla, utiliza esta especificación como fuente principal.

Mantén una **identidad visual única de Pulse Gym** en todas las vistas.

No priorices la complejidad técnica sobre la calidad del prototipo.

Quiero poder abrir el proyecto y presentarlo inmediatamente como:

> **Prototipo interactivo de alta fidelidad del sistema Pulse Gym.**

El resultado debe sentirse coherente, moderno, profesional y navegable.
