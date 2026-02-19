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


def context(*names: str) -> Context:  # a generic context helper that takes in a name for it and sets it to None
    return dict.fromkeys(names, None)


# program tests
def test_check_program_no_param():
    program = Program(  # it has nothing in the body and no parameters so should pass
        parameters=[], body=Imm
    )
    check_program(program)


def test_check_program_single_param():
    program = Program(  # makes a program with a parameter x and body x
        parameters=["x"], body=x
    )
    check_program(program)


def test_check_program_multiple_param():
    program = Program(  # makes a program with parameters x and y and body x so should pass because y is not used but is still a valid parameter
        parameters=["x", "y"], body=x
    )
    check_program(program)


def test_check_program_duplicate_param():
    program = Program(  # makes a program with duplicate parameters x and x and body x so should fail because of the duplicate parameters
        parameters=["x", "x"], body=x
    )
    with pytest.raises(ValueError):
        check_program(program)


def test_check_program_unknown_param():
    program = Program(  # makes a program with parameter y and body x so should fail because x is not a parameter and is not defined anywhere else in the program
        parameters=["y"], body=x
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


def test_check_reference_unrelated():  # makes a reference to x and the context has y so should fail because x is not defined in the context even though there is a different variable y defined
    with pytest.raises(ValueError):
        check_term(x, context("y"))


def test_check_reference_multiple():  # makes a reference to x and the context has x and y so should pass because x is defined in the context even though there is a different variable y defined
    check_term(x, context("x", "y"))


def test_check_reference_duplicate():  # makes a reference to x and the context has x and x so should pass because even though there are duplicate variables in the context it does not affect the reference to x
    check_term(x, context("x", "x"))


# abstract
def test_check_abstract_empty():  # makes an abstract with no parameters and body Imm so should pass
    abstract = Abstract(parameters=[], body=Imm)
    check_term(abstract, context())


def test_check_abstract_single_param():  # makes an abstract with parameter x and body x so should pass because x is a valid parameter and is used in the body
    abstract = Abstract(parameters=["x"], body=x)
    check_term(abstract, context())


def test_check_abstract_multiple_param():  # makes an abstract with parameters x and y and body x so should pass because x is a valid parameter and is used in the body even though y is not used but is still a valid parameter
    abstract = Abstract(parameters=["x", "y"], body=x)
    check_term(abstract, context())


def test_check_abstract_duplicate_param():  # makes an abstract with duplicate parameters x and x and body x so should fail because of the duplicate parameters
    abstract = Abstract(parameters=["x", "x"], body=x)
    with pytest.raises(ValueError):
        check_term(abstract, context())


def test_check_abstract_unknown_param():  # makes an abstract with parameter y and body x so should fail because x is not a parameter and is not defined anywhere else in the abstract
    abstract = Abstract(parameters=["y"], body=x)
    with pytest.raises(ValueError):
        check_term(abstract, context())


def test_check_abstract_param_empty():  # makes an abstract with parameter x and body Imm so should pass because even though x is not used in the body it is still a valid parameter and the body is valid
    abstract = Abstract(parameters=[], body=x)
    with pytest.raises(ValueError):
        check_term(abstract, context())


# apply
def test_check_apply_valid():  # makes an apply with target x and arguments x and x and context has x so should pass because x is a valid target and argument and is defined in the context
    apply = Apply(target=x, arguments=[x])
    check_term(apply, context("x"))


def test_check_apply_unknown_target():  # makes an apply with target x and arguments x and x and context has y so should fail because x is not defined in the context and is not a valid target or argument
    apply = Apply(target=x, arguments=[])
    with pytest.raises(ValueError):
        check_term(apply, context("y"))


def test_check_apply_unknown_argument():  # makes an apply with target Imm and arguments x, should fail because the argument x is not defined in the context and is not a valid argument even though the target is valid
    apply = Apply(target=Imm, arguments=[x])
    with pytest.raises(ValueError):
        check_term(apply, context())


def test_check_apply_no_target():  # makes an apply with target x and no arguments and context has x so should pass because x is a valid target and there are no arguments to check
    apply = Apply(target=Imm, arguments=[x])
    check_term(apply, context("x"))


# allocate
def test_check_allocate_valid():  # makes an allocate with arbitrary count 4 so should pass because it is a valid count
    term = Allocate(count=4)
    check_term(term, context())


# only do the one test for allocate because it passes as long as the count is valid which gets checked already


# begin
def test_check_begin_valid():  # makes a begin with effects Imm and Imm and value Imm so should pass because the effects and value are all valid terms
    term = Begin(effects=[Imm, Imm], value=Imm)
    check_term(term, context("x"))


def test_check_begin_no_effects():  # makes a begin with no effects and value Imm so should pass because the value is a valid term and there are no effects to check
    term = Begin(effects=[], value=Imm)
    check_term(term, context("x"))


def test_check_begin_no_value():  # makes a begin with x as an effect and no value so should fail because the value is not a valid term and is not defined in the context
    term = Begin(effects=[x], value=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_begin_floating_value():  # makes a begin with no effects and x as a value so should fail because the value is not a valid term and is not defined in the context
    term = Begin(effects=[], value=x)
    with pytest.raises(ValueError):
        check_term(term, context())


# branch
def test_check_branch_valid():  # makes a branch with operator < and left x and right x and consequent Imm and otherwise Imm so should pass because the operator is valid and the left and right are valid terms and the consequent and otherwise are valid terms
    term = Branch(operator="<", left=Imm, right=Imm, consequent=Imm, otherwise=Imm)
    check_term(term, context())


def test_check_branch_invalid_left():  # makes a branch with operator < and left x and right Imm and consequent Imm and otherwise Imm so should fail because the left is not a valid term
    term = Branch(operator="<", left=x, right=Imm, consequent=Imm, otherwise=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_branch_invalid_right():  # makes a branch with operator < and left Imm and right x and consequent Imm and otherwise Imm so should fail because the right is not a valid term
    term = Branch(operator="<", left=Imm, right=x, consequent=Imm, otherwise=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_branch_invalid_consequent():  # makes a branch with operator < and left Imm and right Imm and consequent x and otherwise Imm so should fail because the consequent is not a valid term
    term = Branch(operator="<", left=Imm, right=Imm, consequent=x, otherwise=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_branch_invalid_otherwise():  # makes a branch with operator < and left Imm and right Imm and consequent Imm and otherwise x so should fail because the otherwise is not a valid term
    term = Branch(operator="<", left=Imm, right=Imm, consequent=Imm, otherwise=x)
    with pytest.raises(ValueError):
        check_term(term, context())


# if multiple things are invalid then the tests should still catch it


# Let
def test_check_let_valid():  # makes a let with bindings x and x and body x so should pass because the bindings are valid and the body is a valid term and the binding is defined in the context of the body
    term = Let(bindings=[("x", Imm)], body=x)
    check_term(term, context())


def test_check_let_duplicate_binders():  # makes a let with duplicate bindings x and x and body x so should fail because of the duplicate binders
    term = Let(bindings=[("x", Imm), ("x", Imm)], body=x)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_let_unknown_binding():  # makes a let with binding x and body y so should fail because y is not defined in the context of the body and is not a valid term
    term = Let(bindings=[("x", Imm)], body=Reference(name="y"))
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_let_valid_multiple_bindings():  # makes a let with bindings x and y and body x so should pass because the bindings are valid and the body is a valid term and the binding x is defined in the context of the body even though y is not used but is still a valid binding
    term = Let(bindings=[("x", Imm), ("y", Imm)], body=x)
    check_term(term, context())


# letrec


def test_check_letrec_valid():
    # makes a letrec with a binding x that is an abstract with no parameters and a self reference to x in the body
    # and the body is a reference to x so should pass because the binding is valid and the body is a valid term and the binding is defined in the context of the body
    term = LetRec(bindings=[("x", Abstract(parameters=[], body=x))], body=x)
    check_term(term, context())


def test_check_letrec_duplicate_binders():  # makes a letrec with duplicate bindings x and x and body x so should fail because of the duplicate binders
    term = LetRec(
        bindings=[("x", Imm), ("x", Imm)], body=x
    )  # dont need to test the recursive propery of letrec here because the duplicate binders will cause it to fail
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_letrec_unknown_binding():  # makes a letrec with binding x and self reference to y so should fail because y is not defined in the context of the body and is not a valid term
    term = LetRec(bindings=[("x", Reference(name="y"))], body=Imm)
    with pytest.raises(ValueError):
        check_term(term, context())


def test_check_letrec_unknown_body():  # makes a letrec with binding x and body y so should fail because y is not defined in the context of the body and is not a valid term
    term = LetRec(bindings=[("x", Imm)], body=Reference(name="y"))
    with pytest.raises(ValueError):
        check_term(term, context())


# load
def test_check_load_valid():  # makes a load with arbitrary address 0 so should pass because it is a valid address
    term = Load(base=x, index=0)
    check_term(term, context("x"))


def test_check_load_invalid():  # makes a load with arbitrary address 0 so should pass because it is a valid address
    term = Load(base=x, index=0)
    with pytest.raises(ValueError):
        check_term(term, context())


# primitive
def test_check_primitive_valid():  # makes a primitive with operator + and left x and right x and context has x so should pass because the operator is valid and the left and right are valid terms and are defined in the context
    term = Primitive(operator="+", left=x, right=x)
    check_term(term, context("x"))


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
