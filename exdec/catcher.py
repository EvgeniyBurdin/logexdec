import asyncio
import functools
import inspect
from typing import Any, Callable, Optional, Tuple, Type, Union

from .data_classes import DecData, FuncInfo


class ExDecCatcherException(Exception):
    pass


def handle_wrapper(handle_exception_method):
    @functools.wraps(handle_exception_method)
    def handle_exception(self, dec_data: DecData):

        self.try_reraise(dec_data)

        dec_data.handler = self.select_handler(dec_data)

        dec_data.func_info.owner = self.get_func_owner(dec_data)
        print("###", dec_data.func_info.owner)

        if asyncio.iscoroutinefunction(handle_exception_method):
            async def async_func():
                return await handle_exception_method(self, dec_data)
            return async_func()
        else:
            return handle_exception_method(self, dec_data)

    return handle_exception


class Catcher:

    def __init__(
        self,
        default_exception_classes: Union[
            Tuple[Type[Exception], ...], Type[Exception]
        ] = Exception,
    ):
        if not isinstance(default_exception_classes, tuple):
            default_exception_classes = tuple([default_exception_classes, ])

        self.default_exception_classes = default_exception_classes

    def make_exceptions(self, dec_args: tuple) -> Tuple[Type[Exception], ...]:

        exceptions = dec_args
        if not dec_args or (not type(dec_args[0]) is type
           and len(dec_args) == 1 and callable(dec_args[0])):
            exceptions = self.default_exception_classes

        for exc in exceptions:
            if not type(exc) is type or not issubclass(exc, Exception):
                msg = "The positional arguments of the 'cath' decorator must "
                msg += "be subclasses of Exception. But received: "
                msg += f"{exc}, type={type(exc)}."
                raise ExDecCatcherException(msg)
        return exceptions

    def default_handler(self, func_info: FuncInfo):

        print("log:", type(func_info.exception), func_info.exception)

    @staticmethod
    def try_reraise(dec_data: DecData):

        func_exception = dec_data.func_info.exception
        exception_classes = dec_data.exceptions

        if dec_data.exclude:
            if isinstance(func_exception, exception_classes):
                raise
        else:
            if not isinstance(func_exception, exception_classes):
                raise

    @staticmethod
    def get_func_owner(dec_data: DecData) -> Optional[str]:

        func_info = dec_data.func_info
        signature = inspect.signature(func_info.func)
        bound = signature.bind(*func_info.args, **func_info.kwargs)

        owner = bound.arguments.get("self")
        if owner:
            return "self"

        owner = bound.arguments.get("cls")
        if owner:
            return "cls"

        return None

    def select_handler(self, dec_data: DecData) -> Callable:

        return self.default_handler if dec_data.handler is None \
               else dec_data.handler

    @handle_wrapper
    def handle_exception(self, dec_data: DecData) -> Any:

        return dec_data.handler(dec_data.func_info)

    @handle_wrapper
    async def aio_handle_exception(self, dec_data: DecData) -> Any:

        if asyncio.iscoroutinefunction(dec_data.handler):
            return await dec_data.handler(dec_data.func_info)
        else:
            return dec_data.handler(dec_data.func_info)
