"""Test data-base validation"""

from hamp._db import validate, create, create_module
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
    db = create()
    db.update(
        {
            "circuits": {
                "foo": {
                    "foo": {"data": {}},
                    "bar": {
                        "input": ["pi", "clk", "rst1", "rst2"],
                        "output": ["po"],
                        "wire": ["a", "x", "z", "p", "t"],
                        "register": [],
                        "instance": [],
                        "attribute": ["attr1", "attr2"],
                        "data": {
                            "pi": ("input", ("uint", 2)),
                            "po": ("output", ("sint", 10), {}),
                            "clk": ("input", ("clock", 1)),
                            "rst1": ("input", ("reset", 1)),
                            "rst2": ("input", ("async_reset", 1)),
                            "a": ("wire", ("uint", 2)),
                            "x": ("wire", ("uint", 1)),
                            "z": ("wire", ("uint", 1)),
                            "p": ("wire", ("uint", 1)),
                            "t": ("wire", ("uint", 1)),
                            "attr1": ("attribute", 1),
                            "attr2": ("attribute", {"a": 2, "c": [1, 3]}),
                        },
                    },
                    "ok": {
                        "input": ["p1", "p4", "p5", "p6", "p7", "p8"],
                        "output": ["p2", "p3"],
                        "wire": [],
                        "register": [],
                        "instance": ["i0", "i1"],
                        "attribute": [],
                        "data": {
                            "p1": ("input", ("uint", 2), {"a": 1}),
                            "p2": ("output", ("sint", 10)),
                            "p3": ("output", t2),
                            "p4": ("input", ("array", 4, t2)),
                            "p5": ("input", ("sint", 9)),
                            "p6": ("input", ("sint", 9)),
                            "p7": ("input", ("array", 2, ("sint", 8))),
                            "p8": ("input", ("uint", 1)),
                            "i0": ("instance", ("instance", "foo", "bar")),
                            "i1": ("instance", ("instance", "foo", "baz")),
                        },
                        "code": [],
                    },
                },
            },
        }
    )
    baz = create_module(db, "foo", "baz")
    baz["wire"] = ["a"]
    baz["data"]["a"] = ("wire", ("uint", 2))
    return db


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
    bar["input"].append("p1")
    bar["output"].append("p2")
    bar["data"].update(
        {
            "p1": ("input", ("uint", 1)),
            "p2": ("output", ("sint", 3)),
        }
    )
    validate(db)
    bar["data"]["p2"] = ("fooput", ("uint", 1))
    with raises(ValueError, match="Malformed output entry in module bar"):
        validate(db)


def test_validate_wires():
    db = _create_db()
    bar = db["circuits"]["foo"]["bar"]
    bar["wire"] += ["p1", "p2"]
    bar["data"].update(
        {
            "p1": ("wire", ("uint", 1), {"k": 3}),
            "p2": ("wire", ("sint", 3)),
        }
    )
    validate(db)
    bar["data"]["p2"] = ("wopper", 3, 2)
    with raises(ValueError, match="Malformed wire entry in module bar"):
        validate(db)


def test_validate_registers():
    db = _create_db()
    bar = db["circuits"]["foo"]["bar"]
    bar["register"] = ["r1", "r2"]
    bar["data"].update(
        {
            "r1": ("register", ("uint", 1), "clk", ("rst1", 3)),
            "r2": ("register", ("sint", 3), "clk", 0, {"a1": [1, 2, 3]}),
        }
    )
    validate(db)
    bar["data"]["r2"] = ("register", 1, 2)
    with raises(ValueError, match="Malformed register entry in module bar"):
        validate(db)
    with raises(ValueError, match="Malformed attribute value"):
        bar["data"]["r1"] = ("register", ("sint", 3), "clk", 0, {"a1": None})
        validate(db)
    with raises(ValueError, match=r"Surplus attribute data: \[2\]"):
        bar["data"]["r1"] = ("register", ("sint", 3), "clk", 0, {"a1": 1}, 2)
        validate(db)
    with raises(ValueError, match=r"Reset signal q not defined in module bar"):
        bar["data"]["r1"] = ("register", ("sint", 3), "clk", ("q", 1))
        validate(db)
    with raises(ValueError, match=r"Bad register reset type: \('uint', 2\)"):
        bar["data"]["r1"] = ("register", ("sint", 3), "clk", ("a", 1))
        validate(db)
    with raises(
        ValueError, match=r"Malformed value \[1, 2\] of type \('sint', 3\)"
    ):
        bar["data"]["r1"] = ("register", ("sint", 3), "clk", ("rst1", [1, 2]))
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
        ("else-when", (("uint", 1), "t"), (), {"anno2": "a", "anno3": 1}),
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
    ok["wire"].append("z")
    ok["data"]["z"] = ("wire", ("uint", 4))
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
                {"b": 1},
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
            {"hooop": [1, 2]},
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
    ok["code"] = []
    with raises(ValueError, match=r"Malformed data section in module"):
        ok["data"]["ping"] = 3
        validate(db)
    del ok["data"]["ping"]
    with raises(ValueError, match=r"Malformed attribute entry in module"):
        ok["attribute"].append("ako")
        ok["data"]["ako"] = ("flup", 3)
        validate(db)


def test_validate_instances():
    db = _create_db()
    ok = db["circuits"]["foo"]["ok"]
    ok["code"] = [
        (
            "connect",
            (("uint", 2), (".", (("instance", "foo", "bar"), "i0"), "pi")),
            (("uint", 2), 0),
        ),
        (
            "connect",
            (("sint", 10), "p2"),
            (("sint", 10), (".", (("instance", "foo", "bar"), "i0"), "po")),
        ),
    ]
    validate(db)
    with raises(
        ValueError, match="Inconsistent input port type.*for foo::bar.pi"
    ):
        ok["code"] = [
            (
                "connect",
                (("uint", 3), (".", (("instance", "foo", "bar"), "i0"), "pi")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)
    with raises(ValueError, match="Module foo::bar has no port nx"):
        ok["code"] = [
            (
                "connect",
                (("uint", 2), (".", (("instance", "foo", "bar"), "i0"), "nx")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)
    with raises(ValueError, match="No module named foo::z found"):
        ok["instance"] = ["z"]
        ok["data"]["z"] = ("instance", ("instance", "foo", "z"))
        validate(db)
    with raises(ValueError, match="Malformed instance entry in module ok"):
        ok["data"]["z"] = [("inst", "z", "foo")]
        validate(db)
    with raises(ValueError, match="Module ok has no instance wefop"):
        ok["instance"] = []
        del ok["data"]["z"]
        ok["code"] = [
            (
                "connect",
                (("uint", 2), (".", (("instance", "a", "b"), "wefop"), "pi")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)
    with raises(ValueError, match="Inconsistent module names"):
        db = _create_db()
        ok = db["circuits"]["foo"]["ok"]
        ok["code"] = [
            (
                "connect",
                (("uint", 2), (".", (("instance", "a", "b"), "i0"), "pi")),
                (("uint", 2), 0),
            ),
        ]
        validate(db)


def test_redefine_module():
    db = create()
    create_module(db, "flipp", "flopp")
    with raises(NameError, match="Module flipp::flopp already defined"):
        create_module(db, "flipp", "flopp")
