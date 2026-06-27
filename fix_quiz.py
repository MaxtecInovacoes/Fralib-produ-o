#!/usr/bin/env python3
import re

with open('/root/maxtec-app/index.html', 'r') as f:
    html = f.read()

# Fix prazo option to go to step 5
html = html.replace("selectOption('prazo', this, 'disqualified')", "selectOption('prazo', this, 5)")

# Remove isDisqualified function completely
html = re.sub(
    r'\n\s*function isDisqualified\(\).*?^\s*\}',
    '',
    html,
    flags=re.MULTILINE | re.DOTALL
)

# Remove isDisqualified calls
html = re.sub(
    r'\n\s*if \(isDisqualified\(\)\)\s*\{[^}]*goTo\(\'disqualified\'\);[^}]*\}\s*',
    '',
    html
)

with open('/root/maxtec-app/index.html', 'w') as f:
    f.write(html)

print('Fixed quiz!')
