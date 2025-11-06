from app.config import CHUNK_SIZE, CHUNK_OVERLAP

def chunk_text(text: str) -> list:
    """Split text into overlapping chunks"""
    
    # Split by sentences
    sentences = text.replace(".", ".\n").replace("!", "!\n").replace("?", "?\n").split("\n")
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > CHUNK_SIZE:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks
