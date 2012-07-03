# npm.py - an interface to our increasing love of node
import os, sys
import subprocess

MODULE_PATH = os.path.join(os.getcwd(), "deploy", "node_modules")

def popen_results(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0]

def installed():
    """docstring for npm_installed"""
    return popen_results(["command", "-v", "npm"]).strip()

def local_modules_setup():
    """see if npm install has been called before"""
    return os.path.exists(MODULE_PATH)

def package_installed(package, local_only=False):
    """checks to see if the module is installed and returns a path to it"""
    sys_install = popen_results(["command", "-v", package]).strip()
    local_install = os.path.exists( os.path.join(MODULE_PATH, ".bin",package))

    if local_only:
        return os.path.join(MODULE_PATH, ".bin",package) if local_install else local_install
    else:
        return os.path.join(MODULE_PATH, ".bin",package) if local_install else sys_install

def call(cmd):
    """docstring for install_deps"""
    cd = os.getcwd()
    os.chdir(os.path.join(cd, "deploy"))
    npm_results = popen_results(["npm", cmd])
    os.chdir(cd)
    return npm_results

def check_dependencies():
    if not installed():
        print '\033[31m' +  "-- DANGA-ZONE!"+ '\033[0m'
        print "npm isn't installed, try \n"
        print "  curl http://npmjs.org/install.sh | sh"
        print "\nor follow the instructions here:"
        print "  http://npmjs.org/"
        return False

    if local_modules_setup():
        print '\033[32m' + "==> A-OK!"+ '\033[0m' +" npm is updating local module dependencies"
        npm_results = call("update")

    else:
        print '\033[31m' + "==> Danga-Zone!"+ '\033[0m (well not really)'
        print "    Installing node dependencies locally via package.json"
        print '  - this should only happen once, all files are in \033[32mdeploy/node_modules\033[0m\n'
        npm_results = call("install")

    print npm_results
    return True
