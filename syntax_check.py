import ast
import sys

def check_python_syntax(filename):
    try:
        with open(filename, 'r') as f:
            content = f.read()
        ast.parse(content)
        print(f"✓ {filename}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {filename}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"✗ {filename}: Error - {e}")
        return False

# Check files
files_to_check = [
    'api/__init__.py',
    'api/main.py', 
    'api/config.py'
]

all_ok = True
for file in files_to_check:
    if not check_python_syntax(file):
        all_ok = False

sys.exit(0 if all_ok else 1)
