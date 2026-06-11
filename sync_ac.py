import urllib.request
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs

# Fetch spreadsheet HTML function
def fetch_and_parse_sheet(gid):
    url = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vT1qQLyw9iZeU_fEaTO1s6_1mJ_vJhzr3po4ezae3q7Hz88ZNdmQqNSIkRAhB9Nx5HbuZJ0rirK-P2c/pubhtml/sheet?headers=false&gid={gid}&t={int(time.time())}"
    print(f"Fetching Google Sheet GID {gid} from: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'AntigravitySync/1.0'})
    try:
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching Google Sheet GID {gid}: {e}")
        return [], []

    # Detect strikethrough classes from HTML stylesheets
    strikethrough_classes = set()
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html_content, re.DOTALL)
    for block in style_blocks:
        rules = re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{([^}]+)\}', block)
        for cls, rule_content in rules:
            if 'text-decoration' in rule_content and 'line-through' in rule_content:
                strikethrough_classes.add(cls)

    # Parse HTML structure
    class WaffleHTMLParser(HTMLParser):
        def __init__(self, strikethrough_classes):
            super().__init__()
            self.strikethrough_classes = strikethrough_classes
            self.rows = []
            self.current_row = []
            self.current_cell = {"text": "", "link": "", "is_strikethrough": False}
            self.in_cell = False
            self.in_link = False
            self.strikethrough_stack = []

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            classes = attrs_dict.get('class', '').split()
            is_strike_class = any(c in self.strikethrough_classes for c in classes)
            is_strike_tag = tag in ('s', 'strike', 'del')
            
            if is_strike_class or is_strike_tag:
                self.strikethrough_stack.append(tag)

            if tag == 'tr':
                self.current_row = []
            elif tag == 'td':
                self.in_cell = True
                self.current_cell = {"text": "", "link": "", "is_strikethrough": is_strike_class}
            elif tag == 'a' and self.in_cell:
                self.in_link = True
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
                if not self.strikethrough_stack and not self.current_cell.get('is_strikethrough'):
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
            
            if self.strikethrough_stack and self.strikethrough_stack[-1] == tag:
                self.strikethrough_stack.pop()

    parser = WaffleHTMLParser(strikethrough_classes)
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

    def get_competence_from_code(code):
        if len(code) >= 4:
            char = code[3]
            if char == '1': return 'RT1'
            if char == '2': return 'RT2'
            if char == '3': return 'RT3'
            if char == '4': return 'ROM1'
            if char == '5': return 'ROM2'
        return 'RT1'

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
            
            # Resources
            r1 = parse_resources(row[ac_idx + 1]["text"]) if ac_idx + 1 < len(row) else []
            r2 = parse_resources(row[ac_idx + 2]["text"]) if ac_idx + 2 < len(row) else []
            r3 = parse_resources(row[ac_idx + 3]["text"]) if ac_idx + 3 < len(row) else []
            r4 = parse_resources(row[ac_idx + 4]["text"]) if ac_idx + 4 < len(row) else []
            
            # Keep resources from validated levels (2/4 to 4/4) as per the portfolio's logic
            resources = list(dict.fromkeys(r2 + r3 + r4))
            
            # Calculate level based on weighted average of resources (SAÉ has weight 1.5, regular resources have weight 1.0)
            # Level 1/4 (r1) is excluded from the average calculation as it is just for sensitization
            def get_resource_weight(r_name):
                r_name_upper = r_name.strip().upper()
                if r_name_upper.startswith("SAÉ") or r_name_upper.startswith("SAE"):
                    return 1.5
                return 1.0

            total_resources = len(r2) + len(r3) + len(r4)
            if total_resources > 0:
                weighted_sum = (
                    sum(2 * get_resource_weight(r) for r in r2) +
                    sum(3 * get_resource_weight(r) for r in r3) +
                    sum(4 * get_resource_weight(r) for r in r4)
                )
                total_weight = (
                    sum(get_resource_weight(r) for r in r2) +
                    sum(get_resource_weight(r) for r in r3) +
                    sum(get_resource_weight(r) for r in r4)
                )
                level = int((weighted_sum / total_weight) + 0.5)
                level = max(1, min(4, level))
            else:
                level = 1
            
            proof = row[ac_idx + 5]["link"] if ac_idx + 5 < len(row) else ""
            analysis = row[ac_idx + 6]["link"] if ac_idx + 6 < len(row) else ""
            
            is_strong = False
            if ac_idx + 7 < len(row):
                strong_val = row[ac_idx + 7]["text"].strip().lower()
                is_strong = (strong_val == "oui")
            
            if is_strong:
                strong_codes.append(code)
            
            competence = get_competence_from_code(code)
            
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

    print(f"Successfully parsed {len(new_ac_items)} AC items and {len(strong_codes)} strong competence codes for GID {gid}.")
    return new_ac_items, strong_codes

# Run fetch and parse for both years
ac_items_rt2, strong_codes_rt2 = fetch_and_parse_sheet("808860009")
ac_items_rt3, strong_codes_rt3 = fetch_and_parse_sheet("1897392063")

html_path = "index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html_data = f.read()

# Helper to construct fallback array JS string
def make_js_fallback(var_name, items):
    js_str = f"const {var_name} = [\n"
    for i, item in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        escaped_title = item['title'].replace("'", "\\'")
        escaped_desc = item['description'].replace("'", "\\'")
        js_str += f"            {{ code: '{item['code']}', title: '{escaped_title}', competence: '{item['competence']}', description: '{escaped_desc}', levels: {item['levels']}, proof: '{item['proof']}', analysis: '{item['analysis']}', resources: {item['resources']} }}{comma}\n"
    js_str += "        ];"
    return js_str

# Helper to construct strong set JS string
def make_js_strong(var_name, codes):
    js_str = f"const {var_name} = new Set([\n"
    for i, code in enumerate(codes):
        comma = "," if i < len(codes) - 1 else ""
        js_str += f"            '{code}'{comma}\n"
    js_str += "        ]);"
    return js_str

# Replace in html_data
def replace_js_variable(html_text, start_pattern, end_pattern, new_value):
    start_idx = html_text.find(start_pattern)
    if start_idx == -1:
        print(f"Error: Could not find '{start_pattern}' in index.html")
        exit(1)
    end_idx = html_text.find(end_pattern, start_idx)
    if end_idx == -1:
        print(f"Error: Could not find matching end '{end_pattern}' in index.html")
        exit(1)
    end_idx += len(end_pattern)
    return html_text[:start_idx] + new_value + html_text[end_idx:]

# Replacements
html_data = replace_js_variable(html_data, "const acFallbackItemsRT2 = [", "];", make_js_fallback("acFallbackItemsRT2", ac_items_rt2))
html_data = replace_js_variable(html_data, "const acFallbackItemsRT3 = [", "];", make_js_fallback("acFallbackItemsRT3", ac_items_rt3))
html_data = replace_js_variable(html_data, "const fallbackStrongAcCodesRT2 = new Set([", "]);", make_js_strong("fallbackStrongAcCodesRT2", strong_codes_rt2))
html_data = replace_js_variable(html_data, "const fallbackStrongAcCodesRT3 = new Set([", "]);", make_js_strong("fallbackStrongAcCodesRT3", strong_codes_rt3))

# Save changes to index.html
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_data)

print("Successfully updated index.html fallback data for both RT2 and RT3!")
