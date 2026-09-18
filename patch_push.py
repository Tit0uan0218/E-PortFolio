import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# We need to make sure every newAcItems.push has comp_title, comp_level, description
# But where do we get those variables if we don't extract them in the loops?

def patch_push(match):
    return """                        newAcItems.push({
                            code,
                            title,
                            competence: typeof currentCompId !== 'undefined' ? currentCompId : competence,
                            comp_title: typeof currentCompTitle !== 'undefined' ? currentCompTitle : "",
                            comp_level: typeof currentCompLevel !== 'undefined' ? currentCompLevel : 1,
                            description: typeof currentCompDesc !== 'undefined' ? currentCompDesc : (typeof competenceMetaDesc !== 'undefined' ? competenceMetaDesc[competence] : ""),
                            levels: [level],
                            proof,
                            analysis,
                            resources
                        });"""

text = re.sub(r'newAcItems\.push\(\{[^}]*description:\s*competenceMetaDesc\[competence\]\s*\|\|\s*""[^}]*\}\);', patch_push, text, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("index.html patched again!")
