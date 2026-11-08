
import sys
import unittest
import importlib.util
from pathlib import Path

def load_test_module(test_file: Path):
    test_dir = str(test_file.parent)
    sys.path.insert(0, test_dir) # fix for relative imports in test files
    try:
        module_name = f"test_module_{test_file.stem}_{abs(hash(test_file))}"
        spec = importlib.util.spec_from_file_location(module_name, test_file)
        if spec is None: # the 2 is none fixes are for my static typechecker which got really pedantic about it.
            raise ImportError(f"Could not load spec for {test_file}")
        
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None: 
            raise ImportError(f"No loader for spec of {test_file}")
        
        spec.loader.exec_module(module)

        return module

    finally:
        sys.path.remove(test_dir) # Does not remove the actual file path, it removes it from PATH (very different guys, dont worry)


def run_all_tests():
    project_root = Path(__file__).resolve().parent
    test_files = project_root.rglob("*_tests.py")

    loader = unittest.TestLoader()
    all_tests = unittest.TestSuite()

    for test_file in test_files:
        if test_file.resolve() == Path(__file__).resolve():
            continue

        try:
            print(f"Loading tests from {test_file}")
            all_tests.addTests(loader.loadTestsFromModule(load_test_module(test_file))) # simply incredibly coding again

        except Exception as e:
            print(f"ERROR loading {test_file}: {e}")
            raise

    runner = unittest.TextTestRunner()
    result = runner.run(all_tests)

    sys.exit(not result.wasSuccessful())


if __name__ == "__main__":
    run_all_tests()
