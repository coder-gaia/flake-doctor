"""A minimal, faithful extraction of the mechanism behind a real bug:
agronholm/typeguard#221 (https://github.com/agronholm/typeguard/issues/221).
"""
import warnings


class TypeHintWarning(UserWarning):
    pass


def check_annotation(func, arg_name, arg_value, forward_ref_name):
    annotation = func.__annotations__.get(arg_name)
    if isinstance(annotation, str) and annotation == forward_ref_name:
        guessed = type(arg_value)
        warnings.warn(
            f"Replaced forward declaration {forward_ref_name!r} in {func.__name__} with {guessed}",
            TypeHintWarning,
        )
        # MUTANT: substitutes the wrong type -- always `str`, regardless of
        # what the real argument's type actually was.
        func.__annotations__[arg_name] = str
    return arg_value
