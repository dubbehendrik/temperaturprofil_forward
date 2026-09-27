import unittest
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
from streamlit_temperaturprofil_forward_app import (
    DEFAULTS, PARAMS, simulate, validate, data_frames, build_figure,
    export_data, export_images,
)

APP = str(Path(__file__).resolve().parents[1] / "streamlit_temperaturprofil_forward_app.py")


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.p = {k: DEFAULTS[k] for k in PARAMS}

    def test_time_constant_and_cooling(self):
        self.p.update(alpha=10., A=1., m=1., cp=100., t_end=10.)
        t, y = simulate(self.p)
        self.assertEqual(t[0], 0)
        self.assertEqual(y[0], 20)
        self.assertAlmostEqual(y[-1], 100 - 80 / np.e)
        self.p.update(T0=100., T_inf=20.)
        _, y = simulate(self.p)
        self.assertTrue(np.all(np.diff(y) < 0))
        self.assertAlmostEqual(y[-1], 20 + 80 / np.e)

    def test_zero_alpha_equilibrium_and_endpoint(self):
        self.p.update(alpha=0., t_end=2.5, dt=1.)
        t, y = simulate(self.p)
        np.testing.assert_array_equal(t, [0, 1, 2, 2.5])
        np.testing.assert_array_equal(y, [20, 20, 20, 20])
        self.p.update(alpha=10., T_inf=20., dt=5.)
        t, y = simulate(self.p)
        np.testing.assert_array_equal(t, [0, 2.5])
        np.testing.assert_array_equal(y, [20, 20])

    def test_invalid_inputs(self):
        for key, value in [("m", 0), ("A", -1), ("cp", 0), ("alpha", -1),
                           ("dt", 0), ("t_end", 0), ("T0", -274), ("alpha", np.nan),
                           ("t_end", np.inf), ("dt", 1e-10)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate({**self.p, key: value})

    def test_exports_preserve_different_grids_and_parameters(self):
        c1 = dict(name="Kurve 1", color="#0072B2", params={**self.p, "t_end": 2.5})
        c2 = dict(name="Kurve 2", color="#D55E00", params={**self.p, "alpha": 20., "t_end": 3., "dt": 2.})
        curves = [c1, c2]
        data, params = data_frames(curves)
        self.assertEqual(len(data), 7)
        self.assertEqual(params.iloc[1].alpha, 20)
        csv, excel = export_data(curves)
        self.assertEqual(len(pd.read_csv(BytesIO(csv), sep=";", decimal=",")), 7)
        self.assertEqual(pd.ExcelFile(BytesIO(excel)).sheet_names, ["Temperaturverläufe", "Parameter", "Einheiten"])
        png, svg = export_images(curves, "Minuten", 600, [[0, 1], [0, 120]])
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertIn(b"<svg", svg)
        fig = build_figure(curves, self.p, "Minuten", 600)
        self.assertEqual(len(fig.data), 3)
        self.assertEqual(len(fig.layout.annotations), 3)
        self.assertEqual(fig.data[-1].line.dash, "dash")


class InteractionTests(unittest.TestCase):
    def test_preview_keep_replace_reset_and_invalid_parameters(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state.curves), 0)
        at.button(key="plot_action").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state.curves), 1)
        saved = dict(at.session_state.curves[0]["params"])
        at.number_input(key="alpha").set_value(25.).run()
        self.assertEqual(at.session_state.curves[0]["params"], saved)
        at.checkbox(key="keep").check().run()
        at.button(key="plot_action").click().run()
        self.assertEqual(len(at.session_state.curves), 2)
        self.assertEqual(at.session_state.curves[1]["params"]["alpha"], 25.)
        at.checkbox(key="keep").uncheck().run()
        self.assertEqual(len(at.session_state.curves), 2)
        at.number_input(key="alpha").set_value(40.).run()
        at.button(key="plot_action").click().run()
        self.assertEqual(len(at.session_state.curves), 1)
        self.assertEqual(at.session_state.curves[0]["params"]["alpha"], 40.)
        at.number_input(key="m").set_value(0.).run()
        self.assertFalse(at.exception)
        self.assertTrue(at.button(key="plot_action").disabled)
        self.assertEqual(len(at.session_state.curves), 1)
        at.button(key="reset_action").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state.curves), 0)
        for k in DEFAULTS:
            self.assertEqual(at.session_state[k], DEFAULTS[k])


if __name__ == "__main__":
    unittest.main()
