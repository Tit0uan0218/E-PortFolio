import os
import zipfile
import re
import json
import glob
import xml.etree.ElementTree as ET

out_dir = os.path.join('assets', 'images', 'ac_preuves')
os.makedirs(out_dir, exist_ok=True)

# Include both Preuves and Analyses
files = glob.glob('Documents/Preuves/RT2/*') + glob.glob('Documents/Analyses réflexives/RT2/*')

summaries_data = {}

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
    
    if ac_code not in summaries_data:
        summaries_data[ac_code] = {'preuve': '', 'analyse': ''}

    is_analyse = 'Analyse' in filename or 'Analyses' in filepath

    try:
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            # 1. Parse rels
            rels = {}
            try:
                rels_data = zip_ref.read('word/_rels/document.xml.rels')
                rels_root = ET.fromstring(rels_data)
                for rel in rels_root:
                    rId = rel.get('Id')
                    target = rel.get('Target')
                    if target.startswith('media/'):
                        rels[rId] = target
            except Exception:
                pass # some docs might not have rels

            # 2. Parse document.xml
            doc_data = zip_ref.read('word/document.xml')
            doc_root = ET.fromstring(doc_data)
            elements = []
            
            body = doc_root.find(ns('w:body'))
            for child in body:
                if child.tag == ns('w:p'):
                    texts = child.findall(ns('.//w:t'))
                    para_text = ''.join([t.text for t in texts if t.text])
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
                                new_filename = f"{ac_code}_{is_analyse}_{len(elements)}{ext}"
                                new_filepath = os.path.join(out_dir, new_filename)
                                with open(new_filepath, 'wb') as f:
                                    f.write(zip_ref.read(target_path))
                                elements.append({'type': 'image', 'val': new_filepath.replace('\\', '/')})

            # 3. Build summary
            if is_analyse:
                analyse_text = ''
                capture_analyse = False
                for el in elements:
                    if el['type'] == 'text':
                        import re
                        line_clean = el['val']
                        line_clean = re.sub(r'\[.*?\]', '', line_clean).strip()
                        # Trigger on "Analyse R..." or "Auto-évaluation..."
                        lc = line_clean.lower()
                        is_trigger = 'analyse r' in lc or 'auto-évaluation' in lc or 'auto évaluation' in lc
                        if is_trigger and not capture_analyse:
                            capture_analyse = True
                        elif capture_analyse:
                            if line_clean: analyse_text += f"<p class='mb-2'>{line_clean}</p>"
                
                if analyse_text:
                    html = f'''
                    <hr class="my-4" style="border-color: #e2e8f0;">
                    <h6 style="color: #6366f1; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-brain me-2"></i>Analyse Réflexive</h6>
                    <div class="mb-2" style="font-size: 0.95rem; font-style: italic; color: #475569; padding-left: 1rem; border-left: 3px solid #6366f1;">{analyse_text}</div>
                    '''
                    summaries_data[ac_code]['analyse'] = html

            else:
                contexte, savoir_faire, taches = '', '', ''
                current_section = None
                
                for el in elements:
                    if el['type'] == 'text':
                        import re
                        line_clean = el['val']
                        line_clean = re.sub(r'\[.*?\]', '', line_clean).strip()
                        if not line_clean:
                            continue
                        
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
                
                if contexte or savoir_faire or taches:
                    html = f'''
                    <div class="ac-resume-content" style="padding: 1rem;">
                        <h6 style="color: #007bff; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-crosshairs me-2"></i>Contexte & Objectif</h6>
                        <p class="mb-4" style="font-size: 0.95rem;">{contexte.strip()}</p>
                        
                        <h6 style="color: #007bff; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-tools me-2"></i>Savoir-Faire Mobilisés</h6>
                        <p class="mb-4" style="font-size: 0.95rem; line-height: 1.6;">{savoir_faire.strip()}</p>
                        
                        <h6 style="color: #007bff; font-weight: 700; margin-bottom: 0.5rem;"><i class="fas fa-check-circle me-2"></i>Réalisation & Résultats</h6>
                        <div class="mb-4" style="font-size: 0.95rem;">{taches.strip()}</div>
                    </div>
                    '''
                    summaries_data[ac_code]['preuve'] = html

    except Exception as e:
        print(f"Error on {filename}: {e}")

# Combine into final summaries dictionary
summaries = {}
for ac_code, data in summaries_data.items():
    combined = data['preuve']
    
    # If there's an analyse block, append it inside the ac-resume-content div if it exists
    if data['analyse']:
        if combined:
            # Find the last </div> before the banner and insert the analyse block before it
            suffix = '</div>\n                    '
            if suffix in combined:
                parts = combined.rsplit(suffix, 1)
                combined = parts[0] + data['analyse'] + suffix
            else:
                combined += f'<div class="ac-resume-content" style="padding: 1rem;">{data["analyse"]}</div>'
        else:
            combined = f'<div class="ac-resume-content" style="padding: 1rem;">{data["analyse"]}</div>'
            
    if combined:
        # Add the astuce banner at the very bottom
        combined += '''
        <div class="alert alert-info py-2 mt-4 d-flex align-items-center" style="border-radius: 10px; font-size: 0.85rem; background-color: rgba(0, 123, 255, 0.1); border: 1px solid rgba(0, 123, 255, 0.2); margin: 0 1rem;">
            <i class="fas fa-columns me-2 fa-lg text-primary"></i> 
            <span><strong>Astuce :</strong> Clique sur "Preuve" ou "Analyse" en haut pour afficher le document complet à côté de ce résumé (affichage fractionné).</span>
        </div>
        '''
        summaries[ac_code] = combined

with open('acSummaries.js', 'w', encoding='utf-8') as f:
    f.write('const acSummariesContent = ' + json.dumps(summaries, indent=2) + ';\n')
    f.write('window.acSummariesContent = acSummariesContent;\n')

print(f'Extracted images inline and generated summaries for {len(summaries)} ACs!')
