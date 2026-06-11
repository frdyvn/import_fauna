# -*- coding: utf-8 -*-
"""
 ImportFauna — plugin QGIS d'import des exports CSV du portail Fauna (SINP).
 (C) 2026 F. YVONNE / CEN Nouvelle-Aquitaine
"""


def classFactory(iface):
    from .import_fauna import ImportFauna
    return ImportFauna(iface)
