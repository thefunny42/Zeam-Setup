
import py_compile
import sys
import os


if __name__ == "__main__":
    for base_path in sys.args[1:]:
        for path, directories, filenames in os.walk(base_path):
            for filename in filenames:
                if filename.endswith('.py'):
                    try:
                        py_compile.compile(
                            os.path.join(path, filename), doraise=True)
                    except:
                        pass

