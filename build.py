import subprocess
import sys

def install():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build():
    subprocess.check_call([sys.executable, "setup.py", "sdist", "bdist_wheel"])

'''
def upload():
    subprocess.check_call([sys.executable, "-m", "twine", "upload", "dist/*"])
'''

def clean():
    subprocess.check_call(["rm", "-rf", "build", "*.egg-info"])

if __name__ == "__main__":
    # install()
    build()
    # clean()