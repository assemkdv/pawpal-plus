import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PET_CARE_KNOWLEDGE = [
    "Dogs should be walked at least 30 minutes twice daily.",
    "Cats require protein-rich diets and should be fed 2-3 times daily.",
    "Pets need annual veterinary checkups.",
    "Dental hygiene is important for both cats and dogs.",
    "Long-haired pets need grooming every 1-2 days, while short-haired pets need grooming weekly.",
    "Cats should be groomed regularly to prevent matting and hairballs.",
    "Puppies need early socialization and training.",
    "Kittens need frequent feeding and play.",
    "Signs of illness include lethargy, vomiting, or appetite loss.",
    "Exercise and mental stimulation are essential for pets.",
    "Senior pets need more frequent vet visits and softer care."
]


class PetCareRAG:
    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.vectors = self.vectorizer.fit_transform(knowledge)

    def retrieve(self, query, top_k=2):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]

        # Only keep GOOD matches
        results = [self.knowledge[i] for i in top_indices if scores[i] > 0.15]
        return results
