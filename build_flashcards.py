#!/usr/bin/env python3
"""Parse all cached jsonp files and write the clean vocabulary to Excel."""

import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from openpyxl import Workbook

PUA_MAP = {
    '\ue001': 't',
    '\ue002': 'fi',
    '\ue003': 'tt',
    '\ue004': 'ff',
    '\ue005': 'fl',
    '\ue006': 'tti',
    '\ue007': 'tf',
    '\ue008': 'ffi',
    '\ue009': 'fh',
    '\ue00a': 'fb',
    '\ue00b': 'ffl',
}

def clean_text_base(text: str) -> str:
    # Resolve contextual ligature for \ue000 (often 'ft' in German, 't' in Latin titles)
    text = text.replace('la\ue000einisches', 'lateinisches')
    text = text.replace('Wor\ue000', 'Wort')
    text = text.replace('deu\ue000sche', 'deutsche')
    text = text.replace('Bedeu\ue000ung', 'Bedeutung')
    text = text.replace('\ue000', 'ft')
    for k, v in PUA_MAP.items():
        text = text.replace(k, v)
    return text

def fix_word(word: str) -> str:
    # Isolate surrounding punctuation
    m = re.match(r'^([^\w]*)(.*?)([^\w]*)$', word)
    if m:
        prefix, core, suffix = m.groups()
    else:
        core = word
        prefix, suffix = '', ''
        
    if not core:
        return word
        
    is_upper = core[0].isupper() if core else False
    core_lower = core.lower()
    
    # 1. Ends with ts -> tis (e.g. morts -> mortis, hosts -> hostis)
    if core_lower.endswith('ts'):
        # Keep digits/numbers intact
        if not core_lower[:-2].isdigit():
            core_lower = core_lower[:-2] + 'tis'
        
    # 2. tats -> tatis (e.g. civitats -> civitatis)
    core_lower = core_lower.replace('tats', 'tatis')
    
    # 3. Dedicated exact mapping corrections of PDF 'ti' ligature issues
    corrections = {
        'negotum': 'negotium',
        'negotis': 'negotiis',
        'otum': 'otium',
        'otis': 'otiis',
        'aestmare': 'aestimare',
        'aestmo': 'aestimo',
        'aestmabat': 'aestimabat',
        'aestmave': 'aestimavi',
        'aestmata': 'aestimata',
        'adulescentum': 'adulescentium',
        'vestum': 'vestium',
        'montum': 'montium',
        'noctum': 'noctium',
        'gentum': 'gentium',
        'parentum': 'parentium',
        'oratonis': 'orationis',
        'orato': 'oratio',
        'oratores': 'orationes',
        'actonis': 'actionis',
        'acto': 'actio',
        'natonis': 'nationis',
        'nato': 'natio',
        'condito': 'conditio',
        'conditonis': 'conditionis',
        'lots': 'lotis',
        'dots': 'dotis',
        'amicita': 'amicitia',
        'amicitae': 'amicitiae',
        'grata': 'gratia',
        'gratas': 'gratia',
        'inimicita': 'inimicitia',
        'inimicitae': 'inimicitiae',
        'spatum': 'spatium',
        'initum': 'initium',
        'vitum': 'vitium',
        'viti': 'vitii',
        'appettum': 'appetitum',
        'nuntare': 'nuntiare',
        'nunto': 'nuntio',
        'nuntatum': 'nuntiatum',
        'renuntare': 'renuntiare',
        'pronuntare': 'pronuntiare',
        'denuntare': 'denuntiare',
        'solictudo': 'sollicitudo',
        'solictudinis': 'sollicitudinis',
        'consentre': 'consentire',
        'destnare': 'destinare',
        'destnatum': 'destinatum',
        'obstnare': 'obstinare',
    }
    
    # Handle German 'st_mmen' ligature problems
    if 'stmmen' in core_lower:
        core_lower = core_lower.replace('stmmen', 'stimmen')
    if 'bestmmen' in core_lower:
        core_lower = core_lower.replace('bestmmen', 'bestimmen')
    if 'stmm' in core_lower:
        core_lower = core_lower.replace('stmm', 'stimm')
        
    # Exact word replacements
    if core_lower in corrections:
        core_lower = corrections[core_lower]
    else:
        # Check subword matching
        for k, v in corrections.items():
            if len(k) > 4 and k in core_lower:
                core_lower = core_lower.replace(k, v)
                
    # Restore capital letter casing
    if is_upper and core_lower:
        core_lower = core_lower[0].upper() + core_lower[1:]
        
    return prefix + core_lower + suffix

def fix_sentence(text: str) -> str:
    # Corrects spacing and missing characters token-by-token
    tokens = text.split(' ')
    repaired_tokens = [fix_word(t) for t in tokens]
    return re.sub(r'\s+', ' ', ' '.join(repaired_tokens)).strip()

def walk(tag) -> list[str]:
    parts = []
    for child in tag.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.name == 'span' and 'w' in child.get('class', []):
            parts.append('|||')
        else:
            parts.extend(walk(child))
    return parts

def parse_and_build(cache_dir: Path, output_xlsx: Path) -> int:
    all_entries = []
    current_lesson = '1' # default start

    for num in range(1, 68):
        path = cache_dir / f'page_{num}.jsonp'
        if not path.exists():
            print(f'Warning: Cached file {path} not found!')
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
            
        m = re.search(r'window\.page\d+_callback\((.*)\);?\s*$', data, re.DOTALL)
        if not m:
            continue
            
        html_content = json.loads(m.group(1))[0]
        soup = BeautifulSoup(html_content, 'html.parser')
        
        elements = []
        for s in soup.find_all('span', class_='a'):
            style = s.get('style', '')
            left_m = re.search(r'left:(\d+)px', style)
            top_m = re.search(r'top:(\d+)px', style)
            left = int(left_m.group(1)) if left_m else 0
            top = int(top_m.group(1)) if top_m else 0
            text = ''.join(walk(s))
            elements.append({'left': left, 'top': top, 'text': text})
            
        # Group elements vertically by matching the 'top' styles within 15px
        elements.sort(key=lambda x: x['top'])
        rows = []
        curr_row = []
        curr_top = -100
        for el in elements:
            if el['top'] - curr_top <= 15:
                curr_row.append(el)
            else:
                if curr_row:
                    rows.append(curr_row)
                curr_row = [el]
                curr_top = el['top']
        if curr_row:
            rows.append(curr_row)
            
        # Extract row columns and lessons
        for r in rows:
            r.sort(key=lambda x: x['left'])
            
            lesson_val = ''
            vocab_text = ''
            if len(r) >= 2 and r[0]['left'] < 650:
                lesson_val = r[0]['text'].strip()
                if '|||' in lesson_val:
                    lesson_val = ''
                    vocab_text = ' '.join([el['text'] for el in r])
                else:
                    vocab_text = r[-1]['text']
            else:
                text_combined = ' '.join([el['text'] for el in r])
                if '|||' in text_combined:
                    vocab_text = text_combined
                    
            if vocab_text and '|||' in vocab_text:
                cleaned_vocab = clean_text_base(vocab_text)
                parts = cleaned_vocab.split('|||', 1)
                latin = parts[0].strip()
                german = parts[1].strip()
                
                # Skip header titles
                if 'lateinisches wort' in latin.lower() and 'deutsche bedeutung' in german.lower():
                    continue
                # Skip empty latin rows
                if not latin:
                    continue
                    
                if lesson_val:
                    cleaned_lesson = clean_text_base(lesson_val).strip()
                    if cleaned_lesson.isdigit() or re.match(r'^\d+[a-zA-Z]?$', cleaned_lesson):
                        current_lesson = cleaned_lesson
                    elif 'lektion' in cleaned_lesson.lower():
                        lek_m = re.search(r'\d+[a-zA-Z]?', cleaned_lesson)
                        if lek_m:
                            current_lesson = lek_m.group(0)
                
                # Apply word corrections
                repaired_latin = fix_sentence(latin)
                repaired_german = fix_sentence(german)
                
                all_entries.append((current_lesson, repaired_latin, repaired_german))

    # Save to Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'flashcards'
    
    # Exact user-requested headers
    ws.append(['lektion', 'latein words', 'german explainations'])
    for lesson, latin, german in all_entries:
        ws.append([lesson, latin, german])
        
    for col in ('A', 'B', 'C'):
        ws.column_dimensions[col].width = 40
        
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_xlsx))
    return len(all_entries)

def main() -> None:
    cache_dir = Path('cache')
    output_xlsx = Path('out/adeamus_flashcards.xlsx')
    count = parse_and_build(cache_dir, output_xlsx)
    print(f'Successfully built {count} vocabulary items in {output_xlsx}!')

if __name__ == '__main__':
    main()
