from L2 import syntax as L2
from L3 import syntax as L3
from L3.eliminate_letrec import Context, eliminate_letrec_program, eliminate_letrec_term

# Need to write tests that make an L3 version and an L2 version and then compare
# if not equal then it fails

# helpers
L3_Imm = L3.Immediate(value=0)
L2_Imm = L2.Immediate(value=0)  # just some basic immediate value to use in tests

context: Context = {"x": None, "y": None}  # makes a context with given names as letrec identifiers


# Program tests
def test_eliminate_letrec_program_empty():
    # no bindings and no parameters just an immediate value
    program = L3.Program(
        parameters=[],
        body=L3_Imm,
    )

    expected = L2.Program(
        parameters=[],
        body=L2_Imm,
    )

    actual = eliminate_letrec_program(program)

    assert actual == expected


def test_eliminate_letrec_program_params():
    # just parameters and an immediate value, simple but covers basic need
    program = L3.Program(parameters=["x", "y"], body=L3_Imm)
    expected = L2.Program(parameters=["x", "y"], body=L2_Imm)
    actual = eliminate_letrec_program(program)
    assert actual == expected


# let tests
def test_check_term_let_params():
    term = L3.Let(
        bindings=[
            ("x", L3_Imm),
        ],
        body=L3.Reference(name="x"),
    )

    context: Context = {}

    expected = L2.Let(
        bindings=[
            ("x", L2_Imm),
        ],
        body=L2.Reference(name="x"),
    )

    actual = eliminate_letrec_term(term, context)

    assert actual == expected


def test_check_term_let_empty():
    term = L3.Let(
        bindings=[],
        body=L3_Imm,
    )

    context: Context = {}

    expected = L2.Let(
        bindings=[],
        body=L2_Imm,
    )

    actual = eliminate_letrec_term(term, context)

    assert actual == expected
