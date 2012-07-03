#!/usr/bin/env python

import optparse
import os
import sys
# Install the Python unittest2 package before you run this script.
import unittest2

USAGE = """%prog SDK_PATH TEST_PATH
Runs unit tests for App Engine apps.

This sets the appropriate Python PATH and environment. Tests files are
expected to be named with a _test.py suffix.

SDK_PATH    Path to the SDK installation
TEST_PATH   Path to package containing test modules or Python file
            containing test case.
"""


TEST_FILE_RE = '*_test.py'

def file_path_to_module(path):
    return path.replace('.py', '').replace(os.sep, '.')

def main(sdk_path, test_path):
    if 'SERVER_SOFTWARE' not in os.environ:
        os.environ['SERVER_SOFTWARE'] = 'Development'
    if 'CURRENT_VERSION' not in os.environ:
        os.environ['CURRENT_VERSION'] = '764.1'

    sys.path.insert(0, sdk_path)
    import dev_appserver
    dev_appserver.fix_sys_path()
    top_project_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    sys.path.insert(0, os.path.join(top_project_dir, "api/packages"))
    sys.path.insert(0, os.path.join(top_project_dir, "api/packages/flask.zip"))

    loader = unittest2.loader.TestLoader()
    if test_path.endswith('.py'):
        suite =  loader.loadTestsFromName(file_path_to_module(test_path))
    else:
        suite = loader.discover(test_path, pattern=TEST_FILE_RE)

    unittest2.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    options, args = parser.parse_args()
    if len(args) != 2:
        print 'Error: Exactly 2 arguments required.'
        parser.print_help()
        sys.exit(1)
    SDK_PATH = args[0]
    TEST_PATH = args[1]
    main(SDK_PATH, TEST_PATH)
