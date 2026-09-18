import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Patch handleGvizData
gviz_start = text.find('function handleGvizData(data, year) {')
if gviz_start != -1:
    rows_start = text.find('rows.forEach(row => {', gviz_start)
    if rows_start != -1:
        # Insert the state variables
        state_vars = """                let currentCompId = "RT1";
                let currentCompTitle = "";
                let currentCompLevel = 1;
                let currentCompDesc = "";

                """
        text = text[:rows_start] + state_vars + text[rows_start:]

        # Find the loop body start
        loop_body_start = text.find('const cells = row.c || [];', rows_start)
        
        # We want to add logic to parse competence info
        comp_parse_logic = """                    // Look for competence info
                    for (let i = 0; i < cells.length; i++) {
                        const txt = cells[i] && cells[i].v ? String(cells[i].v).trim() : "";
                        if (/^(RT|ROM)\\d+$/i.test(txt)) {
                            if (i + 3 < cells.length) {
                                currentCompId = txt.toUpperCase();
                                currentCompTitle = cells[i+1] && cells[i+1].v ? String(cells[i+1].v).trim() : "";
                                const lvlMatch = (cells[i+2] && cells[i+2].v ? String(cells[i+2].v) : "").match(/(\\d+)/);
                                if (lvlMatch) currentCompLevel = parseInt(lvlMatch[1], 10);
                                currentCompDesc = cells[i+3] && cells[i+3].v ? String(cells[i+3].v).trim() : "";
                            }
                            break;
                        }
                    }

                    """
        text = text[:loop_body_start + 26] + '\n' + comp_parse_logic + text[loop_body_start + 26:]

        # Now replace the newAcItems.push call
        push_start = text.find('newAcItems.push({', rows_start)
        push_end = text.find('});', push_start) + 3
        
        new_push = """                        newAcItems.push({
                            code,
                            title,
                            competence: currentCompId,
                            comp_title: currentCompTitle,
                            comp_level: currentCompLevel,
                            description: currentCompDesc,
                            levels: [level],
                            proof,
                            analysis,
                            resources
                        });"""
        text = text[:push_start] + new_push + text[push_end:]

# Patch fetchCsvData
csv_start = text.find('async function fetchCsvData(gid, year) {')
if csv_start != -1:
    rows_start = text.find('lines.forEach(line => {', csv_start)
    if rows_start != -1:
        state_vars = """                let currentCompId = "RT1";
                let currentCompTitle = "";
                let currentCompLevel = 1;
                let currentCompDesc = "";

                """
        text = text[:rows_start] + state_vars + text[rows_start:]

        loop_body_start = text.find('const columns = line.split', rows_start)
        loop_body_end = text.find(';', loop_body_start) + 1
        
        comp_parse_logic = """
                    // Look for competence info
                    for (let i = 0; i < columns.length; i++) {
                        let txt = columns[i].replace(/^["']|["']$/g, '').trim();
                        if (/^(RT|ROM)\\d+$/i.test(txt)) {
                            if (i + 3 < columns.length) {
                                currentCompId = txt.toUpperCase();
                                currentCompTitle = columns[i+1].replace(/^["']|["']$/g, '').trim();
                                const lvlMatch = columns[i+2].replace(/^["']|["']$/g, '').match(/(\\d+)/);
                                if (lvlMatch) currentCompLevel = parseInt(lvlMatch[1], 10);
                                currentCompDesc = columns[i+3].replace(/^["']|["']$/g, '').trim();
                            }
                            break;
                        }
                    }
"""
        text = text[:loop_body_end] + comp_parse_logic + text[loop_body_end:]

        push_start = text.find('newAcItems.push({', rows_start)
        push_end = text.find('});', push_start) + 3
        
        new_push = """                        newAcItems.push({
                            code,
                            title,
                            competence: currentCompId,
                            comp_title: currentCompTitle,
                            comp_level: currentCompLevel,
                            description: currentCompDesc,
                            levels: [level],
                            proof,
                            analysis,
                            resources
                        });"""
        text = text[:push_start] + new_push + text[push_end:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("index.html patched!")
