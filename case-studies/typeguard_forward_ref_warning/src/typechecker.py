"""A minimal, faithful extraction of the mechanism behind a real bug:
agronholm/typeguard#221 (https://github.com/agronholm/typeguard/issues/221).

typeguard's real ForwardRefPolicy.GUESS feature does this: when a type
annotation is an unresolved forward reference (a string), guess the real
type from the argument actually passed and warn about the substitution.
This module reproduces that one behavior standalone, without pulling in
typeguard itself (whose exact API from 2021 no longer exists in current
releases).
"""
import warnings


class TypeHintWarning(UserWarning):
    pass


def check_annotation(func, arg_name, arg_value, forward_ref_name):
    """If `arg_name`'s annotation is the unresolved forward reference
    `forward_ref_name`, guess its real type from `arg_value` and warn.
    """
    annotation = func.__annotations__.get(arg_name)
    if isinstance(annotation, str) and annotation == forward_ref_name:
        guessed = type(arg_value)
        warnings.warn(
            f"Replaced forward declaration {forward_ref_name!r} in {func.__name__} with {guessed}",
            TypeHintWarning,
        )
        func.__annotations__[arg_name] = guessed
    return arg_value
