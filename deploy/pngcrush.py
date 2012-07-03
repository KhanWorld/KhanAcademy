import re
import subprocess
import os

def popen_results(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0]

def pngcrush_image(path, name):

    name_new = name.replace(".", ".crushed.")

    path_old = os.path.join(path, name)
    path_new = os.path.join(path, name_new)

    output = popen_results(['pngcrush', '-reduce', path_old, path_new])
    print(output)

    output_move = popen_results(['mv', path_new, path_old])
    print(output_move)

def pngcrush_images():
    print "pngcrushing images"
    path = os.path.join(os.path.dirname(__file__), "..", "images")

    for root, dirs, files in os.walk(path):
        for name in files:
            if name.lower().endswith(".png"):
                pngcrush_image(root, name)

def main():
    pngcrush_images()

if __name__ == "__main__":
    main()

