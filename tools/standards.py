"""Tool: Search Virginia SOLs and WIDA Can-Do descriptors.

Standards data is embedded as structured dicts so the tool works offline
without an external database. This covers the most commonly referenced
standards; the teacher can extend by dropping JSON files into a standards/
directory in a future iteration.
"""

import re

# ---------------------------------------------------------------------------
# Virginia Standards of Learning — condensed reference
# Organized by subject > grade band > standard code + description
# ---------------------------------------------------------------------------
VA_SOLS: list[dict] = [
    # --- ELA ---
    {"subject": "ELA", "grade": "K", "code": "K.1", "strand": "Communication and Multimodal Literacies",
     "text": "The student will demonstrate growth in the use of oral language. a) Listen to a variety of literary forms, including stories and poems. b) Participate in a variety of oral language activities including choral and echo speaking."},
    {"subject": "ELA", "grade": "K", "code": "K.3", "strand": "Reading",
     "text": "The student will orally identify, segment, and blend various phonemes to develop phonological and phonemic awareness."},
    {"subject": "ELA", "grade": "K", "code": "K.7", "strand": "Reading",
     "text": "The student will develop an understanding of basic phonetic principles. a) Identify and name the uppercase and lowercase letters of the alphabet. b) Match consonant and short vowel sounds to appropriate letters."},
    {"subject": "ELA", "grade": "1", "code": "1.1", "strand": "Communication and Multimodal Literacies",
     "text": "The student will continue to demonstrate growth in the use of oral language. a) Listen and respond to a variety of media, including books, audiotapes, videos, and other age-appropriate materials."},
    {"subject": "ELA", "grade": "1", "code": "1.5", "strand": "Reading",
     "text": "The student will apply knowledge of how print is organized and read. a) Read from left to right and from top to bottom. b) Match spoken words with print."},
    {"subject": "ELA", "grade": "2", "code": "2.5", "strand": "Reading",
     "text": "The student will use phonetic strategies when reading and spelling. a) Use knowledge of consonants, consonant blends, and consonant digraphs to decode and spell words."},
    {"subject": "ELA", "grade": "3", "code": "3.5", "strand": "Reading",
     "text": "The student will read and demonstrate comprehension of fictional texts, literary nonfiction, and poetry. a) Set a purpose for reading. b) Make connections between previous experiences and reading selections."},
    {"subject": "ELA", "grade": "4", "code": "4.5", "strand": "Reading",
     "text": "The student will read and demonstrate comprehension of fictional texts, literary nonfiction, and poetry. a) Explain the author's purpose. b) Describe how the choice of language, setting, characters, and information contributes to the author's purpose."},
    {"subject": "ELA", "grade": "5", "code": "5.5", "strand": "Reading",
     "text": "The student will read and demonstrate comprehension of fictional texts, narrative nonfiction, and poetry. a) Describe the relationship between text and previously read materials. b) Describe character development."},
    {"subject": "ELA", "grade": "6-8", "code": "6.5", "strand": "Reading",
     "text": "The student will read and demonstrate comprehension of a variety of fictional texts, literary nonfiction, and poetry. a) Identify the elements of narrative structure. b) Make, confirm, and revise predictions."},
    {"subject": "ELA", "grade": "6-8", "code": "7.5", "strand": "Reading",
     "text": "The student will read and demonstrate comprehension of a variety of fictional texts, narrative nonfiction, and poetry. a) Describe the elements of narrative structure. b) Compare and contrast various forms and genres of fictional text."},
    {"subject": "ELA", "grade": "6-8", "code": "8.5", "strand": "Reading",
     "text": "The student will read and demonstrate comprehension of a variety of fictional texts, narrative nonfiction, poetry, and drama. a) Explain the use of symbols and figurative language. b) Make inferences and draw conclusions."},
    {"subject": "ELA", "grade": "9-12", "code": "9.3", "strand": "Reading",
     "text": "The student will apply knowledge of word origins, derivations, and figurative language to extend vocabulary development in authentic texts."},
    {"subject": "ELA", "grade": "9-12", "code": "10.3", "strand": "Reading",
     "text": "The student will read, comprehend, and analyze literary texts of different cultures and eras. a) Identify main and supporting ideas. b) Make predictions, draw inferences, and connect prior knowledge to support reading comprehension."},
    {"subject": "ELA", "grade": "9-12", "code": "11.3", "strand": "Reading",
     "text": "The student will read and analyze relationships among American literature, history, and culture. a) Describe contributions of different cultures to the development of American literature."},
    # --- Math ---
    {"subject": "Math", "grade": "K", "code": "K.1", "strand": "Number and Number Sense",
     "text": "The student will a) tell how many are in a given set of 20 or fewer objects by counting; b) read, write, and represent numbers from 0 through 20."},
    {"subject": "Math", "grade": "1", "code": "1.1", "strand": "Number and Number Sense",
     "text": "The student will a) count from 0 to 110 by 1s and from 0 to 110 by various multiples; b) read and write numerals 0 through 110."},
    {"subject": "Math", "grade": "2", "code": "2.1", "strand": "Number and Number Sense",
     "text": "The student will a) read, write, and identify the place and value of each digit in a three-digit numeral; b) identify the number that is 10 more, 10 less, 100 more, or 100 less than a given number up to 999."},
    {"subject": "Math", "grade": "3", "code": "3.2", "strand": "Number and Number Sense",
     "text": "The student will recognize and use the inverse relationships between addition/subtraction and multiplication/division to complete basic fact sentences."},
    {"subject": "Math", "grade": "4", "code": "4.4", "strand": "Computation and Estimation",
     "text": "The student will a) demonstrate fluency with multiplication facts through 12 x 12, and the corresponding division facts; b) estimate and determine sums, differences, and products of whole numbers."},
    {"subject": "Math", "grade": "5", "code": "5.4", "strand": "Computation and Estimation",
     "text": "The student will create and solve single-step and multistep practical problems involving addition, subtraction, multiplication, and division of whole numbers."},
    {"subject": "Math", "grade": "6-8", "code": "6.6", "strand": "Computation and Estimation",
     "text": "The student will a) add, subtract, multiply, and divide integers; b) solve practical problems involving operations with integers."},
    {"subject": "Math", "grade": "6-8", "code": "7.1", "strand": "Number and Number Sense",
     "text": "The student will investigate and describe the concept of negative exponents for powers of ten; compare and order numbers greater than zero written in scientific notation."},
    {"subject": "Math", "grade": "9-12", "code": "A.1", "strand": "Expressions and Operations",
     "text": "The student will a) represent verbal quantitative situations algebraically; b) evaluate algebraic expressions for given replacement values of the variables."},
    # --- Science ---
    {"subject": "Science", "grade": "3", "code": "3.1", "strand": "Scientific and Engineering Practices",
     "text": "The student will demonstrate an understanding of scientific and engineering practices by a) asking questions and defining problems; b) planning and carrying out investigations."},
    {"subject": "Science", "grade": "5", "code": "5.5", "strand": "Earth and Space Systems",
     "text": "The student will investigate and understand that the ocean environment has geological, physical, and biological characteristics."},
    {"subject": "Science", "grade": "6-8", "code": "LS.2", "strand": "Life Science",
     "text": "The student will investigate and understand that organisms can be classified based on shared characteristics. Key ideas include organism classification systems."},
    # --- History/Social Studies ---
    {"subject": "History", "grade": "3", "code": "VS.1", "strand": "Virginia Studies",
     "text": "The student will demonstrate skills for historical thinking, geographical analysis, economic decision making, and responsible citizenship by a) analyzing artifacts and primary/secondary sources."},
    {"subject": "History", "grade": "6-8", "code": "USI.1", "strand": "US History to 1865",
     "text": "The student will demonstrate skills for historical thinking, geographical analysis, economic decision making, and responsible citizenship."},
    {"subject": "History", "grade": "9-12", "code": "VUS.1", "strand": "Virginia and US History",
     "text": "The student will demonstrate skills for historical thinking, geographical analysis, economic decision making, and responsible citizenship by a) analyzing evidence from primary and secondary sources."},
]

# ---------------------------------------------------------------------------
# WIDA Can-Do Descriptors — by proficiency level and language domain
# ---------------------------------------------------------------------------
WIDA_DESCRIPTORS: list[dict] = [
    # Listening
    {"level": 1, "domain": "Listening", "grade_band": "K-12",
     "descriptor": "Process recurrent words/phrases, general meaning from visual and graphic support, simple commands/statements with visual support."},
    {"level": 2, "domain": "Listening", "grade_band": "K-12",
     "descriptor": "Process key words/phrases in context, main ideas from short oral texts with visual support, multi-step directions with visual support."},
    {"level": 3, "domain": "Listening", "grade_band": "K-12",
     "descriptor": "Process main ideas and some details from oral text, multi-step directions, academic vocabulary in context."},
    {"level": 4, "domain": "Listening", "grade_band": "K-12",
     "descriptor": "Process main ideas and detailed information from oral text, academic discussions, implied meaning from oral discourse."},
    {"level": 5, "domain": "Listening", "grade_band": "K-12",
     "descriptor": "Process grade-level oral text with technical and abstract content, make inferences from oral discourse, interpret speaker's intent."},
    {"level": 6, "domain": "Listening", "grade_band": "K-12",
     "descriptor": "Process oral language at a level comparable to English-proficient peers across all content areas."},
    # Speaking
    {"level": 1, "domain": "Speaking", "grade_band": "K-12",
     "descriptor": "Produce words/phrases, answer WH- questions with single words, name objects/people/pictures, repeat simple sentences."},
    {"level": 2, "domain": "Speaking", "grade_band": "K-12",
     "descriptor": "Produce phrases/short sentences, answer questions with phrases, describe objects/people, retell short narratives."},
    {"level": 3, "domain": "Speaking", "grade_band": "K-12",
     "descriptor": "Produce related sentences, give brief oral presentations, compare/contrast, express opinions with reasons."},
    {"level": 4, "domain": "Speaking", "grade_band": "K-12",
     "descriptor": "Produce connected discourse, explain processes, support ideas with examples, engage in academic discussions."},
    {"level": 5, "domain": "Speaking", "grade_band": "K-12",
     "descriptor": "Produce extended discourse, debate and defend positions, use technical vocabulary, adjust register appropriately."},
    {"level": 6, "domain": "Speaking", "grade_band": "K-12",
     "descriptor": "Produce oral language comparable to English-proficient peers across content areas."},
    # Reading
    {"level": 1, "domain": "Reading", "grade_band": "K-12",
     "descriptor": "Process meaning from environmental print, high-frequency words, phrases with visual/graphic support, patterned text."},
    {"level": 2, "domain": "Reading", "grade_band": "K-12",
     "descriptor": "Process main ideas from illustrated text, sequence events, follow written multi-step directions with visual support."},
    {"level": 3, "domain": "Reading", "grade_band": "K-12",
     "descriptor": "Process main ideas and some details from grade-level text, make inferences from text with visual support, identify text features."},
    {"level": 4, "domain": "Reading", "grade_band": "K-12",
     "descriptor": "Process detailed information from grade-level text, make inferences and predictions, interpret meaning of figurative language."},
    {"level": 5, "domain": "Reading", "grade_band": "K-12",
     "descriptor": "Process grade-level text with technical and abstract content, make complex inferences, analyze author's purpose and craft."},
    {"level": 6, "domain": "Reading", "grade_band": "K-12",
     "descriptor": "Process text at a level comparable to English-proficient peers across content areas."},
    # Writing
    {"level": 1, "domain": "Writing", "grade_band": "K-12",
     "descriptor": "Produce labels, lists, copied words/phrases, high-frequency words related to content, simple patterned sentences."},
    {"level": 2, "domain": "Writing", "grade_band": "K-12",
     "descriptor": "Produce phrases and short sentences, complete graphic organizers, respond to questions in writing with phrases."},
    {"level": 3, "domain": "Writing", "grade_band": "K-12",
     "descriptor": "Produce related sentences, summaries of content-area material, compare/contrast in writing, simple paragraphs."},
    {"level": 4, "domain": "Writing", "grade_band": "K-12",
     "descriptor": "Produce organized paragraphs, content-area reports, essays with main idea and supporting details, edit for conventions."},
    {"level": 5, "domain": "Writing", "grade_band": "K-12",
     "descriptor": "Produce extended writing, research-based content, multiple genres, use technical vocabulary precisely."},
    {"level": 6, "domain": "Writing", "grade_band": "K-12",
     "descriptor": "Produce writing comparable to English-proficient peers across content areas."},
]


def search_standards(
    query: str,
    subject: str = "",
    grade: str = "",
) -> list[dict]:
    """Search Virginia SOLs by keyword, subject, and/or grade.

    Returns matching standards sorted by relevance (simple keyword match).
    """
    query_lower = query.lower()
    keywords = query_lower.split()
    results = []

    for sol in VA_SOLS:
        # Filter by subject if specified
        if subject and subject.lower() not in sol["subject"].lower():
            continue
        # Filter by grade if specified
        if grade and grade.lower() not in sol["grade"].lower():
            continue

        # Score by keyword overlap
        searchable = f"{sol['code']} {sol['strand']} {sol['text']}".lower()
        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            results.append({**sol, "_score": score})

    results.sort(key=lambda x: x["_score"], reverse=True)
    # Strip internal score
    for r in results:
        r.pop("_score", None)
    return results[:10]


def search_wida(
    level: int = 0,
    domain: str = "",
    grade_band: str = "",
) -> list[dict]:
    """Search WIDA Can-Do descriptors by proficiency level and/or domain.

    level=0 returns all levels. domain="" returns all domains.
    """
    results = []
    for desc in WIDA_DESCRIPTORS:
        if level and desc["level"] != level:
            continue
        if domain and domain.lower() not in desc["domain"].lower():
            continue
        if grade_band and grade_band not in desc["grade_band"]:
            continue
        results.append(desc)
    return results


# Tool definitions for Claude API tool_use
TOOLS = [
    {
        "name": "search_standards",
        "description": (
            "Search Virginia Standards of Learning (SOLs) by keyword, subject, "
            "and grade level. Returns matching standards with code, strand, and "
            "full text. Use this when aligning lessons to state standards."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search for (e.g. 'reading comprehension', 'fractions', 'scientific method').",
                },
                "subject": {
                    "type": "string",
                    "description": "Filter by subject: ELA, Math, Science, History. Leave empty for all.",
                },
                "grade": {
                    "type": "string",
                    "description": "Filter by grade level (e.g. '3', '6-8', '9-12', 'K'). Leave empty for all.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_wida",
        "description": (
            "Look up WIDA Can-Do descriptors by proficiency level (1-6) and "
            "language domain (Listening, Speaking, Reading, Writing). Use this "
            "when designing language objectives or differentiation strategies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "WIDA proficiency level 1-6. Use 0 for all levels.",
                },
                "domain": {
                    "type": "string",
                    "description": "Language domain: Listening, Speaking, Reading, or Writing. Leave empty for all.",
                },
                "grade_band": {
                    "type": "string",
                    "description": "Optional grade band filter (for current data this is typically 'K-12').",
                },
            },
        },
    },
]


def handle_tool_call(name: str, input_data: dict) -> str:
    """Execute a standards tool call and return the result as a string."""
    if name == "search_standards":
        results = search_standards(
            query=input_data["query"],
            subject=input_data.get("subject", ""),
            grade=input_data.get("grade", ""),
        )
        if not results:
            return "No matching Virginia SOLs found. Try broader keywords or a different grade band."
        lines = []
        for r in results:
            lines.append(f"**{r['code']}** ({r['subject']}, Grade {r['grade']}) — {r['strand']}")
            lines.append(f"  {r['text']}\n")
        return "\n".join(lines)

    if name == "search_wida":
        results = search_wida(
            level=input_data.get("level", 0),
            domain=input_data.get("domain", ""),
            grade_band=input_data.get("grade_band", ""),
        )
        if not results:
            return "No matching WIDA descriptors found."
        lines = []
        for r in results:
            lines.append(f"**Level {r['level']} — {r['domain']}**: {r['descriptor']}")
        return "\n".join(lines)

    return f"Unknown standards tool: {name}"
