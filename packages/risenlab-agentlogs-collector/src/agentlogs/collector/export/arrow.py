import datetime as dt
from types import UnionType
from typing import Annotated, Any, Type, Union, get_args, get_origin, get_type_hints

import pyarrow as pa

def get_arrow_type(annotation: Any) -> pa.DataType:
    annotation = strip_none(unwrap_annotated(annotation))
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is type(None):
        raise TypeError("NoneType cannot be converted directly")

    if origin is list:
        return pa.list_(get_arrow_type(args[0]))

    if origin is dict:
        key_type, value_type = args
        return pa.map_(
            get_arrow_type(key_type),
            get_arrow_type(value_type),
        )

    if isinstance(annotation, type) and issubclass(annotation, dict):
        fields = [
            pa.field(
                name,
                get_arrow_type(field_type),
                nullable=allows_none(field_type),
            )
            for name, field_type in get_type_hints(annotation).items()
        ]
        return pa.struct(fields)

    match annotation:
        case x if x is str:
            return pa.string()
        case x if x is int:
            return pa.int64()
        case x if x is float:
            return pa.float64()
        case x if x is bool:
            return pa.bool_()
        case x if x is dt.datetime:
            return pa.timestamp("ms")

    raise TypeError(f"Unsupported type: {annotation}")

def allows_none(annotation: Any) -> bool:
    return type(None) in get_args(annotation)

def unwrap_annotated(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]

    return annotation

def strip_none(annotation: Any) -> Any:
    args = get_args(annotation)

    if get_origin(annotation) in (Union, UnionType):
        non_none_args = tuple(arg for arg in args if arg is not type(None))

        if len(non_none_args) == 1:
            return non_none_args[0]
        else:
            return Union[non_none_args]

    return annotation

def arrow_schema_from_typed_dict(cls: Type[Any]) -> pa.Schema:
    return pa.schema([
        pa.field(
            name,
            get_arrow_type(field_type),
            nullable=allows_none(field_type),
        )
        for name, field_type in get_type_hints(cls).items()
    ])
