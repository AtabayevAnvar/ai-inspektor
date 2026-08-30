"""
.doc fayldan YHQ bandlarini ajratib olish va qoidalar.txt faylga yozish
"""
import re
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False
    
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip = True
    
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = False
        if tag == 'div':
            self.result.append('\n')
        if tag == 'br':
            self.result.append('\n')
    
    def handle_data(self, data):
        if not self.skip:
            self.result.append(data)
    
    def get_text(self):
        return ''.join(self.result)


def extract_text_from_doc(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    extractor = HTMLTextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


def main():
    text = extract_text_from_doc(r'd:\Avto AI\172 12.04.2022.doc')
    
    # Remove excessive blank lines
    lines = text.split('\n')
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        stripped = line.strip()
        if stripped == '':
            if not prev_empty:
                cleaned_lines.append('')
            prev_empty = True
        else:
            cleaned_lines.append(stripped)
            prev_empty = False
    
    text = '\n'.join(cleaned_lines)
    
    with open(r'd:\Avto AI\qoidalar.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"Tayyor! Matn uzunligi: {len(text)} belgi")
    print(f"Fayl saqlandi: d:\\Avto AI\\qoidalar.txt")
    
    # Show first 2000 chars
    print("\n--- Dastlabki 2000 ta belgi ---")
    print(text[:2000])

if __name__ == '__main__':
    main()
