from hamp._memory import memory, wmask_type
from hamp._hwtypes import uint, sint
from hamp._struct import struct
from hamp._db import create


def test_base_type_memory():
    db = create()
    memory(
        uint[8], 32, readers=["r"], writers=["w"], readwriters=["rw"], db=db
    )

    assert db == {
        "circuits": {
            "mem": {
                "mem": {
                    "input": ["r", "w", "rw"],
                    "output": [],
                    "data": {
                        "r": (
                            "input",
                            (
                                "struct",
                                ("addr", ("uint", 5), 0),
                                ("en", ("uint", 1), 0),
                                ("clk", ("clock", 1), 0),
                                ("data", ("uint", 8), 1),
                            ),
                            {},
                        ),
                        "w": (
                            "input",
                            (
                                "struct",
                                ("addr", ("uint", 5), 0),
                                ("en", ("uint", 1), 0),
                                ("clk", ("clock", 1), 0),
                                ("data", ("uint", 8), 0),
                                ("mask", ("uint", 1), 0),
                            ),
                            {},
                        ),
                        "rw": (
                            "input",
                            (
                                "struct",
                                ("addr", ("uint", 5), 0),
                                ("en", ("uint", 1), 0),
                                ("clk", ("clock", 1), 0),
                                ("rdata", ("uint", 8), 1),
                                ("wmode", ("uint", 1), 0),
                                ("wdata", ("uint", 8), 0),
                                ("wmask", ("uint", 1), 0),
                            ),
                            {},
                        ),
                        "_ismem": ("attribute", 1),
                        "_depth": ("attribute", 32),
                        "_type": ("attribute", ("uint", 8)),
                        "_readers": ("attribute", ["r"]),
                        "_writers": ("attribute", ["w"]),
                        "_readwriters": ("attribute", ["rw"]),
                    },
                    "wire": [],
                    "register": [],
                    "instance": [],
                    "code": [],
                    "attribute": [
                        "_ismem",
                        "_type",
                        "_depth",
                        "_readers",
                        "_writers",
                        "_readwriters",
                    ],
                }
            }
        }
    }


def test_wmask_type():
    @struct
    class S:
        a: uint[10]
        b: uint[10][20]
        c: sint[10][5][3]

    SA = S[3]

    assert wmask_type(SA).expr == (
        "array",
        3,
        (
            "struct",
            ("a", ("uint", 1), 0),
            ("b", ("array", 20, ("uint", 1)), 0),
            ("c", ("array", 3, ("array", 5, ("uint", 1))), 0),
        ),
    )
