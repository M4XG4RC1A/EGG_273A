import importlib.util
import pathlib
import sys

from app.methods.base import MethodBase


def load_methods_from_folder(folder: pathlib.Path):
    methods = []

    if not folder.exists():
        return methods

    for file in folder.glob("*.py"):
        if file.name.startswith("_"):
            continue

        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"[METHOD LOAD ERROR] {file.name}: {e}")
            continue

        for obj in module.__dict__.values():
            if (
                isinstance(obj, type)
                and issubclass(obj, MethodBase)
                and obj is not MethodBase
            ):
                methods.append(obj)

    return methods


def discover_methods():
    base_dir = pathlib.Path(__file__).parent

    builtin = load_methods_from_folder("app/methods/BuiltIn")
    plugins = load_methods_from_folder(base_dir / "plugins")

    return builtin + plugins
