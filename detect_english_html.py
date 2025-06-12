import os
from bs4 import BeautifulSoup, Comment
import re
from deep_translator import GoogleTranslator

# 🔧 Path to your HTML folder
base_path = r'D:\TRR\TransportM\trrm-email-template\email'

# ✅ Check if a string contains English letters but no Thai
def contains_english(text):
    return bool(re.search(r'[a-zA-Z]', text)) and not re.search(r'[\u0E00-\u0E7F]', text)

# ✅ Skip if the entire string is a single #TOKEN#
def should_ignore(text):
    return bool(re.fullmatch(r"#\w+(_\w+)*#", text.strip()))

# ✅ Split text into segments (tokens and regular text)
def split_text_and_tokens(text):
    # Pattern to match #TOKEN# (including when wrapped in brackets) and URLs
    # This pattern now captures [#TOKEN#] as a single unit
    pattern = re.compile(r"(\[?#\w+(?:_\w+)*#\]?|https?://[^\s]+|www\.[^\s]+)")
    
    # Split the text while keeping the delimiters
    segments = pattern.split(text)
    
    result_segments = []
    for i, segment in enumerate(segments):
        if segment != '':  # Include empty segments to preserve structure
            # Check if this segment is a token/URL (should not be translated)
            if pattern.match(segment):
                result_segments.append({"text": segment, "translate": False})
            else:
                # Check if this segment is between two tokens and only contains punctuation/spaces
                if i > 0 and i < len(segments) - 1:
                    prev_is_token = i > 0 and segments[i-1] and pattern.match(segments[i-1])
                    next_is_token = i < len(segments) - 1 and segments[i+1] and pattern.match(segments[i+1])
                    if prev_is_token and next_is_token and re.match(r'^[\s,;:\-]+$', segment):
                        result_segments.append({"text": segment, "translate": False})
                        continue
                
                result_segments.append({"text": segment, "translate": True})
    
    return result_segments

# ✅ Translate to Thai using Google Translate API
def translate_to_thai(text):
    try:
        if not text.strip():  # If only whitespace, return as is
            return text
            
        # Extract trailing punctuation
        trailing_punct = ""
        clean_text = text.rstrip()
        
        # Check for trailing punctuation (including colon)
        if clean_text and clean_text[-1] in '.!?;:,':
            trailing_punct = clean_text[-1]
            clean_text = clean_text[:-1].strip()
        
        # Translate the clean text
        if clean_text:
            translated = GoogleTranslator(source='auto', target='th').translate(clean_text)
            
            # Add back the trailing punctuation
            if trailing_punct:
                translated = translated + trailing_punct
            
            # Preserve original spacing
            if text.startswith(' ') and text.endswith(' '):
                return f" {translated} "
            elif text.startswith(' '):
                return f" {translated}"
            elif text.endswith(' '):
                return f"{translated} "
            else:
                return translated
        
        return text
    except Exception as e:
        print(f"⚠️ Error translating: {text} | {e}")
        return text

# 🚀 Process each HTML file
for root, _, files in os.walk(base_path):
    for file in files:
        if file.endswith(".html"):
            file_path = os.path.join(root, file)

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            body = soup.body
            if not body:
                continue

            translated = False

            for element in body.find_all(string=True):
                if isinstance(element, Comment):
                    continue  # ❌ Skip comments

                original = str(element).strip()
                
                if not original or not contains_english(original):
                    continue

                if should_ignore(original):
                    continue  # ❌ Skip full-token-only lines

                # 🧠 Split text into segments and translate only non-token parts
                segments = split_text_and_tokens(original)
                
                # Debug print
                print(f"📝 Segments for '{original}':")
                for seg in segments:
                    print(f"   '{seg['text']}' (translate: {seg['translate']})")
                
                # Check if there's any text to translate
                has_translatable = any(seg["translate"] and seg["text"].strip() for seg in segments)
                
                if has_translatable:
                    final_parts = []
                    
                    for segment in segments:
                        if segment["translate"] and segment["text"].strip():
                            # Translate this segment while preserving spaces and punctuation
                            translated_part = translate_to_thai(segment["text"])
                            final_parts.append(translated_part)
                        else:
                            # Keep tokens/URLs/punctuation as-is
                            final_parts.append(segment["text"])
                    
                    final_text = "".join(final_parts)
                    
                    # Clean up any translation artifacts
                    final_text = re.sub(r'  +', ' ', final_text)  # Normalize multiple spaces
                    final_text = re.sub(r'\s*-\s*$', '', final_text)  # Remove trailing dash
                    final_text = final_text.strip()
                    
                    print(f"🔁 '{original}' ➜ '{final_text}'")
                    element.replace_with(final_text)
                    translated = True

            if translated:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))
                print(f"✅ Overwrote original file: {file_path}\n")
