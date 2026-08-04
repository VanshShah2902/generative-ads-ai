import random

class CreativeStrategyBuilder:
    def build(self, payload: dict, cluster: str) -> dict:
        """
        Generates creative strategy based on cluster type.
        """
        from src.config.config_loader import load_emotions
        EMOTION_CONFIG = load_emotions()
        print("[Config] Emotions Loaded:", EMOTION_CONFIG.keys())

        emotions = EMOTION_CONFIG.get(cluster, ["neutral"])
        emotion = random.choice(emotions)

        palette = {
            "primary": "green",
            "secondary": "white",
            "accent": random.choice(["light green", "dark green", "soft green gradient"])
        }

        FONT_MAP = {
            "panic": "ragged distressed bold font",
            "fear": "sharp edgy font",
            "stress": "rough handwritten font",
            "relief": "soft rounded font",
            "calm": "elegant serif font",
            "confidence": "clean modern sans-serif",
            "hope": "smooth minimal font",
            "neutral": "clean readable sans-serif"
        }

        font_style = FONT_MAP.get(emotion, "clean sans-serif")

        if emotion in ["panic", "fear", "stress"]:
            headline_tone = "urgent"
        elif emotion in ["relief", "calm"]:
            headline_tone = "soothing"
        else:
            headline_tone = "informative"

        print("[CreativeStrategy]", {
            "cluster": cluster,
            "emotion": emotion,
            "font": font_style
        })

        return {
            "emotion": emotion,
            "color_palette": palette,
            "font_style": font_style,
            "headline_tone": headline_tone
        }
