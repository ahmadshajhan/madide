import os
import subprocess
import sys

def clone_compiler():
    repo_url = "https://gitlab.com/esr/mad.git"
    target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mad_compiler_src")
    
    if not os.path.exists(target_dir):
        print(f"Cloning MAD compiler into {target_dir}...")
        try:
            subprocess.run(["git", "clone", repo_url, target_dir], check=True)
            print("Cloning complete.")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("Error: 'git' command not found. Please ensure Git is installed.")
            sys.exit(1)
    else:
        print(f"Directory {target_dir} already exists.")

if __name__ == "__main__":
    clone_compiler()
