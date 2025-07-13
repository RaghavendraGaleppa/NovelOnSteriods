**Objective:**
Translate specific fields from a Chinese JSON input string to English and return a valid JSON output string.

**Instructions:**
1.  **Parse the Input:** You will be given a JSON object as a string.
2.  **Identify Target Fields:** Focus exclusively on these five keys: `title_raw`, `author_raw`, `description_raw`, `classification_raw`, and `tags_raw`.
3.  **Translate to English:**
    * Translate the string value of each target key from Chinese to natural-sounding English.
    * If a value is a list of strings (like `tags_raw`), translate each string within the list individually.
    * Clean up any extraneous whitespace, newlines, or special characters (like `\u3000` or `\xa0`) from the source strings before translation.
4.  **Format the Output:**
    * The output must be **only** a valid JSON object.
    * The output JSON should contain *only* the translated keys listed above. Do not include any other keys from the original input.
    * Preserve the original data types. A translated list of strings should remain a list of strings. An empty list should remain an empty list.
    * Do not add any explanations, comments, or markdown formatting (like ```json ... ```) to your response.

**Input JSON:**
```json
{input_json}
```

**Translate now.**