def classFactory(iface):  # noqa: N802 (nombre impuesto por la API de QGIS)
    from .plugin import MovalPgLitePlugin

    return MovalPgLitePlugin(iface)
