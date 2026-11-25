import re

SKILL_ALIASES: dict[str, list[str]] = {
    # Programming Languages
    "python": ["py", "python3"],
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "java": [],
    "c++": ["cpp"],
    "c#": ["csharp"],
    "golang": ["go lang"],
    "rust": [],
    "ruby": [],
    "php": [],
    "swift": [],
    "kotlin": [],
    "scala": [],
    "dart": [],
    "bash": ["shell scripting", "shell"],
    "powershell": [],
    "sql": [],
    "html": ["html5"],
    "css": ["css3"],
    "matlab": [],
    "elixir": [],
    "haskell": [],
    "perl": [],
    "lua": [],
    "groovy": [],
    "solidity": [],
    "assembly": [],

    # Web Frontend
    "react": ["reactjs", "react.js"],
    "next.js": ["nextjs"],
    "vue.js": ["vue", "vuejs"],
    "nuxt.js": ["nuxtjs"],
    "angular": ["angularjs"],
    "svelte": ["sveltekit"],
    "tailwind css": ["tailwindcss", "tailwind"],
    "bootstrap": [],
    "redux": [],
    "webpack": [],
    "vite": [],
    "sass": ["scss"],
    "jquery": [],
    "webassembly": ["wasm"],

    # Web Backend & APIs
    "node.js": ["node", "nodejs"],
    "express": ["expressjs", "express.js"],
    "fastapi": [],
    "django": [],
    "flask": [],
    "spring boot": ["springboot"],
    "spring": [],
    "asp.net": [".net", "dotnet"],
    "ruby on rails": ["rails"],
    "laravel": [],
    "nest.js": ["nestjs"],
    "graphql": [],
    "rest api": ["restful", "rest apis", "rest"],
    "grpc": [],
    "websockets": ["websocket"],
    "oauth": ["oauth2"],
    "jwt": ["json web token"],

    # Mobile
    "react native": [],
    "flutter": [],
    "android": [],
    "ios": [],
    "swiftui": [],
    "jetpack compose": [],

    # Databases & Caching
    "postgresql": ["postgres"],
    "mysql": [],
    "sqlite": [],
    "mongodb": ["mongo"],
    "redis": [],
    "elasticsearch": [],
    "cassandra": [],
    "dynamodb": [],
    "oracle": ["pl/sql"],
    "sql server": ["mssql", "t-sql"],
    "mariadb": [],
    "neo4j": [],
    "firebase": ["firestore"],
    "supabase": [],
    "prisma": [],
    "sqlalchemy": [],

    # Cloud & DevOps
    "aws": ["amazon web services"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure"],
    "docker": [],
    "kubernetes": ["k8s"],
    "terraform": [],
    "ansible": [],
    "ci/cd": ["cicd"],
    "github actions": [],
    "jenkins": [],
    "gitlab ci": [],
    "linux": ["ubuntu", "debian"],
    "nginx": [],
    "apache": [],
    "helm": [],
    "prometheus": [],
    "grafana": [],
    "datadog": [],
    "serverless": ["aws lambda"],
    "cloudflare": [],
    "vercel": [],
    "git": [],
    "github": [],
    "gitlab": [],

    # Data Engineering & Big Data
    "apache spark": ["pyspark", "spark"],
    "apache kafka": ["kafka"],
    "airflow": ["apache airflow"],
    "dbt": [],
    "snowflake": [],
    "bigquery": [],
    "redshift": [],
    "hadoop": [],
    "etl": [],
    "databricks": [],

    # Data Science, ML & AI
    "pytorch": [],
    "tensorflow": ["tf"],
    "keras": [],
    "scikit-learn": ["sklearn"],
    "pandas": [],
    "numpy": [],
    "scipy": [],
    "matplotlib": [],
    "seaborn": [],
    "xgboost": [],
    "lightgbm": [],
    "nlp": ["natural language processing"],
    "llm": ["llms", "large language models", "large language model"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "langchain": [],
    "llamaindex": [],
    "hugging face": ["huggingface", "transformers"],
    "computer vision": ["opencv"],
    "openai": [],
    "mlops": [],
    "mlflow": [],
    "vector database": ["pinecone", "faiss", "qdrant", "chromadb", "milvus"],
    "deep learning": [],
    "machine learning": [],
    "reinforcement learning": [],
    "fine-tuning": ["fine tuning", "lora"],
    "prompt engineering": [],
    "mcp": ["model context protocol"],

    # Testing, Architecture & Tools
    "pytest": [],
    "jest": [],
    "cypress": [],
    "playwright": [],
    "selenium": [],
    "junit": [],
    "unit testing": [],
    "microservices": [],
    "system design": [],
    "distributed systems": [],
    "agile": ["scrum"],
    "jira": [],
    "figma": [],
    "rabbitmq": [],
    "celery": [],
}


def _compile_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for canonical, aliases in SKILL_ALIASES.items():
        terms = [canonical, *aliases]
        # Sort longest-first so multi-word or punctuated forms match cleanly
        terms.sort(key=len, reverse=True)
        dot_terms = [re.escape(t) for t in terms if t.startswith(".")]
        std_terms = [re.escape(t) for t in terms if not t.startswith(".")]

        parts: list[str] = []
        if std_terms:
            parts.append(rf"(?<![a-z0-9_.])(?:{'|'.join(std_terms)})(?![a-z0-9_+#])")
        if dot_terms:
            parts.append(rf"(?<![a-z0-9_])(?:{'|'.join(dot_terms)})(?![a-z0-9_+#])")

        regex = re.compile("|".join(parts), re.IGNORECASE)
        patterns.append((canonical, regex))
    return patterns


_COMPILED_SKILL_PATTERNS = _compile_patterns()


def find_skills(text: str) -> set[str]:
    """Return the set of canonical tech skills mentioned in text."""
    if not text:
        return set()
    found: set[str] = set()
    for canonical, pattern in _COMPILED_SKILL_PATTERNS:
        if pattern.search(text):
            found.add(canonical)
    return found
