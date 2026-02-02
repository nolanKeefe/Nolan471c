import ast
from ast import stmt
from functools import partial

from util.encode import encode

from .syntax import (
    Address,
    Allocate,
    Branch,
    Call,
    Copy,
    Halt,
    Immediate,
    Load,
    Primitive,
    Procedure,
    Program,
    Statement,
    Store,
)


def load(name: str) -> ast.Name:
    return ast.Name(id=encode(name), ctx=ast.Load())


def store(name: str) -> ast.Name:
    return ast.Name(id=encode(name), ctx=ast.Store())


def to_ast_statement(
    term: Statement,
) -> list[ast.stmt]:
    _statement: partial[list[stmt]] = partial(to_ast_statement)

    match term:
        case Copy(destination=destination, source=source, then=then):
            return [
                ast.Assign(targets=[store(destination)], value=load(source)),
                *_statement(then),
            ]

        case Immediate(destination=destination, value=value, then=then):
            return [
                ast.Assign(targets=[store(destination)], value=ast.Constant(value=value)),
                *_statement(then),
            ]

        case Primitive(destination=destination, operator=operator, left=left, right=right, then=then):
            match operator:
                case "+":
                    op = ast.Add()

                case "-":
                    op = ast.Sub()

                case "*":  # pragma: no branch
                    op = ast.Mult()

            return [
                ast.Assign(
                    targets=[store(destination)],
                    value=ast.BinOp(
                        left=load(left),
                        op=op,
                        right=load(right),
                    ),
                ),
                *_statement(then),
            ]

        case Branch(operator=operator, left=left, right=right, then=then, otherwise=otherwise):
            match operator:
                case "<":
                    op = ast.Lt()

                case "==":  # pragma: no branch
                    op = ast.Eq()

            return [
                ast.If(
                    test=ast.Compare(
                        left=load(left),
                        ops=[op],
                        comparators=[load(right)],
                    ),
                    body=_statement(then),
                    orelse=_statement(otherwise),
                ),
            ]

        case Allocate(destination=destination, count=count, then=then):
            return [
                ast.Assign(
                    targets=[store(destination)],
                    value=ast.List(
                        elts=[ast.Constant(None) for _ in range(count)],
                        ctx=ast.Load(),
                    ),
                ),
                *_statement(then),
            ]

        case Load(destination=destination, base=base, index=index, then=then):
            return [
                ast.Assign(
                    targets=[store(destination)],
                    value=ast.Subscript(
                        value=load(base),
                        slice=ast.Constant(index),
                        ctx=ast.Load(),
                    ),
                ),
                *_statement(then),
            ]

        case Store(base=base, index=index, value=value, then=then):
            return [
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=store(base),
                            slice=ast.Constant(index),
                            ctx=ast.Store(),
                        )
                    ],
                    value=load(value),
                ),
                *_statement(then),
            ]

        case Address(destination=destination, name=name, then=then):
            return [
                ast.Assign(targets=[store(destination)], value=load(name)),
                *_statement(then),
            ]

        case Call(target=target, arguments=arguments):
            return [
                ast.Return(
                    value=ast.Call(
                        func=load(target),
                        args=[load(argument) for argument in arguments],
                    )
                )
            ]

        case Halt(value=value):  # pragma: no branch
            return [
                ast.Return(value=load(value)),
            ]


def to_ast_procedure(procedure: Procedure) -> ast.stmt:
    _statement: partial[list[stmt]] = partial(to_ast_statement)

    match procedure:
        case Procedure(name=name, parameters=parameters, body=body):  # pragma: no branch
            return ast.FunctionDef(
                name=name,
                args=ast.arguments(args=[ast.arg(arg=parameter) for parameter in parameters]),
                body=_statement(body),
            )


def to_ast_program(
    program: Program,
) -> str:
    _procedure = partial(to_ast_procedure)
    _statement = partial(to_ast_statement)

    match program:
        case Program(procedures=procedures):  # pragma: no branch
            l0 = next(procedure for procedure in procedures if procedure.name == "l0")

            module = ast.Module(
                body=[
                    *[_procedure(procedure) for procedure in procedures],
                    ast.If(
                        test=ast.Compare(
                            left=ast.Name(id="__name__", ctx=ast.Load()),
                            ops=[ast.Eq()],
                            comparators=[ast.Constant(value="__main__")],
                        ),
                        body=[
                            ast.Import(names=[ast.alias(name="sys", asname=None)]),
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Name(id="print", ctx=ast.Load()),
                                    args=[
                                        ast.Call(
                                            func=ast.Name(id="l0", ctx=ast.Load()),
                                            args=[
                                                ast.Call(
                                                    func=ast.Name(id="int", ctx=ast.Load()),
                                                    args=[
                                                        ast.Subscript(
                                                            value=ast.Attribute(
                                                                value=ast.Name(id="sys", ctx=ast.Load()),
                                                                attr="argv",
                                                                ctx=ast.Load(),
                                                            ),
                                                            slice=ast.Constant(value=i + 1),
                                                        )
                                                    ],
                                                )
                                                for i, _ in enumerate(l0.parameters)
                                            ],
                                        )
                                    ],
                                )
                            ),
                        ],
                    ),
                ]
            )

            ast.fix_missing_locations(module)

            return ast.unparse(module)
