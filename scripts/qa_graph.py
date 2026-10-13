"""Grafo de pregunta-respuesta: recuperar, generar con un LLM y resolver las citas."""

import os
import re
from typing import TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langgraph.graph import END, START, StateGraph
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_MODEL = "ollama:qwen2.5:3b"

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Answer the question using only the numbered context passages. "
     "Cite the passages you use as [n]. If the answer is not in the context, "
     "say exactly: I don't know. Be brief."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])


class TfidfRetriever(BaseRetriever):
    """El mismo TF-IDF de rag_eval.py, expuesto como retriever de LangChain."""

    chunks: list[dict]
    k: int = 5
    vectorizer: TfidfVectorizer | None = None
    matrix: object = None

    def model_post_init(self, __context) -> None:
        self.vectorizer = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=1)
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in self.chunks])

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun):
        sims = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        return [Document(page_content=self.chunks[i]["text"],
                         metadata={k: self.chunks[i][k] for k in ("doc_id", "page", "method")})
                for i in sims.argsort()[::-1][:self.k]]


class QAState(TypedDict, total=False):
    question: str
    docs: list[Document]
    answer: str
    citations: list[str]


def build_qa_graph(retriever: BaseRetriever, model: str | None = None):
    llm = init_chat_model(model or os.environ.get("RAG_MODEL", DEFAULT_MODEL), temperature=0)

    def retrieve(state: QAState) -> QAState:
        return {"docs": retriever.invoke(state["question"])}

    def generate(state: QAState) -> QAState:
        context = "\n\n".join(f"[{i}] {d.page_content}" for i, d in enumerate(state["docs"], 1))
        reply = llm.invoke(PROMPT.format_messages(context=context, question=state["question"]))
        return {"answer": reply.content.strip()}

    def cite(state: QAState) -> QAState:
        # solo cuentan las citas que apuntan a un pasaje que de verdad se le pasó al modelo
        docs = state["docs"]
        cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", state["answer"]) if 1 <= int(n) <= len(docs)})
        return {"citations": [f"{docs[n - 1].metadata['doc_id']}:p{docs[n - 1].metadata['page']}"
                              f"[{docs[n - 1].metadata['method']}]" for n in cited]}

    graph = StateGraph(QAState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("cite", cite)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "cite")
    graph.add_edge("cite", END)
    return graph.compile()
