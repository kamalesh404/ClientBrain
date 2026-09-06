from app.rag import chunk_text, retrieve
from app.store import add_docs, get_docs


def test_chunk_and_retrieve():
    docs = chunk_text("Our timings are 9am-9pm daily in Arcot. We serve meals.", "timings.txt")
    add_docs("test-ws", docs)
    hits = retrieve("What are timings?", get_docs("test-ws"))
    assert hits and "9am" in hits[0]["text"]
