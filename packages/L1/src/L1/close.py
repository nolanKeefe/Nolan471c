from collections.abc import Callable
from functools import partial

from L0 import syntax as L0

from . import syntax as L1

# ── free_variables ────────────────────────────────────────────────────────────
# Walk the L1 statement tree and collect every Identifier that is *used*
# but not *defined* in this subtree.


def free_variables(statement: L1.Statement) -> set[L1.Identifier]:
    match statement:
        case L1.Copy(destination=d, source=s, then=then):
            # 's' is used here; 'd' is bound from here onward
            return ({s} | free_variables(then)) - {d}

        case L1.Abstract(destination=d, parameters=params, body=body, then=then):
            # The body is a self-contained scope: params are bound inside it.
            # Only variables free in the body that are NOT params escape upward.
            body_fvs = free_variables(body) - set(params)
            # 'd' is bound in 'then'
            return (body_fvs | free_variables(then)) - {d}

        case L1.Apply(target=target, arguments=args):
            return {target} | set(args)

        case L1.Immediate(destination=d, then=then):
            return free_variables(then) - {d}

        case L1.Primitive(destination=d, left=l, right=r, then=then):
            return ({l, r} | free_variables(then)) - {d}

        case L1.Branch(left=l, right=r, then=then, otherwise=otherwise):
            return {l, r} | free_variables(then) | free_variables(otherwise)

        case L1.Allocate(destination=d, then=then):
            return free_variables(then) - {d}

        case L1.Load(destination=d, base=b, index=_, then=then):
            return ({b} | free_variables(then)) - {d}

        case L1.Store(base=b, value=v, then=then):
            return {b, v} | free_variables(then)

        case L1.Halt(value=v):
            return {v}

        case _:
            raise ValueError(f"Unhandled statement: {statement}")


# ── close_statement ───────────────────────────────────────────────────────────
# Convert every L1.Abstract into a flat L0.Procedure (lifted to the top level)
# plus an L0 heap allocation that bundles the code pointer and captured
# environment into a two-word closure object.


def close_statement(
    statement: L1.Statement,
    lift: Callable[[L0.Procedure], str],
    fresh: Callable[[str], str],
) -> L0.Statement:
    # Bind fresh and lift so recursive calls only need the statement argument.
    recur = partial(close_statement, lift=lift, fresh=fresh)

    match statement:
        # ── Abstract ──────────────────────────────────────────────────────────
        case L1.Abstract(destination=destination, parameters=parameters, body=body, then=then):
            # Step 1 – give this procedure and its environment-pointer fresh names.
            name = fresh("proc")
            env_p = fresh("env")

            # Step 2 – find which variables the body uses that are NOT parameters.
            # These become the captured environment.
            fvs = list(free_variables(body) - set(parameters))

            # Step 3 – closure-convert the body recursively, then prepend loads
            # that unpack each captured variable from the environment tuple.
            result: L0.Statement = recur(body)
            for i, fv in enumerate(fvs):
                result = L0.Load(destination=fv, base=env_p, index=i, then=result)

            # Step 4 – build and lift the L0 procedure.
            # The environment pointer is appended as an extra parameter.
            proc = L0.Procedure(
                name=name,
                parameters=[*parameters, env_p],
                body=result,
            )
            lift(proc)

            # Step 5 – at the call site, allocate a 2-word closure:
            #   closure[0] = address of the procedure  (code pointer)
            #   closure[1] = address of the env tuple  (captured variables)
            #
            # Building from the inside out (innermost = last thing executed):
            #   a) Allocate env tuple and fill it with the captured variables.
            #   b) Store env tuple pointer into closure[1].
            #   c) Store code pointer         into closure[0].
            #   d) Continue with 'then'.

            # (a) Build the env tuple store-chain (right-to-left so order is correct)
            env_var = fresh("env_tuple")

            # Start with the continuation after the whole Abstract.
            cont: L0.Statement = recur(then)

            # Store each captured variable into the env tuple.
            env_stores: L0.Statement = cont
            for i, fv in reversed(list(enumerate(fvs))):
                env_stores = L0.Store(base=env_var, index=i, value=fv, then=env_stores)

            # (b-c) Store env and code pointer into the closure tuple.
            closure_init: L0.Statement = L0.Store(
                base=destination,
                index=0,
                value=name,  # code pointer  ← fixed: use Address
                then=L0.Store(
                    base=destination,
                    index=1,  # ← fixed: was 0
                    value=env_var,
                    then=env_stores,
                ),
            )

            # (a) Allocate the env tuple, then run the closure init.
            alloc_env: L0.Statement = L0.Allocate(
                destination=env_var,
                count=len(fvs),
                then=closure_init,
            )

            # Wrap everything: allocate the 2-word closure first.
            return L0.Allocate(
                destination=destination,
                count=2,
                then=alloc_env,
            )

        # ── Apply ─────────────────────────────────────────────────────────────
        case L1.Apply(target=target, arguments=arguments):
            # A closure is a pair (code_ptr, env_ptr).
            # Unpack both, then call code_ptr(args..., env_ptr).
            code = fresh("code")
            env = fresh("env")
            return L0.Load(
                destination=code,
                base=target,
                index=0,
                then=L0.Load(
                    destination=env,
                    base=target,
                    index=1,
                    then=L0.Call(target=code, arguments=[*arguments, env]),
                ),
            )

        # ── Straightforward pass-through cases ───────────────────────────────
        # These nodes carry no closures themselves; just recurse into children.

        case L1.Copy(destination=d, source=s, then=then):
            return L0.Copy(destination=d, source=s, then=recur(then))

        case L1.Immediate(destination=d, value=v, then=then):
            return L0.Immediate(destination=d, value=v, then=recur(then))

        case L1.Primitive(destination=d, operator=op, left=l, right=r, then=then):
            return L0.Primitive(destination=d, operator=op, left=l, right=r, then=recur(then))

        case L1.Branch(operator=op, left=l, right=r, then=then, otherwise=otherwise):
            return L0.Branch(operator=op, left=l, right=r, then=recur(then), otherwise=recur(otherwise))

        case L1.Allocate(destination=d, count=c, then=then):
            return L0.Allocate(destination=d, count=c, then=recur(then))

        case L1.Load(destination=d, base=b, index=i, then=then):
            return L0.Load(destination=d, base=b, index=i, then=recur(then))

        case L1.Store(base=b, index=i, value=v, then=then):
            return L0.Store(base=b, index=i, value=v, then=recur(then))

        case L1.Halt(value=v):
            return L0.Halt(value=v)

        case _:
            raise ValueError(f"Unhandled statement: {statement}")


# ── close_program ─────────────────────────────────────────────────────────────
# Entry point: convert a whole L1.Program into an L0.Program.
# 'fresh' must return a globally unique string each time it is called.


def close_program(
    program: L1.Program,
    fresh: Callable[[str], str],
) -> L0.Program:
    procedures: list[L0.Procedure] = []

    def lift(proc: L0.Procedure) -> str:
        procedures.append(proc)
        return proc.name

    # The top-level body becomes the body of a special "main" procedure.
    main_body = close_statement(program.body, lift=lift, fresh=fresh)
    main_proc = L0.Procedure(
        name="main",
        parameters=list(program.parameters),
        body=main_body,
    )
    procedures.append(main_proc)

    return L0.Program(procedures=procedures)
