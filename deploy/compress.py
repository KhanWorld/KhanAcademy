from __future__ import with_statement
import os
import shutil
import subprocess
import md5
import re
import StringIO
import base64
import copy
from js_css_packages import packages
import npm

COMBINED_FILENAME = "combined"
URI_FILENAME = "uri"
COMPRESSED_FILENAME = "compressed"
HASHED_FILENAME_PREFIX = "hashed-"
PATH_PACKAGES = "js_css_packages/packages.py"
PATH_PACKAGES_COMPRESSED = "js_css_packages/packages_compressed.py"
PATH_PACKAGES_HASH = "js_css_packages/packages_hash.py"

packages_stylesheets = copy.deepcopy(packages.stylesheets)
packages_javascript = copy.deepcopy(packages.javascript)
if os.path.isfile(PATH_PACKAGES_HASH):
    import js_css_packages.packages_hash
    hashes = copy.deepcopy(js_css_packages.packages_hash.hashes)
else:
    hashes = {}

def compress_all_javascript():
    dict_packages = packages.javascript
    compress_all_packages(os.path.join("..", "javascript"), dict_packages, ".js")

def compress_all_stylesheets():
    dict_packages = packages.stylesheets
    compress_all_packages(os.path.join("..", "stylesheets"), dict_packages, ".css")

# Combine all .js\.css files in all "-package" suffixed directories
# into a single combined.js\.css file for each package, then
# minify into a single compressed.js\.css file.
def compress_all_packages(default_path, dict_packages, suffix):
    if not check_deps():
        return

    for package, path, files in resolve_files(default_path, dict_packages, suffix):
        compress_package(package, path, files, suffix)

        hashed_content = "compressed_javascript=%s\ncompressed_stylesheets=%s\n" % \
            (str(packages_javascript), str(packages_stylesheets))

        # Remove the old one.
        if os.path.exists(PATH_PACKAGES_COMPRESSED):
            os.remove(PATH_PACKAGES_COMPRESSED)

        with open(PATH_PACKAGES_COMPRESSED, "w") as f:
            f.write(hashed_content)

    with open(PATH_PACKAGES_HASH, 'w') as hash_file:
        hash_file.write('hashes = %s\n' % str(hashes))

# iterate through the packages file and yield the full path for every file
def resolve_files(default_path, packages, suffix):
    for package_name in packages:
        package = packages[package_name]

        if 'files' in package:
            package_path = package.get("base_path")
            if not package_path:
                dir_name = "%s-package" % package_name
                package_path = os.path.join(default_path, dir_name)

            package_path = os.path.join(os.path.dirname(__file__), package_path)
            package_path = os.path.normpath(package_path)

            # Assume any files that do not have the correct suffix are already
            # compiled by some earlier process.
            # For example, a file called template.handlebars will be compiled
            # to template.handlebars.js
            files = []
            for f in package["files"]:
                if f.split('.')[-1] == suffix[1:]:
                    files.append(f)
                else:
                    files.append(f + suffix)

            yield (package_name, package_path, files)

def file_size_report():
    # only works on js for now
    package = packages.javascript
    path = os.path.join("..", "javascript")
    suffix = '.js'
    uglify_path = npm.package_installed("uglifyjs")


    print "Uglifying and gzipping all packages..."
    file_sizes = []
    for package_name, path, files in resolve_files(path, package, suffix):
        for file in files:
            if file in packages.transformations:
                file = packages.transformations[file]
            file_path = os.path.normpath(os.path.join(path, file))
            file_path_min = file_path[:-len(suffix)] + '.min' + suffix
            popen_results([uglify_path, '-o', file_path_min, file_path])
            subprocess.Popen(['gzip', '-f', file_path_min]).wait()
            file_path_gz = file_path_min + '.gz'

            file_size = os.stat(file_path_gz).st_size
            file_sizes.append((package_name, file, file_size))

            # Clean up. The minified file is already deleted by gzip.
            os.remove(file_path_gz)

    file_sizes.sort(key=lambda f: f[2], reverse=True) # size
    file_sizes.sort(key=lambda f: f[0]) # package

    for package_name, file, size in file_sizes:
        print '\t'.join(map(str, [size, package_name, file]))

# Overview:
# Take a set of js or css files then:
# 1. Combine them into one large file
# 2. Hash the file
# 3. Check the hash to see if we already have a copy of the file, stop if we do
# 4. Compress the file
# 5. Replace any images in the file that need replaced (creating a second file)
# For each file (one or two of them):
# 6. Hash the file again
# 7. Create a new file using the second hash in its name
# 8. Insert the hashes into packages_hash.py
# 9. Insert the second hash into packages.py
#
# Note: The two hashes will be different. The reason we hash twice is because
# we use the first hash in packages_hash.py to check if we need to compress the
# file and the second hash to identify the created file.
# packages_hash file format:
#     hashes = {'file': (combined hash, compressed hash, final path), ...}
def compress_package(name, path, files, suffix):
    if not os.path.exists(path):
        raise Exception("Path does not exist: %s" % path)

    # Remove the old combined and minified files then replace them
    remove_combined(path, suffix)
    path_combined = combine_package(path, files, suffix)
    remove_compressed(path, suffix)

    with open(path_combined, 'r') as compressed:
        content = compressed.read()
    new_hash = md5.new(content).hexdigest()

    path_compressed = ''
    fullname = name+suffix
    if (fullname not in hashes
            or hashes[fullname][0] != new_hash
            or not os.path.exists(hashes[fullname][2])):

        path_compressed = minify_package(path, path_combined, suffix)
        path_hashed, hash_sig = hash_package(name, path, path_compressed, suffix)

        insert_hash_sig(name, hash_sig, suffix)

        if not os.path.exists(path_hashed):
            raise Exception("Did not successfully compress and hash: %s" % path)

        hashes[fullname] = new_hash, hash_sig, path_hashed
    else:
        insert_hash_sig(name, hashes[fullname][1], suffix)

    if suffix == '.css' and 'mobile' not in name:
        non_ie_fullname = name + '-non-ie' + suffix
        if non_ie_fullname not in hashes \
                or hashes[non_ie_fullname][0] != new_hash \
                or not os.path.exists(hashes[non_ie_fullname][2]):

            if path_compressed == '':
                path_compressed = minify_package(path, path_combined, suffix)
            path_with_uris = remove_images(path, path_compressed, suffix)
            path_hashed, hash_sig = hash_package(name, path, path_with_uris, suffix)
            insert_hash_sig(name+'-non-ie', hash_sig, suffix)

            if not os.path.exists(path_hashed):
                raise Exception("Did not successfully compress and hash: %s" % \
                    path)

            hashes[non_ie_fullname] = new_hash, hash_sig, path_hashed
        else:
            insert_hash_sig(name+'-non-ie', hashes[non_ie_fullname][1], suffix)

# Remove previous combined.js\.css
def remove_combined(path, suffix):
    filenames = os.listdir(path)
    for filename in filenames:
        if filename.endswith(COMBINED_FILENAME + suffix):
            os.remove(os.path.join(path, filename))

# Remove previous uri.css and compress.js\.css files
def remove_compressed(path, suffix):
    filenames = os.listdir(path)
    for filename in filenames:
        if filename.endswith(URI_FILENAME + suffix) \
                or filename.endswith(COMPRESSED_FILENAME + suffix):
            os.remove(os.path.join(path, filename))

# Use UglifyJS for JS and node-cssmin for CSS to minify the combined file
def minify_package(path, path_combined, suffix):
    uglify_path = npm.package_installed("uglifyjs")
    cssmin_path = npm.package_installed("cssmin")

    path_compressed = os.path.join(path, COMPRESSED_FILENAME + suffix)
    print "Compressing %s into %s" % (path_combined, path_compressed)

    if suffix == ".js":
        print popen_results([uglify_path, "-o", path_compressed, path_combined])
    elif suffix == ".css":
        compressed = popen_results([cssmin_path, path_combined])
        if compressed:
            f = open(path_compressed, 'w')
            f.write(compressed)
            f.close()
    else:
        raise Exception("Unable to compress %s files" % suffix)

    if not os.path.exists(path_compressed):
        raise Exception("Unable to compress: %s" % path_combined)

    return path_compressed

def remove_images_from_line(filename):
    filename = filename.group(0)

    ext = os.path.splitext(filename)[1][1:].lower()
    if ext == 'jpg':
        ext = 'jpeg'

    filename = os.path.join(os.path.dirname(__file__), '..', filename[1:])

    print "Removing images from %s" % filename
    if os.path.isfile(filename):
        with open(filename) as img:
            f = StringIO.StringIO()
            f.write(img.read())
            return '\'data:image/%s;base64,%s\'' % \
                (ext, base64.b64encode(f.getvalue()))

    return filename

def remove_images(path, path_combined, suffix):
    if suffix != '.css': # don't touch js (yes, this is redundant)
        return path_combined

    path_without_urls = os.path.join(path, URI_FILENAME + suffix)
    print "Replacing urls from %s to get %s" % (path_combined, path_without_urls)

    new_file = open(path_without_urls, 'w')

    r = re.compile('/\*! *data-uri\(\'?/images/(\S+)\.(png|gif|GIF|jpg)\'?\) *\*/')
    rs = re.compile('/\*! *data-uri\(\'?data:image/(?:png|gif|jpg);base64,[0-9A-Za-z=/+]+\'?\) *\*/')
    with open(path_combined) as f:
        for line in f:
            if r.search(line):
                for i in r.finditer(line):
                    # /images/dark-page-bg.png
                    #         <----------> <->
                    #             |         |
                    #         i.group(1) i.group(2)
                    urlpath = '/images/%s.%s' % (i.group(1), i.group(2))
                    line = re.sub(urlpath, remove_images_from_line, line)

                # remove the data-uri comments
                line = rs.sub('', line)
            new_file.write(line)

    new_file.close()

    if not os.path.exists(path_without_urls):
        raise Exception("Unable to remove images: %s" % path_combined)

    return path_without_urls

def hash_package(name, path, path_compressed, suffix):
    f = open(path_compressed, "r")
    content = f.read()
    f.close()

    hash_sig = md5.new(content).hexdigest()
    path_hashed = os.path.join(path, "hashed-%s%s" % (hash_sig, suffix))

    print "Copying %s into %s" % (path_compressed, path_hashed)
    shutil.copyfile(path_compressed, path_hashed)

    if not os.path.exists(path_hashed):
        raise Exception("Unable to copy to hashed file: %s" % path_compressed)

    return path_hashed, hash_sig

def insert_hash_sig(name, hash_sig, suffix):
    current_dict = packages_stylesheets if suffix.endswith('.css') else packages_javascript
    if name not in current_dict:
        current_dict[name] = {}
    current_dict[name]["hashed-filename"] = "hashed-%s%s" % (hash_sig, suffix)

# Combine all files into a single combined.js\.css
def combine_package(path, files, suffix):
    path_combined = os.path.join(path, COMBINED_FILENAME + suffix)

    print "Building %s" % path_combined

    content = []
    for static_filename in files:
        if static_filename in packages.transformations:
            static_filename = packages.transformations[static_filename]

        path_static = os.path.join(path, static_filename)
        print "   ...adding %s" % path_static
        f = open(path_static, 'r')
        content.append(f.read())
        f.close()

    if os.path.exists(path_combined):
        raise Exception("File about to be compressed already exists: %s" % path_combined)

    f = open(path_combined, "w")
    separator = "\n" if suffix.endswith(".css") else ";\n"
    f.write(separator.join(content))
    f.close()

    return path_combined

def popen_results(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0]

def check_deps():
    """check for node and friends"""
    uglify_path = npm.package_installed("uglifyjs")
    cssmin_path = npm.package_installed("cssmin")
    
    if uglify_path and cssmin_path:
        return True
    else:
        print "uglify and cssmin not found :("
        return False

