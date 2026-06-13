import os
import pytest
import pandas as pd
from unittest.mock import MagicMock
from core.data_manager import DataManager


# ── sample data ───────────────────────────────────────────────────────────────

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


# ── fixtures ──────────────────────────────────────────────────────────────────

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


# ── _cargar_datos (via __init__) ──────────────────────────────────────────────

class TestLoadData:

    def test_loads_csv_correctly(self, qapp, csv_full, tmp_path):
        dm = DataManager(str(csv_full), str(tmp_path / "trash"))
        assert len(dm.df) == 3
        assert list(dm.df["status"]) == ["active", "active", "deleted"]

    def test_csv_without_status_column_defaults_to_active(self, qapp, csv_no_status, tmp_path):
        dm = DataManager(str(csv_no_status), str(tmp_path / "trash"))
        assert "status" in dm.df.columns
        assert (dm.df["status"] == "active").all()

    def test_missing_file_returns_empty_dataframe(self, qapp, tmp_path):
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.df.empty


# ── get_resumen_global ────────────────────────────────────────────────────────

class TestGetGlobalSummary:

    def test_summary_with_normal_data(self, dm):
        resumen = dm.get_resumen_global()
        assert resumen["total_imgs"] == 3
        assert resumen["activas"] == 2
        assert resumen["borradas"] == 1
        assert resumen["n_especies"] == 2   # Panthera leo + Ailurus fulgens
        assert resumen["n_familias"] == 2   # Felidae + Ailuridae

    def test_empty_dataframe_returns_empty_dict(self, qapp, tmp_path):
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.get_resumen_global() == {}


# ── filtrar_por_lazo ──────────────────────────────────────────────────────────

class TestFilterByLasso:

    # Square enclosing (1,1) and (2,2) but not (5,5)
    LASSO_WITH_POINTS = [(-0.5, -0.5), (2.5, -0.5), (2.5, 2.5), (-0.5, 2.5)]
    EMPTY_LASSO       = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]

    def test_returns_indices_of_points_inside(self, dm):
        indices = dm.filtrar_por_lazo(self.LASSO_WITH_POINTS)
        assert set(indices) == {0, 1}

    def test_empty_lasso_returns_empty_list(self, dm):
        assert dm.filtrar_por_lazo(self.EMPTY_LASSO) == []

    def test_excludes_deleted_points_even_if_inside_lasso(self, qapp, tmp_path):
        csv_path = tmp_path / "con_borrado.csv"
        pd.DataFrame([
            {"x": 1.0, "y": 1.0, "status": "active"},
            {"x": 1.5, "y": 1.5, "status": "deleted"},  # inside the lasso but deleted
        ]).to_csv(csv_path, index=False)
        dm_local = DataManager(str(csv_path), str(tmp_path / "trash"))
        indices = dm_local.filtrar_por_lazo(self.LASSO_WITH_POINTS)
        assert indices == [0]


# ── _calcular_ruta_destino ────────────────────────────────────────────────────

class TestCalculateDestinationPath:

    def test_path_with_images_preserves_intermediate_structure(self, dm, tmp_path):
        trash = dm.trash_path
        ruta = os.path.join(str(tmp_path), "proyecto", "images", "aves", "foto.jpg")
        carpeta, destino = dm._calcular_ruta_destino(ruta)
        assert carpeta == os.path.join(trash, "aves")
        assert destino == os.path.join(trash, "aves", "foto.jpg")

    def test_path_without_images_goes_to_trash_root(self, dm, tmp_path):
        trash = dm.trash_path
        ruta = os.path.join(str(tmp_path), "proyecto", "data", "foto.jpg")
        carpeta, destino = dm._calcular_ruta_destino(ruta)
        assert carpeta == trash
        assert destino == os.path.join(trash, "foto.jpg")


# ── move_to_trash ─────────────────────────────────────────────────────────────

class TestMoveToTrash:

    def test_file_is_moved_state_changes_and_signal_emitted(self, qapp, tmp_path):
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


# ── restore_full_dataset ──────────────────────────────────────────────────────

class TestRestoreFullDataset:

    def test_files_restored_state_changes_and_signal_emitted(self, qapp, tmp_path):
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


# ── get_umap_points ───────────────────────────────────────────────────────────

class TestGetUmapPoints:

    def test_returns_only_active_points(self, dm):
        x, y, colors, indices = dm.get_puntos_umap()
        assert len(x) == 2
        assert len(y) == 2
        assert len(indices) == 2
        assert set(indices) == {0, 1}

    def test_returns_empty_arrays_when_all_deleted(self, qapp, tmp_path):
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


# ── get_detailed_stats ────────────────────────────────────────────────────────

class TestGetDetailedStats:

    def test_has_expected_columns_and_correct_counts(self, dm):
        result = dm.get_estadisticas_detalladas()
        assert isinstance(result, pd.DataFrame)
        for col in ("common_name", "family", "genus", "active", "deleted", "total"):
            assert col in result.columns
        leo = result.loc["Panthera leo"]
        assert leo["active"] == 2 and leo["deleted"] == 0 and leo["total"] == 2
        ailurus = result.loc["Ailurus fulgens"]
        assert ailurus["active"] == 0 and ailurus["deleted"] == 1 and ailurus["total"] == 1

    def test_returns_empty_dataframe_when_no_data(self, qapp, tmp_path):
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.get_estadisticas_detalladas().empty


# ── get_family_stats ──────────────────────────────────────────────────────────

class TestGetFamilyStats:

    def test_counts_per_family(self, dm):
        result = dm.get_estadisticas_familias()
        assert isinstance(result, pd.DataFrame)
        for col in ("active", "deleted", "total"):
            assert col in result.columns
        felidae = result.loc["Felidae"]
        assert felidae["active"] == 2 and felidae["deleted"] == 0 and felidae["total"] == 2
        ailuridae = result.loc["Ailuridae"]
        assert ailuridae["active"] == 0 and ailuridae["deleted"] == 1 and ailuridae["total"] == 1

    def test_returns_empty_dataframe_when_no_data(self, qapp, tmp_path):
        dm = DataManager(str(tmp_path / "no_existe.csv"), str(tmp_path / "trash"))
        assert dm.get_estadisticas_familias().empty


# ── save_csv ──────────────────────────────────────────────────────────────────

class TestSaveCsv:

    def test_persists_changes_to_disk(self, dm):
        dm.df.at[0, "status"] = "deleted"
        dm._guardar_csv()
        reloaded = pd.read_csv(dm.csv_path)
        assert reloaded.at[0, "status"] == "deleted"
