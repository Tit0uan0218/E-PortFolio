import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Patch fetchHtmlProxy
html_start = text.find('async function fetchHtmlProxy')
if html_start != -1:
    rows_start = text.find('rows.forEach(row => {', html_start)
    if rows_start != -1:
        state_vars = """                    let currentCompId = "RT1";
                    let currentCompTitle = "";
                    let currentCompLevel = 1;
                    let currentCompDesc = "";

"""
        text = text[:rows_start] + state_vars + text[rows_start:]

        loop_body_start = text.find('const cells = row.querySelectorAll("td");', rows_start)
        loop_body_end = text.find(';', loop_body_start) + 1
        
        comp_parse_logic = """
                        // Look for competence info
                        for (let i = 0; i < cells.length; i++) {
                            const txt = cells[i].textContent.trim();
                            if (/^(RT|ROM)\\d+$/i.test(txt)) {
                                if (i + 3 < cells.length) {
                                    currentCompId = txt.toUpperCase();
                                    currentCompTitle = cells[i+1].textContent.trim();
                                    const lvlMatch = cells[i+2].textContent.match(/(\\d+)/);
                                    if (lvlMatch) currentCompLevel = parseInt(lvlMatch[1], 10);
                                    currentCompDesc = cells[i+3].textContent.trim();
                                }
                                break;
                            }
                        }
"""
        text = text[:loop_body_end] + comp_parse_logic + text[loop_body_end:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("index.html patched fetchHtmlProxy!")
