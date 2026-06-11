import urllib.request
import re
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs

# 1. Fetch spreadsheet HTML
url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT1qQLyw9iZeU_fEaTO1s6_1mJ_vJhzr3po4ezae3q7Hz88ZNdmQqNSIkRAhB9Nx5HbuZJ0rirK-P2c/pubhtml/sheet?headers=false&gid=808860009"
print(f"Fetching Google Sheet from: {url}")
req = urllib.request.Request(url, headers={'User-Agent': 'AntigravitySync/1.0'})
try:
    with urllib.request.urlopen(req) as response:
        html_content = response.read().decode('utf-8')
except Exception as e:
    print(f"Error fetching Google Sheet: {e}")
    exit(1)

# 2. Parse HTML structure
class WaffleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = {"text": "", "link": ""}
        self.in_cell = False
        self.in_link = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current_row = []
        elif tag == 'td':
            self.in_cell = True
            self.current_cell = {"text": "", "link": ""}
        elif tag == 'a' and self.in_cell:
            self.in_link = True
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            if href:
                if 'q=' in href:
                    parsed = urlparse(href)
                    q = parse_qs(parsed.query).get('q')
                    if q:
                        href = q[0]
                self.current_cell['link'] = href

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell['text'] += data

    def handle_endtag(self, tag):
        if tag == 'tr':
            self.rows.append(self.current_row)
        elif tag == 'td':
            self.in_cell = False
            self.current_cell['text'] = self.current_cell['text'].strip()
            self.current_row.append(self.current_cell)
        elif tag == 'a':
            self.in_link = False

parser = WaffleHTMLParser()
parser.feed(html_content)

new_ac_items = []
strong_codes = []

competence_meta = {
    "RT1": "Administrer un réseau",
    "RT2": "Maîtriser les différentes composantes des solutions de connexion des entreprises et des usagers",
    "RT3": "Développer une application R&T",
    "ROM1": "Gérer les infrastructures des réseaux opérateurs",
    "ROM2": "Mettre en oeuvre le système de téléphonie de l’entreprise"
}

def parse_resources(text):
    if not text:
        return []
    return [r.strip() for r in text.split(",") if r.strip()]

for row in parser.rows:
    # Find cell containing the AC code
    ac_idx = -1
    ac_text = ""
    for idx, cell in enumerate(row):
        txt = cell["text"]
        if re.match(r"^AC\d+", txt, re.IGNORECASE):
            ac_idx = idx
            ac_text = txt
            break
    
    if ac_idx != -1:
        # Extract code and title
        match = re.match(r"^(AC\d+(?:\.\d+)?(?:ROM)?)\s*(.*)$", ac_text, re.IGNORECASE)
        if match:
            code = match.group(1)
            title = match.group(2).strip()
        else:
            code = ac_text
            title = ""
        
        # Resources (BUT1 is ac_idx + 1, BUT2 is ac_idx + 2, BUT3/ROM is ac_idx + 3/4)
        r1 = parse_resources(row[ac_idx + 1]["text"]) if ac_idx + 1 < len(row) else []
        r2 = parse_resources(row[ac_idx + 2]["text"]) if ac_idx + 2 < len(row) else []
        r3 = parse_resources(row[ac_idx + 3]["text"]) if ac_idx + 3 < len(row) else []
        r4 = parse_resources(row[ac_idx + 4]["text"]) if ac_idx + 4 < len(row) else []
        
        # We only keep resources from 2/4, 3/4, and 4/4 as per the portfolio's logic
        resources = list(dict.fromkeys(r2 + r3 + r4))
        
        # Calculate level based on highest populated column
        level = 1
        if r4: level = 4
        elif r3: level = 3
        elif r2: level = 2
        elif r1: level = 1
        
        proof = row[ac_idx + 5]["link"] if ac_idx + 5 < len(row) else ""
        analysis = row[ac_idx + 6]["link"] if ac_idx + 6 < len(row) else ""
        
        is_strong = False
        if ac_idx + 7 < len(row):
            strong_val = row[ac_idx + 7]["text"].strip().lower()
            is_strong = (strong_val == "oui")
        
        if is_strong:
            strong_codes.append(code)
        
        # Parent competence matching
        competence = "RT1"
        if code.upper().startswith("AC24"):
            competence = "ROM1"
        elif code.upper().startswith("AC25"):
            competence = "ROM2"
        else:
            num_part = re.search(r"\d+", code)
            if num_part:
                num_str = num_part.group()
                if num_str.startswith("21"): competence = "RT1"
                elif num_str.startswith("22"): competence = "RT2"
                elif num_str.startswith("23"): competence = "RT3"
        
        new_ac_items.append({
            "code": code,
            "title": title,
            "competence": competence,
            "description": competence_meta.get(competence, ""),
            "levels": [level],
            "proof": proof,
            "analysis": analysis,
            "resources": resources
        })

print(f"Successfully parsed {len(new_ac_items)} AC items and {len(strong_codes)} strong competence codes.")

if not new_ac_items:
    print("Error: No AC items parsed. Mute update skipped.")
    exit(1)

# 3. Update index.html
html_path = "index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html_data = f.read()

# Build index.html replacement strings
js_ac_fallback = "const acFallbackItems = [\n"
for i, item in enumerate(new_ac_items):
    comma = "," if i < len(new_ac_items) - 1 else ""
    escaped_title = item['title'].replace("'", "\\'")
    escaped_desc = item['description'].replace("'", "\\'")
    js_ac_fallback += f"            {{ code: '{item['code']}', title: '{escaped_title}', competence: '{item['competence']}', description: '{escaped_desc}', levels: {item['levels']}, proof: '{item['proof']}', analysis: '{item['analysis']}', resources: {item['resources']} }}{comma}\n"
js_ac_fallback += "        ];"

js_strong = "const fallbackStrongAcCodes = new Set([\n"
for i, code in enumerate(strong_codes):
    comma = "," if i < len(strong_codes) - 1 else ""
    js_strong += f"            '{code}'{comma}\n"
js_strong += "        ]);"

# Replace fallback array
start_idx = html_data.find("const acFallbackItems = [")
if start_idx == -1:
    print("Error: Could not find const acFallbackItems in index.html")
    exit(1)
end_idx = html_data.find("];", start_idx)
if end_idx == -1:
    print("Error: Could not find matching end of acFallbackItems in index.html")
    exit(1)
end_idx += 2

new_html_data = html_data[:start_idx] + js_ac_fallback + html_data[end_idx:]

# Replace strong competence codes
start_strong = new_html_data.find("const fallbackStrongAcCodes = new Set([")
if start_strong == -1:
    print("Error: Could not find const fallbackStrongAcCodes in index.html")
    exit(1)
end_strong = new_html_data.find("]);", start_strong)
if end_strong == -1:
    print("Error: Could not find matching end of fallbackStrongAcCodes in index.html")
    exit(1)
end_strong += 3

new_html_data = new_html_data[:start_strong] + js_strong + new_html_data[end_strong:]

# Save changes to index.html
with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_html_data)

print("Successfully updated index.html fallback data!")
