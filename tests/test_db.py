"""Test data-base validation"""

from hamp._db import validate
from pytest import raises


t1 = (
    "struct",
    ("f1", ("uint", 3), 0),
    ("f2", ("uint", 4), 1),
    ("f3", ("array", 7, ("uint", 10)), 0),
)
t2 = (
    "struct",
    ("f1", t1, 0),
    ("f2", ("array", 3, t1), 1),
    ("f3", ("array", 3, ("array", 2, t1)), 0),
)


def _create_db():
    return {
        "circuits": {
            "foo": {
                "foo": {},
                "bar": {
                    "ports": [
                        ("pi", "input", ("uint", 2)),
                        ("po", "output", ("sint", 10)),
                        ("clk", "input", ("clock", 1)),
                    ],
                    "wires": [
                        ("a", ("uint", 2)),
                        ("x", ("uint", 1)),
                        ("z", ("uint", 1)),
                        ("p", ("uint", 1)),
                        ("t", ("uint", 1)),
                    ],
                },
                "baz": {
                    "ports": [],
                    "wires": [("a", ("uint", 3))],
                    "registers": [],
                    "code": [],
                },
                "ok": {
                    "ports": [
                        ("p1", "input", ("uint", 2)),
                        ("p2", "output", ("sint", 10)),
                        ("p3", "output", t2),
                        ("p4", "input", ("array", 4, t2)),
                        ("p5", "input", ("sint", 9)),
                        ("p6", "input", ("sint", 9)),
                        ("p7", "input", ("array", 2, ("sint", 8))),
                        ("p8", "input", ("uint", 1)),
                    ],
                    "wires": [],
                    "registers": [],
                    "instances": [
                        ("i0", "foo", "bar"),
                        ("i1", "foo", "baz"),
                    ],
                    "code": [],
                },
            },
        },
    }


def test_validate_circuits():
    validate({"circuits": {}})
    validate({"circuits": {"c1": {}, "c2": {}}})
    with raises(ValueError, match="Malformed database"):
        validate(1)
    with raises(ValueError, match="Malformed database"):
        validate({"circ": {}})
    with raises(ValueError, match="Malformed database"):
        validate({"circuits": {}, "foo": 1})
    with raises(ValueError, match="Malformed circuit entry"):
        validate({"circuits": {"blaha": 1}})
    with raises(ValueError, match="Malformed circuit entry"):
        validate({"circuits": {1: {}}})
    with raises(ValueError, match="Malformed module entry"):
        validate({"circuits": {"c": {"m": 1}}})


def test_validate_module():
    db = _create_db()
    validate(db)
    db2 = {**db}
    db2["circuits"]["foo"]["baz"]["blaha"] = []
    with raises(ValueError, match="Malformed item in module baz"):
        validate(db2)


def test_validate_ports():
    db = _create_db()
    bar = db["circuits"]["foo"]["bar"]
    bar["ports"] = [
        ("p1", "input", ("uint", 1)),
        ("p2", "output", ("sint", 3)),
    ]
    validate(db)
    bar["ports"].append(("p3", "fooput", 1, 2))
    with raises(ValueError, match="Malformed port entry in module bar"):
        validate(db)


def test_validate_wires():
    db = _create_db()
    bar = db["circuits"]["foo"]["bar"]
    bar["wires"] = [
        ("p1", ("uint", 1), {"k": 3}),
        ("p2", ("sint", 3)),
    ]
    validate(db)
    bar["wires"].append(("p3",))
    with raises(ValueError, match="Malformed wire entry in module bar"):
        validate(db)


def test_validate_registers():
    db = _create_db()
    bar = db["circuits"]["foo"]["bar"]
    bar["registers"] = [
        ("r1", ("uint", 1), "clk", ("reset", 3)),
        ("r2", ("sint", 3), "clk", 0, {"a1": [1, 2, 3]}),
    ]
    validate(db)
    bar["registers"].append(("r3", 1, 2))
    with raises(ValueError, match="Malformed register entry in module bar"):
        validate(db)
    with raises(ValueError, match="Malformed attribute value"):
        bar["registers"] = [
            ("r2", ("sint", 3), "clk", 0, {"a1": None}),
        ]
        validate(db)


def test_validate_code():
    db = _create_db()
    bar = db["circuits"]["foo"]["bar"]
    bar["code"] = [
        ("connect", (("uint", 2), "a"), (("uint", 2), 3)),
        (
            "when",
            (("uint", 1), "x"),
            (("connect", (("uint", 1), "z"), (("uint", 1), "p")),),
            {"anno": (4.1, "a")},
        ),
        ("else-when", (("uint", 1), "t"), (), {"anno2": "a"}, {"anno3": 1}),
        ("else", (), {"anno2": {"a": {"b": [{"c": 1}]}}}),
    ]
    validate(db)
    bar["code"].append(("bluppa", 1, 2))
    with raises(ValueError, match="Malformed statement in module bar"):
        validate(db)


def test_validate_var():
    db = _create_db()
    ok = db["circuits"]["foo"]["ok"]
    ok["code"] = [
        (
            "connect",
            (t2, "p3"),
            (t2, ("[]", (("array", 4, t2), "p4"), (("uint", 2), "p1"))),
        ),
        (
            "connect",
            (("uint", 3), (".", (t1, (".", (t2, "p3"), "f1")), "f1")),
            (("uint", 2), "p1"),
        ),
    ]
    validate(db)
    ok["wires"].append(("z", ("uint", 4)))
    with raises(ValueError, match="Malformed variable"):
        ok["code"] = [("connect", (("uint", 3), ("z", 2)), (("uint", 3), 1))]
        validate(db)
    with raises(ValueError, match="Malformed name: f-z"):
        ok["code"] = [("connect", (("uint", 3), "f-z"), (("uint", 3), 1))]
        validate(db)
    with raises(ValueError, match="Bad uint size: -3"):
        ok["code"] = [("connect", (("uint", 4), "z"), (("uint", -3), 1))]
        validate(db)
    with raises(ValueError, match="Bad sint size: -3"):
        ok["code"] = [("connect", (("uint", 4), "z"), (("sint", -3), 1))]
        validate(db)
    with raises(ValueError, match="Bad array size: 0"):
        ok["code"] = [
            ("connect", (("array", 0, ("uint", 1)), "z"), (("sint", -3), 1))
        ]
        validate(db)
    with raises(ValueError, match="Malformed struct field z"):
        ok["code"] = [("connect", (("struct", "z"), "a"), (("sint", -3), 1))]
        validate(db)
    with raises(ValueError, match="Malformed type"):
        ok["code"] = [("connect", (("strukt", "z"), "a"), (("sint", -3), 1))]
        validate(db)
    with raises(ValueError, match="Struct .* has no field a"):
        ok["code"] = [
            (
                "connect",
                (
                    ("sint", 2),
                    (".", (("struct", ("b", ("sint", 1), 0)), "x"), "a"),
                ),
                (("sint", -3), 1),
            )
        ]
        validate(db)
    with raises(ValueError, match="Module ok has no member named nope"):
        ok["code"] = [("connect", (("uint", 4), "nope"), (("uint", 4), 1))]
        validate(db)
    with raises(
        ValueError, match=r"Inconsistent type \('uint', 4\) != \('uint', 7\)"
    ):
        ok["code"] = [("connect", (("uint", 7), "z"), (("uint", 4), 1))]
        validate(db)


def test_validate_expr():
    db = _create_db()
    ok = db["circuits"]["foo"]["ok"]
    ok["code"] = [
        (
            "connect",
            (("sint", 10), "p2"),
            (("sint", 10), ("+", (("sint", 9), "p5"), (("sint", 9), "p6"))),
        ),
        (
            "connect",
            (("uint", 2), "p1"),
            (("uint", 2), ("*", (("uint", 1), "p8"), (("uint", 1), "p8"))),
        ),
        (
            "connect",
            (("sint", 10), "p2"),
            (
                ("sint", 10),
                (
                    "+",
                    (("sint", 9), "p5"),
                    (
                        ("sint", 9),
                        (
                            "-",
                            (
                                ("sint", 8),
                                (
                                    "[]",
                                    (("array", 2, ("sint", 8)), "p7"),
                                    (("uint", 1), 0),
                                ),
                            ),
                            (
                                ("sint", 8),
                                (
                                    "[]",
                                    (("array", 2, ("sint", 8)), "p7"),
                                    (("uint", 1), 1),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ]
    validate(db)
    with raises(ValueError, match="Malformed expression:"):
        ok["code"] = [
            (
                "connect",
                (("sint", 10), "p2"),
                (("sint", 10), ("+", 1, (("sint", 9), "p6"))),
            ),
        ]
        validate(db)


def test_validate_values():
    db = _create_db()
    ok = db["circuits"]["foo"]["ok"]
    ok["code"] = [
        ("connect", (t2, "p3"), (t2, {"f1": {"f2": 3}})),
        ("connect", (t2, "p3"), (t2, {"f1": {"f2": 3, "f3": [1] * 7}})),
        (
            "connect",
            (t2, "p3"),
            (
                t2,
                {
                    "f1": {"f2": 3},
                    "f3": [
                        [{"f2": 1}, {"f1": 1}],
                        [{"f3": [1, 2, 3, 4, 5, 6, 7]}, {"f2": 0}],
                        [{"f2": 2}, {"f1": 3}],
                    ],
                },
            ),
        ),
    ]
    validate(db)
    with raises(ValueError, match="Struct .* has no field fx"):
        ok["code"] = [
            ("connect", (t2, "p3"), (t2, {"fx": {"f2": 3}})),
        ]
        validate(db)
    with raises(ValueError, match="Struct .* has no field fx"):
        ok["code"] = [
            ("connect", (t2, "p3"), (t2, {"f1": {"fx": 3}})),
        ]
        validate(db)
    with raises(ValueError, match="Wrong number of array values: 8 != 7"):
        ok["code"] = [
            ("connect", (t2, "p3"), (t2, {"f1": {"f2": 3, "f3": [1] * 8}})),
        ]
        validate(db)
    with raises(
        ValueError, match=r"Malformed value 3\.2 of type \('uint', 10\)"
    ):
        ok["code"] = [
            ("connect", (t2, "p3"), (t2, {"f1": {"f2": 3, "f3": [3.2] * 7}})),
        ]
        validate(db)


def test_validate_instances():
    db = _create_db()
    ok = db["circuits"]["foo"]["ok"]
    ok["code"] = [
        (
            "connect",
            (("uint", 2), (".", "instance", "i0", "pi")),
            (("uint", 2), 0),
        ),
        (
            "connect",
            (("sint", 10), "p2"),
            (("sint", 10), (".", "instance", "i0", "po")),
        ),
    ]
    validate(db)
    with raises(
        ValueError, match="Inconsistent input port type.*for foo::bar.pi"
    ):
        ok["code"] = [
            (
                "connect",
                (("uint", 3), (".", "instance", "i0", "pi")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)
    with raises(ValueError, match="Module foo::bar has no port nix"):
        ok["code"] = [
            (
                "connect",
                (("uint", 2), (".", "instance", "i0", "nix")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)
    with raises(ValueError, match="No module named foo::z found"):
        ok["instances"] = [("z", "foo", "z")]
        validate(db)
    with raises(ValueError, match="Malformed instance entry in module ok"):
        ok["instances"] = [("z", "foo")]
        validate(db)
    with raises(ValueError, match="Module ok has no instance wefop"):
        ok["instances"] = []
        ok["code"] = [
            (
                "connect",
                (("uint", 2), (".", "instance", "wefop", "pi")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)
