"""RAG query pipeline: embed → retrieve → enrich → generate.

Query flow
----------
1. Embed the natural-language question with the local embedding model.
2. Run an approximate nearest-neighbour search in Milvus to retrieve the
   most relevant AUTOSAR component text chunks.
3. Fetch graph context from Neo4j for the retrieved ARXML refs (port names,
   connected interfaces) to enrich the prompt beyond what the vector index alone
   can provide.
4. Assemble a context block and inject it into a structured prompt template.
5. Call the local LLM (Ollama) and return the grounded answer with source citations.

No external AI API is called at any point in this pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from rag_engine.embeddings import EmbeddingModel
from rag_engine.llm import OllamaClient
from rag_engine.milvus_client import MilvusComponentStore, SearchResult
from rag_engine.neo4j_client import Neo4jComponentGraph

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
You are an AUTOSAR expert assistant embedded in the polyarchos platform.
Answer the user's question about AUTOSAR software components, ports, and interfaces
using ONLY the context provided below.

Rules:
- If the context does not contain enough information, say so explicitly.
- Do not invent ARXML paths, component names, or interface names.
- Keep your answer concise and technically precise.
- Reference source component names when citing evidence.

--- CONTEXT START ---
{context}
--- CONTEXT END ---

Question: {question}

Answer:"""


@dataclass
class QueryResult:
    """The output of a RAG pipeline query."""

    answer: str
    sources: list[SearchResult] = field(default_factory=list)
    model_id: str = ""


class RagPipeline:
    """End-to-end RAG query pipeline."""

    def __init__(
        self,
        embedder: EmbeddingModel,
        milvus: MilvusComponentStore,
        neo4j: Neo4jComponentGraph,
        llm: OllamaClient,
        context_chunks: int = 5,
    ) -> None:
        self._embedder = embedder
        self._milvus = milvus
        self._neo4j = neo4j
        self._llm = llm
        self._default_k = context_chunks

    async def query(self, question: str, top_k: int | None = None) -> QueryResult:
        """Answer a natural-language question about the AUTOSAR component graph.

        Args:
            question: The user's question, e.g. "Which SWCs provide the FuelInjection interface?"
            top_k: Number of Milvus chunks to retrieve. Defaults to ``context_chunks``
                from config.

        Returns:
            :class:`QueryResult` with the generated answer, source chunks, and model ID.
        """
        k = top_k if top_k is not None else self._default_k

        # 1. Embed question
        query_vec = self._embedder.embed_one(question)

        # 2. Vector search
        hits = self._milvus.search(query_vec, top_k=k)
        logger.info(
            "Milvus search complete",
            extra={"question": question[:80], "hits": len(hits)},
        )

        # 3. Graph enrichment — fetch related port/interface context
        arxml_refs = [h.arxml_ref for h in hits]
        graph_context = await self._neo4j.get_component_context(arxml_refs)

        # 4. Build context block
        vector_context = "\n\n".join(
            f"[Source: {h.document_name} | {h.component_name} | score={h.score:.3f}]\n"
            f"{h.text_chunk}"
            for h in hits
        )
        context = vector_context
        if graph_context:
            context += f"\n\n[Graph context — connected ports and interfaces]\n{graph_context}"

        # 5. Generate answer (local LLM — no external API call)
        prompt = _PROMPT_TEMPLATE.format(context=context, question=question)
        answer = self._llm.generate(prompt)

        return QueryResult(answer=answer, sources=hits, model_id=self._llm.model_id)
