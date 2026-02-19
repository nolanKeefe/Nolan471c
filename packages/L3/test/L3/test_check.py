import pytest
from L3.check import Context, check_program, check_term
from L3.syntax import (
    Abstract,
    Apply,
    Immediate,
    Program,
    Reference,
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
    apply = Apply(target=x, arguments=[x, x])
    check_term(apply, context("x"))


def test_check_apply_unknown_target():  # makes an apply with target x and arguments x and x and context has y so should fail because x is not defined in the context and is not a valid target or argument
    apply = Apply(target=x, arguments=[x, x])
    with pytest.raises(ValueError):
        check_term(apply, context("y"))


def test_check_apply_unknown_argument():  # makes an apply with target x and arguments x and x and context has x and y so should fail because even though x is a valid target and argument and is defined in the context there is an argument that is not defined in the context which is y
    apply = Apply(target=x, arguments=[x, x])
    with pytest.raises(ValueError):
        check_term(apply, context("x", "y"))
