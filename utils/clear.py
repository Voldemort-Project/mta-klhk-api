def clear_markdown(text: str) -> str:
    return text.replace("```markdown", "").replace("```", "").strip()
