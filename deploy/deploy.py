from __future__ import with_statement
import sys
import subprocess
import os
import optparse
import datetime
import urllib2
import webbrowser
import getpass
import re

sys.path.append(os.path.abspath("."))
import compress
import glob
import tempfile
import npm

try:
    import secrets
    hipchat_deploy_token = secrets.hipchat_deploy_token
except Exception, e:
    print "Exception raised while trying to import secrets. Attempting to continue..."
    print repr(e)
    hipchat_deploy_token = None

try:
    from secrets import app_engine_username, app_engine_password
except Exception, e:
    (app_engine_username, app_engine_password) = (None, None)

if hipchat_deploy_token:
    import hipchat.room
    import hipchat.config
    hipchat.config.manual_init(hipchat_deploy_token)

def popen_results(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0]

def popen_return_code(args, input=None):
    proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.communicate(input)
    return proc.returncode

def get_app_engine_credentials():
    if app_engine_username and app_engine_password:
        print "Using password for %s from secrets.py" % app_engine_username
        return (app_engine_username, app_engine_password)
    else:
        email = raw_input("App Engine Email: ")
        password = getpass.getpass("Password for %s: " % email)
        return (email, password)

def send_hipchat_deploy_message(version, includes_local_changes, email):
    if hipchat_deploy_token is None:
        return

    app_id = get_app_id()
    if app_id != "khan-academy":
        # Don't notify hipchat about deployments to test apps
        print 'Skipping hipchat notification as %s looks like a test app' % app_id
        return

    url = "http://%s.%s.appspot.com" % (version, app_id)

    hg_id = hg_version()
    hg_msg = hg_changeset_msg(hg_id)
    kiln_url = "https://khanacademy.kilnhg.com/Search?search=%s" % hg_id

    git_id = git_version()
    git_msg = git_revision_msg(git_id)
    github_url = "https://github.com/Khan/khan-exercises/commit/%s" % git_id

    local_changes_warning = " (including uncommitted local changes)" if includes_local_changes else ""
    message_tmpl = """
            %(hg_id)s%(local_changes_warning)s to <a href='%(url)s'>a non-default url</a>. Includes
            website changeset "<a href='%(kiln_url)s'>%(hg_msg)s</a>" and khan-exercises
            revision "<a href='%(github_url)s'>%(git_msg)s</a>."
            """ % {
                "url": url,
                "hg_id": hg_id,
                "kiln_url": kiln_url,
                "hg_msg": hg_msg,
                "github_url": github_url,
                "git_msg": git_msg,
                "local_changes_warning": local_changes_warning,
            }
    public_message = "Just deployed %s" % message_tmpl
    private_message = "%s just deployed %s" % (email, message_tmpl)

    hipchat_message(public_message, ["Exercises"])
    hipchat_message(private_message, ["1s and 0s"])

def hipchat_message(msg, rooms):
    if hipchat_deploy_token is None:
        return

    for room in hipchat.room.Room.list():

        if room.name in rooms:

            result = ""
            msg_dict = {"room_id": room.room_id, "from": "Mr Monkey", "message": msg, "color": "purple"}

            try:
                result = str(hipchat.room.Room.message(**msg_dict))
            except:
                pass

            if "sent" in result:
                print "Notified Hipchat room %s" % room.name
            else:
                print "Failed to send message to Hipchat: %s" % msg

def get_app_id():
    f = open("app.yaml", "r")
    contents = f.read()
    f.close()

    app_re = re.compile("^application:\s+(.+)$", re.MULTILINE)
    match = app_re.search(contents)

    return match.groups()[0]

def hg_st():
    output = popen_results(['hg', 'st', '-mard', '-S'])
    return len(output) > 0

def hg_pull_up():
    # Pull latest
    popen_results(['hg', 'pull'])

    # Hg up and make sure we didn't hit a merge
    output = popen_results(['hg', 'up'])
    lines = output.split("\n")
    if len(lines) != 2 or lines[0].find("files updated") < 0:
        # Ran into merge or other problem
        return -1

    return hg_version()

def hg_version():
    # grab the tip changeset hash
    current_version = popen_results(['hg', 'identify','-i']).strip()
    return current_version or -1

def hg_changeset_msg(changeset_id):
    # grab the summary and date
    output = popen_results(['hg', 'log', '--template','{desc}', '-r', changeset_id])
    return output

def git_version():
    # grab the tip changeset hash
    return popen_results(['git', '--work-tree=khan-exercises/', '--git-dir=khan-exercises/.git', 'rev-parse', 'HEAD']).strip()

def git_revision_msg(revision_id):
    return popen_results(['git', '--work-tree=khan-exercises/', '--git-dir=khan-exercises/.git', 'show', '-s', '--pretty=format:%s', revision_id]).strip()

def check_secrets():
    content = ""

    try:
        f = open("secrets.py", "r")
        content = f.read()
        f.close()
    except:
        return False

    # Try to find the beginning of our production facebook app secret
    # to verify deploy is being sent from correct directory.
    regex = re.compile("^facebook_app_secret = '050c.+'$", re.MULTILINE)
    return regex.search(content)

def tidy_up():
    """moves all pycs and compressed js/css to a rubbish folder alongside the project"""
    trashdir = tempfile.mkdtemp(dir="../", prefix="rubbish-")

    print "Moving old files to %s." % trashdir

    with open(".hgignore", "r") as f:
        please_tidy = [line.strip() for line in f]

    please_tidy = [line for line in please_tidy if not line.startswith("#")]
    but_ignore = set(["secrets.py", "", "syntax: glob", ".git", ".pydevproject"])
    please_tidy = set(please_tidy) - but_ignore

    for root, dirs, files in os.walk("."):
        if ".git" in dirs:
            dirs.remove(".git")
        if ".hg" in dirs:
            dirs.remove(".hg")

        for dirname in dirs:
            removables = [glob.glob(os.path.join(root, dirname, p)) for p in please_tidy]
            removables = [p for p in removables if p]

            # flatten sublists of removable files
            please_remove = [filename for sublist in removables for filename in sublist]
            for path in please_remove:
                os.renames(path, os.path.join(trashdir, path))

def check_deps():
    """Check if npm and friends are installed"""
    return npm.check_dependencies()

def compile_handlebar_templates():
    print "Compiling handlebar templates"
    return 0 == popen_return_code([sys.executable,
                                   'deploy/compile_handlebar_templates.py'])

def compress_js():
    print "Compressing javascript"
    compress.compress_all_javascript()

def compress_css():
    print "Compressing stylesheets"
    compress.compress_all_stylesheets()

def compile_templates():
    print "Compiling all templates"
    return 0 == popen_return_code([sys.executable, 'deploy/compile_templates.py'])

def prime_cache(version):
    try:
        resp = urllib2.urlopen("http://%s.%s.appspot.com/api/v1/autocomplete?q=calc" % (version, get_app_id()))
        resp.read()
        resp = urllib2.urlopen("http://%s.%s.appspot.com/api/v1/playlists/library/compact" % (version, get_app_id()))
        resp.read()
        print "Primed cache"
    except:
        print "Error when priming cache"

def open_browser_to_ka_version(version):
    webbrowser.open("http://%s.%s.appspot.com" % (version, get_app_id()))

def deploy(version, email, password):
    print "Deploying version " + str(version)
    return 0 == popen_return_code(['appcfg.py', '-V', str(version), "-e", email, "--passin", "update", "."], "%s\n" % password)

def main():

    start = datetime.datetime.now()

    version = 2

    compress.hashes = {}

    print "Deploying version " + str(version)

    if not compile_templates():
        print "Failed to compile templates, bailing."
        return

    if not compile_handlebar_templates():
        print "Failed to compile handlebars templates, bailing."
        return

    compress_js()
    compress_css()

    end = datetime.datetime.now()
    print "Done. Duration: %s" % (end - start)

if __name__ == "__main__":
    main()
