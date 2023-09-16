from src.tecplot_reader.tecplotreader import TecplotFile
import numpy

def test_tecplotreader() -> None:
    FILE = "./data/tecplot.dat"

    testdata = TecplotFile(FILE)

    title = "Simple Data File"
    zone_names = ["Zone 1", "Zone 2"]
    auxdata = {"Alpha": "5", "Pi": "3.14 "}
    testdata = TecplotFile(FILE)

    assert testdata.title == title, title
    assert testdata.first_zone_name == zone_names[0], zone_names[0]
    result = testdata.get_values("Zone 2", 1)
    reference = [1.0, 1.0e-04, 2.0, 0.1, 9.0234]
    numpy.testing.assert_allclose(result, reference, rtol=1e-5, atol=0)

    assert testdata.auxdata == auxdata, auxdata
    assert testdata.zone_names == zone_names, zone_names
