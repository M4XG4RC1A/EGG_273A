import importlib
import pkgutil

from app.methods.base import MethodBase

def load_methods():
    method_classes = []

    package_name = "app.methods.BuiltIn"
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, MethodBase)
                and obj is not MethodBase
            ):
                method_classes.append(obj)

    return method_classes
