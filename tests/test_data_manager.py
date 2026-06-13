import os
import pytest
import pandas as pd
from unittest.mock import MagicMock
from core.data_manager import DataManager


SAMPLE_ROWS = [
    {
        "scientific_name": "Panthera leo",
        "common_name": "Lion",
        "family": "Felidae",
        "genus": "Panthera",
        "x": 1.0, "y": 1.0,
        "absolute_path": "/data/images/cat1/img1.jpg",
        "status": "active",
    },
    {
        "scientific_name": "Panthera leo",
        "common_name": "Lion",
        "family": "Felidae",
        "genus": "Panthera",
        "x": 2.0, "y": 2.0,
        "absolute_path": "/data/images/cat1/img2.jpg",
        "status": "active",
    },
    {
        "scientific_name": "Ailurus fulgens",
        "common_name": "Red Panda",
        "family": "Ailuridae",
        "genus": "Ailurus",
        "x": 5.0, "y": 5.0,
        "absolute_path": "/data/images/cat2/img3.jpg",
        "status": "deleted",
    },
]


@pytest.fixture
def csv_full(tmp_path):
    p = tmp_path / "datos.csv"
    pd.DataFrame(SAMPLE_ROWS).to_csv(p, index=False)
    return p


@pytest.fixture
def csv_no_status(tmp_path):
    rows = [{k: v for k, v in r.items() if k != "status"} for r in SAMPLE_ROWS]
    p = tmp_path / "datos_sin_estado.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


@pytest.fixture
def dm(qapp, csv_full, tmp_path):
    """DataManager with 3 rows: indices 0 and 1 active, index 2 deleted."""
    return DataManager(str(csv_full), str(tmp_path / "trash"))


class TestLoadData:

    def test_loads_csv_correctly(self, qapp, csv_full, tmp_path):
        """DataFrame contains all CSV rows with their original status values."""
        dm = DataManager(str(csv_full), str(tmp_path / "trash"))
        assert len(dm.df) == 3
        assert list(dm.df["status"]) == ["active", "active", "deleted"]

    def test_csv_without_status_column_defaults_to_active(self, qapp, csv_no_status, tmp_path):
        """Missing 'status' column is created and all rows default to 'active'."""
        dm = DataManager(str(csv_no_status), str(tmp_path / "trash"))
        assert "status" in dm.df.columns
        assert (dm.df["status"] == "active").all()

    def test_missing_file_returns_empty_dataframe(self, qapp, tmp_path):
        """A non-existent CSV yields an empty DataFrame without raising."""
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.df.empty

    def test_corrupted_csv_returns_empty_dataframe(self, qapp, tmp_path):
        """Unparseable file content yields an empty DataFrame without raising."""
        csv_path = tmp_path / "corrupted.csv"
        csv_path.write_bytes(b"@@@@\x00\nbad{{{content\nnot,valid,csv,at,all")
        dm = DataManager(str(csv_path), str(tmp_path / "trash"))
        assert dm.df.empty

    def test_empty_file_returns_empty_dataframe(self, qapp, tmp_path):
        """An empty file yields an empty DataFrame without raising."""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        dm = DataManager(str(csv_path), str(tmp_path / "trash"))
        assert dm.df.empty


class TestGetGlobalSummary:

    def test_summary_with_normal_data(self, dm):
        """All summary counters (total, active, deleted, species, families) are accurate."""
        resumen = dm.get_resumen_global()
        assert resumen["total_imgs"] == 3
        assert resumen["activas"] == 2
        assert resumen["borradas"] == 1
        assert resumen["n_especies"] == 2
        assert resumen["n_familias"] == 2

    def test_empty_dataframe_returns_empty_dict(self, qapp, tmp_path):
        """An empty dataset returns an empty dict instead of raising."""
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.get_resumen_global() == {}


class TestFilterByLasso:

    LASSO_WITH_POINTS = [(-0.5, -0.5), (2.5, -0.5), (2.5, 2.5), (-0.5, 2.5)]
    EMPTY_LASSO       = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]

    def test_returns_indices_of_points_inside(self, dm):
        """Lasso selection returns the original DataFrame indices of active points inside the polygon."""
        indices = dm.filtrar_por_lazo(self.LASSO_WITH_POINTS)
        assert set(indices) == {0, 1}

    def test_empty_lasso_returns_empty_list(self, dm):
        """A lasso enclosing no points returns an empty list."""
        assert dm.filtrar_por_lazo(self.EMPTY_LASSO) == []

    def test_excludes_deleted_points_even_if_inside_lasso(self, qapp, tmp_path):
        """Deleted points inside the lasso polygon are excluded from the result."""
        csv_path = tmp_path / "con_borrado.csv"
        pd.DataFrame([
            {"x": 1.0, "y": 1.0, "status": "active"},
            {"x": 1.5, "y": 1.5, "status": "deleted"},
        ]).to_csv(csv_path, index=False)
        dm_local = DataManager(str(csv_path), str(tmp_path / "trash"))
        indices = dm_local.filtrar_por_lazo(self.LASSO_WITH_POINTS)
        assert indices == [0]


class TestCalculateDestinationPath:

    def test_path_with_images_preserves_intermediate_structure(self, dm, tmp_path):
        """The sub-directory after 'images/' is mirrored under the trash root."""
        trash = dm.trash_path
        ruta = os.path.join(str(tmp_path), "proyecto", "images", "aves", "foto.jpg")
        carpeta, destino = dm._calcular_ruta_destino(ruta)
        assert carpeta == os.path.join(trash, "aves")
        assert destino == os.path.join(trash, "aves", "foto.jpg")

    def test_path_without_images_goes_to_trash_root(self, dm, tmp_path):
        """Paths without an 'images/' segment land directly at the trash root."""
        trash = dm.trash_path
        ruta = os.path.join(str(tmp_path), "proyecto", "data", "foto.jpg")
        carpeta, destino = dm._calcular_ruta_destino(ruta)
        assert carpeta == trash
        assert destino == os.path.join(trash, "foto.jpg")


class TestMoveToTrash:

    def test_file_is_moved_state_changes_and_signal_emitted(self, qapp, tmp_path):
        """File moves to trash, row becomes 'deleted', and data_changed fires exactly once."""
        img_dir = tmp_path / "project" / "images" / "felidae"
        img_dir.mkdir(parents=True)
        img_file = img_dir / "lion.jpg"
        img_file.write_text("fake image")

        trash_dir = tmp_path / "trash"
        csv_path = tmp_path / "datos.csv"
        pd.DataFrame([{
            "scientific_name": "Panthera leo", "common_name": "Lion",
            "family": "Felidae", "genus": "Panthera",
            "x": 1.0, "y": 1.0,
            "absolute_path": str(img_file), "status": "active",
        }]).to_csv(csv_path, index=False)

        dm = DataManager(str(csv_path), str(trash_dir))
        slot = MagicMock()
        dm.data_changed.connect(slot)

        movidos, errores = dm.mover_a_descartes([0])

        assert movidos == 1
        assert errores == 0
        assert not img_file.exists()
        assert (trash_dir / "felidae" / "lion.jpg").exists()
        assert dm.df.at[0, "status"] == "deleted"
        slot.assert_called_once()

    def test_missing_source_file_does_not_raise(self, qapp, tmp_path):
        """A missing source file still marks the row 'deleted' and emits data_changed without raising."""
        trash_dir = tmp_path / "trash"
        csv_path = tmp_path / "datos.csv"
        pd.DataFrame([{
            "scientific_name": "Panthera leo", "common_name": "Lion",
            "family": "Felidae", "genus": "Panthera",
            "x": 1.0, "y": 1.0,
            "absolute_path": str(tmp_path / "images" / "missing.jpg"),
            "status": "active",
        }]).to_csv(csv_path, index=False)

        dm = DataManager(str(csv_path), str(trash_dir))
        slot = MagicMock()
        dm.data_changed.connect(slot)

        movidos, errores = dm.mover_a_descartes([0])

        assert movidos == 1
        assert errores == 0
        assert dm.df.at[0, "status"] == "deleted"
        slot.assert_called_once()


class TestRestoreFullDataset:

    def test_files_restored_state_changes_and_signal_emitted(self, qapp, tmp_path):
        """File returns to its original path, row becomes 'active', and data_changed fires exactly once."""
        original_dir = tmp_path / "project" / "images" / "felidae"
        original_dir.mkdir(parents=True)
        img_file = original_dir / "lion.jpg"

        trash_dir = tmp_path / "trash"
        trash_subdir = trash_dir / "felidae"
        trash_subdir.mkdir(parents=True)
        trash_file = trash_subdir / "lion.jpg"
        trash_file.write_text("fake image")

        csv_path = tmp_path / "datos.csv"
        pd.DataFrame([{
            "scientific_name": "Panthera leo", "common_name": "Lion",
            "family": "Felidae", "genus": "Panthera",
            "x": 1.0, "y": 1.0,
            "absolute_path": str(img_file), "status": "deleted",
        }]).to_csv(csv_path, index=False)

        dm = DataManager(str(csv_path), str(trash_dir))
        slot = MagicMock()
        dm.data_changed.connect(slot)

        restaurados, errores = dm.restaurar_dataset_completo()

        assert restaurados == 1
        assert errores == 0
        assert img_file.exists()
        assert not trash_file.exists()
        assert dm.df.at[0, "status"] == "active"
        slot.assert_called_once()


class TestGetUmapPoints:

    def test_returns_only_active_points(self, dm):
        """Only active rows contribute points; deleted rows are excluded."""
        x, y, colors, indices = dm.get_puntos_umap()
        assert len(x) == 2
        assert len(y) == 2
        assert len(indices) == 2
        assert set(indices) == {0, 1}

    def test_returns_empty_arrays_when_all_deleted(self, qapp, tmp_path):
        """When all rows are deleted, all four returned arrays are empty."""
        csv_path = tmp_path / "all_deleted.csv"
        pd.DataFrame([{
            "scientific_name": "Panthera leo", "common_name": "Lion",
            "family": "Felidae", "genus": "Panthera",
            "x": 1.0, "y": 1.0,
            "absolute_path": "/data/img.jpg", "status": "deleted",
        }]).to_csv(csv_path, index=False)
        dm = DataManager(str(csv_path), str(tmp_path / "trash"))
        x, y, colors, indices = dm.get_puntos_umap()
        assert list(x) == [] and list(y) == [] and list(indices) == []


class TestGetDetailedStats:

    def test_has_expected_columns_and_correct_counts(self, dm):
        """Result DataFrame has required columns and correct per-species active/deleted/total counts."""
        result = dm.get_estadisticas_detalladas()
        assert isinstance(result, pd.DataFrame)
        for col in ("common_name", "family", "genus", "active", "deleted", "total"):
            assert col in result.columns
        leo = result.loc["Panthera leo"]
        assert leo["active"] == 2 and leo["deleted"] == 0 and leo["total"] == 2
        ailurus = result.loc["Ailurus fulgens"]
        assert ailurus["active"] == 0 and ailurus["deleted"] == 1 and ailurus["total"] == 1

    def test_returns_empty_dataframe_when_no_data(self, qapp, tmp_path):
        """An empty dataset returns an empty DataFrame instead of raising."""
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.get_estadisticas_detalladas().empty


class TestGetFamilyStats:

    def test_counts_per_family(self, dm):
        """Result DataFrame has required columns and correct per-family active/deleted/total counts."""
        result = dm.get_estadisticas_familias()
        assert isinstance(result, pd.DataFrame)
        for col in ("active", "deleted", "total"):
            assert col in result.columns
        felidae = result.loc["Felidae"]
        assert felidae["active"] == 2 and felidae["deleted"] == 0 and felidae["total"] == 2
        ailuridae = result.loc["Ailuridae"]
        assert ailuridae["active"] == 0 and ailuridae["deleted"] == 1 and ailuridae["total"] == 1

    def test_returns_empty_dataframe_when_no_data(self, qapp, tmp_path):
        """An empty dataset returns an empty DataFrame instead of raising."""
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.get_estadisticas_familias().empty


class TestSaveCsv:

    def test_persists_changes_to_disk(self, dm):
        """In-memory edits are written to the CSV file and visible when re-read from disk."""
        dm.df.at[0, "status"] = "deleted"
        dm._guardar_csv()
        reloaded = pd.read_csv(dm.csv_path)
        assert reloaded.at[0, "status"] == "deleted"
