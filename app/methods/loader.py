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

    candidates = []

    # 1️⃣ Normal source execution
    candidates.append(
        pathlib.Path(__file__).parent / "BuiltIn"
    )

    # 2️⃣ EXE moved to project root
    if getattr(sys, "frozen", False):
        exe_dir = pathlib.Path(sys.executable).parent
        candidates.append(
            exe_dir / "app/methods/BuiltIn"
        )

    methods = []

    for folder in candidates:
        if folder.exists():
            print(f"[METHOD LOADER] Using: {folder}")
            methods.extend(load_methods_from_folder(folder))
            break
    else:
        print("[METHOD LOADER] No BuiltIn methods found")

    return methods
