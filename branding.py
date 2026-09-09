"""Identidad visual de Moval para la version LITE.

Version autonoma: no depende del paquete compartido de la suite, para que el
complemento se pueda entregar a un cliente como una sola carpeta.

Par de colores aprobado en el Manual de Marca. No se escriben colores literales
en ningun otro modulo: si la marca cambia, se cambia aqui.
"""

import os

from qgis.PyQt import QtGui

PLUGIN_NAME = "Moval - Actualizar conexiones PostgreSQL Lite"
WINDOW_SUFFIX = "Moval GIS"

ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png")

#: Par aprobado: fondo verde corporativo con texto crema. Marca lo que va a cambiar.
SELECTION_BG = "#1E4C3D"
SELECTION_FG = "#EBDAAD"

#: El mismo par invertido: crema con texto verde. Marca lo que no se puede editar.
#: Se fija siempre el color de texto ademas del de fondo: sobre un fondo crema, el
#: texto claro que hereda el tema oscuro de QGIS seria ilegible.
READONLY_BG = SELECTION_FG
READONLY_FG = SELECTION_BG


def plugin_icon():
    return QtGui.QIcon(ICON_PATH) if os.path.exists(ICON_PATH) else QtGui.QIcon()


def window_title(text):
    return f"{text} · {WINDOW_SUFFIX}"


def apply_window_branding(widget, text):
    widget.setWindowTitle(window_title(text))
    if os.path.exists(ICON_PATH):
        widget.setWindowIcon(QtGui.QIcon(ICON_PATH))


def _set_font(item, bold=False, strike=False, italic=False):
    font = item.font()
    font.setBold(bold)
    font.setStrikeOut(strike)
    font.setItalic(italic)
    item.setFont(font)


def style_readonly(item):
    """Estilo base de una celda que no se puede modificar: par institucional inverso."""
    item.setBackground(QtGui.QBrush(QtGui.QColor(READONLY_BG)))
    item.setForeground(QtGui.QBrush(QtGui.QColor(READONLY_FG)))
    _set_font(item)


def style_editable(item):
    """Estilo base de una celda donde se puede escribir: la deja con el color del tema."""
    item.setBackground(QtGui.QBrush())
    item.setForeground(QtGui.QBrush())
    _set_font(item)


def mark_as_new(item):
    """Resalta un valor nuevo con el par corporativo."""
    item.setBackground(QtGui.QBrush(QtGui.QColor(SELECTION_BG)))
    item.setForeground(QtGui.QBrush(QtGui.QColor(SELECTION_FG)))
    _set_font(item, bold=True)


def mark_as_replaced(item):
    """Marca un valor que va a ser sustituido, sin tocar sus colores.

    Se usa tachado y cursiva porque son independientes del color: asi la marca se
    superpone al fondo institucional de la celda sin comprometer la legibilidad.
    """
    _set_font(item, strike=True, italic=True)
