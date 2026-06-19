import re
import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace backend. prefixed imports in routes, services, etc.
    content = re.sub(r'from backend\.db\.', 'from db.', content)
    content = re.sub(r'from backend\.middleware\.', 'from middleware.', content)
    content = re.sub(r'from backend\.domain\.', 'from domain.', content)
    content = re.sub(r'from backend\.services\.', 'from services.', content)
    content = re.sub(r'from backend\.config\.', 'from config.', content)
    content = re.sub(r'from backend\.api\.', 'from api.', content)
    content = re.sub(r'import backend\.db\.', 'import db.', content)
    content = re.sub(r'import backend\.middleware\.', 'import middleware.', content)
    content = re.sub(r'import backend\.domain\.', 'import domain.', content)
    content = re.sub(r'import backend\.services\.', 'import services.', content)
    content = re.sub(r'import backend\.config\.', 'import config.', content)
    content = re.sub(r'import backend\.api\.', 'import api.', content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

changed = []
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') and '__pycache__' not in root:
            path = os.path.join(root, f)
            try:
                if fix_file(path):
                    changed.append(path)
            except Exception as e:
                print(f"Error processing {path}: {e}")

print(f"Fixed {len(changed)} files:")
for c in changed:
    print(f"  - {c}")