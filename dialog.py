"""Ventana unica del complemento.

Una tabla y dos botones. Cada fila es un servidor del proyecto: se muestran sus
datos actuales y hay dos casillas para escribir los nuevos. Lo que se deje en
blanco no se toca.
"""

from qgis.PyQt import QtCore, QtWidgets

from . import connections
from .branding import (
    apply_window_branding,
    mark_as_new,
    mark_as_replaced,
    style_editable,
    style_readonly,
)

COL_DB = 0
COL_HOST = 1
COL_PORT = 2
COL_NEW_HOST = 3
COL_NEW_PORT = 4
COL_LAYERS = 5
COL_SAVED = 6

HEADERS = [
    "Base de datos",
    "Host actual",
    "Puerto actual",
    "Host nuevo",
    "Puerto nuevo",
    "Capas",
    "Conexion guardada",
]

EDITABLE = (COL_NEW_HOST, COL_NEW_PORT)


class LiteDialog(QtWidgets.QDialog):
    """Actualiza el servidor de las conexiones PostgreSQL del proyecto."""

    def __init__(self, parent=None):
        super().__init__(parent)
        apply_window_branding(self, "Actualizar conexiones PostgreSQL Lite")
        self.resize(940, 420)

        self._groups = []
        self._updating = False
        self._build_ui()

    # ------------------------------------------------------------------ interfaz
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.intro = QtWidgets.QLabel(
            "Estas son las conexiones PostgreSQL que usa el proyecto abierto. "
            "Escriba el host o el puerto nuevos solo donde haga falta: "
            "<b>lo que deje en blanco se queda como esta</b>."
        )
        self.intro.setWordWrap(True)
        self.intro.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(self.intro)

        self.table = QtWidgets.QTableWidget(0, len(HEADERS), self)
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table, 1)

        credenciales = QtWidgets.QHBoxLayout()
        credenciales.addWidget(QtWidgets.QLabel(
            "Si el servidor nuevo pide credenciales:"))
        credenciales.addWidget(QtWidgets.QLabel("Usuario"))
        self.user_edit = QtWidgets.QLineEdit()
        self.user_edit.setPlaceholderText("opcional")
        self.user_edit.setMaximumWidth(160)
        credenciales.addWidget(self.user_edit)
        credenciales.addWidget(QtWidgets.QLabel("Contrasena"))
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setPlaceholderText("opcional")
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password_edit.setMaximumWidth(160)
        credenciales.addWidget(self.password_edit)
        credenciales.addStretch()
        layout.addLayout(credenciales)

        self.hint = QtWidgets.QLabel(
            "Rellenarlos evita que QGIS los pregunte capa por capa. No se guardan en "
            "el proyecto: solo se usan durante esta sesion."
        )
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        self.apply_button = QtWidgets.QPushButton("Actualizar")
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.apply_changes)
        self.close_button = QtWidgets.QPushButton("Cerrar")
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    # -------------------------------------------------------------------- datos
    def refresh(self):
        self._groups = connections.scan_project()
        self._updating = True
        try:
            self.table.setRowCount(0)
            for group in self._groups:
                self._add_row(group)
            self.table.resizeColumnsToContents()
        finally:
            self._updating = False
        self._update_status()

    def _add_row(self, group):
        row = self.table.rowCount()
        self.table.insertRow(row)

        usa_servicio = bool(group["service"])
        valores = {
            COL_DB: group["database"],
            COL_HOST: group["service"] and f"(servicio {group['service']})" or group["host"],
            COL_PORT: "" if usa_servicio else group["port"],
            COL_NEW_HOST: "",
            COL_NEW_PORT: "",
            COL_LAYERS: str(len(group["layers"])),
            COL_SAVED: ", ".join(group["saved"]) if group["saved"] else "—",
        }

        for column, text in valores.items():
            item = QtWidgets.QTableWidgetItem(text)
            editable = column in EDITABLE and not usa_servicio
            if editable:
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled
                              | QtCore.Qt.ItemFlag.ItemIsEditable)
                item.setToolTip("Dejar en blanco para no cambiarlo")
                style_editable(item)
            else:
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                # Color institucional secundario: lo que aqui se ve no se toca.
                style_readonly(item)
            self.table.setItem(row, column, item)

        if usa_servicio:
            for column in (COL_DB, COL_HOST, COL_PORT, COL_LAYERS, COL_SAVED):
                self.table.item(row, column).setToolTip(
                    "Esta conexion usa un servicio de pg_service.conf: el host y el "
                    "puerto se definen en ese archivo, no aqui."
                )

        nombres = ", ".join(layer.name() for layer in group["layers"])
        self.table.item(row, COL_LAYERS).setToolTip(nombres)

    # -------------------------------------------------------------------- edicion
    def _on_item_changed(self, item):
        if self._updating or item.column() not in EDITABLE:
            return
        self._updating = True
        try:
            self._restyle_row(item.row())
        finally:
            self._updating = False
        self._update_status()

    def _restyle_row(self, row):
        """Marca en cada columna si su valor va a cambiar."""
        for actual, nuevo in ((COL_HOST, COL_NEW_HOST), (COL_PORT, COL_NEW_PORT)):
            item_actual = self.table.item(row, actual)
            item_nuevo = self.table.item(row, nuevo)
            if item_actual is None or item_nuevo is None:
                continue

            texto = item_nuevo.text().strip()
            cambia = bool(texto) and texto != item_actual.text().strip()
            # La celda actual conserva siempre su fondo institucional; solo cambia
            # la tipografia para indicar que va a ser sustituida.
            style_readonly(item_actual)
            if cambia:
                mark_as_replaced(item_actual)
                mark_as_new(item_nuevo)
            else:
                style_editable(item_nuevo)

    def _pending(self):
        """Filas con algo que cambiar: [(grupo, host, puerto)]."""
        pending = []
        for row, group in enumerate(self._groups):
            if row >= self.table.rowCount():
                break
            host = self.table.item(row, COL_NEW_HOST).text().strip()
            port = self.table.item(row, COL_NEW_PORT).text().strip()
            if host == group["host"]:
                host = ""
            if port == group["port"]:
                port = ""
            if host or port:
                pending.append((group, host, port))
        return pending

    def _update_status(self):
        pending = self._pending()
        if not self._groups:
            self.status.setText(
                "El proyecto abierto no tiene ninguna capa PostgreSQL.")
        elif not pending:
            self.status.setText(
                f"{len(self._groups)} conexion(es) en el proyecto. "
                "Escriba un host o un puerto nuevo para habilitar la actualizacion.")
        else:
            capas = sum(len(g["layers"]) for g, _h, _p in pending)
            guardadas = sum(len(g["saved"]) for g, _h, _p in pending)
            self.status.setText(
                f"Se actualizaran {len(pending)} conexion(es): "
                f"{capas} capa(s) del proyecto y {guardadas} conexion(es) guardada(s).")
        self.apply_button.setEnabled(bool(pending))

    # ------------------------------------------------------------------ aplicar
    def apply_changes(self):
        pending = self._pending()
        if not pending:
            return

        for group, _host, port in pending:
            valido, mensaje = connections.validate_port(port)
            if not valido:
                QtWidgets.QMessageBox.warning(self, "Dato no valido", mensaje)
                return

        detalle = "\n".join(
            f"  - {g['database']}:  {g['host']}:{g['port']}  ->  "
            f"{h or g['host']}:{p or g['port']}"
            for g, h, p in pending
        )
        if QtWidgets.QMessageBox.question(
            self, "Actualizar conexiones",
            f"Se actualizaran {len(pending)} conexion(es):\n\n{detalle}\n\n"
            "Se cambian tanto las capas del proyecto como las conexiones guardadas.\n\n"
            "¿Desea continuar?"
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        # apply_all congela el lienzo: sustituir el proveedor con el mapa
        # repintando puede cerrar QGIS.
        resultados = connections.apply_all(
            pending,
            self.user_edit.text().strip(),
            self.password_edit.text(),
        )

        capas = sum(len(r["layers_ok"]) for r in resultados)
        guardadas = sum(len(r["saved"]) for r in resultados)
        invalidas = [c for r in resultados for c in r["layers_invalid"]]
        fallidas = [c for r in resultados for c in r.get("layers_failed", [])]

        connections.refresh_provider_cache()

        resumen = (f"Actualizadas {capas} capa(s) del proyecto y "
                   f"{guardadas} conexion(es) guardada(s).")
        if invalidas:
            resumen += ("\n\nAviso: estas capas no responden con el dato nuevo: "
                        f"{self._nombres(invalidas)}.\nEl cambio se ha guardado "
                        "igualmente; compruebe que el servidor sea accesible desde "
                        "este equipo y que el usuario y la contrasena sean correctos.")
        if fallidas:
            resumen += ("\n\nNo se han podido modificar: "
                        f"{self._nombres(fallidas)}.")
        resumen += "\n\nRecuerde guardar el proyecto para conservar los cambios."

        QtWidgets.QMessageBox.information(self, "Actualizar conexiones", resumen)
        self.refresh()

    @staticmethod
    def _nombres(capas, limite=5):
        nombres = ", ".join(layer.name() for layer in capas[:limite])
        if len(capas) > limite:
            nombres += f" y {len(capas) - limite} mas"
        return nombres
