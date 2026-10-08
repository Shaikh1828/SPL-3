"""
Script to generate benchmark sample archery videos.
Usage: python -m scripts.generate_sample_videos
"""
import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.kinematic_video_generator import KinematicVideoGenerator

def main():
    print("Generating Archer Kinematic Benchmark Videos...")
    generator = KinematicVideoGenerator(output_dir="storage/sample_videos")
    results = generator.generate_all_samples()
    print(f"Successfully generated {len(results)} videos:")
    for r in results:
        print(f" - [{r['video_id']}] {r['title']} -> {r['file_path']} (Target Score: {r['target_score']})")

if __name__ == "__main__":
    main()
