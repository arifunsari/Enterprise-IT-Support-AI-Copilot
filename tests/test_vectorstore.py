import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.rag import vectorstore


class EnsureIndexTests(unittest.TestCase):
    def test_creates_configured_index_and_returns_connection(self):
        settings = SimpleNamespace(
            pinecone_api_key="test-key",
            pinecone_index_name="industry-agentic-rag-kb-v2",
            embedding_model="text-embedding-3-small",
        )
        created_indexes = []
        connected_indexes = []
        index_handle = object()
        pinecone_client = SimpleNamespace(
            list_indexes=lambda: [],
            create_index=lambda **kwargs: created_indexes.append(kwargs),
            describe_index=lambda name: SimpleNamespace(
                status={"ready": True}
            ),
            Index=lambda name: connected_indexes.append(name) or index_handle,
        )

        with (
            patch.object(vectorstore, "settings", settings),
            patch.object(vectorstore, "Pinecone", return_value=pinecone_client),
        ):
            result = vectorstore.ensure_index()

        self.assertIs(result, index_handle)
        self.assertEqual(len(created_indexes), 1)
        self.assertEqual(created_indexes[0]["name"], "industry-agentic-rag-kb-v2")
        self.assertEqual(created_indexes[0]["dimension"], 1536)
        self.assertEqual(created_indexes[0]["metric"], "cosine")
        self.assertEqual(connected_indexes, ["industry-agentic-rag-kb-v2"])

    def test_dimension_mismatch_preserves_existing_index(self):
        settings = SimpleNamespace(
            pinecone_api_key="test-key",
            pinecone_index_name="existing-index",
            embedding_model="text-embedding-3-small",
        )
        pinecone_client = SimpleNamespace(
            list_indexes=lambda: [{"name": "existing-index"}],
            describe_index=lambda name: SimpleNamespace(dimension=768),
            delete_index=lambda **kwargs: self.fail("Existing index must not be deleted"),
        )

        with (
            patch.object(vectorstore, "settings", settings),
            patch.object(vectorstore, "Pinecone", return_value=pinecone_client),
        ):
            with self.assertRaisesRegex(RuntimeError, "existing index was not changed"):
                vectorstore.ensure_index()


if __name__ == "__main__":
    unittest.main()
