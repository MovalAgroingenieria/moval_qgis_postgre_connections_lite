# Moval - Actualizar conexiones PostgreSQL Lite

Complemento de QGIS para **cambiar el servidor de las conexiones PostgreSQL que
usa un proyecto**. Pensado para entregar a personas ajenas a Moval: hace una sola
cosa, en una sola ventana.

## Qué hace

Al abrirlo muestra las conexiones PostgreSQL que usa el proyecto abierto, con su
host, su puerto y su base de datos. Se escribe el host o el puerto nuevos y se
pulsa **Actualizar**. El cambio se aplica a la vez a:

- las **capas cargadas** en el proyecto, y
- la **conexión guardada** en QGIS correspondiente a esa base de datos.

Lo que se deja **en blanco no se toca**: si solo cambia el puerto, se rellena el
puerto y el host se queda como está.

## Instalación

1. Copie la carpeta `moval_qgis_postgre_connections_lite` en la carpeta de
   complementos de su perfil de QGIS. En Windows suele ser:

   ```
   %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
   ```

   Puede abrirla desde QGIS en *Complementos > Administrar e instalar complementos
   > Configuración > Abrir la carpeta de complementos*.

2. Reinicie QGIS y actívelo en *Complementos > Administrar e instalar complementos
   > Instalados*.

3. Aparece en el menú **Base de datos** y como icono en la barra de herramientas.

También se puede instalar desde un ZIP de la carpeta, con *Instalar desde ZIP*.

## Uso

1. Abra el proyecto que quiera actualizar.
2. Abra el complemento. Cada fila es un servidor, no una capa: si el proyecto
   tiene treinta capas del mismo servidor, aparecen como una sola fila, y la
   columna *Capas* indica cuántas son (pose el ratón para ver sus nombres).
3. Escriba el **host nuevo**, el **puerto nuevo**, o ambos, solo en las filas que
   deba cambiar. La tabla se lee por el color:
   - **Fondo crema** (color institucional secundario): dato que **no se puede
     modificar**. Son las columnas informativas y las casillas bloqueadas.
   - **Fondo blanco o el del tema**: casilla donde **sí** se puede escribir.
   - **Fondo verde corporativo**: el valor nuevo que se va a aplicar.
   - El valor al que sustituye aparece **tachado y en cursiva**, conservando su
     fondo crema.
   - Escribir el mismo valor que ya había, o dejarlo en blanco, cuenta como "no
     cambiar", y el resalte desaparece.
4. Si el servidor nuevo va a pedir credenciales, rellene **Usuario** y
   **Contraseña**. Son opcionales, pero conviene: evitan que QGIS las pregunte capa
   por capa. La contraseña **no se guarda en el proyecto**; solo se usa durante esa
   sesión de QGIS.
5. La línea inferior resume cuántas capas y cuántas conexiones guardadas se van a
   actualizar. El botón **Actualizar** solo se habilita si hay algo que cambiar.
6. Confirme el resumen. Al terminar, **guarde el proyecto** para conservar los
   cambios en las capas (las conexiones guardadas de QGIS sí quedan guardadas al
   instante).

## Detalles que conviene saber

- **La correspondencia con la conexión guardada se hace por el nombre de la base
  de datos**, no por el nombre de la conexión. El nombre de una conexión lo pone
  cada usuario y no sirve para identificarla. Si no existe una conexión guardada
  para esa base de datos, la columna muestra `—` y solo se actualizan las capas.
- **Se conserva todo lo demás de la capa**: esquema, tabla, columna de geometría,
  columna clave, SRID y filtro. Solo cambian el host y el puerto.
- **Si una capa no responde con el dato nuevo**, el cambio se guarda igualmente y
  se avisa al final. Es lo deseable cuando se apunta a un servidor que todavía no
  es accesible desde ese equipo; si fuera un error de escritura, basta con volver
  a abrir el complemento y corregirlo.
- **Las conexiones que usan un servicio** de `pg_service.conf` aparecen como
  `(servicio nombre)` y no se pueden editar aquí: su host y su puerto están
  definidos en ese archivo.
- El complemento **no borra ni crea conexiones** y no envía nada a ningún sitio. Se
  limita a reescribir host y puerto.

## Nota técnica: por qué se congela el mapa al actualizar

Durante la actualización el mapa se queda unos instantes sin repintar. Es
deliberado. Sustituir el origen de datos de una capa la deja momentáneamente en un
estado inconsistente; si en ese momento QGIS abre el diálogo modal de credenciales,
su bucle de eventos anidado permite que el temporizador del mapa dispare un
repintado sobre esa capa a medio reconstruir, y QGIS **se cierra** con una
violación de acceso.

La versión 1.1 lo corrige por partida doble: congela el mapa mientras dura la
operación, y siembra las credenciales que se hayan indicado para que el diálogo no
llegue a abrirse. Si aun así apareciera, ya no puede tumbar el programa.

## Diferencias con la versión completa

Esta versión es un subconjunto deliberado del complemento interno *Moval -
Administrador de conexiones PostgreSQL*. No incluye la importación masiva desde
CSV, la generación de `pg_service.conf`, el autocompletado del diálogo nativo ni
la integración con el menú **Moval GIS**.

Es **autónoma**: no depende del paquete compartido de la suite, de modo que la
carpeta se copia tal cual y funciona. Los colores corporativos están únicamente en
`branding.py`; si cambia el Manual de Marca, se cambia ahí.

Sobre el uso del color: se emplea el par aprobado y su inverso, nunca un color de
texto suelto sobre el fondo heredado del diálogo. Un color de texto sin fondo
propio no es legible a la vez en el tema claro y en el oscuro de QGIS; por eso las
celdas de solo lectura fijan **fondo crema con texto verde**, y las de valor nuevo
**fondo verde con texto crema**.

## Estructura

```
moval_qgis_postgre_connections_lite/
├── __init__.py       classFactory
├── plugin.py         alta y baja: una accion, un dialogo
├── dialog.py         la ventana
├── connections.py    logica: detectar, agrupar y actualizar (sin interfaz)
├── branding.py       identidad visual de Moval
├── metadata.txt
└── icon.png
```
