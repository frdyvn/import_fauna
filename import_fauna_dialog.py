# -*- coding: utf-8 -*-

import os
import csv
import re
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QTableWidgetItem, QHeaderView, QApplication

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_fauna_dialog_base.ui'))

# ── Détection du type géométrique ──────────────────────────────────────────────

_WKT_TYPE_MAP = {
    'point':             'point',
    'multipoint':        'point',
    'linestring':        'linestring',
    'multilinestring':   'linestring',
    'polygon':           'polygon',
    'multipolygon':      'polygon',
}

LABELS_TYPE = {
    'point':      'Point',
    'linestring': 'Linéaire',
    'polygon':    'Polygone',
}


def _type_depuis_wkt(wkt):
    if ';' in wkt:
        wkt = wkt.split(';', 1)[1].strip()
    m = re.match(r'^([A-Za-z]+)', wkt)
    if m:
        return _WKT_TYPE_MAP.get(m.group(1).lower())
    return None


def _detecter_type_geom(chemin):
    """Retourne le type de géométrie en lisant le WKT de la première ligne de données."""
    for encoding in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(chemin, encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                if not reader.fieldnames or 'GeomWkt' not in reader.fieldnames:
                    return None
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    wkt = (row.get('GeomWkt') or '').strip()
                    if wkt:
                        return _type_depuis_wkt(wkt)
            break
        except UnicodeDecodeError:
            continue
        except Exception:
            return None
    return None


def _compter_entites(chemin):
    """Compte le nombre de lignes de données du CSV (sans l'en-tête)."""
    for encoding in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(chemin, encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                return sum(1 for _ in reader)
        except UnicodeDecodeError:
            continue
        except Exception:
            return 0
    return 0


def _est_metadonnees(chemin):
    nom = os.path.basename(chemin).lower()
    if any(k in nom for k in ('metadonn', 'metadata')):
        return True
    for encoding in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(chemin, encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                return bool(reader.fieldnames and 'NomJeuDonnees' in reader.fieldnames)
        except UnicodeDecodeError:
            continue
        except Exception:
            return False
    return False


def scanner_dossier(dossier):
    """
    Scanne tous les CSV du dossier.
    Retourne une liste de dicts :
      { 'chemin', 'nom', 'type_geom', 'nb_entites' }
    Le fichier Metadonnees est ignoré.
    """
    resultats = []
    if not dossier or not os.path.isdir(dossier):
        return resultats

    for nom in sorted(os.listdir(dossier)):
        if not nom.lower().endswith('.csv'):
            continue
        chemin = os.path.join(dossier, nom)
        if _est_metadonnees(chemin):
            continue
        type_geom = _detecter_type_geom(chemin)
        if type_geom is None:
            continue
        nb = _compter_entites(chemin)
        resultats.append({
            'chemin':     chemin,
            'nom':        nom,
            'type_geom':  type_geom,
            'nb_entites': nb,
        })
    return resultats


# ── Dialogue ───────────────────────────────────────────────────────────────────

class ImportFaunaDialog(QDialog, FORM_CLASS):

    COL_CHECK  = 0
    COL_NOM    = 1
    COL_TYPE   = 2
    COL_NB     = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self._fichiers = []   # liste des dicts renvoyés par scanner_dossier
        self._meta_paths = []

        style_bleu = (
            "QPushButton { background-color: #0a6ebd; color: white; font-weight: bold; border-radius: 3px; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #085a9e; }"
            "QPushButton:pressed { background-color: #064a82; }"
            "QPushButton:disabled { background-color: #a0b8d0; }"
        )
        self.btnScanner.setStyleSheet(style_bleu)
        self.btnImporter.setStyleSheet(style_bleu)

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.labelIcon.setPixmap(QPixmap(icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.btnParcourir.clicked.connect(self._choisir_dossier)
        self.btnScanner.clicked.connect(self._scanner)
        self.btnTout.clicked.connect(lambda: self._cocher_tout(True))
        self.btnRien.clicked.connect(lambda: self._cocher_tout(False))
        self.btnImporter.clicked.connect(self.accept)
        self.btnFermer.clicked.connect(self.reject)
        self.tableFiles.itemChanged.connect(self._maj_bouton_importer)
        self.chkExportGpkg.toggled.connect(self._toggle_gpkg)
        self.btnGpkg.clicked.connect(self._choisir_gpkg)

        self._init_tableau()

    def _init_tableau(self):
        t = self.tableFiles
        t.setColumnCount(4)
        t.setHorizontalHeaderLabels(['Import', 'Fichier', 'Type géométrie', 'Nb entités'])
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.setSelectionBehavior(t.SelectRows)
        t.setSelectionMode(t.SingleSelection)
        t.setEditTriggers(t.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(self.COL_CHECK, QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(self.COL_NOM,   QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(self.COL_TYPE,  QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(self.COL_NB,    QHeaderView.ResizeToContents)

    def _toggle_gpkg(self, active):
        self.lineEditGpkg.setEnabled(active)
        self.btnGpkg.setEnabled(active)

    def _choisir_gpkg(self):
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le GeoPackage", "", "GeoPackage (*.gpkg)")
        if chemin:
            if not chemin.lower().endswith('.gpkg'):
                chemin += '.gpkg'
            self.lineEditGpkg.setText(chemin)

    def _choisir_dossier(self):
        dossier = QFileDialog.getExistingDirectory(
            self, "Choisir le dossier contenant les exports Fauna", "")
        if dossier:
            self.lineEditDossier.setText(dossier)

    def _scanner(self):
        dossier = self.lineEditDossier.text().strip()
        if not dossier:
            self.set_statut("Veuillez indiquer un dossier.", "orange")
            return

        self.set_statut("Scan en cours…", "blue")
        QApplication.processEvents()

        self._fichiers = scanner_dossier(dossier)
        self._remplir_tableau()

        # Détection des fichiers métadonnées (peut y en avoir plusieurs)
        self._meta_paths = []
        for nom in sorted(os.listdir(dossier)):
            if nom.lower().endswith('.csv'):
                chemin = os.path.join(dossier, nom)
                if _est_metadonnees(chemin):
                    self._meta_paths.append(chemin)

        if self._meta_paths:
            noms = ", ".join(os.path.basename(p) for p in self._meta_paths)
            label = f"<b style='color:green'>{len(self._meta_paths)} fichier(s) métadonnées : {noms}</b>"
            self.labelMeta.setText(label)
            self.chkJointureMeta.setEnabled(True)
        else:
            self.labelMeta.setText("<i>Métadonnées : non détectées</i>")
            self.chkJointureMeta.setEnabled(False)
            self.chkJointureMeta.setChecked(False)

        if self._fichiers:
            self.set_statut(
                f"{len(self._fichiers)} fichier(s) Fauna détecté(s).", "green")
        else:
            self.set_statut(
                "Aucun fichier CSV Fauna reconnu dans ce dossier.", "orange")

    def _remplir_tableau(self):
        t = self.tableFiles
        t.blockSignals(True)
        t.setRowCount(0)

        for info in self._fichiers:
            row = t.rowCount()
            t.insertRow(row)

            # Colonne 0 : checkbox
            item_chk = QTableWidgetItem()
            item_chk.setCheckState(Qt.Checked)
            item_chk.setTextAlignment(Qt.AlignCenter)
            item_chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            t.setItem(row, self.COL_CHECK, item_chk)

            # Colonne 1 : nom du fichier
            t.setItem(row, self.COL_NOM, QTableWidgetItem(info['nom']))

            # Colonne 2 : type de géométrie
            t.setItem(row, self.COL_TYPE,
                      QTableWidgetItem(LABELS_TYPE.get(info['type_geom'], info['type_geom'])))

            # Colonne 3 : nombre d'entités
            item_nb = QTableWidgetItem(str(info['nb_entites']))
            item_nb.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            t.setItem(row, self.COL_NB, item_nb)

        t.blockSignals(False)
        self._maj_bouton_importer()

    def _cocher_tout(self, cocher):
        t = self.tableFiles
        t.blockSignals(True)
        for row in range(t.rowCount()):
            t.item(row, self.COL_CHECK).setCheckState(
                Qt.Checked if cocher else Qt.Unchecked)
        t.blockSignals(False)
        self._maj_bouton_importer()

    def _maj_bouton_importer(self):
        cochees = any(
            self.tableFiles.item(r, self.COL_CHECK).checkState() == Qt.Checked
            for r in range(self.tableFiles.rowCount())
        )
        self.btnImporter.setEnabled(cochees)

    # ── Accesseurs utilisés par import_fauna.py ──────────────────────────────

    def get_dossier(self):
        return self.lineEditDossier.text().strip()

    def get_fichiers_a_importer(self):
        """Retourne la liste des dicts des fichiers cochés."""
        t = self.tableFiles
        return [
            self._fichiers[row]
            for row in range(t.rowCount())
            if t.item(row, self.COL_CHECK).checkState() == Qt.Checked
        ]

    def get_meta_paths(self):
        return self._meta_paths

    def get_export_gpkg(self):
        """Retourne le chemin du GeoPackage si l'option est cochée, sinon None."""
        if self.chkExportGpkg.isChecked():
            chemin = self.lineEditGpkg.text().strip()
            return chemin if chemin else None
        return None

    def get_option_jointure(self):
        return self.chkJointureMeta.isChecked() and self.chkJointureMeta.isEnabled()

    def set_statut(self, msg, couleur="black"):
        self.labelStatut.setText(f"<span style='color:{couleur}'>{msg}</span>")

    def set_progress(self, valeur, maximum=None):
        self.progressBar.setVisible(True)
        if maximum is not None:
            self.progressBar.setMaximum(maximum)
        self.progressBar.setValue(valeur)
