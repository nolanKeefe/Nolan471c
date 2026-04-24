from L0 import syntax as L0
from L1 import syntax as L1
from L1.close import close_program, close_statement, free_variables
from util.sequential_name_generator import SequentialNameGenerator

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def make_lift():
    """Returns (lift, collected) so tests can inspect lifted procedures."""
    collected: list[L0.Procedure] = []

    def lift(proc: L0.Procedure) -> str:
        collected.append(proc)
        return proc.name

    return lift, collected


# ═══════════════════════════════════════════════════════════════════════════════
# free_variables
# ═══════════════════════════════════════════════════════════════════════════════


def test_free_variables_halt():
    actual = free_variables(L1.Halt(value="x"))
    assert actual == {"x"}


def test_free_variables_copy_source_is_free():
    actual = free_variables(L1.Copy(destination="b", source="a", then=L1.Halt(value="b")))
    assert actual == {"a"}


def test_free_variables_copy_destination_is_bound():
    actual = free_variables(L1.Copy(destination="b", source="a", then=L1.Halt(value="b")))
    assert "b" not in actual


def test_free_variables_immediate_binds_destination():
    actual = free_variables(L1.Immediate(destination="x", value=42, then=L1.Halt(value="x")))
    assert actual == set()


def test_free_variables_primitive():
    actual = free_variables(L1.Primitive(destination="r", operator="+", left="a", right="b", then=L1.Halt(value="r")))
    assert actual == {"a", "b"}


def test_free_variables_branch():
    actual = free_variables(
        L1.Branch(operator="<", left="x", right="y", then=L1.Halt(value="x"), otherwise=L1.Halt(value="y"))
    )
    assert actual == {"x", "y"}


def test_free_variables_allocate_binds_destination():
    actual = free_variables(L1.Allocate(destination="p", count=2, then=L1.Halt(value="p")))
    assert actual == set()


def test_free_variables_load():
    actual = free_variables(L1.Load(destination="v", base="p", index=0, then=L1.Halt(value="v")))
    assert actual == {"p"}


def test_free_variables_store():
    actual = free_variables(L1.Store(base="p", index=0, value="v", then=L1.Halt(value="p")))
    assert actual == {"p", "v"}


def test_free_variables_apply():
    actual = free_variables(L1.Apply(target="f", arguments=["a", "b"]))
    assert actual == {"f", "a", "b"}


def test_free_variables_abstract_parameter_not_free():
    # "x" is bound by the parameter; only "y" from the then-clause escapes
    actual = free_variables(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Halt(value="x"),
            then=L1.Apply(target="f", arguments=["y"]),
        )
    )
    assert actual == {"y"}


def test_free_variables_abstract_captured_variable_is_free():
    # "z" is used in the body but not a parameter — it must escape
    actual = free_variables(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Halt(value="z"),
            then=L1.Halt(value="f"),
        )
    )
    assert "z" in actual


# ═══════════════════════════════════════════════════════════════════════════════
# close_statement — pass-through cases
# ═══════════════════════════════════════════════════════════════════════════════


def test_close_statement_halt():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(L1.Halt(value="x"), lift=lift, fresh=fresh)

    expected = L0.Halt(value="x")
    assert actual == expected


def test_close_statement_copy():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Copy(destination="b", source="a", then=L1.Halt(value="b")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Copy(destination="b", source="a", then=L0.Halt(value="b"))
    assert actual == expected


def test_close_statement_immediate():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Immediate(destination="x", value=7, then=L1.Halt(value="x")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Immediate(destination="x", value=7, then=L0.Halt(value="x"))
    assert actual == expected


def test_close_statement_primitive():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Primitive(destination="r", operator="+", left="a", right="b", then=L1.Halt(value="r")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Primitive(destination="r", operator="+", left="a", right="b", then=L0.Halt(value="r"))
    assert actual == expected


def test_close_statement_branch():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Branch(operator="<", left="x", right="y", then=L1.Halt(value="x"), otherwise=L1.Halt(value="y")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Branch(operator="<", left="x", right="y", then=L0.Halt(value="x"), otherwise=L0.Halt(value="y"))
    assert actual == expected


def test_close_statement_allocate():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Allocate(destination="p", count=3, then=L1.Halt(value="p")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Allocate(destination="p", count=3, then=L0.Halt(value="p"))
    assert actual == expected


def test_close_statement_load():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Load(destination="v", base="p", index=2, then=L1.Halt(value="v")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Load(destination="v", base="p", index=2, then=L0.Halt(value="v"))
    assert actual == expected


def test_close_statement_store():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Store(base="p", index=1, value="v", then=L1.Halt(value="p")),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Store(base="p", index=1, value="v", then=L0.Halt(value="p"))
    assert actual == expected


def test_close_statement_pass_through_does_not_lift():
    lift, collected = make_lift()
    fresh = SequentialNameGenerator()

    close_statement(L1.Halt(value="x"), lift=lift, fresh=fresh)

    assert collected == []


# ═══════════════════════════════════════════════════════════════════════════════
# close_statement — Apply
# ═══════════════════════════════════════════════════════════════════════════════


def test_close_statement_apply():
    lift, collected = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Apply(target="f", arguments=["a", "b"]),
        lift=lift,
        fresh=fresh,
    )

    # Expect: Load code from closure[0], load env from closure[1], call code(a, b, env)
    expected = L0.Load(
        destination="code0",
        base="f",
        index=0,
        then=L0.Load(
            destination="env0",
            base="f",
            index=1,
            then=L0.Call(target="code0", arguments=["a", "b", "env0"]),
        ),
    )
    assert actual == expected
    assert collected == []


def test_close_statement_apply_no_arguments():
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Apply(target="f", arguments=[]),
        lift=lift,
        fresh=fresh,
    )

    expected = L0.Load(
        destination="code0",
        base="f",
        index=0,
        then=L0.Load(
            destination="env0",
            base="f",
            index=1,
            then=L0.Call(target="code0", arguments=["env0"]),
        ),
    )
    assert actual == expected


# ═══════════════════════════════════════════════════════════════════════════════
# close_statement — Abstract
# ═══════════════════════════════════════════════════════════════════════════════


def test_close_statement_abstract_no_free_variables():
    # Body only uses its parameter — nothing to capture, env tuple is empty.
    lift, collected = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Halt(value="x"),
            then=L1.Halt(value="f"),
        ),
        lift=lift,
        fresh=fresh,
    )

    # One procedure must have been lifted
    assert len(collected) == 1
    proc = collected[0]

    # Lifted procedure has env appended to parameters
    assert list(proc.parameters) == ["x", "env0"]

    # Procedure body: no free vars so no loads, goes straight to converted body
    assert proc.body == L0.Halt(value="x")

    # Call site: Allocate closure(2) → Allocate env(0) → Store[0]=code → Store[1]=env → then
    expected = L0.Allocate(
        destination="f",
        count=2,
        then=L0.Allocate(
            destination="env_tuple0",
            count=0,
            then=L0.Store(
                base="f",
                index=0,
                value="proc0",
                then=L0.Store(
                    base="f",
                    index=1,
                    value="env_tuple0",
                    then=L0.Halt(value="f"),
                ),
            ),
        ),
    )
    assert actual == expected


def test_close_statement_abstract_lifts_one_procedure():
    lift, collected = make_lift()
    fresh = SequentialNameGenerator()

    close_statement(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Halt(value="x"),
            then=L1.Halt(value="f"),
        ),
        lift=lift,
        fresh=fresh,
    )

    assert len(collected) == 1


def test_close_statement_abstract_free_variable_loaded_in_proc_body():
    # Body uses "z" which is not a parameter — the lifted proc must unpack it.
    lift, collected = make_lift()
    fresh = SequentialNameGenerator()

    close_statement(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Halt(value="z"),
            then=L1.Halt(value="f"),
        ),
        lift=lift,
        fresh=fresh,
    )

    assert len(collected) == 1
    proc = collected[0]
    assert isinstance(proc.body, L0.Load)
    assert proc.body.destination == "z"


def test_close_statement_abstract_free_variable_env_tuple_size_1():
    # One free variable means the env tuple must have count=1.
    lift, _ = make_lift()
    fresh = SequentialNameGenerator()

    actual = close_statement(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Halt(value="z"),
            then=L1.Halt(value="f"),
        ),
        lift=lift,
        fresh=fresh,
    )

    # actual is Allocate(closure, count=2)
    # actual.then is Allocate(env_tuple, count=1)
    assert isinstance(actual, L0.Allocate)
    assert actual.count == 2
    alloc_env = actual.then
    assert isinstance(alloc_env, L0.Allocate)
    assert alloc_env.count == 1


def test_close_statement_abstract_nested_lifts_two_procedures():
    lift, collected = make_lift()
    fresh = SequentialNameGenerator()

    close_statement(
        L1.Abstract(
            destination="f",
            parameters=["x"],
            body=L1.Abstract(
                destination="g",
                parameters=["y"],
                body=L1.Halt(value="y"),
                then=L1.Halt(value="g"),
            ),
            then=L1.Halt(value="f"),
        ),
        lift=lift,
        fresh=fresh,
    )

    assert len(collected) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# close_program
# ═══════════════════════════════════════════════════════════════════════════════


def test_close_program_produces_l0_program():
    fresh = SequentialNameGenerator()

    actual = close_program(
        L1.Program(parameters=[], body=L1.Halt(value="x")),
        fresh=fresh,
    )

    assert isinstance(actual, L0.Program)


def test_close_program_main_always_present():
    fresh = SequentialNameGenerator()

    actual = close_program(
        L1.Program(parameters=[], body=L1.Halt(value="x")),
        fresh=fresh,
    )

    assert "main" in [p.name for p in actual.procedures]


def test_close_program_main_parameters():
    fresh = SequentialNameGenerator()

    actual = close_program(
        L1.Program(parameters=["a", "b"], body=L1.Halt(value="a")),
        fresh=fresh,
    )

    main = next(p for p in actual.procedures if p.name == "main")
    assert list(main.parameters) == ["a", "b"]


def test_close_program_with_abstract_lifts_extra_procedure():
    fresh = SequentialNameGenerator()

    actual = close_program(
        L1.Program(
            parameters=[],
            body=L1.Abstract(
                destination="f",
                parameters=["x"],
                body=L1.Halt(value="x"),
                then=L1.Halt(value="f"),
            ),
        ),
        fresh=fresh,
    )

    assert len(actual.procedures) == 2  # lifted proc + main


def test_close_program_halt_body():
    fresh = SequentialNameGenerator()

    actual = close_program(
        L1.Program(parameters=["v"], body=L1.Halt(value="v")),
        fresh=fresh,
    )

    main = next(p for p in actual.procedures if p.name == "main")
    assert main.body == L0.Halt(value="v")
