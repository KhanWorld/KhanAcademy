import os
import cgi

from app import App
from js_css_packages import packages
import request_cache
import util

# Attempt to load compressed packages (may not exist in dev mode)
try:
    from js_css_packages import packages_compressed
except Exception:
    pass

@request_cache.cache()
def use_compressed_packages():
    qs = os.environ.get("QUERY_STRING")
    dict_qs = cgi.parse_qs(qs)

    if App.is_dev_server and ["1"] != dict_qs.get("compressed_packages"):
        return False

    if ["1"] == dict_qs.get("uncompressed_packages"):
        return False

    return True

def base_name(file_name):
    return file_name[:file_name.index(".")]

def get_inline_template(package_name, file_name):
    """ Generate a string for <script> tag that contains the contents
    of the specified template.

    This is used in debug mode so that templates can be changed without having
    to precompile them to test.
    Note - this does not work in production! Static files are
    served from a different server and are not part of the main
    package. "clienttemplates" is a symlink to get around this
    limitation in development only.

    This logic is dependent on javascript/shared-package/templates.js

    """
    path = "clienttemplates/%s-package/%s" % (package_name, file_name)
    handle = open(path, 'r')
    contents = handle.read()
    handle.close()
    name = base_name(file_name)
    return ("<script type='text/x-handlebars-template' "
         	"id='template_%s-package_%s'>%s</script>") % (package_name, name, contents)


def js_package(package_name):
    loaded_script = "<script type='text/javascript'>dynamicPackageLoader.setPackageLoaded('%s');</script>" % package_name
    if not use_compressed_packages():
        package = packages.javascript[package_name]
        base_url = package.get("base_url") or "/javascript/%s-package" % package_name
        list_js = []
        for file_name in package["files"]:
            if file_name.split('.')[-1] == 'handlebars':
                # In debug mode, templates are served as inline <script> tags.
                list_js.append(get_inline_template(package_name, file_name))
            else:
                list_js.append("<script type='text/javascript' src='%s/%s'></script>" % (base_url, file_name))
        list_js.append(loaded_script)
        return "\n".join(list_js)
    else:
        package = packages_compressed.compressed_javascript[package_name]
        base_url = package.get("base_url") or "/javascript/%s-package" % package_name
        return "<script type='text/javascript' src='%s/%s'></script>%s" % (util.static_url(base_url), package["hashed-filename"], loaded_script)

def js_dynamic_package(package_name):
    list_js = [ "function dynamicLoadPackage_%s(callback) {" % package_name, "dynamicPackageLoader.load('%s', callback, [" % package_name ]
    if not use_compressed_packages():
        package = packages.javascript[package_name]
        base_url = package.get("base_url") or "/javascript/%s-package" % package_name
        files_js = []
        for file_name in package["files"]:
            files_js.append("'%s/%s'" % (base_url, file_name))
        list_js.append(",\n".join(files_js))
    else:
        package = packages_compressed.compressed_javascript[package_name]
        base_url = package.get("base_url") or "/javascript/%s-package" % package_name
        list_js.append("'%s/%s'" % (base_url, package["hashed-filename"]))

    list_js.extend(["]);","}"])
    return "\n".join(list_js)

def css_package(package_name):

    if not use_compressed_packages():
        package = packages.stylesheets[package_name]
    else:
        package = packages_compressed.compressed_stylesheets[package_name]
    base_url = package.get("base_url") or "/stylesheets/%s-package" % package_name

    list_css = []
    if not use_compressed_packages():
        for filename in package["files"]:
            list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
                % (base_url, filename))
    elif package_name+'-non-ie' not in packages_compressed.compressed_stylesheets:
        list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
            % (util.static_url(base_url), package["hashed-filename"]))
    else:
        # Thank you Jammit (https://github.com/documentcloud/jammit) for the
        # conditional comments.
        non_ie_package = packages_compressed.compressed_stylesheets[package_name+'-non-ie']

        list_css.append("<!--[if (!IE)|(gte IE 8)]><!-->")

        # Stylesheets using data-uris
        list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
            % (util.static_url(base_url), non_ie_package["hashed-filename"]))

        list_css.append("<!--<![endif]-->")
        list_css.append("<!--[if lte IE 7]>")

        # Without data-uris, for IE <= 7
        list_css.append("<link rel='stylesheet' type='text/css' href='%s/%s'/>" \
            % (util.static_url(base_url), package["hashed-filename"]))

        list_css.append("<![endif]-->")

    return "".join(list_css)
