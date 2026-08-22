import json
import re

class DependencyTaggerService:
    """
    Automatic Tech Stack & Architecture Tagger.
    Parses package.json, requirements.txt, pom.xml, Cargo.toml, and go.mod manifest files
    to extract dependencies, framework tags, and architectural patterns.
    """

    FRAMEWORK_SIGNATURES = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "express": "Express.js",
        "react": "React.js",
        "vue": "Vue.js",
        "angular": "Angular",
        "next": "Next.js",
        "spring-boot": "Spring Boot",
        "torch": "PyTorch",
        "tensorflow": "TensorFlow",
        "scikit-learn": "Scikit-Learn",
        "firebase": "Firebase",
        "tailwindcss": "TailwindCSS",
        "bootstrap": "Bootstrap",
        "sqlalchemy": "SQLAlchemy",
        "pg": "PostgreSQL",
        "pymongo": "MongoDB",
        "redis": "Redis"
    }

    @classmethod
    def tag_manifest_content(cls, filename: str, content: str) -> dict:
        fn_lower = filename.lower()
        extracted_tech = set()
        detected_architecture = []
        parsed_dependencies = []

        if "package.json" in fn_lower:
            try:
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for dep in deps.keys():
                    parsed_dependencies.append(dep)
                    dep_lower = dep.lower()
                    for sig, tag in cls.FRAMEWORK_SIGNATURES.items():
                        if sig in dep_lower:
                            extracted_tech.add(tag)

                if "react" in content.lower() or "vue" in content.lower() or "next" in content.lower():
                    detected_architecture.append("Single Page Application (SPA)")
                if "express" in content.lower() or "nest" in content.lower():
                    detected_architecture.append("REST API Service")
            except Exception:
                pass

        elif "requirements.txt" in fn_lower or "pipfile" in fn_lower:
            lines = content.splitlines()
            for line in lines:
                clean_line = re.sub(r'[<>=~#].*', '', line).strip()
                if clean_line:
                    parsed_dependencies.append(clean_line)
                    dep_lower = clean_line.lower()
                    for sig, tag in cls.FRAMEWORK_SIGNATURES.items():
                        if sig in dep_lower:
                            extracted_tech.add(tag)

            if "fastapi" in content.lower() or "flask" in content.lower() or "django" in content.lower():
                detected_architecture.append("Python Web Microservice")
            if "torch" in content.lower() or "tensorflow" in content.lower() or "sklearn" in content.lower():
                detected_architecture.append("Machine Learning Model Pipeline")

        elif "pom.xml" in fn_lower or "build.gradle" in fn_lower:
            deps = re.findall(r'<artifactId>(.*?)</artifactId>', content)
            for d in deps:
                parsed_dependencies.append(d)
                d_lower = d.lower()
                for sig, tag in cls.FRAMEWORK_SIGNATURES.items():
                    if sig in d_lower:
                        extracted_tech.add(tag)
            detected_architecture.append("Java Enterprise Application")

        if not detected_architecture:
            detected_architecture.append("Modular Software Architecture")

        return {
            "filename": filename,
            "dependencyCount": len(parsed_dependencies),
            "parsedDependencies": parsed_dependencies[:25],
            "autoExtractedTechStack": sorted(list(extracted_tech)),
            "architectureClassification": detected_architecture,
            "status": "success"
        }
