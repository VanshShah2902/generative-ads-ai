import os
import sys

# Add root to path for imports
sys.path.append(os.getcwd())

from src.generation.prompt_assembler import PromptAssembler
from src.generation.image_generator import ImageGenerator
from src.composition.assembly_engine import AssemblyEngine

def run_pipeline():
    print("--- Starting Generation & Composition Pipeline ---")
    
    # 1. Assemble Prompt
    assembler = PromptAssembler()
    assembler.assemble_prompt()
    
    # 2. Generate Scene
    generator = ImageGenerator()
    generator.generate_scene()
    
    # 3. Assemble Ad
    engine = AssemblyEngine()
    engine.assemble_ad()
    
    print("--- Generation Pipeline Complete ---")

if __name__ == "__main__":
    run_pipeline()
