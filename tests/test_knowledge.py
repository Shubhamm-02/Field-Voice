from backend.app.services.domain import load_domain_catalog
from backend.app.services.knowledge import KnowledgeBase, load_markdown_knowledge_chunks, FIELD_WORK_KB_PATH


def test_markdown_kb_is_chunked_for_rag_search():
    chunks = load_markdown_knowledge_chunks(FIELD_WORK_KB_PATH)

    assert len(chunks) >= 10
    assert any("monsoon" in chunk.text.lower() for chunk in chunks)
    assert any("DG-125KVA-01" in chunk.text for chunk in chunks)


def test_rag_answers_india_specific_monsoon_query():
    kb = KnowledgeBase(load_domain_catalog())

    response = kb.answer("What should I check during monsoon inspection of an LT panel?")

    assert "Monsoon Field Work Notes" in response.answer
    assert "water ingress" in response.answer.lower()
    assert "field-kb:" in response.sources[0]

