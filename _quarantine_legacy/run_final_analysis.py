import json, os
f = os.path.expanduser('~/deployflow_model_comparison.json')
data = json.load(open(f, encoding='utf-8'))

cat_names = {
    'debug': 'Debugging',
    'algorithm': 'Algorithm Design',
    'architecture': 'System Design',
    'edge_cases': 'Edge Cases',
    'code_review': 'Security Review'
}

out = []
out.append('=== RANKING FINAL DEFINITIVO ===')
out.append('')

for cat in ['debug', 'algorithm', 'architecture', 'edge_cases', 'code_review']:
    out.append(f'--- {cat_names[cat]} ---')
    results = []
    for m, v in data.items():
        p = v.get('prompts', {}).get(cat)
        if p and p.get('status') == 'OK':
            resp = p.get('response', '')
            tokens = p.get('completion_tokens', 0)
            results.append((tokens, m, resp))
    results.sort(reverse=True)

    for i, (tokens, m, resp) in enumerate(results[:3], 1):
        structure_score = 0
        if '## ' in resp:
            structure_score += 1
        if '```' in resp:
            structure_score += 1
        if '**' in resp:
            structure_score += 1
        if ('- ' in resp[:500]) or ('1.' in resp[:500]):
            structure_score += 1

        preview = resp[:300].replace('\n', ' ')
        out.append(f'  {i}. {m} ({tokens}tk) | structure={structure_score}/4')
        out.append(f'     {preview}')

    thinking = [(t, m, r) for t, m, r in results if '-thinking' in m]
    non_thinking = [(t, m, r) for t, m, r in results if '-thinking' not in m]
    best_thinking = thinking[0] if thinking else None
    best_non = non_thinking[0] if non_thinking else None
    if best_thinking and best_non and best_non[0] > best_thinking[0]:
        out.append(f'  *** Non-thinking beats thinking: {best_non[1]} ({best_non[0]}tk) vs {best_thinking[1]} ({best_thinking[0]}tk)')
    out.append('')

out.append('')
out.append('=== THINKING vs NON-THINKING ===')
th_wins = 0
nth_wins = 0
for cat in ['debug', 'algorithm', 'architecture', 'edge_cases', 'code_review']:
    results = []
    for m, v in data.items():
        p = v.get('prompts', {}).get(cat)
        if p and p.get('status') == 'OK':
            results.append((p.get('completion_tokens', 0), m))
    results.sort(reverse=True)
    top3 = [m for _, m in results[:3]]
    th_count = sum(1 for m in top3 if '-thinking' in m)
    if th_count >= 2:
        th_wins += 1
    else:
        nth_wins += 1

out.append(f'Categories won by thinking (>=2 of top 3): {th_wins}')
out.append(f'Categories won by non-thinking: {nth_wins}')

with open('C:/Users/JESUS TE AMA/final_analysis.txt', 'w', encoding='utf-8') as f2:
    f2.write('\n'.join(out))
print('done')
