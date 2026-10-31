import importlib.util
import sys
import types
from pathlib import Path


class _Decorators:
    @staticmethod
    def write(function):
        return function

    @staticmethod
    def view(function):
        return function


class _UserError(Exception):
    pass


_fake_genlayer = types.ModuleType("genlayer")
_fake_genlayer.gl = types.SimpleNamespace(
    Contract=object,
    public=_Decorators(),
    vm=types.SimpleNamespace(UserError=_UserError),
)
_fake_genlayer.u256 = int
_fake_genlayer.TreeMap = dict

_contract_path = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "quake_witness.py"
)
_previous_genlayer = sys.modules.get("genlayer")
sys.modules["genlayer"] = _fake_genlayer
try:
    _spec = importlib.util.spec_from_file_location(
        "quake_witness_under_test",
        _contract_path,
    )
    _contract = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_contract)
finally:
    if _previous_genlayer is None:
        sys.modules.pop("genlayer", None)
    else:
        sys.modules["genlayer"] = _previous_genlayer


CSV_SAMPLE = (
    "time,latitude,longitude,depth,mag,magType,nst,gap,dmin,rms,net,id,"
    "updated,place,type,horizontalError,depthError,magError,magNst,status,"
    "locationSource,magSource\n"
    '2026-10-31T07:37:26.189Z,38.3161,-112.3258,7.806,2.5,ml,38,74,'
    '0.867,0.49,us,us7000tuhe,2026-10-31T08:18:45.040Z,'
    '"12 km NW of Junction, Utah",earthquake,2.81,5.59,0.038,89,'
    "reviewed,us,us\n"
)


def test_scaled_magnitude_accepts_integer_and_decimal():
    assert _contract._scaled_magnitude("2.5") == 2500
    assert _contract._scaled_magnitude("0.64") == 640
    assert _contract._scaled_magnitude("-0.1") == -100


def test_scaled_magnitude_rejects_too_many_decimal_places():
    assert _contract._scaled_magnitude("2.5001") is None


def test_scaled_magnitude_rejects_out_of_range_values():
    assert _contract._scaled_magnitude("11") is None


def test_csv_parser_extracts_reviewed_event_with_quoted_comma():
    parsed = _contract._parse_event_csv(CSV_SAMPLE, "us7000tuhe")
    assert parsed["status"] == "OK"
    assert parsed["event"]["id"] == "us7000tuhe"
    assert parsed["event"]["mag"] == "2.5"
    assert parsed["event"]["place"] == "12 km NW of Junction, Utah"
    assert parsed["event"]["status"] == "reviewed"


def test_csv_parser_rejects_event_id_mismatch():
    assert _contract._parse_event_csv(CSV_SAMPLE, "wrong-id") is None


def test_csv_parser_reports_not_found_for_header_only_response():
    header = CSV_SAMPLE.splitlines()[0]
    result = _contract._parse_event_csv(header, "missing-event")
    assert result == {
        "status": "NOT_FOUND",
        "event_id": "missing-event",
    }


def test_csv_parser_rejects_malformed_csv():
    assert _contract._parse_event_csv(
        "not,a,usgs,csv",
        "us7000tuhe",
    ) is None
