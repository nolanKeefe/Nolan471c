from collections.abc import Callable
from functools import partial
from L0 import syntax as L0
from . import syntax as L1


#Going through the L1 statmeent tree and getting all used identifiers
def free_variables(term:L1.Statement) -> set[L1.Identifier]:
    match term:
        case L1.Copy(destination = d, source = s, then = then):
               return ({s} | free_variables(then))- {d}
        case L1.Abstract(destination=d, parameters=params, body=body, then=then):
            # The body is a self-contained
            # Variables that aren't params go up
            body_fvs = free_variables(body) - set(params)
            # d gets bound in then
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
            raise ValueError(f"Unhandled term: {term}")
 



def close_term(
        term: L1.Statement,
        lift: Callable[[L0.Procedure],str],
        fresh: Callable[[str], str],
        ) -> L0.Statement:  # this whole thing is producing the statement
     
     recur = partial(close_term,fresh= fresh)

     match statement:
         case L1.Abstract(destination=destination, parameters=parameters,body = body, then=then):
            # 1. close the abstract / lift to top level
            name = fresh("proc")
            env_p = fresh("env")

            fvs = list(free_variables(body)-set(parameters))

            result = recur(body)
            
            for i,fv in enumerate(fvs):
                result = L0.Load(destination= fv, base = env_p, index = i, then = result)

            p = L0.Procedure(
                name = name,
                parameters = [*parameters,env_p],
                body = result,
            )
            lift(p)

            # 2. create closure (tuple of code and environment)
            L0.Allocate(
                 destination = destination,
                 count = 2,
                 then = L0.Store(base = destination, index = 0, value = name,then = L0.Store(
                      base = destination,
                      index = 0,
                      value = ...,
                      then = ...,)),
                 )
            pass



        case L1.Apply(target=target, arguments=arguments):
            # 1. seperate code  and environment from the closure
            # call the code with the arfuments and then the environment
            code = "c"
            env = "e"
            return L0.Load(
                destination=code,
                base=target,
                index=0,
                then=L0.Load(
                    destination=env, base=target, index=1, then=L0.Call(target=code, arguments=[*arguments, env])
                ),
            )
            pass
