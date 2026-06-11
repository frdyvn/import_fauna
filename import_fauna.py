# -*- coding: utf-8 -*-

import os
import csv

from qgis.PyQt.QtCore import QSettings, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QApplication

from qgis.core import (
    QgsProject,
    QgsGeometry,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsFeature,
    QgsField,
    QgsRectangle,
    QgsVectorFileWriter,
)

from .resources import *
from .import_fauna_dialog import ImportFaunaDialog


CHAMPS_CSV = [
    ('IdCadreAc',       QVariant.String),
    ('IdJdd',           QVariant.String),
    ('IdReleve',        QVariant.String),
    ('IdRegional',      QVariant.String),
    ('IdProduct',       QVariant.String),
    ('DateModif',       QVariant.String),
    ('TypeSource',      QVariant.String),
    ('RefSource',       QVariant.String),
    ('NomCite',         QVariant.String),
    ('TaxVersion',      QVariant.String),
    ('CdNomCite',       QVariant.String),
    ('CdRef',           QVariant.String),
    ('CdEspece',        QVariant.String),
    ('Classe',          QVariant.String),
    ('Ordre',           QVariant.String),
    ('Famille',         QVariant.String),
    ('TaxNomVal',       QVariant.String),
    ('TaxNomVern',      QVariant.String),
    ('Observer',        QVariant.String),
    ('StatPresen',      QVariant.String),
    ('Determiner',      QVariant.String),
    ('ComDetermi',      QVariant.String),
    ('DateDebut',       QVariant.String),
    ('DateFin',         QVariant.String),
    ('TypeGeom',        QVariant.String),
    ('NomLocalisation', QVariant.String),
    ('CodeDpt',         QVariant.String),
    ('InseeCom',        QVariant.String),
    ('NomCom',          QVariant.String),
    ('Maille10',        QVariant.String),
    ('Maille5',         QVariant.String),
    ('Maille2',         QVariant.String),
    ('Maille1',         QVariant.String),
    ('Maille500',       QVariant.String),
    ('Maille100',       QVariant.String),
    ('ComLocal',        QVariant.String),
    ('ComHabitat',      QVariant.String),
    ('ComObserv',       QVariant.String),
    ('SensiNiv',        QVariant.String),
    ('SensiDate',       QVariant.String),
    ('SensiRef',        QVariant.String),
    ('NivValReg',       QVariant.String),
    ('TypeValReg',      QVariant.String),
    ('DateValReg',      QVariant.String),
    ('DenbrMin',        QVariant.Int),
    ('DenbrMax',        QVariant.Int),
    ('ObjDenbr',        QVariant.String),
    ('DenbrType',       QVariant.String),
    ('IndicePres',      QVariant.String),
    ('Sexe',            QVariant.String),
    ('StadeDevlp',      QVariant.String),
    ('ProcObserv',      QVariant.String),
    ('Comportmt',       QVariant.String),
    ('StatBiolog',      QVariant.String),
    ('ComDescTax',      QVariant.String),
    ('PreuvNum',        QVariant.String),
]

# Champs de métadonnées ajoutés directement dans la couche (préfixe Meta_)
CHAMPS_META = [
    'NomCadre', 'NomJeuDonnees', 'TypeDonnees', 'Financeur',
    'MaitreOuvrage', 'MaitreOeuvre', 'Fournisseur', 'Producteur',
    'GestionnaireJdd', 'GestionnaireCadre', 'Lien',
]

TYPE_GEOM_WKB = {
    'point':      QgsWkbTypes.MultiPoint,
    'linestring': QgsWkbTypes.MultiLineString,
    'polygon':    QgsWkbTypes.MultiPolygon,
}


def _lire_wkt(valeur_wkt):
    if valeur_wkt and ';' in valeur_wkt:
        return valeur_wkt.split(';', 1)[1]
    return valeur_wkt


def _valeur_int(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _ouvrir_csv(chemin):
    """Retourne l'encodage détecté pour un CSV Fauna."""
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(chemin, encoding=enc, newline='') as f:
                f.read(1024)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'


def lire_metadonnees(chemins_meta):
    """
    Lit un ou plusieurs CSV Metadonnees et retourne un dict :
      { IdJeuDonnees: { 'NomCadre': ..., 'NomJeuDonnees': ..., ... } }
    Les doublons sur IdJeuDonnees sont ignorés (premier trouvé conservé).
    """
    index = {}
    for chemin in chemins_meta:
        enc = _ouvrir_csv(chemin)
        try:
            with open(chemin, encoding=enc, newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    id_jdd = (row.get('IdJeuDonnees') or '').strip()
                    if not id_jdd or id_jdd in index:
                        continue
                    index[id_jdd] = {col: (row.get(col) or '') for col in CHAMPS_META}
        except Exception:
            pass
    return index


def importer_csv_fauna(chemin, type_geom, nom_couche, meta_index=None):
    """
    Lit un fichier CSV Fauna et retourne un QgsVectorLayer en mémoire.
    Si meta_index est fourni, les champs de métadonnées sont ajoutés directement.
    Retourne (layer, nb_features, nb_erreurs).
    """
    wkb_type = TYPE_GEOM_WKB[type_geom]
    geom_str = QgsWkbTypes.displayString(wkb_type)

    layer = QgsVectorLayer(f"{geom_str}?crs=EPSG:2154", nom_couche, "memory")
    pr = layer.dataProvider()

    # Champs d'observations
    champs = list(CHAMPS_CSV)
    # Champs de métadonnées ajoutés à la suite si dispo
    if meta_index is not None:
        for nom in CHAMPS_META:
            champs.append((f'Meta_{nom}', QVariant.String))

    pr.addAttributes([QgsField(nom, qtype) for nom, qtype in champs])
    layer.updateFields()

    int_fields = {'DenbrMin', 'DenbrMax'}
    nb_features = 0
    nb_erreurs = 0
    features = []

    enc = _ouvrir_csv(chemin)
    with open(chemin, encoding=enc, newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fields = layer.fields()

        for row in reader:
            wkt = _lire_wkt(row.get('GeomWkt', ''))
            if not wkt:
                nb_erreurs += 1
                continue

            geom = QgsGeometry.fromWkt(wkt)
            if geom is None or geom.isNull():
                nb_erreurs += 1
                continue

            feat = QgsFeature(fields)
            feat.setGeometry(geom)

            # Attributs d'observation
            attrs = []
            for nom, qtype in CHAMPS_CSV:
                val = row.get(nom, '')
                if nom in int_fields:
                    attrs.append(_valeur_int(val))
                else:
                    attrs.append(val or None)

            # Attributs de métadonnées (lookup par IdJdd)
            if meta_index is not None:
                id_jdd = (row.get('IdJdd') or '').strip()
                meta = meta_index.get(id_jdd, {})
                for nom in CHAMPS_META:
                    attrs.append(meta.get(nom, '') or None)

            feat.setAttributes(attrs)
            features.append(feat)
            nb_features += 1

    pr.addFeatures(features)
    layer.updateExtents()
    return layer, nb_features, nb_erreurs


class ImportFauna:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = u'&Import Fauna'

    def tr(self, message):
        return QCoreApplication.translate('ImportFauna', message)

    def add_action(self, icon_path, text, callback, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=u'Import Fauna (SINP)',
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        dlg = ImportFaunaDialog(self.iface.mainWindow())

        last_dir = QSettings().value('ImportFauna/last_dir', '')
        if last_dir:
            dlg.lineEditDossier.setText(last_dir)

        if not dlg.exec_():
            return

        dlg.show()   # ré-affiche pour les mises à jour de progression pendant l'import

        dossier        = dlg.get_dossier()
        fichiers       = dlg.get_fichiers_a_importer()
        faire_jointure = dlg.get_option_jointure()
        meta_paths     = dlg.get_meta_paths()
        chemin_gpkg    = dlg.get_export_gpkg()

        QSettings().setValue('ImportFauna/last_dir', dossier)

        if not fichiers:
            self.iface.messageBar().pushWarning("Import Fauna", "Aucun fichier sélectionné.")
            return

        # Lecture des métadonnées dans un dict Python (pas de couche QGIS intermédiaire)
        meta_index = None
        if faire_jointure and meta_paths:
            meta_index = lire_metadonnees(meta_paths)
            if not meta_index:
                self.iface.messageBar().pushWarning(
                    "Import Fauna", "Métadonnées introuvables ou vides.")

        nom_groupe = os.path.basename(dossier) or "Fauna"
        total = len(fichiers)
        dlg.set_progress(0, total)

        root = QgsProject.instance().layerTreeRoot()
        groupe = root.insertGroup(0, f"Fauna — {nom_groupe}")

        couches_importees = []
        messages = []

        for i, info in enumerate(fichiers):
            nom_couche = os.path.splitext(info['nom'])[0]
            dlg.set_statut(f"Import {nom_couche}…", "blue")
            QApplication.processEvents()

            try:
                layer_mem, nb_ok, nb_err = importer_csv_fauna(
                    info['chemin'], info['type_geom'], nom_couche, meta_index)
            except Exception as e:
                messages.append(f"Erreur sur {info['nom']} : {e}")
                dlg.set_progress(i + 1)
                continue

            if chemin_gpkg:
                # --- Mode GeoPackage : écriture puis chargement depuis le fichier ---
                premiere_couche = len(couches_importees) == 0
                opts = QgsVectorFileWriter.SaveVectorOptions()
                opts.driverName = 'GPKG'
                opts.layerName = nom_couche
                opts.fileEncoding = 'UTF-8'
                opts.actionOnExistingFile = (
                    QgsVectorFileWriter.CreateOrOverwriteFile if premiere_couche
                    else QgsVectorFileWriter.CreateOrOverwriteLayer
                )
                err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer_mem, chemin_gpkg,
                    QgsProject.instance().transformContext(), opts)
                if err != QgsVectorFileWriter.NoError:
                    messages.append(f"⚠ Export GPKG échoué pour {nom_couche} : {msg}")
                    dlg.set_progress(i + 1)
                    continue
                layer = QgsVectorLayer(f"{chemin_gpkg}|layername={nom_couche}", nom_couche, "ogr")
                if not layer.isValid():
                    messages.append(f"⚠ Couche GPKG invalide après écriture : {nom_couche}")
                    dlg.set_progress(i + 1)
                    continue
            else:
                # --- Mode temporaire : couche mémoire directement ---
                layer = layer_mem

            QgsProject.instance().addMapLayer(layer, False)
            groupe.addLayer(layer)

            couches_importees.append(layer)
            messages.append(
                f"{info['nom']} : {nb_ok} entité(s)"
                + (f", {nb_err} ignorée(s)" if nb_err else "")
            )
            dlg.set_progress(i + 1)
            QApplication.processEvents()

        if couches_importees:
            extent = QgsRectangle()
            for lyr in couches_importees:
                extent.combineExtentWith(lyr.extent())
            if not extent.isNull():
                self.iface.mapCanvas().setExtent(extent)
                self.iface.mapCanvas().refresh()

        dlg.hide()

        if couches_importees:
            self.iface.messageBar().pushSuccess(
                "Import Fauna",
                f"{len(couches_importees)} couche(s) importée(s) depuis « {nom_groupe} ».")
        else:
            root.removeChildNode(groupe)
            self.iface.messageBar().pushWarning(
                "Import Fauna", "Aucune couche n'a pu être importée.")

        dlg.set_statut(
            f"Terminé : {len(couches_importees)}/{total} couche(s) importée(s).",
            "green" if couches_importees else "red")
