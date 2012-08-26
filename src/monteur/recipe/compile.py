
import py_compile
import sys
import os


if __name__ == "__main__":
    success = 0
    failed = 0
    for base_path in sys.argv[1:]:
        for path, directories, filenames in os.walk(base_path):
            for filename in filenames:
                if filename.endswith('.py'):
                    try:
                        py_compile.compile(
                            os.path.join(path, filename), doraise=True)
                        success += 1
                    except:
                        failed += 1
    print 'Compiled %d Python files, plus %d failures.' % (success, failed)

