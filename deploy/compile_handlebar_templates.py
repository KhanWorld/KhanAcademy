# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import shutil
import npm


def validate_env():
    """ Ensures that pre-requisites are met for compiling handlebar templates.
    
    TODO: point to documents when they're made.
    Handlebars doc: https://github.com/wycats/handlebars.js/
    """
    handlebars_path = npm.package_installed("handlebars")
    if handlebars_path:
        subprocess.call([handlebars_path],
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE)
    else:
        sys.exit("Can't find handlebars. Did you install it?")
        
def compile_template(root_path, rel_path, file_name):
    """ Compiles a single template into an output that can be used by the
    JavaScript client.
    
    This logic is dependent on javascript/shared-package/templates.js
    
    """
    handlebars_path = npm.package_installed("handlebars")
    try:
        dir_path = os.path.join(root_path, rel_path)
        
        # Total hack to rename the file temporarily to be namespaced. There
        # is no way to tell handlebars to prefix the resulting template with
        # a namespace, so we need to rename the file temporarily.
        qualified_name = file_name
        while True:
            head, tail = os.path.split(rel_path)
            if tail:
                qualified_name = "%s_%s" % (tail, qualified_name)
            else:
                break
            rel_path = head
        
        input_path = os.path.join(dir_path, qualified_name)
        shutil.copyfile(os.path.join(dir_path, file_name), input_path)
        
        # Append ".js" to the template name for the output name.
        output_path = "%s.js" % os.path.join(dir_path, file_name)
        
        # "-m" for minified output
        # "-f" specifies output file
        subprocess.call([handlebars_path, "-m", "-f", output_path, input_path],
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE)
        os.remove(input_path)
        print "Compiled to %s" % output_path
    except subprocess.CalledProcessError:
        #sys.exit("Error compiling %s" % file_path)
        pass

def compile_templates():
    root_path = "javascript"
    rel_path_index = len(root_path) + 1
    for dir_path, dir_names, file_names in os.walk(root_path):
        for file_name in file_names:
            if file_name.endswith(".handlebars"):
                # os.path.relpath is not available until Python 2.6
                compile_template(root_path,
                                 dir_path[rel_path_index:],
                                 file_name)

if __name__ == "__main__":
    validate_env()
    compile_templates()
