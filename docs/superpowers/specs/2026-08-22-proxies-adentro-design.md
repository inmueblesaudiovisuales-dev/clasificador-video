# Los proxies, adentro de la carpeta del material

*(Spec aprobado por Bruno el 2026-08-22. Revierte a propósito una decisión
suya del 2026-08-10.)*

## Lo que cambia, y por qué revierte algo

Hoy los proxies van a una carpeta **`Proxies` al lado** de la del material.
Bruno lo eligió así el 2026-08-10 con este argumento: *adentro ensuciaría la
copia de la tarjeta, que es justo lo que uno quiere poder volver a copiar tal
cual.*

Ahora pide lo contrario: **adentro**, `01. VIDEOS SONY/Proxies/`. La razón
nueva es que así **los proxies viajan con el material**: mueves o copias la
carpeta a otro disco y se van con ella, en vez de quedarse huérfanos al lado.

Queda escrito el costo que él aceptó: **la copia de respaldo de la tarjeta
ahora pesa más**, porque incluye los proxies.

## Lo que se construye

### 1. Los proxies nuevos van adentro

`carpeta_de_proxies` pasa a devolver `<carpeta del material>/Proxies`. Es el
único lugar del código que decide dónde viven, así que el cambio es de una
línea — lo demás es no romper lo que ya existe.

**Meter la carpeta adentro NO hace que se reimporten como clips.** El ingest
toma solo los archivos directos de una carpeta y no baja a las subcarpetas —
una regla que ya existía para no tragarse las carpetas de sistema de la
tarjeta. Comprobado antes de proponerlo; era el riesgo grande y no existe.

### 2. Los de antes siguen sirviendo

Al buscar un proxy se miran **dos lugares, en este orden**:

1. adentro (`<material>/Proxies`), que es donde van los nuevos;
2. al lado (`<material>/../Proxies`), que es donde están los viejos.

Gana el primero que exista. Con eso, un proyecto de antes abre igual: nada se
regenera y nada se mueve.

**Los viejos NO se mudan.** Mover archivos que ya funcionan es riesgo sin
ganancia — y un proyecto abierto en otra computadora, o con la carpeta vieja
compartida entre dos bins, convierte esa mudanza en algo que hay que deshacer
a mano. Si Bruno quiere juntarlos algún día, los arrastra él.

**Nada de esto toca el `.cvproj`.** Un proxy ya enganchado guarda su ruta
completa: el proyecto abre exactamente igual que hoy.

### 3. Si no se puede escribir adentro, se escribe al lado

El material puede estar en una tarjeta protegida contra escritura, o llena.
Antes eso no importaba —se escribía al lado, casi siempre en otro disco— y
ahora sí.

Cuando la carpeta del material no se pueda escribir, los proxies **caen al
lado**, que es donde funcionaban, y se anota en el log. No se falla: quedarse
sin proxies por dónde iba a ir la carpeta sería peor que ponerla un nivel
arriba.

## Lo que NO cambia

- **El nombre es `Proxies`**, el mismo de siempre. Elegido para que en un
  proyecto que ya tenga proxies no convivan dos carpetas con nombres
  distintos.
- Los proxies siguen terminando en **`S03`**, así que si alguien arrastra esa
  carpeta como material, el ingest los descarta igual.
- **Enlazar proxies a mano** sigue funcionando desde cualquier carpeta: ahí
  eliges el archivo y el patrón sale de él.
- La validación cuadro a cuadro no se toca.

## Cómo se prueba

- Un proxy nuevo se escribe adentro de la carpeta del material.
- Un proxy que está al lado —de antes— se encuentra y no se regenera.
- Si están en los dos lados, gana el de adentro.
- Un clip sin proxy en ninguno de los dos entra a la lista de pendientes.
- Con la carpeta del material sin permiso de escritura, se escribe al lado.
- Importar la carpeta del material **no** trae los proxies como clips.
