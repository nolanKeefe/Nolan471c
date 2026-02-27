import pytest
from L3.check import Context, check_program, check_term
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

# Helpers so I don't need to rewrite the same code for every test
x = Reference(name="x")
Imm = Immediate(value=0)

def test_check_term():
    term = Let(
        bindings=[
            ("x", Immediate(value=0)),
        ],
        body=Reference(name="x"),
    )
    check_program(program)


def test_check_program_single_param():
    program = Program(  # makes a program with a parameter x and body x
        parameters=["x"], body=x
    )
    check_program(program)


def test_check_term_let_scope():
    term = Let(
        bindings=[
            ("x", Immediate(value=0)),
            ("y", Reference(name="x")),
        ],
        body=Reference(name="y"),
    )
    check_program(program)


def test_check_program_duplicate_param():
    program = Program(  # makes a program with duplicate parameters x and x and body x so should fail because of the duplicate parameters
        parameters=["x", "x"], body=x
    )
    with pytest.raises(ValueError):
        check_program(program)


def test_check_term_let_duplicate_binders():
    term = Let(
        bindings=[
            ("x", Immediate(value=0)),
            ("x", Immediate(value=1)),
        ],
        body=Reference(name="x"),
    )
    with pytest.raises(ValueError):
        check_program(program)


# term tests
# reference
def test_check_reference_bound():  # makes a reference to x and the context has x so should pass
    check_term(x, context("x"))


def test_check_reference_empty():  # makes a reference to x and the context does not have x so should fail because x is not defined in the context
    with pytest.raises(ValueError):
        check_term(x, context())


def test_check_term_letrec():
    term = LetRec(
        bindings=[
            ("x", Immediate(value=0)),
        ],
        body=Reference(name="x"),
    )


def test_check_reference_multiple():  # makes a reference to x and the context has x and y so should pass because x is defined in the context even though there is a different variable y defined
    check_term(x, context("x", "y"))


def test_check_term_letrec_scope():
    term = LetRec(
        bindings=[
            ("y", Reference(name="x")),
            ("x", Immediate(value=0)),
        ],
        body=Reference(name="x"),
    )


# abstract
def test_check_abstract_empty():  # makes an abstract with no parameters and body Imm so should pass
    abstract = Abstract(parameters=[], body=Imm)
    check_term(abstract, context())


def test_check_term_letrec_duplicate_binders():
    term = LetRec(
        bindings=[
            ("x", Immediate(value=0)),
            ("x", Immediate(value=1)),
        ],
        body=Reference(name="x"),
    )

def test_check_abstract_multiple_param():  # makes an abstract with parameters x and y and body x so should pass because x is a valid parameter and is used in the body even though y is not used but is still a valid parameter
    abstract = Abstract(parameters=["x", "y"], body=x)
    check_term(abstract, context())


def test_check_abstract_duplicate_param():  # makes an abstract with duplicate parameters x and x and body x so should fail because of the duplicate parameters
    abstract = Abstract(parameters=["x", "x"], body=x)
    with pytest.raises(ValueError):
        check_term(abstract, context())


def test_check_term_reference_bound():
    term = Reference(name="x")


def test_check_abstract_param_empty():  # makes an abstract with parameter x and body Imm so should pass because even though x is not used in the body it is still a valid parameter and the body is valid
    abstract = Abstract(parameters=[], body=x)
    with pytest.raises(ValueError):
        check_term(abstract, context())


def test_check_term_reference_free():
    term = Reference(name="x")


def test_check_apply_unknown_target():  # makes an apply with target x and arguments x and x and context has y so should fail because x is not defined in the context and is not a valid target or argument
    apply = Apply(target=x, arguments=[])
    with pytest.raises(ValueError):
        check_term(apply, context("y"))


def test_check_term_abstract():
    term = Abstract(
        parameters=["x"],
        body=Immediate(value=0),
    )


def test_check_apply_no_target():  # makes an apply with target x and no arguments and context has x so should pass because x is a valid target and there are no arguments to check
    apply = Apply(target=Imm, arguments=[x])
    check_term(apply, context("x"))


def test_check_term_abstract_duplicate_parameters():
    term = Abstract(
        parameters=["x", "x"],
        body=Immediate(value=0),
    )


def test_check_begin_no_value():  # makes a begin with x as an effect and no value so should fail because the value is not a valid term and is not defined in the context
    term = Begin(effects=[x], value=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_term_apply():
    term = Apply(
        target=Reference(name="x"),
        arguments=[Immediate(value=0)],
    )


# branch
def test_check_branch_valid():  # makes a branch with operator < and left x and right x and consequent Imm and otherwise Imm so should pass because the operator is valid and the left and right are valid terms and the consequent and otherwise are valid terms
    term = Branch(operator="<", left=Imm, right=Imm, consequent=Imm, otherwise=Imm)
    check_term(term, context())


def test_check_term_immediate():
    term = Immediate(value=0)


def test_check_branch_invalid_right():  # makes a branch with operator < and left Imm and right x and consequent Imm and otherwise Imm so should fail because the right is not a valid term
    term = Branch(operator="<", left=Imm, right=x, consequent=Imm, otherwise=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_term_primitive():
    term = Primitive(
        operator="+",
        left=Immediate(value=1),
        right=Immediate(value=2),
    )


def test_check_branch_invalid_otherwise():  # makes a branch with operator < and left Imm and right Imm and consequent Imm and otherwise x so should fail because the otherwise is not a valid term
    term = Branch(operator="<", left=Imm, right=Imm, consequent=Imm, otherwise=x)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_term_branch():
    term = Branch(
        operator="<",
        left=Immediate(value=1),
        right=Immediate(value=2),
        consequent=Immediate(value=0),
        otherwise=Immediate(value=1),
    )


# Let
def test_check_let_valid():  # makes a let with bindings x and x and body x so should pass because the bindings are valid and the body is a valid term and the binding is defined in the context of the body
    term = Let(bindings=[("x", Imm)], body=x)
    check_term(term, context())


def test_check_term_allocate():
    term = Allocate(count=0)


def test_check_let_unknown_binding():  # makes a let with binding x and body y so should fail because y is not defined in the context of the body and is not a valid term
    term = Let(bindings=[("x", Imm)], body=Reference(name="y"))
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_term_load():
    term = Load(
        base=Reference(name="x"),
        index=0,
    )


# letrec


def test_check_term_store():
    term = Store(
        base=Reference(name="x"),
        index=0,
        value=Immediate(value=0),
    )


def test_check_letrec_duplicate_binders():  # makes a letrec with duplicate bindings x and x and body x so should fail because of the duplicate binders
    term = LetRec(
        bindings=[("x", Imm), ("x", Imm)], body=x
    )  # dont need to test the recursive propery of letrec here because the duplicate binders will cause it to fail
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_term_begin():
    term = Begin(
        effects=[Immediate(value=0)],
        value=Immediate(value=0),
    )


def test_check_letrec_unknown_body():  # makes a letrec with binding x and body y so should fail because y is not defined in the context of the body and is not a valid term
    term = LetRec(bindings=[("x", Imm)], body=Reference(name="y"))
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_program():
    program = Program(
        parameters=[],
        body=Immediate(value=0),
    )


def test_check_load_invalid():  # makes a load with arbitrary address 0 so should pass because it is a valid address
    term = Load(base=x, index=0)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_program_duplicate_parameters():
    program = Program(
        parameters=["x", "x"],
        body=Immediate(value=0),
    )


def test_check_primitive_left_invalid():  # makes a primitive with operator + and left y and right x and context has x so should fail because y is not defined in the context
    term = Primitive(operator="+", left=Reference(name="y"), right=x)
    with pytest.raises(ValueError):
        check_term(term, context("x"))


def test_check_primitive_right_invalid():  # makes a primitive with operator + and left x and right y and context has x so should fail because y is not defined in the context
    term = Primitive(operator="+", left=x, right=Reference(name="y"))
    with pytest.raises(ValueError):
        check_term(term, context("x"))


# store
def test_check_store_valid():  # makes a store with base x and index 0 and value Imm and context has x so should pass because the base is a valid term and is defined in the context and the index is a valid index and the value is a valid term
    term = Store(base=x, index=0, value=Imm)
    check_term(term, context("x"))


def test_check_store_invalid():  # makes a store with base y and index 0 and value Imm and context has x so should fail because the base is not defined in the context and is not a valid term
    term = Store(base=x, index=0, value=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())
