import glob, zipfile, os, shutil, re

filepath = glob.glob('Documents/Analyses réflexives/RT2/Analyse - AC22.05*')[0]
temp_dir = 'temp_docx_ac2205'
os.makedirs(temp_dir, exist_ok=True)

with zipfile.ZipFile(filepath, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
with open(doc_xml_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Replace "3/4 (ou 4/4 selon l'évaluation finale)" with "4/4"
# The text in the XML might be: 3/4 (ou 4/4 selon l'&#233;valuation finale) or similar
# Let's just do a greedy replace from "3/4" to "finale)" if it contains "ou 4/4".
pattern = re.compile(r'3/4.*?finale\)', re.DOTALL)
new_xml, count = pattern.subn('4/4', xml_content)
print(f'Replaced {count} times using regex')

if count == 0:
    print('Trying exact replace without regex')
    new_xml = xml_content.replace("3/4 (ou 4/4 selon l'évaluation finale)", '4/4')
    if new_xml != xml_content:
        count = 1

with open(doc_xml_path, 'w', encoding='utf-8') as f:
    f.write(new_xml)

new_filepath = filepath + '.new'
with zipfile.ZipFile(new_filepath, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, temp_dir)
            zip_ref.write(file_path, arcname)

if count > 0:
    shutil.move(new_filepath, filepath)
    print('Patched', filepath)
else:
    print('Failed to replace.')
    os.remove(new_filepath)

shutil.rmtree(temp_dir)
