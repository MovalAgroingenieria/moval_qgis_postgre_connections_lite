"""Deteccion y actualizacion de las conexiones PostgreSQL del proyecto.

Toda la logica vive aqui, sin interfaz, para poder probarla sin abrir ventanas.

Las capas del proyecto se agrupan por servidor (host, puerto, base de datos): un
proyecto con treinta capas del mismo servidor es una sola cosa que actualizar, no
treinta. La conexion guardada correspondiente se localiza por nombre de base de
datos, que es lo que identifica de verdad a una conexion; el nombre que le haya
puesto cada usuario es libre y no sirve para cruzar.
"""

import contextlib

from qgis.core import (
    QgsCredentials,
    QgsDataProvider,
    QgsDataSourceUri,
    QgsProject,
    QgsSettings,
)

PG_PROVIDER_NAMES = ("postgres", "postgresraster")
CONNECTIONS_GROUP = "PostgreSQL/connections"


# --------------------------------------------------------------- reentrada

def map_canvas():
    """Lienzo de QGIS, o None si el complemento se usa fuera de la aplicacion."""
    try:
        from qgis.utils import iface

        return iface.mapCanvas() if iface is not None else None
    except Exception:
        return None


@contextlib.contextmanager
def canvas_guard(canvas=None):
    """Impide que el lienzo repinte mientras se sustituye el origen de datos.

    Sustituir el proveedor de una capa la deja unos instantes en un estado
    inconsistente. Si en ese momento QGIS necesita credenciales, abre un dialogo
    modal cuyo bucle de eventos anidado deja correr el temporizador del lienzo: el
    repintado lee la capa a medio construir y QGIS se cierra con una violacion de
    acceso. Congelar el lienzo elimina ese repintado.

    Todo va protegido: si alguna de estas llamadas no existiera en una version de
    QGIS, la operacion debe seguir adelante igualmente.
    """
    canvas = canvas if canvas is not None else map_canvas()
    if canvas is None:
        yield
        return

    previous_render = None
    try:
        canvas.stopRendering()
        if hasattr(canvas, "renderFlag"):
            previous_render = canvas.renderFlag()
            canvas.setRenderFlag(False)
        canvas.freeze(True)
    except Exception:
        pass

    try:
        yield
    finally:
        try:
            canvas.freeze(False)
            if previous_render is not None:
                canvas.setRenderFlag(previous_render)
            canvas.refresh()
        except Exception:
            pass


def seed_credentials(uri, username, password):
    """Deja las credenciales en la cache de QGIS antes de reconectar.

    Asi el proveedor las encuentra y no abre el dialogo modal de login, que es lo
    que provocaba la reentrada. La clave se queda solo en memoria: no se escribe en
    la URI de la capa, para que no acabe en el archivo del proyecto.
    """
    if not username and not password:
        return ""
    try:
        realm = uri.connectionInfo(False)
        QgsCredentials.instance().put(realm, username, password)
        return realm
    except Exception:
        return ""


def _uri_of(layer):
    return QgsDataSourceUri(layer.source())


def postgres_layers(project=None):
    """Capas PostgreSQL/PostGIS del proyecto."""
    project = project if project is not None else QgsProject.instance()
    found = []
    for layer in project.mapLayers().values():
        try:
            provider = layer.dataProvider()
        except Exception:
            continue
        if provider is None or provider.name() not in PG_PROVIDER_NAMES:
            continue
        found.append(layer)
    return found


def saved_connections():
    """Conexiones guardadas: {nombre: {host, port, database, service}}."""
    settings = QgsSettings()
    settings.beginGroup(CONNECTIONS_GROUP)
    names = settings.childGroups()
    settings.endGroup()

    result = {}
    for name in names:
        base = f"{CONNECTIONS_GROUP}/{name}"
        result[name] = {
            "host": str(settings.value(f"{base}/host", "") or ""),
            "port": str(settings.value(f"{base}/port", "") or ""),
            "database": str(settings.value(f"{base}/database", "") or ""),
            "service": str(settings.value(f"{base}/service", "") or ""),
        }
    return result


def scan_project(project=None):
    """Agrupa las capas del proyecto por servidor.

    Devuelve una lista de diccionarios con:
      host, port, database  -> valores actuales
      layers                -> capas afectadas
      saved                 -> nombres de conexiones guardadas con esa base de datos
      service               -> nombre del servicio, si la capa usa pg_service.conf
    """
    saved = saved_connections()
    by_database = {}
    for name, values in saved.items():
        database = values["database"].strip().casefold()
        if database:
            by_database.setdefault(database, []).append(name)
    for names in by_database.values():
        names.sort(key=str.lower)

    groups = {}
    for layer in postgres_layers(project):
        uri = _uri_of(layer)
        key = (uri.host(), uri.port(), uri.database(), uri.service())
        group = groups.get(key)
        if group is None:
            group = {
                "host": uri.host(),
                "port": uri.port(),
                "database": uri.database(),
                "service": uri.service(),
                "layers": [],
                "saved": by_database.get(uri.database().strip().casefold(), []),
            }
            groups[key] = group
        group["layers"].append(layer)

    ordered = sorted(
        groups.values(),
        key=lambda g: (g["database"].lower(), g["host"].lower(), g["port"]),
    )
    return ordered


def validate_port(value):
    """Devuelve (valido, mensaje). Vacio es valido: significa 'no cambiar'."""
    text = str(value or "").strip()
    if not text:
        return True, ""
    if not text.isdigit() or not (1 <= int(text) <= 65535):
        return False, f"El puerto '{text}' no es valido (debe estar entre 1 y 65535)."
    return True, ""


def apply_to_layers(layers, host, port, username="", password=""):
    """Reescribe las capas con el host y el puerto indicados.

    Devuelve (actualizadas, invalidas, fallidas). Las que quedan invalidas conservan
    el dato nuevo: puede tratarse de un servidor correcto pero aun no accesible desde
    el equipo, y revertirlo dejaria al usuario sin el cambio que ha pedido.

    Debe llamarse dentro de canvas_guard(): sustituir el proveedor con el lienzo
    activo puede cerrar QGIS.
    """
    updated, invalid, failed = [], [], []
    options = QgsDataProvider.ProviderOptions()

    for layer in layers:
        try:
            uri = _uri_of(layer)
            user = username or uri.username()
            # Si se han indicado credenciales nuevas, se retira la clave guardada en
            # la URI: la del servidor anterior podria no valer para el nuevo.
            stored_password = "" if password else uri.password()

            uri.setConnection(
                host if host else uri.host(),
                port if port else uri.port(),
                uri.database(),
                user,
                stored_password,
                uri.sslMode(),
                uri.authConfigId(),
            )
            seed_credentials(uri, user, password)
            layer.setDataSource(uri.uri(False), layer.name(), layer.providerType(),
                                options)
        except Exception:
            # Una capa problematica no debe abortar el resto de la operacion.
            failed.append(layer)
            continue
        updated.append(layer)

    return updated, invalid, failed


def apply_to_saved(names, host, port):
    """Actualiza el host y el puerto de las conexiones guardadas indicadas."""
    if not names:
        return []
    settings = QgsSettings()
    changed = []
    for name in names:
        base = f"{CONNECTIONS_GROUP}/{name}"
        if host:
            settings.setValue(f"{base}/host", host)
        if port:
            settings.setValue(f"{base}/port", port)
        changed.append(name)
    settings.sync()
    return changed


def apply_group(group, new_host, new_port, username="", password=""):
    """Aplica los datos nuevos a un grupo. Devuelve un resumen del resultado.

    Pensada para llamarse desde apply_all(), que es quien congela el lienzo.
    """
    host = str(new_host or "").strip()
    port = str(new_port or "").strip()
    if not host and not port:
        return None

    updated, invalid, failed = apply_to_layers(
        group["layers"], host, port, username, password)
    saved = apply_to_saved(group["saved"], host, port)
    return {
        "database": group["database"],
        "host": host or group["host"],
        "port": port or group["port"],
        "layers_ok": updated,
        "layers_invalid": invalid,
        "layers_failed": failed,
        "saved": saved,
    }


def apply_all(items, username="", password=""):
    """Aplica todos los cambios con el lienzo congelado.

    'items' es [(grupo, host_nuevo, puerto_nuevo)]. Es el unico punto de entrada
    que deberia usar la interfaz: garantiza que ninguna sustitucion de proveedor
    ocurra con el lienzo repintando.
    """
    resultados = []
    with canvas_guard():
        for group, host, port in items:
            resultado = apply_group(group, host, port, username, password)
            if resultado is not None:
                resultados.append(resultado)

    # La validez se comprueba con el lienzo ya descongelado: preguntarla durante la
    # sustitucion puede forzar una conexion en mal momento.
    for resultado in resultados:
        todavia_ok, invalidas = [], list(resultado["layers_invalid"])
        for layer in resultado["layers_ok"]:
            try:
                (todavia_ok if layer.isValid() else invalidas).append(layer)
            except RuntimeError:
                pass
        resultado["layers_ok"] = todavia_ok
        resultado["layers_invalid"] = invalidas
    return resultados


def refresh_provider_cache():
    """Avisa a QGIS de que las conexiones guardadas han cambiado."""
    try:
        from qgis.core import QgsProviderRegistry

        metadata = QgsProviderRegistry.instance().providerMetadata("postgres")
        if metadata is None:
            return
        metadata.connections(False)
        try:
            from qgis.utils import iface

            if iface is not None:
                iface.browserModel().reload()
        except Exception:
            pass
    except Exception:
        pass
