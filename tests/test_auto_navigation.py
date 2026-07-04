import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "zidou" / "mecanum.py"

spec = importlib.util.spec_from_file_location("mecanum_module", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_heading_and_speed_from_tag_position():
    controller = module.AutoNavigator()
    vx, vy, omega = controller.compute_cmd(x=0.3, z=0.8)
    assert vx < 0
    assert vy == 0.0
    assert omega > 0


def test_no_command_when_tag_missing():
    controller = module.AutoNavigator()
    vx, vy, omega = controller.compute_cmd(x=None, z=None)
    assert (vx, vy, omega) == (0.0, 0.0, 0.0)
