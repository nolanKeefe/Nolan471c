from L2 import syntax as L2
from L3 import syntax as L3
from L3.eliminate_letrec import Context, eliminate_letrec_program, eliminate_letrec_term

# Need to write tests that make an L3 version and an L2 version and then compare
# if not equal then it fails

# helpers
L3_Imm = L3.Immediate(value=0)
L2_Imm = L2.Immediate(value=0)  # just some basic immediate value to use in tests


def ctx(*names: str) -> Context:
    """Build a context containing exactly the given names as letrec-bound identifiers."""
    return dict.fromkeys(names, None)


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
def test_eliminate_letrec_let_params():
    term = L3.Let(
        bindings=[
            ("x", L3_Imm),
        ],
        body=L3.Reference(name="x"),
    )

    expected = L2.Let(
        bindings=[
            ("x", L2_Imm),
        ],
        body=L2.Reference(name="x"),
    )

    actual = eliminate_letrec_term(term, ctx())

    assert actual == expected


def test_eliminate_letrec_let_empty():
    term = L3.Let(
        bindings=[],
        body=L3_Imm,
    )

    expected = L2.Let(
        bindings=[],
        body=L2_Imm,
    )

    actual = eliminate_letrec_term(term, ctx())

    assert actual == expected


def test_eliminate_letrec_let_recurse_value():
    # the value of the binding is a primitive operation that uses an immediate value
    # checking that the let will properly recurse when converting
    term = L3.Let(
        bindings=[("x", L3.Primitive(operator="+", left=L3_Imm, right=L3_Imm))],
        body=L3.Reference(name="x"),
    )
    expected = L2.Let(
        bindings=[("x", L2.Primitive(operator="+", left=L2_Imm, right=L2_Imm))],
        body=L2.Reference(name="x"),
    )
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_let_does_not_extend_context():
    # Let names are not placed in the letrec context
    # reference in the body to a let-bound name remains a Reference, not a Load.
    term = L3.Let(bindings=[("x", L3_Imm)], body=L3_Imm)
    expected = L2.Let(bindings=[("x", L2_Imm)], body=L2_Imm)
    assert eliminate_letrec_term(term, ctx()) == expected


# LetRec tests here comes the wopper


def test_eliminate_letrec_letrec_become_let():
    # the letrec should be converted into a let
    # this should be a basic check to see if it is being converted at all
    term = L3.LetRec(
        bindings=[("x", L3_Imm)],
        body=L3.Reference(name="x"),
    )
    expected = L2.Let(
        bindings=[("x", L2_Imm)],
        body=L2.Load(base=L2.Reference(name="x"), index=0),
    )
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_letrec_self_reference_value():
    # the value of the binding is a primitive operation that uses an immediate value and a reference to itself
    # checking that the letrec will properly recurse when converting and that the self reference is converted to a load
    term = L3.LetRec(
        bindings=[("x", L3.Reference(name="x"))],
        body=L3_Imm,
    )
    expected = L2.Let(
        # has a load to the reference instead of just a reference
        bindings=[("x", L2.Load(base=L2.Reference(name="x"), index=0))],
        body=L2_Imm,
    )
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_letrec_nonrecursive_ref():
    # A reference in the letrec body to a name that is NOT letrec-bound should
    # remain a plain Reference, not a Load because it isn't recursively called
    term = L3.LetRec(
        bindings=[("x", L3_Imm)],
        body=L3.Reference(name="y"),
    )
    expected = L2.Let(
        bindings=[("x", L2_Imm)],
        body=L2.Reference(name="y"),
    )
    assert eliminate_letrec_term(term, ctx()) == expected


# reference tests


def test_eliminate_letrec_reference_not_in_context():
    # A reference that is not in the context should remain a Reference
    term = L3.Reference(name="x")
    expected = L2.Reference(name="x")
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_reference_in_context():
    # A reference that is in the context should be converted to a Load of the Reference
    term = L3.Reference(name="x")
    expected = L2.Load(base=L2.Reference(name="x"), index=0)
    assert eliminate_letrec_term(term, ctx("x")) == expected


# immediate tests
def test_eliminate_letrec_immediate():
    # an immediate value should just be converted to the same immediate value in L2
    assert eliminate_letrec_term(L3_Imm, ctx()) == L2_Imm


# Abstract tests


def test_eliminate_letrec_abstract():
    # an abstract should just be converted to the same abstract in L2 with the body converted
    term = L3.Abstract(parameters=["x"], body=L3_Imm)
    expected = L2.Abstract(parameters=["x"], body=L2_Imm)
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_abstract_letrec_context():
    # an abstract in a letrec context should be converted to an L2 abstract with the body converted
    term = L3.Abstract(parameters=[], body=L3.Reference(name="x"))
    expected = L2.Abstract(parameters=[], body=L2.Load(base=L2.Reference(name="x"), index=0))
    assert eliminate_letrec_term(term, ctx("x")) == expected


# apply tests


def test_eliminate_letrec_apply():
    # an apply should just be converted to the same apply in L2 with the target and arguments converted
    # so long as it doesnt have a recursive reference in the target or arguments that would be converted to a load
    term = L3.Apply(target=L3.Reference(name="x"), arguments=[L3_Imm])
    expected = L2.Apply(target=L2.Reference(name="x"), arguments=[L2_Imm])
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_term_apply_no_args():
    # An application with no arguments should still translate correctly,
    # exercising the empty-argument-list branch of the list comprehension.
    term = L3.Apply(target=L3_Imm, arguments=[])
    expected = L2.Apply(target=L2_Imm, arguments=[])
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_term_apply_letrec_target_becomes_load():
    # A letrec-bound name used as the call target must be rewritten to a Load.
    term = L3.Apply(target=L3.Reference(name="x"), arguments=[])
    expected = L2.Apply(target=L2.Load(base=L2.Reference(name="x"), index=0), arguments=[])
    assert eliminate_letrec_term(term, ctx("x")) == expected


# primitive tests
def test_eliminate_letrec_primitive():
    # a primitive should just be converted to the same primitive in L2 with the left and right converted
    term = L3.Primitive(operator="+", left=L3_Imm, right=L3_Imm)
    expected = L2.Primitive(operator="+", left=L2_Imm, right=L2_Imm)
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_primitive_letrec_left():
    # a primitive in a letrec context should be converted to an L2 primitive with the left and right converted
    term = L3.Primitive(operator="+", left=L3.Reference(name="x"), right=L3_Imm)
    expected = L2.Primitive(operator="+", left=L2.Load(base=L2.Reference(name="x"), index=0), right=L2_Imm)
    assert eliminate_letrec_term(term, ctx("x")) == expected


def test_eliminate_letrec_primitive_letrec_right():
    # a primitive in a letrec context should be converted to an L2 primitive with the left and right converted
    term = L3.Primitive(operator="+", left=L3_Imm, right=L3.Reference(name="x"))
    expected = L2.Primitive(operator="+", left=L2_Imm, right=L2.Load(base=L2.Reference(name="x"), index=0))
    assert eliminate_letrec_term(term, ctx("x")) == expected


# branch tests
def test_eliminate_letrec_branch():
    # a branch should just be converted to the same branch in L2 with the left, right, consequent, and otherwise converted
    term = L3.Branch(
        operator="<",
        left=L3_Imm,
        right=L3_Imm,
        consequent=L3_Imm,
        otherwise=L3_Imm,
    )
    expected = L2.Branch(
        operator="<",
        left=L2_Imm,
        right=L2_Imm,
        consequent=L2_Imm,
        otherwise=L2_Imm,
    )
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_branch_letrec():
    # a branch in a letrec context should be converted to an L2 branch with the left, right, consequent, and otherwise converted
    # i aint doing 4 individual cases for this one so we bundling
    term = L3.Branch(
        operator="<",
        left=L3.Reference(name="x"),
        right=L3.Reference(name="y"),
        consequent=L3.Reference(name="p"),
        otherwise=L3.Reference(name="q"),
    )
    expected = L2.Branch(
        operator="<",
        left=L2.Load(base=L2.Reference(name="x"), index=0),
        right=L2.Load(base=L2.Reference(name="y"), index=0),
        consequent=L2.Load(base=L2.Reference(name="p"), index=0),
        otherwise=L2.Load(base=L2.Reference(name="q"), index=0),
    )
    assert eliminate_letrec_term(term, ctx("x", "y", "p", "q")) == expected


# allocate tests
def test_eliminate_letrec_allocate():
    # an allocate should just be converted to the same allocate in L2 with the count converted
    term = L3.Allocate(count=0)
    expected = L2.Allocate(count=0)
    assert eliminate_letrec_term(term, ctx()) == expected


# load tests
def test_eliminate_letrec_load():
    # a load should just be converted to the same load in L2 with the base and index converted
    term = L3.Load(base=L3.Reference(name="x"), index=0)
    expected = L2.Load(base=L2.Reference(name="x"), index=0)
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_load_letrec():
    # a load in a letrec context should be converted to an L2 load with the base converted
    term = L3.Load(base=L3.Reference(name="x"), index=1)
    expected = L2.Load(base=L2.Load(base=L2.Reference(name="x"), index=0), index=1)
    assert eliminate_letrec_term(term, ctx("x")) == expected


# store tests


def test_eliminate_letrec_store():
    # a store should just be converted to the same store in L2 with the base, index, and value converted
    term = L3.Store(base=L3.Reference(name="x"), index=0, value=L3_Imm)
    expected = L2.Store(base=L2.Reference(name="x"), index=0, value=L2_Imm)
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_store_letrec():
    # a store in a letrec context should be converted to an L2 store with the base and value converted
    term = L3.Store(base=L3.Reference(name="x"), index=1, value=L3.Reference(name="y"))
    expected = L2.Store(
        base=L2.Load(base=L2.Reference(name="x"), index=0), index=1, value=L2.Load(base=L2.Reference(name="y"), index=0)
    )
    assert eliminate_letrec_term(term, ctx("x", "y")) == expected


# begin tests
def test_eliminate_letrec_begin():
    # a begin should just be converted to the same begin in L2 with the effects and value converted
    term = L3.Begin(effects=[L3_Imm], value=L3_Imm)
    expected = L2.Begin(effects=[L2_Imm], value=L2_Imm)
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_begin_no_effects():
    # a begin with no effects should still be converted correctly
    term = L3.Begin(effects=[], value=L3_Imm)
    expected = L2.Begin(effects=[], value=L2_Imm)
    assert eliminate_letrec_term(term, ctx()) == expected


def test_eliminate_letrec_begin_letrec():
    # a begin in a letrec context should be converted to an L2 begin with the effects and value converted
    term = L3.Begin(effects=[L3.Reference(name="x")], value=L3.Reference(name="y"))
    expected = L2.Begin(
        effects=[L2.Load(base=L2.Reference(name="x"), index=0)], value=L2.Load(base=L2.Reference(name="y"), index=0)
    )
    assert eliminate_letrec_term(term, ctx("x", "y")) == expected
