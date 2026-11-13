"""Keep the optional visual scene in sync with its upstream world."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

WORLDS = Path(__file__).resolve().parents[1] / "worlds"


def normalized(element):
    """Compare SDF structure without formatting-only whitespace."""
    return (element.tag, tuple(sorted(element.attrib.items())),
            (element.text or "").strip(),
            tuple(normalized(child) for child in element))


class OceanVisualTest(unittest.TestCase):
    def test_only_fog_differs_from_original_world(self):
        original = ET.parse(WORLDS / "ocean_waves.world").getroot()
        visual = ET.parse(WORLDS / "ocean_waves_underwater.world").getroot()
        scene = visual.find("./world/scene")
        fog = scene.find("fog")
        self.assertIsNotNone(fog)
        self.assertEqual(fog.findtext("type"), "linear")
        self.assertEqual(fog.findtext("start"), "10")
        self.assertEqual(fog.findtext("end"), "100")
        scene.remove(fog)
        self.assertEqual(normalized(original), normalized(visual))


if __name__ == "__main__":
    unittest.main()
