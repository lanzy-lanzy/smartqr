with open(r'C:\Users\gerla\dev\smartqr\core\views.py', 'r') as f:
    lines = f.readlines()

lines[239] = '    """Supply detail view (modal-ready)."""\n'

with open(r'C:\Users\gerla\dev\smartqr\core\views.py', 'w') as f:
    f.writelines(lines)

print('Fixed')
