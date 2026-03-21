from L3.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    LetRec,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
)
from L3.uniqify import Context, uniqify_program, uniqify_term
from util.sequential_name_generator import SequentialNameGenerator


def test_uniqify_term_reference():
    term = Reference(name="x")

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh=fresh)

    expected = Reference(name="y")

    assert actual == expected


def test_uniqify_immediate():
    term = Immediate(value=42)

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Immediate(value=42)

    assert actual == expected


def test_uniqify_term_let():
    term = Let(
        bindings=[
            ("x", Immediate(value=1)),
            ("y", Reference(name="x")),
        ],
        body=Apply(
            target=Reference(name="x"),
            arguments=[
                Reference(name="y"),
            ],
        ),
    )

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Let(
        bindings=[
            ("x0", Immediate(value=1)),
            ("y0", Reference(name="y")),
        ],
        body=Apply(
            target=Reference(name="x0"),
            arguments=[
                Reference(name="y0"),
            ],
        ),
    )

    assert actual == expected


def test_uniqify_letrec():
    term = LetRec(
        bindings=[
            ("x", Abstract(parameters=["n"], body=Reference(name="y"))),
            ("y", Abstract(parameters=["n"], body=Reference(name="x"))),
        ],
        body=Reference(name="x"),
    )

    context: Context = {}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)

    expected = LetRec(
        bindings=[
            # "x" freshened to "x0", its body sees "y" -> "y0"
            ("x0", Abstract(parameters=["n0"], body=Reference(name="y0"))),
            # "y" freshened to "y0", its body sees "x" -> "x0"
            ("y0", Abstract(parameters=["n1"], body=Reference(name="x0"))),
        ],
        # body sees "x" -> "x0"
        body=Reference(name="x0"),
    )

    assert actual == expected


def test_uniqify_abstract():
    term = Abstract(
        parameters=["x", "y"],
        # body refers to one of the parameters
        body=Reference(name="x"),
    )

    context: Context = {}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)

    expected = Abstract(
        # both parameters freshened
        parameters=["x0", "y0"],
        # body sees "x" -> "x0"
        body=Reference(name="x0"),
    )

    assert actual == expected


def test_uniqify_Allocate():
    term = Allocate(count=42)

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Allocate(count=42)

    assert actual == expected


def test_uniqify_Load():
    term = Load(base=Reference(name="x"), index=0)

    context: Context = {"x": "x0"}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)
    expected = Load(base=Reference(name="x0"), index=0)

    assert actual == expected


def test_uniqify_Store():
    term = Store(base=Reference(name="x"), index=0, value=Reference(name="y"))

    context: Context = {"x": "x0", "y": "y0"}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)
    expected = Store(base=Reference(name="x0"), index=0, value=Reference(name="y0"))

    assert actual == expected


def test_uniqify_begin():
    term = Begin(
        effects=[
            Store(
                base=Reference(name="x"),
                index=0,
                value=Reference(name="y"),
            ),
        ],
        value=Reference(name="x"),
    )
    context: Context = {"x": "x0", "y": "y0"}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)

    expected = Begin(
        effects=[
            Store(
                base=Reference(name="x0"),  # renamed via context
                index=0,  # plain integer, unchanged
                value=Reference(name="y0"),  # renamed via context
            ),
        ],
        value=Reference(name="x0"),  # renamed via context
    )

    assert actual == expected


def test_uniqify_primitive():
    term = Primitive(
        operator="+",
        left=Reference(name="x"),
        right=Reference(name="y"),
    )

    context: Context = {"x": "x0", "y": "y0"}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)

    expected = Primitive(
        operator="+",  # unchanged
        left=Reference(name="x0"),  # renamed via context
        right=Reference(name="y0"),  # renamed via context
    )

    assert actual == expected


def test_uniqify_branch():
    term = Branch(
        operator="<",
        left=Reference(name="x"),
        right=Reference(name="y"),
        consequent=Reference(name="x"),
        otherwise=Reference(name="y"),
    )

    context: Context = {"x": "x0", "y": "y0"}
    fresh = SequentialNameGenerator()

    actual = uniqify_term(term, context, fresh)

    expected = Branch(
        operator="<",  # unchanged
        left=Reference(name="x0"),  # renamed via context
        right=Reference(name="y0"),  # renamed via context
        consequent=Reference(name="x0"),  # renamed via context
        otherwise=Reference(name="y0"),  # renamed via context
    )

    assert actual == expected


def test_uniqify_program():
    program = Program(  # make the program
        parameters=["x", "y"],
        body=Primitive(
            operator="+",
            left=Reference(name="x"),
            right=Reference(name="y"),
        ),
    )

    fresh, actual = uniqify_program(program)  # run uniqify program and freshen it

    expected = Program(  # check
        parameters=["x0", "y0"],
        body=Primitive(
            operator="+",
            left=Reference(name="x0"),  # renamed via local
            right=Reference(name="y0"),  # renamed via local
        ),
    )

    assert actual == expected
