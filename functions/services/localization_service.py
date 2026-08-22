class LocalizationEngine:
    """
    Multi-Language Search Localization Engine supporting:
    English (en), Hindi (hi), Spanish (es), French (fr), German (de).
    """

    TRANSLATION_DICTIONARY = {
        "hi": {
            "projects": "परियोजनाएं",
            "students": "छात्र",
            "search": "खोजें",
            "verified": "सत्यापित",
            "trust_score": "विश्वास स्कोर",
            "python": "पायथन",
            "artificial intelligence": "कृत्रिम बुद्धिमत्ता",
            "web development": "वेब विकास",
            "software": "सॉफ्टवेयर",
            "welcome": "डिजीइंडिया नवाचार मंच में आपका स्वागत है"
        },
        "es": {
            "projects": "Proyectos",
            "students": "Estudiantes",
            "search": "Buscar",
            "verified": "Verificado",
            "trust_score": "Puntuación de Confianza",
            "python": "Python",
            "artificial intelligence": "Inteligencia Artificial",
            "web development": "Desarrollo Web",
            "software": "Software",
            "welcome": "Bienvenido a la Plataforma de Innovación DigiIndia"
        },
        "fr": {
            "projects": "Projets",
            "students": "Étudiants",
            "search": "Rechercher",
            "verified": "Vérifié",
            "trust_score": "Score de Confiance",
            "python": "Python",
            "artificial intelligence": "Intelligence Artificielle",
            "web development": "Développement Web",
            "software": "Logiciel",
            "welcome": "Bienvenue sur la plateforme d'innovation DigiIndia"
        },
        "de": {
            "projects": "Projekte",
            "students": "Studenten",
            "search": "Suchen",
            "verified": "Verifiziert",
            "trust_score": "Vertrauenswert",
            "python": "Python",
            "artificial intelligence": "Künstliche Intelligenz",
            "web development": "Webentwicklung",
            "software": "Software",
            "welcome": "Willkommen auf der DigiIndia Innovationsplattform"
        }
    }

    @classmethod
    def translate_query(cls, text: str, target_lang: str = "en") -> str:
        if not text or target_lang == "en" or target_lang not in cls.TRANSLATION_DICTIONARY:
            return text

        dict_lang = cls.TRANSLATION_DICTIONARY[target_lang]
        text_lower = text.lower().strip()

        # Reverse lookup translation
        for en_key, localized_val in dict_lang.items():
            if localized_val.lower() == text_lower:
                return en_key

        return text

    @classmethod
    def translate_summary(cls, text: str, target_lang: str = "en") -> str:
        if not text or target_lang == "en" or target_lang not in cls.TRANSLATION_DICTIONARY:
            return text

        dict_lang = cls.TRANSLATION_DICTIONARY[target_lang]
        translated = text
        for en_key, localized_val in dict_lang.items():
            translated = translated.replace(en_key, localized_val)

        return translated
