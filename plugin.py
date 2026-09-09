"""Ciclo de vida del complemento.

Version LITE, pensada para entregar a clientes: una sola entrada de menu, un solo
dialogo y ninguna dependencia del paquete compartido de la suite Moval GIS. La
carpeta se copia tal cual y funciona.
"""

from qgis.PyQt.QtWidgets import QAction

from .branding import PLUGIN_NAME, plugin_icon
from .dialog import LiteDialog

MENU_TEXT = f"&{PLUGIN_NAME}"


class MovalPgLitePlugin:

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction(plugin_icon(), PLUGIN_NAME, self.iface.mainWindow())
        self.action.setObjectName("movalPgLiteAction")
        self.action.setWhatsThis(
            "Actualiza el host y el puerto de las conexiones PostgreSQL del proyecto")
        self.action.triggered.connect(self.run)

        self.iface.addPluginToDatabaseMenu(MENU_TEXT, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        # Idempotente: QGIS puede llamarlo mas de una vez al recargar el complemento.
        if self.action is not None:
            self.iface.removePluginDatabaseMenu(MENU_TEXT, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

        if self.dialog is not None:
            self.dialog.close()
            self.dialog = None

    def run(self):
        if self.dialog is None:
            self.dialog = LiteDialog(self.iface.mainWindow())
        self.dialog.refresh()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
