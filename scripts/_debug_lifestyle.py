import sys
sys.path.insert(0, '/root/fralib/backend')
from services.vite_react_renderer import _generate_studio_fallback_files

facts = {'business': {'segmento': 'barbearia', 'name': 'Teste', 'city': 'Curitiba'}}
files = _generate_studio_fallback_files(facts)
ls = files['src/components/LifestyleSection.tsx']
print(repr(ls[:500]))
print('---')
print('Files:', list(files.keys())[:3])
print('---')
# Check with the actual barbearia specifics
facts2 = {'business': {'segmento': 'barbearia', 'name': 'Barbearia Fio Nobre Pinhais', 'city': 'Pinhais'}}
files2 = _generate_studio_fallback_files(facts2)
ls2 = files2['src/components/LifestyleSection.tsx']
print('has {lifestyle_title} literal:', '{lifestyle_title}' in ls2)
print('has Tradição:', 'Tradi' in ls2)
print('Content:', ls2[:600])
