from app.methods.loader import load_methods

method_classes = load_methods()

for cls in method_classes:
    print(cls.name)
