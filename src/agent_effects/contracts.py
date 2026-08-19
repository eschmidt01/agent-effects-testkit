"""Deterministic contract composition."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from .models import ContractReport, ContractViolation, EvaluationContext
from .protocols import Contract

ContractFunction = Callable[[EvaluationContext], Iterable[ContractViolation]]
Predicate = Callable[[EvaluationContext], bool]


@dataclass(frozen=True, slots=True)
class FunctionContract:
    name: str
    function: ContractFunction

    def evaluate(self, context: EvaluationContext) -> Sequence[ContractViolation]:
        return tuple(self.function(context))


def contract(name: str) -> Callable[[ContractFunction], FunctionContract]:
    """Turn a pure evaluation function into a named contract."""

    def decorate(function: ContractFunction) -> FunctionContract:
        return FunctionContract(name=name, function=function)

    return decorate


@dataclass(frozen=True, slots=True)
class PredicateContract:
    name: str
    code: str
    message: str
    predicate: Predicate
    path: str | None = None

    def evaluate(self, context: EvaluationContext) -> Sequence[ContractViolation]:
        if self.predicate(context):
            return ()
        return (
            ContractViolation(
                code=self.code,
                message=self.message,
                contract=self.name,
                path=self.path,
            ),
        )


def evaluate_contracts(
    contracts: Sequence[Contract],
    context: EvaluationContext,
) -> ContractReport:
    violations: list[ContractViolation] = []
    for item in contracts:
        try:
            violations.extend(item.evaluate(context))
        except Exception as exc:  # defensive: a broken oracle must fail closed
            violations.append(
                ContractViolation(
                    code="contract_error",
                    message=f"Contract {item.name!r} raised {type(exc).__name__}: {exc}",
                    contract=item.name,
                    details={"error_type": type(exc).__name__},
                )
            )
    return ContractReport(passed=not violations, violations=tuple(violations))
