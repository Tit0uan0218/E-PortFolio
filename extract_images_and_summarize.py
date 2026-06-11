import os
import zipfile
import re
import json
import glob
import xml.etree.ElementTree as ET

out_dir = os.path.join('assets', 'images', 'ac_preuves')
os.makedirs(out_dir, exist_ok=True)

files = glob.glob('Documents/Preuves/RT2/*') + glob.glob('Documents/Analyses/RT2/*')

summaries = {}

def ns(tag):
    return tag.replace('w:', '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}') \
              .replace('a:', '{http://schemas.openxmlformats.org/drawingml/2006/main}') \
              .replace('pic:', '{http://schemas.openxmlformats.org/drawingml/2006/picture}') \
              .replace('r:', '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}') \
              .replace('wp:', '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}')

for filepath in files:
    if not os.path.isfile(filepath): continue
    filename = os.path.basename(filepath)
    match = re.search(r'AC\d{2}\.\d{2}(?:ROM)?', filename)
    if not match: continue
    ac_code = match.group(0)
    
    try:
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            # 1. Parse rels to map rId to image path
            rels_data = zip_ref.read('word/_rels/document.xml.rels')
            rels_root = ET.fromstring(rels_data)
            rels = {}
            for rel in rels_root:
                rId = rel.get('Id')
                target = rel.get('Target') # e.g. media/image1.png
                if target.startswith('media/'):
                    rels[rId] = target

            # 2. Parse document.xml
            doc_data = zip_ref.read('word/document.xml')
            doc_root = ET.fromstring(doc_data)
            
            elements = [] # list of dicts: {'type': 'text'|'image', 'val': string|path}
            
            body = doc_root.find(ns('w:body'))
            for child in body:
                if child.tag == ns('w:p'):
                    # Check for text
                    texts = child.findall(ns('.//w:t'))
                    para_text = ''.join([t.text for t in texts if t.text])
                    
                    # Check for images in this paragraph
                    drawings = child.findall(ns('.//w:drawing'))
                    
                    if para_text.strip():
                        elements.append({'type': 'text', 'val': para_text.strip()})
                        
                    for drawing in drawings:
                        blip = drawing.find(ns('.//a:blip'))
                        if blip is not None:
                            rId = blip.get(ns('r:embed'))
                            if rId in rels:
                                target_path = 'word/' + rels[rId]
                                ext = os.path.splitext(target_path)[1]
                                new_filename = f"{ac_code}_{len(elements)}{ext}"
                                new_filepath = os.path.join(out_dir, new_filename)
                                
                                # Extract image
                                with open(new_filepath, 'wb') as f:
                                    f.write(zip_ref.read(target_path))
                                
                                elements.append({'type': 'image', 'val': new_filepath.replace('\\', '/')})

            # 3. Build summary
            contexte, savoir_faire, taches = '', '', ''
            current_section = None
            
            for el in elements:
                if el['type'] == 'text':
                    line_clean = el['val']
                    if 'Contexte' in line_clean and len(line_clean) < 30:
                        current_section = 'contexte'
                    elif 'Savoir-faire' in line_clean and len(line_clean) < 40:
                        current_section = 'savoir_faire'
                    elif ('Tâche' in line_clean or 'Tache' in line_clean or 'résultats' in line_clean) and len(line_clean) < 50:
                        current_section = 'taches'
                    elif ('Savoir mis' in line_clean or 'Savoir-être' in line_clean) and len(line_clean) < 40:
                        current_section = None
                    else:
                        if current_section == 'contexte':
                            contexte += line_clean + ' '
                        elif current_section == 'savoir_faire':
                            savoir_faire += '• ' + line_clean + '<br>'
                        elif current_section == 'taches':
                            taches += f"<p class='mb-2'>{line_clean}</p>"
                elif el['type'] == 'image':
                    if current_section == 'taches':
                        img_path = el['val']
                        taches += f'''
                        <div class="text-center my-3">
                            <img src="{img_path}" class="img-fluid rounded shadow-sm border" style="max-height: 250px; object-fit: contain; background: #fff; cursor: zoom-in;" onclick="openLightbox('{img_path}')" title="Cliquez pour agrandir">
                        </div>
                        '''
            
            if not contexte and not savoir_faire and not taches:
                continue

            html = f'''
            <div class="ac-resume-content" style="padding: 1rem;">
                <h6 style="color: #007bff; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-crosshairs me-2"></i>Contexte & Objectif</h6>
                <p class="mb-4" style="font-size: 0.95rem;">{contexte.strip()}</p>
                
                <h6 style="color: #007bff; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-tools me-2"></i>Savoir-Faire Mobilisés</h6>
                <p class="mb-4" style="font-size: 0.95rem; line-height: 1.6;">{savoir_faire.strip()}</p>
                
                <h6 style="color: #007bff; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-check-circle me-2"></i>Réalisation & Résultats</h6>
                <div class="mb-4" style="font-size: 0.95rem;">{taches.strip()}</div>
                
                <div class="alert alert-info py-2 mt-4 d-flex align-items-center" style="border-radius: 10px; font-size: 0.85rem; background-color: rgba(0, 123, 255, 0.1); border: 1px solid rgba(0, 123, 255, 0.2);">
                    <i class="fas fa-columns me-2 fa-lg text-primary"></i> 
                    <span><strong>Astuce :</strong> Clique sur "Preuve" ou "Analyse" en haut pour afficher le document complet à côté de ce résumé (affichage fractionné).</span>
                </div>
            </div>
            '''
            # If multiple proofs for same AC exist, append them (or we can just overwrite if it's an analysis)
            if 'Analyse' not in filename or ac_code not in summaries:
                summaries[ac_code] = html

    except Exception as e:
        print(f"Error on {filename}: {e}")

with open('acSummaries.js', 'w', encoding='utf-8') as f:
    f.write('const acSummariesContent = ' + json.dumps(summaries, indent=2) + ';\n')
    f.write('window.acSummariesContent = acSummariesContent;\n')

print(f'Extracted images inline and generated summaries for {len(summaries)} ACs!')
